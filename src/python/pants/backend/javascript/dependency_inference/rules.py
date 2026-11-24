# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

import itertools
import logging
import os.path
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePath

from pants.backend.javascript import package_json
from pants.backend.javascript.package_json import (
    FirstPartyNodePackageTargets,
    NodePackageDependenciesField,
    NodePackageNameField,
    OwningNodePackage,
    OwningNodePackageRequest,
    PackageJsonImports,
    PackageJsonSourceField,
    find_owning_package,
    script_entrypoints_for_source,
    subpath_imports_for_source,
)
from pants.backend.javascript.subsystems.nodejs_infer import NodeJSInfer
from pants.backend.javascript.target_types import (
    JS_FILE_EXTENSIONS,
    JSRuntimeDependenciesField,
    JSRuntimeSourceField,
)
from pants.backend.jsx.target_types import JSX_FILE_EXTENSIONS
from pants.backend.tsx.target_types import TSX_FILE_EXTENSIONS
from pants.backend.typescript import tsconfig
from pants.backend.typescript.target_types import TS_FILE_EXTENSIONS
from pants.backend.typescript.tsconfig import ParentTSConfigRequest, TSConfig, find_parent_ts_config
from pants.build_graph.address import Address
from pants.core.target_types import AssetSourceField
from pants.core.util_rules.unowned_dependency_behavior import (
    UnownedDependencyError,
    UnownedDependencyUsage,
)
from pants.engine.addresses import Addresses
from pants.engine.fs import PathGlobs
from pants.engine.internals.graph import (
    OwnersRequest,
    find_owners,
    hydrate_sources,
    resolve_targets,
)
from pants.engine.internals.native_dep_inference import JavascriptDependencyCandidate
from pants.engine.internals.native_engine import InferenceMetadata, NativeDependenciesRequest
from pants.engine.internals.selectors import concurrently
from pants.engine.intrinsics import get_digest_contents, parse_javascript_deps, path_globs_to_paths
from pants.engine.rules import Rule, collect_rules, implicitly, rule
from pants.engine.target import (
    Dependencies,
    FieldSet,
    HydrateSourcesRequest,
    InferDependenciesRequest,
    InferredDependencies,
)
from pants.engine.unions import UnionRule
from pants.util.docutil import doc_url
from pants.util.frozendict import FrozenDict
from pants.util.ordered_set import FrozenOrderedSet
from pants.util.strutil import bullet_list, softwrap

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NodePackageInferenceFieldSet(FieldSet):
    required_fields = (PackageJsonSourceField, NodePackageDependenciesField)

    source: PackageJsonSourceField
    dependencies: NodePackageDependenciesField


class InferNodePackageDependenciesRequest(InferDependenciesRequest):
    infer_from = NodePackageInferenceFieldSet


@dataclass(frozen=True)
class JSSourceInferenceFieldSet(FieldSet):
    required_fields = (JSRuntimeSourceField, JSRuntimeDependenciesField)

    source: JSRuntimeSourceField
    dependencies: JSRuntimeDependenciesField


class InferJSDependenciesRequest(InferDependenciesRequest):
    infer_from = JSSourceInferenceFieldSet


@dataclass(frozen=True)
class StylesheetInferenceFieldSet(FieldSet):
    """A `file` or `resource` holding a stylesheet, which links what it styles with."""

    required_fields = (AssetSourceField, Dependencies)

    source: AssetSourceField
    dependencies: Dependencies


class InferStylesheetDependenciesRequest(InferDependenciesRequest):
    infer_from = StylesheetInferenceFieldSet


@rule
async def infer_node_package_dependencies(
    request: InferNodePackageDependenciesRequest,
    nodejs_infer: NodeJSInfer,
) -> InferredDependencies:
    if not nodejs_infer.package_json_entry_points:
        return InferredDependencies(())
    entry_points = await script_entrypoints_for_source(request.field_set.source)
    candidate_js_files = await find_owners(
        OwnersRequest(tuple(entry_points.globs_from_root())), **implicitly()
    )
    js_targets = await resolve_targets(**implicitly(Addresses(candidate_js_files)))
    return InferredDependencies(
        tgt.address for tgt in js_targets if tgt.has_field(JSRuntimeSourceField)
    )


class NodePackageCandidateMap(FrozenDict[str, Address]):
    pass


@dataclass(frozen=True)
class RequestNodePackagesCandidateMap:
    address: Address


@rule
async def map_candidate_node_packages(
    req: RequestNodePackagesCandidateMap, first_party: FirstPartyNodePackageTargets
) -> NodePackageCandidateMap:
    owning_pkg = await find_owning_package(OwningNodePackageRequest(req.address))
    candidate_tgts = itertools.chain(
        first_party, owning_pkg.third_party if owning_pkg != OwningNodePackage.no_owner() else ()
    )
    return NodePackageCandidateMap(
        (tgt[NodePackageNameField].value, tgt.address) for tgt in candidate_tgts
    )


