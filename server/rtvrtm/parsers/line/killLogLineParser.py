from __future__ import with_statement

from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...models.kill import Kill
from ...models.logLine import LogLine


class KillLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("Kill:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        data_str = line.data[6:]
        data_str_pieces = data_str.split(" ")
        killer_id = int(data_str_pieces[0])
        victim_id = int(data_str_pieces[1])
        killer = self.jaserver.players.get(killer_id, None)
        if killer is not None:
            if self.jaserver.gamemode == "duel":
                # Keep detailed track of kills and calculate lamer suspicion score only on duel servers.
                previous_suspicion_score = killer.kill_info.lamer_suspicion_score
                killer.kill_info.add_kill(Kill(line.time, killer_id, victim_id))
                self.jaserver.judgment_manager.check_kill_info(killer, previous_suspicion_score)
            victim = self.jaserver.players.get(victim_id, None)
            if victim is not None:
                victim.kill_info.last_killer = killer
