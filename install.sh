#!/usr/bin/env bash
#
# Installer for the Text Web Browser.
#
# - Checks for Python 3
# - Ensures Tkinter is available (offers to install it via your package manager)
# - Installs a `textbrowser` launcher onto your PATH
#
# Usage:
#   ./install.sh            # install to ~/.local/bin (no sudo)
#   PREFIX=/usr/local ./install.sh   # install to /usr/local/bin (may need sudo)
#
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SRC_DIR/textbrowser.py"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

[ -f "$APP" ] || die "textbrowser.py not found next to this script."

# --- Python 3 -------------------------------------------------------------
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || die "python3 not found. Please install Python 3.7+."
info "Found $($PYTHON --version 2>&1)"

# --- Tkinter --------------------------------------------------------------
tk_ok() { "$PYTHON" -c "import tkinter" >/dev/null 2>&1; }

install_tkinter() {
    local pm
    if   command -v apt-get >/dev/null 2>&1; then pm="sudo apt-get install -y python3-tk";
    elif command -v dnf     >/dev/null 2>&1; then pm="sudo dnf install -y python3-tkinter";
    elif command -v yum     >/dev/null 2>&1; then pm="sudo yum install -y python3-tkinter";
    elif command -v pacman  >/dev/null 2>&1; then pm="sudo pacman -S --noconfirm tk";
    elif command -v zypper  >/dev/null 2>&1; then pm="sudo zypper install -y python3-tk";
    elif command -v brew    >/dev/null 2>&1; then pm="brew install python-tk";
    else
        warn "Could not detect a package manager. Install Tkinter manually, e.g. python3-tk."
        return 1
    fi
    info "Installing Tkinter:  $pm"
    eval "$pm"
}

if tk_ok; then
    info "Tkinter is available."
else
    warn "Tkinter is not available."
    if install_tkinter && tk_ok; then
        info "Tkinter installed."
    else
        warn "Tkinter still unavailable; the launcher will be installed but the app needs Tkinter to run."
    fi
fi

# --- Install launcher -----------------------------------------------------
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
TARGET="$BIN_DIR/textbrowser"

mkdir -p "$BIN_DIR"
chmod +x "$APP" 2>/dev/null || true

cat > "$TARGET" <<EOF
#!/usr/bin/env bash
exec "$PYTHON" "$APP" "\$@"
EOF
chmod +x "$TARGET"

info "Installed launcher: $TARGET"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR is not on your PATH. Add it, e.g.:"
       printf '       echo '\''export PATH="%s:$PATH"'\'' >> ~/.bashrc\n' "$BIN_DIR" ;;
esac

info "Done. Run:  textbrowser example.com"