def _create_inference_metadata(
    imports: PackageJsonImports, config: TSConfig | None
) -> InferenceMetadata:
    return InferenceMetadata.javascript(
        imports.root_dir,
        dict(imports.imports),
        config.resolution_root_dir if config else None,
        dict(config.paths or {}) if config else {},
    )


async def _prepare_inference_metadata(address: Address, file_path: str) -> InferenceMetadata:
    owning_pkg, maybe_config = await concurrently(
        find_owning_package(OwningNodePackageRequest(address)),
        find_parent_ts_config(ParentTSConfigRequest(file_path), **implicitly()),
    )
    if not owning_pkg.target:
        return InferenceMetadata.javascript(
            (
                os.path.dirname(maybe_config.ts_config.path)
                if maybe_config.ts_config
                else address.spec_path
            ),
            {},
            maybe_config.ts_config.resolution_root_dir if maybe_config.ts_config else None,
            dict(maybe_config.ts_config.paths or {}) if maybe_config.ts_config else {},
        )
    return _create_inference_metadata(
        await subpath_imports_for_source(owning_pkg.target[PackageJsonSourceField]),
        maybe_config.ts_config,
    )


# TypeScript resolves a `.js` or `.jsx` specifier to the source it compiles from, see
# https://www.typescriptlang.org/docs/handbook/modules/reference.html#file-extension-substitution
_TYPESCRIPT_SOURCES_OF_SPECIFIER = {
    ".js": (".ts", ".tsx", ".d.ts"),
    ".jsx": (".tsx",),
}


def _file_candidates(
    file_path: str, extensions: tuple[str, ...], valid_file_extensions: set[str]
) -> list[str]:
    suffix = PurePath(file_path).suffix
    if suffix not in valid_file_extensions:
        # Any other import may name a file that is not a module (a stylesheet, a JSON
        # document), so the exact path is a candidate too. The extension-completed candidates
        # stay for a module path whose name contains a dot (`./moduleA.generated`).
        return [file_path, *(f"{file_path}{ext}" for ext in extensions)]
    stem = file_path[: -len(suffix)]
    return [
        file_path,
        *(
            f"{stem}{source}"
            for source in _TYPESCRIPT_SOURCES_OF_SPECIFIER.get(suffix, ())
            if source in valid_file_extensions
        ),
    ]


def _add_extensions(file_imports: frozenset[str], file_extensions: tuple[str, ...]) -> PathGlobs:
    extensions = file_extensions + tuple(f"/index{ext}" for ext in file_extensions)
    valid_file_extensions = set(file_extensions)
    # A bundler's query (`./App.tsx?raw`, `./logo.svg?url`) names the file before the `?`.
    file_paths = {file_import.partition("?")[0] for file_import in file_imports}
    return PathGlobs(
        candidate
        for file_path in file_paths
        for candidate in _file_candidates(file_path, extensions, valid_file_extensions)
    )


async def _determine_import_from_candidates(
    candidates: JavascriptDependencyCandidate,
    package_candidate_map: NodePackageCandidateMap,
    file_extensions: tuple[str, ...],
) -> Addresses:
    paths = await path_globs_to_paths(
        _add_extensions(
            candidates.file_imports,
            file_extensions,
        )
    )
    local_owners = await find_owners(OwnersRequest(paths.files), **implicitly())
    owning_targets = await resolve_targets(**implicitly(Addresses(local_owners)))

    addresses = Addresses(tgt.address for tgt in owning_targets)
    if not local_owners:
        non_path_string_bases = FrozenOrderedSet(
            (
                # Handle scoped packages like "@foo/bar"
                # Ref: https://docs.npmjs.com/cli/v11/using-npm/scope
                "/".join(non_path_string.split("/")[:2])
                if non_path_string.startswith("@")
                # Handle regular packages like "foo"
                else non_path_string.partition("/")[0]
            )
            for non_path_string in candidates.package_imports
        )
        addresses = Addresses(
            package_candidate_map[pkg_name]
            for pkg_name in non_path_string_bases
            if pkg_name in package_candidate_map
        )
    return addresses


def _handle_unowned_imports(
    address: Address,
    unowned_dependency_behavior: UnownedDependencyUsage,
    unowned_imports: frozenset[str],
) -> None:
    if not unowned_imports or unowned_dependency_behavior is UnownedDependencyUsage.DoNothing:
        return

    url = doc_url(
        "docs/using-pants/troubleshooting-common-issues#import-errors-and-missing-dependencies"
    )
    msg = softwrap(
        f"""
        Pants cannot infer owners for the following imports in the target {address}:

        {bullet_list(sorted(unowned_imports))}

        If you do not expect an import to be inferable, add `// pants: no-infer-dep` to the
        import line. Otherwise, see {url} for common problems.
        """
    )
    if unowned_dependency_behavior is UnownedDependencyUsage.LogWarning:
        logger.warning(msg)
    else:
        raise UnownedDependencyError(msg)


