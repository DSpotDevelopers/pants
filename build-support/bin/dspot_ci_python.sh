#!/usr/bin/env bash
# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

# The same pinned, relocatable interpreter on every CI runner. setup-python's shared-library
# builds need LD_LIBRARY_PATH, which Pants deliberately doesn't pass to sandboxed children.
set -euo pipefail

# The Linux x86_64 distribution already pinned by core/subsystems/python_bootstrap.py.
readonly VERSION="3.14.0"
readonly RELEASE="20251014"
readonly SHA256="493c477b4a88bb1ea2f6c6f57fa0e88ffbe55d9e7b1405c4699f2d41c04eb154"
readonly URL="https://github.com/astral-sh/python-build-standalone/releases/download/${RELEASE}/cpython-${VERSION}+${RELEASE}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
root="${RUNNER_TOOL_CACHE:?}/dspot-python"
install="${root}/${VERSION}-${SHA256}"
mkdir -p "${root}"

# Concurrent slots may share the tool cache. Publish only a completely extracted installation.
exec 9> "${root}/install.lock"
flock 9
if [[ ! -x "${install}/bin/python3" ]]; then
  staging="$(mktemp -d "${root}/.install.XXXXXX")"
  trap 'rm -rf "${staging}"' EXIT
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "${URL}" --output "${staging}/python.tar.gz"
  echo "${SHA256}  ${staging}/python.tar.gz" | sha256sum --check --strict -
  tar --extract --gzip --file "${staging}/python.tar.gz" --directory "${staging}"
  mv "${staging}/python" "${install}"
  rm -rf "${staging}"
  trap - EXIT
fi
flock -u 9

# Exercise the exact property needed by archive extraction: no inherited loader/Python env.
env -i "${install}/bin/python3" -c 'import gzip, sys; assert sys.version_info[:3] == (3, 14, 0); print(sys.executable, sys.version)'
# Pants runs scripts through its dev-deps venv, not just the base interpreter.
probe="$(mktemp -d "${RUNNER_TEMP:?}/dspot-python-check.XXXXXX")"
trap 'rm -rf "${probe}"' EXIT
"${install}/bin/python3" -m venv --without-pip "${probe}"
env -i "${probe}/bin/python" -c 'import gzip; assert gzip.decompress(gzip.compress(b"bootstrap")) == b"bootstrap"; print("venv gzip: passed without loader environment")'
echo "PY=${install}/bin/python3" >> "${GITHUB_ENV:?}"
echo "${install}/bin" >> "${GITHUB_PATH:?}"
