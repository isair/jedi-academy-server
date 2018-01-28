#! /bin/bash

# Environment variables and their default values.
[ -z "$NET_PORT" ] && NET_PORT=29070
[ -z "$FS_GAME" ] && FS_GAME=base
[ -z "$SERVER_CFG" ] && SERVER_CFG=server.cfg

# Configuration files need to be under /root/.ja/base directory.
mkdir -p /root/.ja/base
cp /jedi-academy/*.cfg /root/.ja/base
cp /jedi-academy/*.dat /root/.ja/base

# Shouldn't +set fs_game for base.
SET_FS_GAME="+set fs_game $FS_GAME"
if [ "$FS_GAME" = base ]; then
  SET_FS_GAME=""
fi

# If an rtvrtm configuration file has been defined and it exists, start rtvrtm.
RTVRTM_CFG_PATH="/root/.ja/base/$RTVRTM_CFG"
if [ -f "$RTVRTM_CFG_PATH" ]; then
  cp /jedi-academy/*.txt /opt/rtvrtm
  mv "$RTVRTM_CFG_PATH" /opt/rtvrtm/rtvrtm.cfg
  until (sleep 10; python /opt/rtvrtm/rtvrtm.py -c /opt/rtvrtm/rtvrtm.cfg --noupdate); do
    echo "RTVRTM crashed with exit code $?. Restarting..." >&2
  done &
fi

# Start the server.
/opt/ja-server/linuxjampded \
  +set dedicated 2 \
  +set net_port "$NET_PORT" \
  "$SET_FS_GAME" \
  +exec "$SERVER_CFG"
