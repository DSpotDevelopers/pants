# docker-archive-staging: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/docker-archive-staging` at `ded282e6f`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (Docker sandbox archives).
- **Files:** `src/rust/Cargo.lock`, `src/rust/Cargo.toml`, `src/rust/process_execution/docker/Cargo.toml`, `src/rust/process_execution/docker/src/lib.rs`, `src/rust/process_execution/docker/src/volume_archive.rs`.
- **Tests:** none changed. Run: `cargo test` in the changed crate (upstream CI).
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Adds `volume_archive.rs` and the `tar` crate; only declared here (#53/#54 use it). `Cargo.lock` gained only `tar` (its `filetime` and `libc` are in upstream's lock); not compiled here. Best opened together with the Docker volume change once #53/#54 settle on our fork.

## Feedback applied
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** (Groundwork) a Docker sandbox is to be transferred through Docker's archive API, without interpreting its path on the daemon host, and without changing CAS hardlinked inputs.
- **Change:** Adds `process_execution/docker/src/volume_archive.rs` (archive staging that unlinks original inputs before replacing them and never lets deleted inputs survive) and the `tar` crate. Used by the Docker sandbox-volume change, not yet prepared.
- **Tests:** Unit tests in `volume_archive.rs`.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
