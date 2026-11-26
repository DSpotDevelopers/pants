#!/usr/bin/env bash
# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

# Builds DSpot's Pants release with Pants' own release steps (the wheels, then the PEX), linking every native file
# against glibc 2.28, the manylinux_2_28 floor DSPOT-PATCHES.md names, without a container: zig supplies the 2.28
# glibc stubs, and cargo-zigbuild's `zig cc` mode adapts rustc's linker arguments to it. The release is refused when
# any native file of its wheel or PEX needs a newer glibc.
#
# Run by .github/workflows/dspot-pants.yaml's build job from the checked-out source, after the source's Rust
# toolchain and protoc are installed, with PY naming the release's Python and EXPECTED_HEAD the source's commit.

set -euo pipefail

readonly GLIBC="2.28"
readonly ZIG_VERSION="0.15.2"
readonly ZIG_SHA256="02aa270f183da276e5b5920b1dac44a63f1a49e55050ebde3aecc9eb82f93239"
readonly CARGO_ZIGBUILD_VERSION="0.22.1"

repo="$(git rev-parse --show-toplevel)"
cd "${repo}"
test "$(git rev-parse HEAD)" = "${EXPECTED_HEAD:?the source commit this run builds}"

# zig, pinned by version and checksum, kept in the runner's tool cache.
zig_home="${RUNNER_TOOL_CACHE:-${HOME}/.cache}/dspot-zig/${ZIG_VERSION}"
if [[ ! -x "${zig_home}/zig" ]]; then
  archive="$(mktemp)"
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    "https://ziglang.org/download/${ZIG_VERSION}/zig-x86_64-linux-${ZIG_VERSION}.tar.xz" --output "${archive}"
  echo "${ZIG_SHA256}  ${archive}" | sha256sum --check --strict -
  unpacked="$(mktemp -d)"
  tar --extract --xz --file "${archive}" --directory "${unpacked}" --strip-components=1
  mkdir -p "$(dirname "${zig_home}")"
  rm -rf "${zig_home}"
  mv "${unpacked}" "${zig_home}"
  rm -f "${archive}"
fi
export PATH="${zig_home}:${PATH}"

# cargo-zigbuild, pinned by version and its lockfile.
if [[ "$(cargo-zigbuild --version 2> /dev/null || true)" != "cargo-zigbuild ${CARGO_ZIGBUILD_VERSION}" ]]; then
  cargo install --locked --quiet cargo-zigbuild --version "${CARGO_ZIGBUILD_VERSION}"
fi
zigbuild="$(command -v cargo-zigbuild)"

# The compiler and linker wrappers, as cargo-zigbuild writes its own, in the runner's temp folder: outside the checkout,
# whose build-support/bin/rust files the engine hash covers, so the tests job (another checkout of the same source)
# computes the same hash and takes the natives this job hands it.
wrappers="${RUNNER_TEMP:?the runner temp folder}/dspot-glibc-${GLIBC}"
mkdir -p "${wrappers}"
# The bootstrap reuses a cached engine of the same source whatever it was linked against (its cache key, the engine
# hash, does not cover the linker), so a release clears that cache and links its own.
rm -rf "${HOME}/.cache/pants/native_code"
for tool in cc c++; do
  cat > "${wrappers}/${tool}" << EOF
#!/bin/sh
exec "${zigbuild}" zig ${tool} -- -g -fno-sanitize=all -target x86_64-linux-gnu.${GLIBC} "\$@"
EOF
  chmod +x "${wrappers}/${tool}"
done
# Python's wheel backend uses these; Rust's native builds use the target-specific settings.
export CC="${wrappers}/cc"
export LDSHARED="${wrappers}/cc -shared"
export CC_x86_64_unknown_linux_gnu="${wrappers}/cc"
export CXX_x86_64_unknown_linux_gnu="${wrappers}/c++"
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="${wrappers}/cc"
# aws-lc's jitter entropy source must be compiled without optimisation, which zig's driver does not keep.
export AWS_LC_SYS_NO_JITTER_ENTROPY=1

TIMEFORMAT='release elapsed=%R user=%U system=%S seconds'
time {
  ./pants run src/python/pants_release/release.py -- build-wheels
  ./pants package src/python/pants:pants-pex
}

"${PY:-python3}" build-support/bin/dspot_glibc_floor.py --glibc "${GLIBC}" \
  dist/deploy/wheels/pantsbuild.pants/*/pantsbuild_pants-*-manylinux*.whl \
  dist/src.python.pants/pants-pex.pex
