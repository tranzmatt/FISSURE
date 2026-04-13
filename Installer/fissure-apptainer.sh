#!/bin/bash
set -e

FISSURE_DIR="__FISSURE_DIR__"
FISSURE_MODE="__FISSURE_MODE__"
CONTAINER_DIR="$HOME/fissure_apptainer"
ENV_FILE="$FISSURE_DIR/.env"

#######################################
# Ensure PostgreSQL container is running
#######################################
if [[ "$FISSURE_MODE" == "full" || "$FISSURE_MODE" == "base" || "$FISSURE_MODE" == "HIPRFISR" ]]; then
    cd "$FISSURE_DIR"
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
    else
        echo "[!] No .env file found — creating from example.env"
        cp example.env .env
        source .env
    fi

    echo "[*] Checking PostgreSQL container..."
    if ! sudo docker compose ps | grep -q "Up"; then
        echo "[*] Starting PostgreSQL container..."
        sudo docker compose up -d
    else
        echo "[✓] PostgreSQL container already running."
    fi


    # Wait for database to be ready
    echo "[*] Waiting for PostgreSQL to respond..."
    export PGPASSWORD="$POSTGRES_PASSWORD"
    until pg_isready -U "$POSTGRES_USER" -h "$POSTGRES_HOST" -p "$POSTGRES_EXTERNAL_PORT" >/dev/null 2>&1; do
        sleep 2
    done
    echo "[✓] PostgreSQL ready."
fi

#######################################
# Prepare Pulse Audio
#######################################
if [ -f "$HOME/.config/pulse/cookie" ]; then
    cp "$HOME/.config/pulse/cookie" /tmp/pulse-cookie
    chmod 644 /tmp/pulse-cookie
else
    echo "[!] PulseAudio cookie not found for $USER"
fi

#######################################
# Launch FISSURE Apptainer
#######################################
echo "[*] Launching FISSURE Apptainer..."

# Detect display server type
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
  echo "[*] Wayland session detected."
  # Needed for GUI apps under Wayland
  xhost +local:root 2>/dev/null || true
  RUNTIME_DEST="/tmp/runtime-user"
  sudo mkdir -p "$RUNTIME_DEST"

  sudo apptainer shell \
    --writable \
    --bind /dev/bus/usb:/dev/bus/usb \
    $(for dev in /dev/ttyACM* /dev/ttyUSB*; do [ -e "$dev" ] && echo --bind "$dev:$dev"; done) \
    --bind /run/udev:/run/udev \
    --bind /run/user/$(id -u $SUDO_USER)/pulse:/tmp/pulse \
    --bind "$XDG_RUNTIME_DIR:$RUNTIME_DEST" \
    --env DISPLAY=$DISPLAY \
    --env XDG_RUNTIME_DIR=$RUNTIME_DEST \
    --env QT_QPA_PLATFORM=xcb \
    --env PULSE_SERVER=unix:/tmp/pulse/native \
    --env PULSE_COOKIE=/tmp/pulse-cookie \
    "$CONTAINER_DIR"

else
  echo "[*] X11 session detected."
  xhost +local:root 2>/dev/null || true

  sudo apptainer shell \
    --writable \
    --bind /dev/bus/usb:/dev/bus/usb \
    $(for dev in /dev/ttyACM* /dev/ttyUSB*; do [ -e "$dev" ] && echo --bind "$dev:$dev"; done) \
    --bind /run/udev:/run/udev \
    --bind /tmp/.X11-unix:/tmp/.X11-unix \
    --bind /run/user/$(id -u $SUDO_USER)/pulse:/tmp/pulse \
    --env DISPLAY=$DISPLAY \
    --env PULSE_SERVER=unix:/tmp/pulse/native \
    --env PULSE_COOKIE=/tmp/pulse-cookie \
    "$CONTAINER_DIR"
fi
