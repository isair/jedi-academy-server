#! /bin/bash

# Environment variables and their default values.
[ -z "$NET_PORT" ] && NET_PORT=29070
[ -z "$FS_GAME" ] && FS_GAME=base
[ -z "$SERVER_CFG" ] && SERVER_CFG=server.cfg

# Symlink directories under /jedi-academy to /root/.local/share/openjk.
mkdir -p /root/.local/share/openjk
find /jedi-academy -maxdepth 1 -mindepth 1 -type d -exec ln -s "{}" /root/.local/share/openjk \; 2>/dev/null

# Configuration files need to be under /opt/ja-server/base directory.
mkdir -p /opt/ja-server/base
cp /jedi-academy/*.cfg /opt/ja-server/base

# Build the +set fs_game command.
SET_FS_GAME="+set fs_game $FS_GAME"
if [ "$FS_GAME" = base ]; then
  # Shouldn't +set fs_game for base.
  SET_FS_GAME=""
fi

# If an rtvrtm configuration file has been defined and it exists, start rtvrtm.
RTVRTM_CFG_PATH="/jedi-academy/$RTVRTM_CFG"
if [ -f "$RTVRTM_CFG_PATH" ]; then
  until (sleep 10; cd /jedi-academy && python /opt/yoda/run-rtvrtm.py -c "$RTVRTM_CFG"); do
    echo "RTVRTM crashed with exit code $?. Restarting..." >&2
  done &
fi

# Start the server.
/opt/ja-server/openjkded.i386 \
  $SET_FS_GAME \
  +set dedicated 2 \
  +set net_port "$NET_PORT" \
  +exec "$SERVER_CFG"
