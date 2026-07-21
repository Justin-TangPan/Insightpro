#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="${COMPOSE_VERSION:-v5.3.1}"
ARCH="${COMPOSE_ARCH:-x86_64}"
BASE_URL="https://github.com/docker/compose/releases/download/${VERSION}"
ASSET="docker-compose-linux-${ARCH}"
INSTALL_PATH="${COMPOSE_INSTALL_PATH:-/usr/local/bin/docker-compose}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

curl --fail --location --silent --show-error \
  "${BASE_URL}/${ASSET}" -o "$TEMP_DIR/$ASSET"
curl --fail --location --silent --show-error \
  "${BASE_URL}/${ASSET}.sha256" -o "$TEMP_DIR/$ASSET.sha256"

(
  cd "$TEMP_DIR"
  sha256sum --check "$ASSET.sha256"
)

install -m 0755 "$TEMP_DIR/$ASSET" "$INSTALL_PATH"
"$INSTALL_PATH" version
