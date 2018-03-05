from __future__ import with_statement

import re

from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...models.logLine import LogLine
from ...models.player import Player


class ClientConnectLogLineParser(LogLineParser):

    def __init__(self, jaserver, catch_up=False):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        assert isinstance(catch_up, bool)
        self.jaserver = jaserver
        self.catch_up = catch_up

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("ClientConnect:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        player_id = int(line.data[15:17])
        player_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line.data)[0]
        player = self.jaserver.players.get(player_id, None)
        if player is not None:
            player.ip = player_ip
        else:
            player = Player(player_id, player_ip)
        self.jaserver.players[player_id] = player
        if not self.catch_up:
            self.jaserver.judgment_manager.check_entry(player)
