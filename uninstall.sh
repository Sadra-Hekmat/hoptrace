#!/usr/bin/env sh
set -eu
PREFIX=${PREFIX:-"$HOME/.local"}
rm -f "$PREFIX/bin/packet-odyssey"
rm -rf "$PREFIX/lib/packet-odyssey-cli"
printf 'Removed Packet Odyssey CLI. History was preserved.\n'
