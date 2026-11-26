#!/usr/bin/env bash
# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

# Pants uses its own interpreter in clean subprocesses. The runner's setup-python interpreter can depend on
# LD_LIBRARY_PATH, which those processes intentionally do not inherit. Use Pants' pinned standalone Python instead.
set -euo pipefail

readonly release="3.14.0+20251014"
readonly sha256="493c477b4a88bb1ea2f6c6f57fa0e88ffbe55d9e7b1405c4699f2d41c04eb154"
readonly url="https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-${release}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"

if [[ $(uname -sm) != 'Linux x86_64' ]]; then
  echo 'The CI bootstrap requires Linux x86_64' >&2
  exit 1
fi
: "${RUNNER_TEMP:?the job needs its own temporary directory}"
cache="${RUNNER_TOOL_CACHE:-${HOME}/.cache}/dspot-python/${release}"
archive="$(mktemp "${RUNNER_TEMP}/dspot-python-archive.XXXXXXXX")"
trap 'rm -f "${archive}"' EXIT
pinned() { printf '%s  %s\n' "${sha256}" "$1" | sha256sum --check --status; }

if [[ -f "${cache}/release.tar.gz" && ! -L "${cache}/release.tar.gz" ]] &&
  cp "${cache}/release.tar.gz" "${archive}" && pinned "${archive}"; then
  echo "Standalone Python ${release} from the runner cache" >&2
else
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    --connect-timeout 10 --max-time 120 "${url}" --output "${archive}"
  if ! pinned "${archive}"; then
    echo 'Refusing a standalone Python archive with the wrong checksum' >&2
    exit 1
  fi
  mkdir -p "${cache}"
  cp "${archive}" "${cache}/release.tar.gz.part.$$"
  mv -f "${cache}/release.tar.gz.part.$$" "${cache}/release.tar.gz"
fi

# Extract into this job's directory, rather than sharing an interpreter installation between concurrent jobs.
installation="$(mktemp -d "${RUNNER_TEMP}/dspot-python.XXXXXXXX")"
tar -xzf "${archive}" -C "${installation}"
python="${installation}/python/bin/python3.14"
env -i "${python}" --version >&2
printf '%s\n' "${python}"
