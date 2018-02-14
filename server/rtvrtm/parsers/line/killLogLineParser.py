from __future__ import with_statement

from logLineParser import LogLineParser, LogLine
from ...jaserver import JAServer
from ...models.kill import Kill


class KillLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        return line.data.startswith("Kill:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        if self.jaserver.gamemode != "duel":
            # No need to track kills and calculate suspicion scores unless it's a duel server.
            return
        data_str = line.data[6:]
        data_str_pieces = data_str.split(" ")
        killer_id = int(data_str_pieces[0])
        victim_id = int(data_str_pieces[1])
        killer = self.jaserver.players.get(killer_id, None)
        if killer is not None:
            previous_suspicion_score = killer.kill_info.lamer_suspicion_score
            killer.kill_info.add_kill(Kill(line.time, killer_id, victim_id))
            self.jaserver.laming_manager.check_player(killer, previous_suspicion_score)
