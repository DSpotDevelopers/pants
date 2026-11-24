# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).


from pants.backend.python.target_types import (
    PythonSourcesGeneratorTarget,
    PythonSourceTarget,
    PythonTestsGeneratorTarget,
    PythonTestTarget,
    PythonTestUtilsGeneratorTarget,
)
from pants.core.target_types import (
    FilesGeneratorTarget,
    FileTarget,
    ResourcesGeneratorTarget,
    ResourceTarget,
)
from pants.engine.target import BoolField


class SkipRuffField(BoolField):
    alias = "skip_ruff"
    default = False
    help = "If True, do not run any Ruff tools on this target's code."


def rules():
    return [
        PythonSourcesGeneratorTarget.register_plugin_field(SkipRuffField),
        PythonSourceTarget.register_plugin_field(SkipRuffField),
        PythonTestsGeneratorTarget.register_plugin_field(SkipRuffField),
        PythonTestTarget.register_plugin_field(SkipRuffField),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipRuffField),
        FileTarget.register_plugin_field(SkipRuffField),
        FilesGeneratorTarget.register_plugin_field(SkipRuffField),
        ResourceTarget.register_plugin_field(SkipRuffField),
        ResourcesGeneratorTarget.register_plugin_field(SkipRuffField),
    ]
