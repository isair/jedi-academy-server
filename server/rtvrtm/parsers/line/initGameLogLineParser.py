from __future__ import with_statement

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer


class InitGameLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("InitGame:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        cvars = line.data[11:].split("\\")
        cvars = dict((cvars[i].lower(), cvars[i + 1]) for i in xrange(0, len(cvars), 2))
        cvars["g_authenticity"] = int(cvars["g_authenticity"])
        self.jaserver.cvars = cvars
