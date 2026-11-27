# buildbarn-relay-containerized-jobs: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/buildbarn-relay-containerized-jobs` at `de104aeae`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (Buildbarn integration tests).
- **Files:** `src/python/pants/engine/internals/buildbarn_integration_tests/buildbarn_test.py`, `src/python/pants/engine/internals/buildbarn_integration_tests/config/docker-compose.yaml`, `src/python/pants/engine/internals/buildbarn_integration_tests/docker_tunnel.py`, `src/python/pants/engine/internals/buildbarn_integration_tests/docker_tunnel_test.py`, `src/python/pants/engine/internals/buildbarn_integration_tests/stack.py`.
- **Tests:** `src/python/pants/engine/internals/buildbarn_integration_tests/buildbarn_test.py`, `src/python/pants/engine/internals/buildbarn_integration_tests/docker_tunnel_test.py`. Run: `pants test src/python/pants/engine/internals/buildbarn_integration_tests/buildbarn_test.py src/python/pants/engine/internals/buildbarn_integration_tests/docker_tunnel_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Test infrastructure: the Buildbarn integration tests reach their stack when the test job itself runs in a container. No release note.

## Feedback applied
- F7
- F1: every added comment read; the relay comment reworded from our fork's jargon into upstream's terms (de104aeae)

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** The Buildbarn integration tests reach their stack through host ports, which a test job that itself runs in a container cannot use.
- **Change:** The stack seeds its volumes through `compose cp`, and every gRPC stream reaches the cache/frontend from the stack's own network through a relay container in the stack; the test job needs no host port and joins no network.
- **Tests:** `buildbarn_test.py` and `docker_tunnel_test.py` (a real streaming child stands in for `docker exec`).

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
