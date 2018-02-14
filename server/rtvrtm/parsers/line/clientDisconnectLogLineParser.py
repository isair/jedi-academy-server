from __future__ import with_statement

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer


class ClientDisconnectLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("ClientDisconnect:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        try:
            player_id = int(line.data[18:])
            del self.jaserver.players[player_id]
        except KeyError:
            pass
