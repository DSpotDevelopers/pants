# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Prints the targets qualification runs: the change's selection, within the qualified scope.

The scope is the parts of Pants the company uses (dspot_qualification_scope.toml names its backends): the folders holding
code that Pants loads when it runs with those backends, from its entry code and the backends' register modules, plus
those Pants always loads. Pants itself computes that closure (`dependencies --transitive`). A target under
src/python/pants/ is in scope when its folder is in the closure, so a feature none of them loads (Docker environments'
backend, remote execution's Buildbarn tests, the JVM) falls outside by itself. Every target outside src/python/pants/
(the fork's own CI, build-support) is in scope.

Within those suites, the contract is the environment kinds the scope names (environment_targets): a test cell whose
processes run in a Pants environment of another kind (a docker_environment needs a Docker daemon, a remote_environment
a remote execution service) tests a feature none of the company's runs use. Pants' own target types name the kinds. A
cell runs in an environment when its RuleRunner's inherent_environment, or a target's `environment` field, names it, and
`--environments-preview-names` maps that name to the environment's target; a cell that only declares environments, to
choose among them, runs in none. The cell's source is read with the module's helpers and fixtures it calls, the helpers'
branches on the literal arguments it passes. Such a cell is left out (pytest's --deselect) and printed as outside the
qualified contract, never counted as passing.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path

SCOPE = Path(__file__).with_name("dspot_qualification_scope.toml")
PANTS = "src/python/pants/"
# Pants' entry code, what every run loads before any backend: the module pants_loader.py runs. Never a target of bin's
# folder: pants_loader's depends on `:plugins`, every backend the release PEX ships, and bin's other target holds the
# folder's tests, whose integration helpers reach pants_loader again through pants/__main__.py
ENTRY = "src/python/pants/bin/pants_runner.py"
# Pants' environment target types, whose aliases are the environment kinds
ENVIRONMENT_TARGET_TYPES = Path("src/python/pants/core/environments/target_types.py")
# The backends every Pants run loads (pants/init/extension_loader.py, load_build_configuration_from_source).
ALWAYS_LOADED = ("pants.core", "pants.backend.project_info")

Pants = Callable[..., list[str]]


def scope() -> dict:
    return tomllib.loads(SCOPE.read_text())


def register_module(backend: str) -> str:
    return f"src/python/{backend.replace('.', '/')}/register.py"


def directory(address: str) -> str:
    # A file address names a file with a suffix; no directory under src/python/pants has a dot.
    path = address.split(":", 1)[0].split("#", 1)[0]
    return path.rsplit("/", 1)[0] if "." in path.rsplit("/", 1)[-1] else path


def scope_directories(pants: Pants, backends: Iterable[str]) -> set[str]:
    roots = [ENTRY, *(register_module(b) for b in (*ALWAYS_LOADED, *backends))]
    loaded = [*roots, *pants("dependencies", "--transitive", *roots)]
    return {directory(a) for a in loaded if a.startswith(PANTS)}


def in_scope(address: str, directories: set[str]) -> bool:
    return not address.startswith(PANTS) or directory(address) in directories


def selection(pants: Pants, base: str) -> tuple[list[str], list[str]]:
    """The change's selection, split into the qualified targets and those outside the scope."""
    directories = scope_directories(pants, scope()["backend_packages"])
    changed = pants(f"--changed-since={base}", "--changed-dependents=direct", "list")
    return (
        [a for a in changed if in_scope(a, directories)],
        [a for a in changed if not in_scope(a, directories)],
    )


def environment_kinds(target_types: str) -> set[str]:
    """The aliases of the environment target types in Pants' target_types.py source."""
    kinds = set()
    for node in ast.parse(target_types).body:
        if isinstance(node, ast.ClassDef) and any(ast.unparse(b) == "Target" for b in node.bases):
            for statement in node.body:
                match statement:
                    case ast.Assign(
                        targets=[ast.Name("alias")], value=ast.Constant(str(alias))
                    ) if alias.endswith("_environment"):
                        kinds.add(alias)
    return kinds


class _Branches(ast.NodeTransformer):
    """A helper's body with its branches on a parameter the call binds to a literal resolved."""

    def __init__(self, bound: dict[str, bool]) -> None:
        self.bound = bound

    def _taken(self, test: ast.expr) -> bool | None:
        match test:
            case ast.Name(name) if name in self.bound:
                return self.bound[name]
            case ast.UnaryOp(ast.Not(), ast.Name(name)) if name in self.bound:
                return not self.bound[name]
        return None

    def visit_If(self, node: ast.If):
        taken = self._taken(node.test)
        if taken is None:
            return self.generic_visit(node)
        kept = [self.visit(n) for n in (node.body if taken else node.orelse)]
        return [n for k in kept for n in (k if isinstance(k, list) else [k])]

    def visit_IfExp(self, node: ast.IfExp):
        taken = self._taken(node.test)
        if taken is None:
            return self.generic_visit(node)
        return self.visit(node.body if taken else node.orelse)


def _bound(function: ast.FunctionDef, call: ast.Call) -> dict[str, bool]:
    names = [a.arg for a in function.args.args]
    pairs = [*zip(names, call.args), *((k.arg, k.value) for k in call.keywords)]
    return {n: bool(v.value) for n, v in pairs if isinstance(v, ast.Constant)}


def _reached(cell: ast.FunctionDef, functions: dict[str, ast.FunctionDef]) -> list[ast.AST]:
    """The cell's code with the module's functions it calls or takes as fixtures."""
    code: list[ast.AST] = [cell]
    seen = {cell.name}
    for fixture in (a.arg for a in cell.args.args):
        if fixture in functions and fixture not in seen:
            seen.add(fixture)
            code.append(functions[fixture])
    for node in code:
        for call in [n for n in ast.walk(node) if isinstance(n, ast.Call)]:
            match call.func:
                case ast.Name(name) if name in functions and name not in seen:
                    seen.add(name)
                    helper = functions[name]
                    code.append(_Branches(_bound(helper, call)).visit(_copy(helper)))
    return code


def _copy(function: ast.FunctionDef) -> ast.FunctionDef:
    return ast.parse(ast.unparse(function)).body[0]


def _strings(code: list[ast.AST]) -> str:
    strings = []
    for node in (n for c in code for n in ast.walk(c)):
        if isinstance(node, ast.JoinedStr):
            strings.append("".join(v.value for v in node.values if isinstance(v, ast.Constant)))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return "\n".join(strings)


def runs_outside(
    cell: ast.FunctionDef, functions: dict[str, ast.FunctionDef], kinds: set[str]
) -> bool:
    """Whether a process of the cell runs in an environment of one of `kinds`."""
    code = _reached(cell, functions)
    text = _strings(code)
    run_in = set(re.findall(r"\benvironment\s*=\s*['\"]([\w.-]+)['\"]", text))
    for node in (n for c in code for n in ast.walk(c)):
        if isinstance(node, ast.keyword) and node.arg == "inherent_environment":
            for call in (n for n in ast.walk(node.value) if isinstance(n, ast.Call)):
                match call:
                    case ast.Call(ast.Name("EnvironmentName"), [ast.Constant(str(name))]):
                        run_in.add(name)
    declared = {
        name
        for arguments in re.findall(r"\b(?:%s)\(([^()]*)\)" % "|".join(sorted(kinds)), text)
        for name in re.findall(r"\bname\s*=\s*['\"]([\w.-]+)['\"]", arguments)
    }
    names = {
        name: target
        for mapping in re.findall(r"environments-preview-names=(\{[^}]*\})", text)
        for name, target in re.findall(
            r"['\"]([\w.-]+)['\"]\s*:\s*['\"][^'\"]*:([\w.-]+)['\"]", mapping
        )
    }
    return any(names.get(name) in declared for name in run_in)


def cells_of(tree: ast.Module) -> list[tuple[str, ast.FunctionDef]]:
    """A test module's cells as pytest names them: `test_x`, and `TestY::test_x` for a method."""
    cells = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            cells.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            cells.extend(
                (f"{node.name}::{f.name}", f) for f in node.body if isinstance(f, ast.FunctionDef)
            )
    return [(name, fn) for name, fn in cells if fn.name.startswith("test")]


def _test_files(selected: Iterable[str]) -> list[str]:
    files = []
    for address in selected:
        path = address.split(":", 1)[0].split("#", 1)[0]
        candidates = sorted(Path(path).glob("*.py")) if Path(path).is_dir() else [Path(path)]
        files.extend(
            str(f)
            for f in candidates
            if f.suffix == ".py" and (f.name.startswith("test_") or f.name.endswith("_test.py"))
        )
    return list(dict.fromkeys(files))


def unqualified_cells(selected: Iterable[str], kinds: set[str]) -> list[str]:
    """The pytest node ids of the selected test files' cells whose processes run in an environment of `kinds`."""
    cells = []
    for path in _test_files(a for a in selected if a.startswith(PANTS)):
        tree = ast.parse(Path(path).read_text())
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        cells.extend(
            f"{path}::{name}" for name, fn in cells_of(tree) if runs_outside(fn, functions, kinds)
        )
    return cells


def kinds_outside_the_contract() -> set[str]:
    kinds = environment_kinds(ENVIRONMENT_TARGET_TYPES.read_text())
    qualified = set(scope()["environment_targets"])
    if not qualified <= kinds:
        raise SystemExit(
            f"the scope names environments Pants does not have: {sorted(qualified - kinds)}"
        )
    return kinds - qualified


def pytest_args(cells: Iterable[str]) -> str:
    """`--pytest-args` fromfile content: deselecting the cells, appended to the configured args."""
    return "+" + json.dumps([f"--deselect={cell}" for cell in cells])


def run_pants(*args: str) -> list[str]:
    out = subprocess.run(["./pants", *args], check=True, stdout=subprocess.PIPE, text=True).stdout
    return [line for line in out.splitlines() if line]


def main(argv: list[str]) -> int:
    base, outside_cells = argv
    qualified, outside = selection(run_pants, base)
    for address in outside:
        print(f"outside the qualified scope: {address}", file=sys.stderr)
    cells = unqualified_cells(qualified, kinds_outside_the_contract())
    for cell in cells:
        print(f"outside the qualified contract (its environment kind): {cell}", file=sys.stderr)
    Path(outside_cells).write_text(pytest_args(cells))
    print("\n".join(qualified))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
