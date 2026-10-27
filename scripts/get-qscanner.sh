#!/usr/bin/env bash
# Download the CNAPP demo qscanner build for this OS/arch from the GitHub release.
# Usage: scripts/get-qscanner.sh [dest_dir]   -> prints path to the qscanner binary
# Env:   QSCANNER_RELEASE_TAG (default: newest qscanner-* release), GH_TOKEN (CI)
set -euo pipefail

REPO="nelssec/pipeline-demo"
DEST="${1:-$(pwd)/bin}"
mkdir -p "$DEST"

os=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m)
case "$arch" in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) echo "unsupported arch $arch" >&2; exit 1 ;;
esac
platform="${os}-${arch}"

TAG="${QSCANNER_RELEASE_TAG:-}"
if [[ -z "$TAG" ]]; then
  TAG=$(gh release list --repo "$REPO" --limit 50 --json tagName -q '[.[] | select(.tagName | startswith("qscanner-"))][0].tagName')
fi
[[ -n "$TAG" ]] || { echo "no qscanner-* release found in $REPO" >&2; exit 1; }

tmp=$(mktemp -d)
gh release download "$TAG" --repo "$REPO" --dir "$tmp" --pattern "*.${platform}.tar.gz" --pattern SHA256SUMS
( cd "$tmp" && grep "${platform}.tar.gz" SHA256SUMS | shasum -a 256 -c - >/dev/null )
tar -C "$DEST" -xzf "$tmp"/*."${platform}".tar.gz qscanner
chmod +x "$DEST/qscanner"
rm -rf "$tmp"
echo "$DEST/qscanner"
