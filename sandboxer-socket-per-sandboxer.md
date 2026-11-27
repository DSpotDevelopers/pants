# sandboxer-socket-per-sandboxer: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/sandboxer-socket-per-sandboxer` at `8c21fe964`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 17.
- **Files:** `docs/notes/2.35.x.md`, `src/rust/process_execution/sandboxer/src/lib.rs`, `src/rust/process_execution/sandboxer/src/tests.rs`.
- **Tests:** `src/rust/process_execution/sandboxer/src/tests.rs`. Run: `cargo test` in the changed crate (upstream CI).
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "### General".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Upstream's own #23720 (our patch 15) named one socket per process; this is the next step, for two Sandboxers in one process. The Rust test was resolved beside upstream's new `test_sandboxer_service_missing_digest`; not compiled here.

## Feedback applied
- F4: note in 2.35.x.md, worded as a fix
- F7
- F6: the Rust change keeps its logic outside macro bodies
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(sandboxer): two Sandboxers of one process get their own sockets (red)

pantsd builds a new scheduler, and so a new Sandboxer, when its options change, while the old
one's server still runs. With patch 15's per-process name both use sandboxer-<pid>.sock.

Red: cargo test -p sandboxer --lib test_each_sandboxer_of_one_process_has_its_own_socket fails,
left == right == .../sandboxer-<pid>.sock.


### sandboxer: each Sandboxer gets its own socket, not one per process

A process can hold two Sandboxers at once: pantsd builds a new scheduler,
and so a new Sandboxer, when its options change, while the old Sandboxer's
server still runs until it is dropped. With one socket path per process
(`sandboxer-<pid>.sock`), the new client could connect to the old server and
lose it mid-request. Each Sandboxer now names its socket by its process and
its own number (`sandboxer-<pid>-<n>.sock`).

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
