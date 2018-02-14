from __future__ import with_statement

import re

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer
from ...models.player import Player


class ClientConnectLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("ClientConnect:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        player_id = int(line.data[15:17])
        player_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line.data)[0]
        self.jaserver.players[player_id] = Player(player_id, player_ip)
