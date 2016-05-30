#! /bin/bash

GAME_APP_PATH="/Volumes/Storage/SteamLibrary/steamapps/common/Jedi Academy/SWJKJA.app"
NET_PORT=29071
FS_GAME=base
SERVER_CFG=server.cfg
RTVRTM_CFG=rtvrtm.cfg

docker rm -f ja 2>/dev/null

docker run \
  -t=true \
  -d \
  --restart=always \
  --name ja \
  -v "$GAME_APP_PATH/Contents":"/jedi-academy" \
  -e NET_PORT="$NET_PORT" \
  -e FS_GAME="$FS_GAME" \
  -e SERVER_CFG="$SERVER_CFG" \
  -e RTVRTM_CFG="$RTVRTM_CFG" \
  --net=host \
  -p "$NET_PORT" \
  bsencan/jedi-academy-server
