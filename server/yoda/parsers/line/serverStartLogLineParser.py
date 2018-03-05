from __future__ import with_statement

from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...models.logLine import LogLine


class ServerStartLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.time == 0 and line.data == "------------------------------------------------------------"

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        self.jaserver.players = {}
        self.jaserver.cvars = None
