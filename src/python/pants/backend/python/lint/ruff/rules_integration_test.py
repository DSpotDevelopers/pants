# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from pathlib import Path

import pytest

from pants.backend.python import target_types_rules
from pants.backend.python.lint.ruff import skip_field
from pants.backend.python.lint.ruff.check import skip_field as ruff_check_skip_field
from pants.backend.python.lint.ruff.check.rules import (
    RuffCheckFieldSet,
    RuffFixRequest,
    RuffLintRequest,
)
from pants.backend.python.lint.ruff.check.rules import rules as ruff_check_rules
from pants.backend.python.lint.ruff.check.skip_field import SkipRuffCheckField
from pants.backend.python.lint.ruff.format import skip_field as ruff_format_skip_field
from pants.backend.python.lint.ruff.format.rules import RuffFormatFieldSet, RuffFormatRequest
from pants.backend.python.lint.ruff.format.rules import rules as ruff_fmt_rules
from pants.backend.python.lint.ruff.format.skip_field import SkipRuffFormatField
from pants.backend.python.lint.ruff.skip_field import SkipRuffField
from pants.backend.python.lint.ruff.subsystem import rules as ruff_subsystem_rules
from pants.backend.python.target_types import PythonSourcesGeneratorTarget
from pants.core.goals.fix import FixResult
from pants.core.goals.fmt import FmtResult
from pants.core.goals.lint import Lint, LintResult
from pants.core.register import rules as core_rules
from pants.core.target_types import (
    FilesGeneratorTarget,
    FileTarget,
    ResourcesGeneratorTarget,
    ResourceTarget,
)
from pants.core.util_rules import config_files, source_files
from pants.core.util_rules.partitions import Partitions, _EmptyMetadata
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine import process
from pants.engine.addresses import Address
from pants.engine.fs import DigestContents
from pants.engine.target import Target
from pants.testutil.python_interpreter_selection import all_major_minor_python_versions
from pants.testutil.rule_runner import GoalRuleResult, QueryRule, RuleRunner

GOOD_FILE = 'a = "string without any placeholders"\n'
BAD_FILE = 'a = f"string without any placeholders"\n'
UNFORMATTED_FILE = 'a ="string without any placeholders"\n'
IMPORTS_SHADOWED_BY_LOCAL_PACKAGE = (
    "from opentelemetry import trace\n"
    "\n"
    "from pants.backend.observability.opentelemetry.config import Config\n"
)
IMPORTS_FIXED_FOR_LOCAL_PACKAGE = (
    "from opentelemetry import trace\n"
    "from pants.backend.observability.opentelemetry.config import Config\n"
)


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *ruff_check_rules(),
            *ruff_fmt_rules(),
            *skip_field.rules(),
            *ruff_check_skip_field.rules(),
            *ruff_format_skip_field.rules(),
            *ruff_subsystem_rules(),
            *config_files.rules(),
            *target_types_rules.rules(),
            QueryRule(FixResult, [RuffFixRequest.Batch]),
            QueryRule(LintResult, [RuffLintRequest.Batch]),
            QueryRule(FmtResult, [RuffFormatRequest.Batch]),
            QueryRule(Partitions, [RuffFixRequest.PartitionRequest]),
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[PythonSourcesGeneratorTarget],
    )


def run_ruff(
    rule_runner: RuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> tuple[FixResult, LintResult, FmtResult]:
    args = ["--backend-packages=pants.backend.python.lint.ruff", *(extra_args or ())]
    rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})

    check_field_sets = [
        RuffCheckFieldSet.create(tgt) for tgt in targets if RuffCheckFieldSet.is_applicable(tgt)
    ]
    check_source_reqs = [SourceFilesRequest(field_set.source for field_set in check_field_sets)]
    check_input_sources = rule_runner.request(SourceFiles, check_source_reqs)

    format_field_sets = [
        RuffFormatFieldSet.create(tgt) for tgt in targets if RuffFormatFieldSet.is_applicable(tgt)
    ]
    format_source_reqs = [SourceFilesRequest(field_set.source for field_set in format_field_sets)]
    format_input_sources = rule_runner.request(SourceFiles, format_source_reqs)

    fix_result = rule_runner.request(
        FixResult,
        [
            RuffFixRequest.Batch(
                "",
                check_input_sources.snapshot.files,
                partition_metadata=_EmptyMetadata(),
                snapshot=check_input_sources.snapshot,
            ),
        ],
    )
    lint_result = rule_runner.request(
        LintResult,
        [
            RuffLintRequest.Batch(
                "",
                tuple(check_field_sets),
                partition_metadata=_EmptyMetadata(),
            ),
        ],
    )
    fmt_result = rule_runner.request(
        FmtResult,
        [
            RuffFormatRequest.Batch(
                "",
                format_input_sources.snapshot.files,
                partition_metadata=_EmptyMetadata(),
                snapshot=format_input_sources.snapshot,
            )
        ],
    )

    return fix_result, lint_result, fmt_result


