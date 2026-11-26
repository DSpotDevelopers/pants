# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

# Who may start DSpot's Pants build, and how it builds the release: the files they read at run time.
python_tests(
    name="tests",
    dependencies=[
        "//.github/workflows:workflows",
        "//build-support/bin:dspot_release_build",
        "//build-support:venv_bootstrap",
    ],
)
