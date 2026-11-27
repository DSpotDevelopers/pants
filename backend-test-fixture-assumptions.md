# backend-test-fixture-assumptions: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/backend-test-fixture-assumptions` at `05b1aec53`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: fork #43 (test repairs).
- **Files:** `src/python/pants/backend/cc/util_rules/toolchain_test.py`, `src/python/pants/backend/docker/goals/package_image_test.py`, `src/python/pants/backend/nfpm/native_libs/elfdeps/rules_integration_test.py`.
- **Tests:** `src/python/pants/backend/cc/util_rules/toolchain_test.py`, `src/python/pants/backend/docker/goals/package_image_test.py`, `src/python/pants/backend/nfpm/native_libs/elfdeps/rules_integration_test.py`. Run: `pants test src/python/pants/backend/cc/util_rules/toolchain_test.py src/python/pants/backend/docker/goals/package_image_test.py src/python/pants/backend/nfpm/native_libs/elfdeps/rules_integration_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Tests only (cc toolchain, docker package_image, nfpm elfdeps): no release note.

## Feedback applied
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** Three tests assume their host: the cc toolchain test, Docker's `package_image_test` (which reaches the real engine intrinsics), and nfpm's ELF dependency test, which calls `platform.architecture()`, which shells out to an ambient `file` program a sandbox may lack.
- **Change:** The fixtures stand in for those host facts.
- **Tests:** The three tests themselves.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
