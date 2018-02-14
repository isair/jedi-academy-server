from __future__ import with_statement

import re

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer


class ClientUserinfoChangedLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("ClientUserinfoChanged:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        player_id = int(line.data[23:25])
        player = self.jaserver.players.get(player_id)
        if player is not None:
            try:
                player.name = re.findall(r'n\\([^\\]*)', line)[0]
            except Exception:
                player.name = ""
