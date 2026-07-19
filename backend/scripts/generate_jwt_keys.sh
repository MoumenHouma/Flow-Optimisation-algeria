#!/usr/bin/env bash
# Generate an RS256 keypair for JWT signing (docs/ARCHITECTURE.md §5.1).
# Dev only — in prod, load keys from a vault. Output dir is git-ignored.
set -euo pipefail

KEYS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/keys"
mkdir -p "$KEYS_DIR"

openssl genrsa -out "$KEYS_DIR/jwt-private.pem" 2048
openssl rsa -in "$KEYS_DIR/jwt-private.pem" -pubout -out "$KEYS_DIR/jwt-public.pem"

echo "Wrote $KEYS_DIR/jwt-private.pem and jwt-public.pem"
echo "Set JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH in .env to point here."