@pytest.mark.platform_specific_behavior
@pytest.mark.parametrize(
    "major_minor_interpreter",
    all_major_minor_python_versions(["CPython>=3.9,<3.15"]),
)
def test_passing(rule_runner: RuleRunner, major_minor_interpreter: str) -> None:
    rule_runner.write_files({"f.py": GOOD_FILE, "BUILD": "python_sources(name='t')"})
    tgt = rule_runner.get_target(Address("", target_name="t", relative_file_path="f.py"))
    fix_result, lint_result, fmt_result = run_ruff(
        rule_runner,
        [tgt],
        extra_args=[f"--python-interpreter-constraints=['=={major_minor_interpreter}.*']"],
    )
    assert lint_result.exit_code == 0
    assert fix_result.stderr == ""
    assert fix_result.stdout == "All checks passed!\n"
    assert not fix_result.did_change
    assert fix_result.output == rule_runner.make_snapshot({"f.py": GOOD_FILE})
    assert not fmt_result.did_change
    assert fmt_result.output == rule_runner.make_snapshot({"f.py": GOOD_FILE})


def test_failing(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({"f.py": BAD_FILE, "BUILD": "python_sources(name='t')"})
    tgt = rule_runner.get_target(Address("", target_name="t", relative_file_path="f.py"))
    fix_result, lint_result, fmt_result = run_ruff(rule_runner, [tgt])
    assert lint_result.exit_code == 1
    assert fix_result.stdout == "Found 1 error (1 fixed, 0 remaining).\n"
    assert fix_result.stderr == ""
    assert fix_result.did_change
    assert fix_result.output == rule_runner.make_snapshot({"f.py": GOOD_FILE})
    assert not fmt_result.did_change
    assert fmt_result.output == rule_runner.make_snapshot({"f.py": BAD_FILE})


def test_multiple_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "good.py": GOOD_FILE,
            "bad.py": BAD_FILE,
            "unformatted.py": UNFORMATTED_FILE,
            "BUILD": "python_sources(name='t')",
        }
    )
    tgts = [
        rule_runner.get_target(Address("", target_name="t", relative_file_path="good.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="bad.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="unformatted.py")),
    ]
    fix_result, lint_result, fmt_result = run_ruff(rule_runner, tgts)
    assert lint_result.exit_code == 1
    assert fix_result.output == rule_runner.make_snapshot(
        {"good.py": GOOD_FILE, "bad.py": GOOD_FILE, "unformatted.py": UNFORMATTED_FILE}
    )
    assert fix_result.did_change is True
    assert fmt_result.output == rule_runner.make_snapshot(
        {"good.py": GOOD_FILE, "bad.py": BAD_FILE, "unformatted.py": GOOD_FILE}
    )
    assert fmt_result.did_change is True


def test_fix_preserves_init_py_package_context_for_import_sorting(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "pyproject.toml": "\n".join(
                [
                    "[tool.ruff.lint]",
                    'select = ["I"]',
                    "",
                    "[tool.ruff.lint.isort]",
                    'known-first-party = ["pants"]',
                    "",
                ]
            ),
            "src/python/pants/backend/observability/opentelemetry/BUILD": "python_sources()",
            "src/python/pants/backend/observability/opentelemetry/__init__.py": "",
            "src/python/pants/backend/observability/opentelemetry/processor.py": (
                IMPORTS_SHADOWED_BY_LOCAL_PACKAGE
            ),
        }
    )
    rule_runner.set_options(
        ["--backend-packages=pants.backend.python.lint.ruff"],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )

    init_tgt = rule_runner.get_target(
        Address(
            "src/python/pants/backend/observability/opentelemetry",
            relative_file_path="__init__.py",
        )
    )
    processor_tgt = rule_runner.get_target(
        Address(
            "src/python/pants/backend/observability/opentelemetry",
            relative_file_path="processor.py",
        )
    )
    init_field_set = RuffCheckFieldSet.create(init_tgt)
    processor_field_set = RuffCheckFieldSet.create(processor_tgt)

    lint_result = rule_runner.request(
        LintResult,
        [
            RuffLintRequest.Batch(
                "",
                (init_field_set, processor_field_set),
                partition_metadata=_EmptyMetadata(),
            ),
        ],
    )
    assert lint_result.exit_code == 1
    assert "I001" in lint_result.stdout

    partitions = rule_runner.request(
        Partitions,
        [RuffFixRequest.PartitionRequest((init_field_set, processor_field_set))],
    )
    assert len(partitions) == 1
    partition = partitions[0]
    assert partition.elements == (
        "src/python/pants/backend/observability/opentelemetry/__init__.py",
        "src/python/pants/backend/observability/opentelemetry/processor.py",
    )
    assert partition.metadata.init_files == (
        "src/python/pants/backend/observability/opentelemetry/__init__.py",
    )

    fix_input_sources = rule_runner.request(
        SourceFiles, [SourceFilesRequest([processor_field_set.source])]
    )
    fix_result = rule_runner.request(
        FixResult,
        [
            RuffFixRequest.Batch(
                "",
                ("src/python/pants/backend/observability/opentelemetry/processor.py",),
                partition_metadata=partition.metadata,
                snapshot=fix_input_sources.snapshot,
            ),
        ],
    )

    assert fix_result.stdout == "Found 1 error (1 fixed, 0 remaining).\n"
    assert fix_result.output == rule_runner.make_snapshot(
        {
            "src/python/pants/backend/observability/opentelemetry/processor.py": (
                IMPORTS_FIXED_FOR_LOCAL_PACKAGE
            )
        }
    )


