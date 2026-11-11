# Copyright 2025 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from pants.backend.javascript.nodejs_project import AllNodeJSProjects, find_node_js_projects
from pants.backend.javascript.package_json import (
    AllPackageJson,
    OwningNodePackageRequest,
    PackageJson,
    all_package_json,
    find_owning_package,
)
from pants.backend.javascript.resolve import ChosenNodeResolve
from pants.backend.javascript.subsystems.nodejs_tool import NodeJSToolRequest, prepare_tool_process
from pants.backend.javascript.target_types import JS_FILE_EXTENSIONS, JSRuntimeSourceField
from pants.backend.typescript.subsystem import TypeScriptSubsystem
from pants.backend.typescript.target_types import (
    TS_FILE_EXTENSIONS,
    TypeScriptSourceField,
    TypeScriptTestSourceField,
)
from pants.backend.typescript.tsconfig import AllTSConfigs, TSConfig, construct_effective_ts_configs
from pants.base.build_root import BuildRoot
from pants.core.goals.check import CheckRequest, CheckResult, CheckResults, CheckSubsystem
from pants.core.target_types import FileSourceField, ResourceSourceField
from pants.core.util_rules.system_binaries import CpBinary, FindBinary, MkdirBinary, TouchBinary
from pants.engine.fs import (
    EMPTY_DIGEST,
    CreateDigest,
    Digest,
    FileContent,
    GlobMatchErrorBehavior,
    PathGlobs,
)
from pants.engine.internals.graph import find_all_targets, hydrate_sources, transitive_targets
from pants.engine.internals.native_engine import MergeDigests
from pants.engine.internals.selectors import concurrently
from pants.engine.intrinsics import (
    create_digest,
    digest_to_snapshot,
    execute_process,
    merge_digests,
    path_globs_to_digest,
)
from pants.engine.process import Process
from pants.engine.rules import collect_rules, implicitly, rule
from pants.engine.target import (
    AllTargets,
    FieldSet,
    HydrateSourcesRequest,
    SourcesField,
    Target,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionRule
from pants.option.global_options import GlobalOptions
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel
from pants.util.ordered_set import FrozenOrderedSet, OrderedSet

if TYPE_CHECKING:
    from pants.backend.javascript.nodejs_project import NodeJSProject

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateTscWrapperScriptRequest:
    project: NodeJSProject
    package_output_dirs: tuple[str, ...]
    build_root: BuildRoot
    named_cache_sandbox_mount_dir: str
    tsc_wrapper_filename: str


@dataclass(frozen=True)
class TypeScriptCheckFieldSet(FieldSet):
    required_fields = (JSRuntimeSourceField,)

    sources: JSRuntimeSourceField


class TypeScriptCheckRequest(CheckRequest):
    field_set_type = TypeScriptCheckFieldSet
    tool_name = TypeScriptSubsystem.options_scope


def _build_workspace_tsconfig_map(
    workspaces: FrozenOrderedSet[PackageJson], all_ts_configs: list[TSConfig]
) -> dict[str, TSConfig]:
    workspace_dir_map = {os.path.normpath(pkg.root_dir): pkg for pkg in workspaces}
    workspace_dir_to_tsconfig: dict[str, TSConfig] = {}

    # Only consider tsconfig.json files (exclude tsconfig.build.json, tsconfig.test.json, etc.)
    # since tsc only reads tsconfig.json by default and we don't support the `--project` flag currently
    # Additionally, TSConfig class only supports tsconfig.json.
    tsconfig_json_files = [
        cfg for cfg in all_ts_configs if os.path.basename(cfg.path) == "tsconfig.json"
    ]

    for ts_config in tsconfig_json_files:
        config_dir = os.path.normpath(os.path.dirname(ts_config.path))

        if config_dir in workspace_dir_map:
            workspace_dir_to_tsconfig[config_dir] = ts_config

    return workspace_dir_to_tsconfig


def _collect_package_output_dirs(
    project: NodeJSProject, project_ts_configs: list[TSConfig], project_root_path: Path
) -> tuple[str, ...]:
    workspace_dir_to_tsconfig = _build_workspace_tsconfig_map(
        project.workspaces, project_ts_configs
    )

    package_output_dirs: OrderedSet[str] = OrderedSet()
    for workspace_pkg in project.workspaces:
        workspace_pkg_path = Path(workspace_pkg.root_dir)

        if workspace_pkg_path == project_root_path:
            pkg_prefix = ""
        else:
            relative_path = workspace_pkg_path.relative_to(project_root_path)
            pkg_prefix = f"{relative_path.as_posix()}/"

        pkg_tsconfig = workspace_dir_to_tsconfig.get(os.path.normpath(workspace_pkg.root_dir))

        if pkg_tsconfig and pkg_tsconfig.out_dir:
            resolved_out_dir = f"{pkg_prefix}{pkg_tsconfig.out_dir.lstrip('./')}"
            package_output_dirs.add(resolved_out_dir)

    return tuple(package_output_dirs)


def _collect_project_configs(
    project: NodeJSProject, all_package_jsons: AllPackageJson, all_ts_configs: AllTSConfigs
) -> tuple[list, list[TSConfig]]:
    project_package_jsons = [
        pkg for pkg in all_package_jsons if pkg.root_dir.startswith(project.root_dir)
    ]
    project_ts_configs = [
        config for config in all_ts_configs if config.path.startswith(project.root_dir)
    ]
    return project_package_jsons, project_ts_configs


async def _collect_config_files_for_project(
    project: NodeJSProject,
    targets: list[Target],
    project_package_jsons: list,
    project_ts_configs: list[TSConfig],
) -> list[str]:
    config_files = []

    for pkg_json in project_package_jsons:
        config_files.append(pkg_json.file)

    for ts_config in project_ts_configs:
        config_files.append(ts_config.path)

    # The compiler reads imported assets as well as runtime sources (for example JSON schemas).
    # Note: Package manager config files
    # (.npmrc, .pnpmrc, pnpm-workspace.yaml) should be dependencies of package_json targets
    # since they affect package installation, not TypeScript compilation directly.
    target_addresses = [target.address for target in targets]
    transitive_targets_result = await transitive_targets(
        TransitiveTargetsRequest(target_addresses), **implicitly()
    )

    for target in transitive_targets_result.closure:
        for field_type in (FileSourceField, ResourceSourceField):
            if target.has_field(field_type):
                config_files.append(target[field_type].file_path)

    return config_files


@rule
async def create_tsc_wrapper_script(
    request: CreateTscWrapperScriptRequest,
    cp_binary: CpBinary,
    mkdir_binary: MkdirBinary,
    find_binary: FindBinary,
    touch_binary: TouchBinary,
) -> Digest:
    project = request.project
    package_output_dirs = request.package_output_dirs
    build_root = request.build_root
    named_cache_sandbox_mount_dir = request.named_cache_sandbox_mount_dir
    tsc_wrapper_filename = request.tsc_wrapper_filename

    project_abs_path = os.path.join(build_root.path, project.root_dir)
    cache_key = sha256(project_abs_path.encode()).hexdigest()

    project_depth = len([p for p in project.root_dir.strip("/").split("/") if p])
    cache_relative_path = (
        "../" * project_depth + named_cache_sandbox_mount_dir
        if project_depth > 0
        else named_cache_sandbox_mount_dir
    )
    project_cache_subdir = f"{cache_relative_path}/{cache_key}"

    package_dirs = []
    for workspace_pkg in project.workspaces:
        if workspace_pkg.root_dir != project.root_dir:
            package_relative = workspace_pkg.root_dir.removeprefix(f"{project.root_dir}/")
            package_dirs.append(package_relative)
        else:
            package_dirs.append(".")
    package_dirs_str = " ".join(f'"{d}"' for d in package_dirs)
    output_dirs_str = " ".join(f'"{d}"' for d in package_output_dirs)

    script_content = f"""#!/bin/sh
# TypeScript incremental compilation cache wrapper

# All source files in sandbox have mtime as at sandbox creation (e.g. when the process started).
# Without any special handling, tsc will do a fast immediate rebuild (without checking tsbuildinfo metadata).
# (tsc outputs: "Project 'tsconfig.json' is out of date because output 'tsconfig.tsbuildinfo' is older than input 'tsconfig.json'")
# What we want: tsconfig (oldest), tsbuildinfo (newer), source files (newest).
# See also https://github.com/microsoft/TypeScript/issues/54563

set -e

CP_BIN="{cp_binary.path}"
MKDIR_BIN="{mkdir_binary.path}"
FIND_BIN="{find_binary.path}"
TOUCH_BIN="{touch_binary.path}"

PROJECT_CACHE_SUBDIR="{project_cache_subdir}"

# Ensure cache directory exists (it won't on first run)
"$MKDIR_BIN" -p "$PROJECT_CACHE_SUBDIR" > /dev/null 2>&1

# Copy cached files to working directory
"$CP_BIN" -a "$PROJECT_CACHE_SUBDIR/." . > /dev/null 2>&1

# Make tsconfig files oldest
# This could be improved by passing a list of tsconfig files, but that might be best done if/when we have a Target for tsconfig files.
"$FIND_BIN" . -type f -name "tsconfig*.json" -exec "$TOUCH_BIN" -t 202001010000 {{}} +

# Run tsc
"$@"

# Update cache
# Copy .tsbuildinfo files located at package root to cache
for package_dir in {package_dirs_str}; do
    for tsbuildinfo_file in "$package_dir"/*.tsbuildinfo; do
        if [ -f "$tsbuildinfo_file" ]; then
            "$MKDIR_BIN" -p "$PROJECT_CACHE_SUBDIR/$package_dir"
            "$CP_BIN" "$tsbuildinfo_file" "$PROJECT_CACHE_SUBDIR/$package_dir/"
        fi
    done
done

# Copy output directories to cache
# (the output files are needed because tsc checks them against tsbuildinfo hashes when determining if a rebuild is required)
for output_dir in {output_dirs_str}; do
    if [ -d "$output_dir" ]; then
        output_parent="$(dirname "$output_dir")"
        "$MKDIR_BIN" -p "$PROJECT_CACHE_SUBDIR/$output_parent"
        "$CP_BIN" -r "$output_dir" "$PROJECT_CACHE_SUBDIR/$output_parent/"
    fi
done
"""

    script_digest = await create_digest(
        CreateDigest(
            [
                FileContent(
                    os.path.join(project.root_dir, tsc_wrapper_filename),
                    script_content.encode(),
                    is_executable=True,
                )
            ]
        ),
        **implicitly(),
    )

    return script_digest


async def _collect_project_targets(
    project: NodeJSProject,
    all_targets: AllTargets,
    all_projects: AllNodeJSProjects,
    project_ts_configs: list[TSConfig],
    *,
    include_assets: bool = False,
) -> list[Target]:
    # checkJs controls diagnostics, not whether JS modules are compiler inputs. TypeScript
    # still follows imports into JS with allowJs, and declarations can sit beside those modules.
    compiler_extensions = TS_FILE_EXTENSIONS + JS_FILE_EXTENSIONS + (".tsx", ".jsx", ".json")
    targets = [
        target
        for target in all_targets
        if target.has_field(JSRuntimeSourceField)
        or include_assets
        and any(
            target.has_field(field_type)
            and target[field_type].file_path.endswith(compiler_extensions)
            for field_type in (FileSourceField, ResourceSourceField)
        )
    ]

    target_owning_packages = await concurrently(
        find_owning_package(OwningNodePackageRequest(target.address), **implicitly())
        for target in targets
    )

    project_targets = []
    for target, owning_package in zip(targets, target_owning_packages):
        if owning_package.target:
            package_directory = owning_package.target.address.spec_path
            target_project = all_projects.project_for_directory(package_directory)
            if target_project == project:
                project_targets.append(target)

    has_check_js = any(config.allow_js and config.check_js for config in project_ts_configs)
    if (
        not include_assets
        and not has_check_js
        and not any(
            target.has_field(TypeScriptSourceField) or target.has_field(TypeScriptTestSourceField)
            for target in project_targets
        )
    ):
        return []

    return project_targets


async def _hydrate_project_sources(
    project_targets: list[Target],
) -> Digest:
    workspace_target_sources = await concurrently(
        hydrate_sources(
            HydrateSourcesRequest(target[SourcesField]),
            **implicitly(),
        )
        for target in project_targets
    )

    return await merge_digests(
        MergeDigests([sources.snapshot.digest for sources in workspace_target_sources])
    )


async def _prepare_compilation_input(
    project: NodeJSProject,
    project_targets: list[Target],
    project_package_jsons: list,
    project_ts_configs: list[TSConfig],
    all_workspace_sources: Digest,
) -> Digest:
    config_files = await _collect_config_files_for_project(
        project, project_targets, project_package_jsons, project_ts_configs
    )
    config_digest = (
        await path_globs_to_digest(
            PathGlobs(config_files, glob_match_error_behavior=GlobMatchErrorBehavior.ignore),
            **implicitly(),
        )
        if config_files
        else EMPTY_DIGEST
    )

    return await merge_digests(MergeDigests([all_workspace_sources, config_digest]))


@dataclass(frozen=True)
class TypeScriptPrograms:
    config_paths: tuple[str, ...]
    source_files: frozenset[str]
    config_files: tuple[str, ...]


async def _select_tsconfig_programs(
    project: NodeJSProject,
    subsystem: TypeScriptSubsystem,
    input_digest: Digest,
    project_ts_configs: list[TSConfig],
    selected_files: tuple[str, ...],
    asset_paths: tuple[str, ...],
    global_options: GlobalOptions,
) -> TypeScriptPrograms | CheckResult:
    # A Node resolve supplies dependencies, not a TypeScript compilation boundary.
    # TypeScript owns files/include/exclude/extends semantics and named project references.
    configs = {config.path: config for config in project_ts_configs}
    defaults = sorted(
        (
            config
            for config in project_ts_configs
            if os.path.basename(config.path) == "tsconfig.json"
        ),
        key=lambda config: len(os.path.dirname(config.path)),
        reverse=True,
    )
    pending = list(
        dict.fromkeys(
            next(
                (
                    config.path
                    for config in defaults
                    if Path(source).is_relative_to(os.path.dirname(config.path))
                ),
                os.path.join(project.root_dir, "tsconfig.json"),
            )
            for source in selected_files
        )
    )
    program_files: dict[str, set[str]] = {}
    references: dict[str, tuple[str, ...]] = {}
    selected: OrderedSet[str] = OrderedSet()
    source_paths = set(selected_files)
    while pending:
        path = pending.pop(0)
        if path in program_files:
            continue
        relative_path = os.path.relpath(path, project.root_dir or ".")
        # Explicit references can name configurations beyond the tsconfig*.json glob.
        config_digest = await path_globs_to_digest(
            PathGlobs([path], glob_match_error_behavior=GlobMatchErrorBehavior.ignore),
            **implicitly(),
        )
        query_input = await merge_digests(MergeDigests([input_digest, config_digest]))
        request = subsystem.request(
            args=("--showConfig", "--project", relative_path),
            input_digest=query_input,
            description=f"Discover TypeScript program in {path}",
            level=LogLevel.DEBUG,
        )
        process = await prepare_tool_process(
            replace(request, resolve=ChosenNodeResolve(project).resolve_name), **implicitly()
        )
        # --showConfig enumerates filenames; it does not parse source contents. Supply
        # empty candidate files for this discovery only, without hydrating their blobs.
        # Installed dependency/config contents remain authoritative and are never replaced.
        existing = await digest_to_snapshot(process.input_digest)
        existing_files = set(existing.files)
        inventory = await create_digest(
            CreateDigest(
                [FileContent(asset, b"") for asset in asset_paths if asset not in existing_files]
            )
        )
        discovery_input = await merge_digests(MergeDigests([process.input_digest, inventory]))
        result = await execute_process(
            replace(process, input_digest=discovery_input, working_directory=project.root_dir),
            **implicitly(),
        )
        if result.exit_code:
            return CheckResult.from_fallible_process_result(
                result,
                partition_description=f"TypeScript configuration {path}",
                output_simplifier=global_options.output_simplifier(),
            )
        program = json.loads(result.stdout)
        directory = os.path.dirname(path)
        files = {
            os.path.normpath(os.path.join(directory, file)) for file in program.get("files", ())
        }
        program_files[path] = files
        if source_paths.intersection(files):
            config = configs.get(path) or TSConfig(
                path, out_dir=program.get("compilerOptions", {}).get("outDir")
            )
            config.validate_outdir()
            selected.add(path)
        child_configs = []
        for reference in program.get("references", ()):
            referenced = os.path.normpath(os.path.join(directory, reference["path"]))
            if not referenced.endswith(".json"):
                referenced = os.path.join(referenced, "tsconfig.json")
            child_configs.append(referenced)
        references[path] = tuple(child_configs)
        pending.extend(child_configs)

    # Only selected programs and their declared reference closure contribute ambient assets.
    active: OrderedSet[str] = OrderedSet()
    pending = list(selected)
    while pending:
        path = pending.pop(0)
        if path not in active:
            active.add(path)
            pending.extend(references[path])
    return TypeScriptPrograms(
        tuple(os.path.relpath(path, project.root_dir or ".") for path in selected),
        frozenset(file for path in active for file in program_files[path]),
        tuple(active),
    )


async def _prepare_tsc_build_process(
    project: NodeJSProject,
    subsystem: TypeScriptSubsystem,
    input_digest: Digest,
    package_output_dirs: tuple[str, ...],
    project_targets: list[Target],
    build_root: BuildRoot,
    config_paths: tuple[str, ...],
) -> Process:
    tsc_args = ("--build", *config_paths, *subsystem.extra_build_args)
    tsc_wrapper_filename = "__tsc_wrapper.sh"
    named_cache_local_dir = "typescript_cache"
    named_cache_sandbox_mount_dir = "._tsc_cache"

    project_resolve = ChosenNodeResolve(project)

    script_digest = await create_tsc_wrapper_script(
        CreateTscWrapperScriptRequest(
            project=project,
            package_output_dirs=package_output_dirs,
            build_root=build_root,
            named_cache_sandbox_mount_dir=named_cache_sandbox_mount_dir,
            tsc_wrapper_filename=tsc_wrapper_filename,
        ),
        **implicitly(),
    )

    tool_input = await merge_digests(MergeDigests([input_digest, script_digest]))

    tool_request = subsystem.request(
        args=tsc_args,
        input_digest=tool_input,
        description=f"Type-check TypeScript programs {config_paths} ({len(project_targets)} selected targets)",
        level=LogLevel.DEBUG,
        project_caches=FrozenDict({named_cache_local_dir: named_cache_sandbox_mount_dir}),
    )

    # Uses the project's resolve as TypeScript execution requires project deps.
    tool_request_with_resolve: NodeJSToolRequest = replace(
        tool_request, resolve=project_resolve.resolve_name
    )

    process = await prepare_tool_process(tool_request_with_resolve, **implicitly())

    process_with_wrapper = replace(
        process,
        argv=(f"./{tsc_wrapper_filename}",) + process.argv,
        working_directory=project.root_dir,
        output_directories=package_output_dirs,
    )

    return process_with_wrapper


async def _typecheck_single_project(
    project: NodeJSProject,
    subsystem: TypeScriptSubsystem,
    check_subsystem: CheckSubsystem,
    global_options: GlobalOptions,
    all_targets: AllTargets,
    all_projects: AllNodeJSProjects,
    all_package_jsons: AllPackageJson,
    all_ts_configs: AllTSConfigs,
    build_root: BuildRoot,
    field_sets: tuple[TypeScriptCheckFieldSet, ...],
) -> CheckResult:
    project_package_jsons, project_ts_configs = _collect_project_configs(
        project, all_package_jsons, all_ts_configs
    )

    project_targets = await _collect_project_targets(
        project, all_targets, all_projects, project_ts_configs
    )

    if not project_targets:
        return CheckResult(
            exit_code=0,
            stdout="",
            stderr="",
            partition_description=f"TypeScript check on {project.root_dir} (no targets)",
        )

    # Imported assets come from the inferred dependency closure. Unimported declarations
    # are discovered by their filenames below, then hydrated only for active programs.
    all_workspace_sources = await _hydrate_project_sources(project_targets)
    input_digest = await _prepare_compilation_input(
        project,
        project_targets,
        project_package_jsons,
        project_ts_configs,
        all_workspace_sources,
    )
    package_output_dirs = _collect_package_output_dirs(
        project, project_ts_configs, Path(project.root_dir)
    )

    candidates = await _collect_project_targets(
        project, all_targets, all_projects, project_ts_configs, include_assets=True
    )
    assets = {
        target[field_type].file_path: target
        for target in candidates
        for field_type in (FileSourceField, ResourceSourceField)
        if target.has_field(field_type)
    }
    selection = await _select_tsconfig_programs(
        project,
        subsystem,
        input_digest,
        project_ts_configs,
        tuple(field_set.sources.file_path for field_set in field_sets),
        tuple(assets),
        global_options,
    )
    if isinstance(selection, CheckResult):
        return selection
    if not selection.config_paths:
        return CheckResult(
            exit_code=0,
            stdout="",
            stderr="",
            partition_description=f"TypeScript check on {project.root_dir} (no selected source in a TypeScript program)",
        )
    actual_assets = await _hydrate_project_sources(
        [target for path, target in assets.items() if path in selection.source_files]
    )
    selected_configs = await path_globs_to_digest(PathGlobs(selection.config_files), **implicitly())
    # The compile gets actual contents only. Discovery's empty inventory never reaches tsc --build.
    input_digest = await merge_digests(
        MergeDigests([input_digest, actual_assets, selected_configs])
    )
    config_paths = selection.config_paths
    selected_addresses = {field_set.address for field_set in field_sets}
    selected_targets = [
        target for target in project_targets if target.address in selected_addresses
    ]

    process = await _prepare_tsc_build_process(
        project,
        subsystem,
        input_digest,
        package_output_dirs,
        selected_targets,
        build_root,
        config_paths,
    )

    process = replace(process, cache_scope=check_subsystem.default_process_cache_scope)

    result = await execute_process(process, **implicitly())

    return CheckResult.from_fallible_process_result(
        result,
        partition_description=f"TypeScript check on {config_paths} ({len(selected_targets)} selected targets)",
        output_simplifier=global_options.output_simplifier(),
    )


@rule(desc="Check TypeScript compilation")
async def typecheck_typescript(
    request: TypeScriptCheckRequest,
    subsystem: TypeScriptSubsystem,
    check_subsystem: CheckSubsystem,
    global_options: GlobalOptions,
    build_root: BuildRoot,
) -> CheckResults:
    if subsystem.skip:
        return CheckResults([], checker_name=request.tool_name, output_per_partition=False)

    field_sets = request.field_sets
    (
        all_projects,
        all_targets,
        all_package_jsons,
        all_ts_configs,
        owning_packages,
    ) = await concurrently(
        find_node_js_projects(**implicitly()),
        find_all_targets(),
        all_package_json(),
        construct_effective_ts_configs(),
        concurrently(
            find_owning_package(OwningNodePackageRequest(field_set.address), **implicitly())
            for field_set in field_sets
        ),
    )

    projects: dict[NodeJSProject, list[TypeScriptCheckFieldSet]] = {}
    for field_set, owning_package in zip(field_sets, owning_packages):
        if owning_package.target:
            package_directory = owning_package.target.address.spec_path
            owning_project = all_projects.project_for_directory(package_directory)
            if owning_project:
                projects.setdefault(owning_project, []).append(field_set)

    project_results = await concurrently(
        _typecheck_single_project(
            project,
            subsystem,
            check_subsystem,
            global_options,
            all_targets,
            all_projects,
            all_package_jsons,
            all_ts_configs,
            build_root,
            tuple(project_field_sets),
        )
        for project, project_field_sets in projects.items()
    )

    return CheckResults(project_results, checker_name=request.tool_name, output_per_partition=False)


def rules():
    return [
        *collect_rules(),
        UnionRule(CheckRequest, TypeScriptCheckRequest),
    ]
