#!/usr/bin/env sh
set -eu
PREFIX=${PREFIX:-"$HOME/.local"}
BIN_DIR="$PREFIX/bin"
APP_DIR="$PREFIX/lib/packet-odyssey-cli"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$BIN_DIR" "$APP_DIR"
rm -rf "$APP_DIR/src"
cp -R "$SCRIPT_DIR/src" "$APP_DIR/src"
cat > "$BIN_DIR/packet-odyssey" <<WRAPPER
#!/usr/bin/env sh
PYTHONPATH="$APP_DIR/src\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m packet_odyssey "\$@"
WRAPPER
chmod +x "$BIN_DIR/packet-odyssey"
printf 'Installed packet-odyssey to %s\n' "$BIN_DIR/packet-odyssey"
printf 'Ensure %s is in your PATH.\n' "$BIN_DIR"