def test_skip_field(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "good.py": GOOD_FILE,
            "bad.py": BAD_FILE,
            "unformatted.py": UNFORMATTED_FILE,
            "BUILD": "python_sources(name='t', skip_ruff=True)",
        }
    )
    tgts = [
        rule_runner.get_target(Address("", target_name="t", relative_file_path="good.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="bad.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="unformatted.py")),
    ]
    for tgt in tgts:
        assert tgt.get(SkipRuffField).value is True

    fix_result, lint_result, fmt_result = run_ruff(rule_runner, tgts)

    assert lint_result.exit_code == 0
    assert fix_result.output == rule_runner.make_snapshot({})
    assert fix_result.did_change is False
    assert fmt_result.output == rule_runner.make_snapshot({})
    assert fmt_result.did_change is False


def test_skip_check_field(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "good.py": GOOD_FILE,
            "bad.py": BAD_FILE,
            "unformatted.py": UNFORMATTED_FILE,
            "BUILD": "python_sources(name='t', skip_ruff_check=True)",
        }
    )
    tgts = [
        rule_runner.get_target(Address("", target_name="t", relative_file_path="good.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="bad.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="unformatted.py")),
    ]
    for tgt in tgts:
        assert tgt.get(SkipRuffCheckField).value is True

    fix_result, lint_result, fmt_result = run_ruff(rule_runner, tgts)

    assert lint_result.exit_code == 0
    assert fix_result.output == rule_runner.make_snapshot({})
    assert fix_result.did_change is False
    assert fmt_result.output == rule_runner.make_snapshot(
        {"good.py": GOOD_FILE, "bad.py": BAD_FILE, "unformatted.py": GOOD_FILE}
    )
    assert fmt_result.did_change is True