def _is_node_builtin_module(import_string: str) -> bool:
    """https://nodejs.org/api/modules.html#built-in-modules."""
    return import_string.startswith("node:")


_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# `@import "x"`, `@import url("x")` (a trailing `theme(...)` or `layer(...)` aside), and Tailwind's `@source "x"`;
# Tailwind's `@source not "x"` excludes a path and links nothing
_CSS_LINK = re.compile(r"""@(?:import\s+(?:url\(\s*)?|source\s+)(["'])([^"']+)\1""")


def _stylesheet_links(text: str) -> frozenset[str]:
    """The files and packages a stylesheet links: never a URL, an absolute path or inline data."""
    return frozenset(
        link
        for link in (match.group(2) for match in _CSS_LINK.finditer(_CSS_COMMENT.sub("", text)))
        if "://" not in link and not link.startswith(("/", "data:", "#"))
    )


def _package_name(specifier: str) -> str:
    """The package a bare specifier names: `@scope/name` of `@scope/name/sub`, `name` of `name/sub`."""
    if specifier.startswith("@"):
        return "/".join(specifier.split("/")[:2])
    return specifier.partition("/")[0]


@rule
async def infer_stylesheet_dependencies(
    request: InferStylesheetDependenciesRequest,
    nodejs_infer: NodeJSInfer,
) -> InferredDependencies:
    source = request.field_set.source
    if not nodejs_infer.imports or not (
        isinstance(source.value, str) and source.value.endswith(".css")
    ):
        return InferredDependencies(())
    sources = await hydrate_sources(HydrateSourcesRequest(source), **implicitly())
    contents = await get_digest_contents(sources.snapshot.digest)
    links = _stylesheet_links(
        "".join(entry.content.decode("utf-8", errors="replace") for entry in contents)
    )
    if not links:
        return InferredDependencies(())
    folder = os.path.dirname(source.file_path)
    relative = sorted(link for link in links if link.startswith("."))
    packages = sorted(link for link in links if not link.startswith("."))
    # Node resolves a stylesheet's links from the file's folder, whichever target owns it
    candidate_pkgs = await map_candidate_node_packages(
        RequestNodePackagesCandidateMap(Address(folder)), **implicitly()
    )
    owners = await concurrently(
        find_owners(OwnersRequest((os.path.normpath(os.path.join(folder, link)),)), **implicitly())
        for link in relative
    )
    found: dict[str, tuple[Address, ...]] = dict(zip(relative, (tuple(owned) for owned in owners)))
    for link in packages:
        name = _package_name(link)
        found[link] = (candidate_pkgs[name],) if name in candidate_pkgs else ()
    _handle_unowned_imports(
        request.field_set.address,
        nodejs_infer.unowned_dependency_behavior,
        frozenset(link for link, addresses in found.items() if not addresses),
    )
    return InferredDependencies(itertools.chain.from_iterable(found.values()))


@rule
async def infer_js_source_dependencies(
    request: InferJSDependenciesRequest,
    nodejs_infer: NodeJSInfer,
) -> InferredDependencies:
    source: JSRuntimeSourceField = request.field_set.source
    if not nodejs_infer.imports:
        return InferredDependencies(())

    sources = await hydrate_sources(
        HydrateSourcesRequest(source, for_sources_types=[JSRuntimeSourceField]), **implicitly()
    )
    metadata = await _prepare_inference_metadata(request.field_set.address, source.file_path)

    native_results, candidate_pkgs = await concurrently(
        parse_javascript_deps(NativeDependenciesRequest(sources.snapshot.digest, metadata)),
        map_candidate_node_packages(
            RequestNodePackagesCandidateMap(request.field_set.address), **implicitly()
        ),
    )
    assert len(native_results.path_to_deps) == 1
    native_result = next(iter(native_results.path_to_deps.values()))

    imports = dict(
        zip(
            native_result.imports,
            await concurrently(
                _determine_import_from_candidates(
                    candidates,
                    candidate_pkgs,
                    file_extensions=(
                        JS_FILE_EXTENSIONS
                        + JSX_FILE_EXTENSIONS
                        + TS_FILE_EXTENSIONS
                        + TSX_FILE_EXTENSIONS
                    ),
                )
                for string, candidates in native_result.imports.items()
            ),
        )
    )
    _handle_unowned_imports(
        request.field_set.address,
        nodejs_infer.unowned_dependency_behavior,
        frozenset(
            string
            for string, addresses in imports.items()
            if not addresses and not _is_node_builtin_module(string)
        ),
    )

    return InferredDependencies(itertools.chain.from_iterable(imports.values()))


def rules() -> Iterable[Rule | UnionRule]:
    return [
        *collect_rules(),
        *package_json.rules(),
        *tsconfig.rules(),
        UnionRule(InferDependenciesRequest, InferNodePackageDependenciesRequest),
        UnionRule(InferDependenciesRequest, InferJSDependenciesRequest),
        UnionRule(InferDependenciesRequest, InferStylesheetDependenciesRequest),
    ]
