# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

import dataclasses
import os.path
from collections.abc import Iterable
from dataclasses import dataclass

from pants.backend.javascript import nodejs_project_environment
from pants.backend.javascript.dependency_inference.rules import rules as dependency_inference_rules
from pants.backend.javascript.nodejs_project import NodeJSProject
from pants.backend.javascript.nodejs_project_environment import (
    NodeJsProjectEnvironment,
    NodeJsProjectEnvironmentProcess,
    NodeJSProjectEnvironmentRequest,
    get_nodejs_environment,
    setup_nodejs_project_environment_process,
)
from pants.backend.javascript.package_json import (
    NodePackageNameField,
    NodePackageVersionField,
    PackageJsonSourceField,
)
from pants.backend.javascript.package_manager import PackageManager
from pants.backend.javascript.subsystems import nodejs
from pants.backend.javascript.target_types import JSRuntimeSourceField
from pants.build_graph.address import Address
from pants.core.environments.target_types import EnvironmentTarget
from pants.core.target_types import FileSourceField, ResourceSourceField
from pants.core.util_rules.source_files import (
    SourceFiles,
    SourceFilesRequest,
    determine_source_files,
)
from pants.engine.internals.graph import transitive_targets
from pants.engine.internals.native_engine import AddPrefix, Digest, MergeDigests
from pants.engine.intrinsics import add_prefix, merge_digests
from pants.engine.process import (
    Process,
    ProcessCacheScope,
    execute_process_or_raise,
    fallible_to_exec_result_or_raise,
)
from pants.engine.rules import Rule, collect_rules, implicitly, rule
from pants.engine.target import SourcesField, Target, TransitiveTargetsRequest
from pants.engine.unions import UnionMembership, UnionRule


@dataclass(frozen=True)
class InstalledNodePackageRequest:
    address: Address


@dataclass(frozen=True)
class InstalledNodePackage:
    project_env: NodeJsProjectEnvironment
    digest: Digest

    @property
    def project_dir(self) -> str:
        return self.project_env.root_dir

    def join_relative_workspace_directory(self, path: str) -> str:
        return os.path.join(self.project_env.relative_workspace_directory(), path)

    @property
    def target(self) -> Target:
        return self.project_env.ensure_target()

    @property
    def package_manager(self) -> PackageManager:
        return self.project_env.project.package_manager


@dataclass(frozen=True)
class InstalledNodePackageWithSource(InstalledNodePackage):
    pass


async def _get_relevant_source_files(
    sources: Iterable[SourcesField], with_js: bool = False
) -> SourceFiles:
    return await determine_source_files(
        SourceFilesRequest(
            sources,
            for_sources_types=(PackageJsonSourceField, FileSourceField)
            + ((ResourceSourceField, JSRuntimeSourceField) if with_js else ()),
            enable_codegen=True,
        )
    )


@dataclass(frozen=True)
class WorkspaceNodeProjectInstallRequest:
    project: NodeJSProject


@dataclass(frozen=True)
class WorkspaceNodeProjectInstalled:
    project: NodeJSProject


@rule
async def install_node_project_in_workspace(
    req: WorkspaceNodeProjectInstallRequest, environment: EnvironmentTarget
) -> WorkspaceNodeProjectInstalled:
    """In a workspace environment, install the whole project into the checkout, once per session.

    The install's result there is the project's node_modules in the checkout, which processes read in place; no
    digest of it is materialized. So it is never reused from the process cache (a new checkout under a warm cache
    would get no node_modules), and it is one install of the project, not one per package: every package of a
    project shares its node_modules tree, and concurrent installs into one tree race.
    """
    process = await setup_nodejs_project_environment_process(
        NodeJsProjectEnvironmentProcess(
            NodeJsProjectEnvironment.from_root(req.project),
            req.project.immutable_install_args,
            description=f"Installing the Node.js project at {req.project.root_dir or '.'} in the workspace.",
        ),
        **implicitly(),
    )
    process = dataclasses.replace(process, cache_scope=environment.default_cache_scope)
    await execute_process_or_raise(**implicitly({process: Process}))
    return WorkspaceNodeProjectInstalled(req.project)


@rule
async def install_node_packages_for_address(
    req: InstalledNodePackageRequest,
    union_membership: UnionMembership,
    nodejs: nodejs.NodeJS,
    environment: EnvironmentTarget,
) -> InstalledNodePackage:
    project_env = await get_nodejs_environment(NodeJSProjectEnvironmentRequest(req.address))
    target = project_env.ensure_target()
    transitive_tgts = await transitive_targets(
        TransitiveTargetsRequest([target.address]), **implicitly()
    )

    source_files = await _get_relevant_source_files(
        (tgt[SourcesField] for tgt in transitive_tgts.closure if tgt.has_field(SourcesField)),
        with_js=False,
    )
    package_digest = source_files.snapshot.digest

    if environment.default_cache_scope == ProcessCacheScope.PER_SESSION:
        await install_node_project_in_workspace(
            WorkspaceNodeProjectInstallRequest(project_env.project), **implicitly()
        )
        return InstalledNodePackage(project_env, digest=package_digest)

    install_result = await fallible_to_exec_result_or_raise(
        **implicitly(
            NodeJsProjectEnvironmentProcess(
                project_env,
                project_env.project.immutable_install_args,
                description=f"Installing {target[NodePackageNameField].value}@{target[NodePackageVersionField].value}.",
                include_workspace_dependencies=True,
                input_digest=package_digest,
                output_directories=tuple(project_env.node_modules_directories),
            )
        )
    )
    node_modules = await add_prefix(AddPrefix(install_result.output_digest, project_env.root_dir))

    return InstalledNodePackage(
        project_env,
        digest=await merge_digests(
            MergeDigests(
                [
                    package_digest,
                    node_modules,
                ]
            )
        ),
    )


@rule
async def add_sources_to_installed_node_package(
    req: InstalledNodePackageRequest,
) -> InstalledNodePackageWithSource:
    installation = await install_node_packages_for_address(req, **implicitly())
    transitive_tgts = await transitive_targets(
        TransitiveTargetsRequest([installation.target.address]), **implicitly()
    )

    source_files = await _get_relevant_source_files(
        (tgt[SourcesField] for tgt in transitive_tgts.dependencies if tgt.has_field(SourcesField)),
        with_js=True,
    )
    digest = await merge_digests(MergeDigests((installation.digest, source_files.snapshot.digest)))
    return InstalledNodePackageWithSource(installation.project_env, digest=digest)


def rules() -> Iterable[Rule | UnionRule]:
    return [
        *nodejs.rules(),
        *nodejs_project_environment.rules(),
        *dependency_inference_rules(),
        *collect_rules(),
    ]
