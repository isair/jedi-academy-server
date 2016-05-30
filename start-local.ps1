$gameAppPath = "D:\SteamLibrary\steamapps\common\Jedi Academy\"
$netPort = 29071
$fsGame = "MBII"
$serverCfg = "server.cfg"
$rtvrtmCfg = "rtvrtm.cfg"

# docker.exe rm -f ja

& docker.exe run `
    -t=true `
    -d `
    --restart=always `
    --name ja `
    -v "${gameAppPath}\GameData":"/jedi-academy" `
    -e NET_PORT=${netPort} `
    -e FS_GAME=${fsGame} `
    -e SERVER_CFG=${serverCfg} `
    -e RTVRTM_CFG=${rtvrtmCfg} `
    --net=host `
    -p ${netPort} `
    bsencan/jedi-academy-server-private