def test_skip_format_field(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "good.py": GOOD_FILE,
            "bad.py": BAD_FILE,
            "unformatted.py": UNFORMATTED_FILE,
            "BUILD": "python_sources(name='t', skip_ruff_format=True)",
        }
    )
    tgts = [
        rule_runner.get_target(Address("", target_name="t", relative_file_path="good.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="bad.py")),
        rule_runner.get_target(Address("", target_name="t", relative_file_path="unformatted.py")),
    ]
    for tgt in tgts:
        assert tgt.get(SkipRuffFormatField).value is True

    fix_result, lint_result, fmt_result = run_ruff(rule_runner, tgts)

    assert lint_result.exit_code == 1
    assert fix_result.output == rule_runner.make_snapshot(
        {"good.py": GOOD_FILE, "bad.py": GOOD_FILE, "unformatted.py": UNFORMATTED_FILE}
    )
    assert fix_result.did_change is True
    assert fmt_result.output == rule_runner.make_snapshot({})
    assert fmt_result.did_change is False


@pytest.mark.parametrize(
    "file_path,config_path,extra_args,should_change",
    (
        [Path("f.py"), Path("pyproject.toml"), [], False],
        [Path("f.py"), Path("ruff.toml"), [], False],
        [Path("custom/f.py"), Path("custom/ruff.toml"), [], False],
        [Path("custom/f.py"), Path("custom/pyproject.toml"), [], False],
        [Path("f.py"), Path("custom/ruff.toml"), ["--ruff-config=custom/ruff.toml"], False],
        [Path("f.py"), Path("custom/ruff.toml"), [], True],
    ),
)
def test_config_file(
    rule_runner: RuleRunner,
    file_path: Path,
    config_path: Path,
    extra_args: list[str],
    should_change: bool,
) -> None:
    hierarchy = "[tool.ruff]\n" if config_path.stem == "pyproject" else ""
    rule_runner.write_files(
        {
            file_path: BAD_FILE,
            file_path.parent / "BUILD": "python_sources()",
            config_path: f'{hierarchy}ignore = ["F541"]',
        }
    )
    spec_path = str(file_path.parent).replace(".", "")
    rel_file_path = file_path.relative_to(*file_path.parts[:1]) if spec_path else file_path
    addr = Address(spec_path, relative_file_path=str(rel_file_path))
    tgt = rule_runner.get_target(addr)
    fix_result, lint_result, fmt_result = run_ruff(rule_runner, [tgt], extra_args=extra_args)
    assert lint_result.exit_code == bool(should_change)
    assert fix_result.did_change is should_change


def test_report_file(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({"f.py": BAD_FILE, "BUILD": "python_sources(name='t')"})
    tgt = rule_runner.get_target(Address("", target_name="t", relative_file_path="f.py"))
    fix_result, lint_result, fmt_result = run_ruff(
        rule_runner,
        [tgt],
        extra_args=["--ruff-args='--output-file=reports/foo.txt'"],
    )
    assert lint_result.exit_code == 1
    report_files = rule_runner.request(DigestContents, [lint_result.report])
    assert len(report_files) == 1
    assert "f.py:1:5" in report_files[0].content.decode()
    assert "F541" in report_files[0].content.decode()


@pytest.fixture
def lint_goal_rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *core_rules(),
            *source_files.rules(),
            *process.rules(),
            *ruff_check_rules(),
            *skip_field.rules(),
            *ruff_check_skip_field.rules(),
            *ruff_subsystem_rules(),
            *config_files.rules(),
            *target_types_rules.rules(),
        ],
        target_types=[
            PythonSourcesGeneratorTarget,
            FileTarget,
            FilesGeneratorTarget,
            ResourceTarget,
            ResourcesGeneratorTarget,
        ],
    )


PYTHON_ASSETS_BUILD = (
    'resources(name="read", sources=["read/*.py", "read/*.txt"])\n'
    'files(name="raw", sources=["raw/*.py"])\n'
)


def python_assets(
    *, read: str = GOOD_FILE, raw: str = GOOD_FILE, notes: str = "plain notes\n"
) -> dict[str, str]:
    return {
        "fixtures/BUILD": PYTHON_ASSETS_BUILD,
        "fixtures/read/sample.py": read,
        "fixtures/read/notes.txt": notes,
        "fixtures/raw/__init__.py": raw,
    }


def lint_python_assets(rule_runner: RuleRunner, *args: str) -> GoalRuleResult:
    rule_runner.set_options(
        ["--backend-packages=pants.backend.python.lint.ruff"],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    return rule_runner.run_goal_rule(Lint, args=["--only=ruff-check", *args, "fixtures::"])


@pytest.mark.parametrize("bad", ["read", "raw"])
def test_python_assets_are_checked_when_enabled(
    lint_goal_rule_runner: RuleRunner, bad: str
) -> None:
    lint_goal_rule_runner.write_files(python_assets(**{bad: BAD_FILE}))
    result = lint_python_assets(lint_goal_rule_runner, "--ruff-check-python-assets")
    assert result.exit_code == 1
    assert "ruff check failed" in result.stderr


def test_python_assets_check_only_python_files(lint_goal_rule_runner: RuleRunner) -> None:
    # A `.txt` resource beside them is never given to Ruff: as Python it would not parse.
    lint_goal_rule_runner.write_files(python_assets(notes="this is not Python (\n"))
    result = lint_python_assets(lint_goal_rule_runner, "--ruff-check-python-assets")
    assert result.exit_code == 0
    assert "ruff check succeeded" in result.stderr


def test_python_assets_are_not_checked_by_default(lint_goal_rule_runner: RuleRunner) -> None:
    lint_goal_rule_runner.write_files(python_assets(read=BAD_FILE, raw=BAD_FILE))
    result = lint_python_assets(lint_goal_rule_runner)
    assert result.exit_code == 0
    assert "ruff check" not in result.stderr


@pytest.mark.parametrize("skip_field_name", ["skip_ruff_check", "skip_ruff"])
def test_python_assets_opt_out_with_the_skip_fields(
    lint_goal_rule_runner: RuleRunner, skip_field_name: str
) -> None:
    lint_goal_rule_runner.write_files(
        {
            **python_assets(read=BAD_FILE),
            "fixtures/BUILD": PYTHON_ASSETS_BUILD.replace(
                '"read/*.txt"]', f'"read/*.txt"], {skip_field_name}=True'
            ),
        }
    )
    result = lint_python_assets(lint_goal_rule_runner, "--ruff-check-python-assets")
    assert result.exit_code == 0
    assert "ruff check succeeded" in result.stderr
