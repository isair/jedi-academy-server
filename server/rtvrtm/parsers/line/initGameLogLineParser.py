from __future__ import with_statement

from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...models.logLine import LogLine


class InitGameLogLineParser(LogLineParser):

    def __init__(self, jaserver, catch_up=False):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver
        self.catch_up = catch_up

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
        if self.catch_up:
            return
        self.jaserver.message_manager.say_timed_messages()
        for player in self.jaserver.players.values():
            player.duel_challengee = None
            player.duel_pair = None
