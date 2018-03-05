from __future__ import with_statement

import re

from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...models.logLine import LogLine


class ClientUserinfoChangedLogLineParser(LogLineParser):

    def __init__(self, jaserver, catch_up=False):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        assert isinstance(catch_up, bool)
        self.jaserver = jaserver
        self.catch_up = catch_up

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
                player.name = re.findall(r'n\\([^\\]*)', line.data)[0]
            except Exception:
                player.name = ""
            if not self.catch_up:
                self.jaserver.judgment_manager.check_info(player)
