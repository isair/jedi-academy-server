from __future__ import with_statement

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer


class ServerStartLogLineParser(LogLineParser):

    def __init__(self, jaserver):
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
