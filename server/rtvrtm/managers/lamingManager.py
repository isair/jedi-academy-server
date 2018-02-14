from __future__ import with_statement

from ..models.player import Player


class LamingManager:

    def __init__(self, jaserver):
        self.jaserver = jaserver

    def check_player(self, player, previous_score):
        """Updates a player's laming suspicion score and takes necessary action."""
        assert isinstance(player, Player)
        assert isinstance(previous_score, int)
        score = player.kill_info.lamer_suspicion_score
        if score == 0:
            # TODO: Check reports.
            return
        elif score == 1:
            if score != previous_score:
                print("[LamingManager] Suspect: %d" % player.id)
                self.jaserver.svsay("^1FBI^7: %s ^7is now a laming suspect." % player.name)
            # TODO: Check reports.
            return
        elif score == 2:
            print("[LamingManager] Possible lamer: %d" % player.id)
            self.jaserver.svsay("^1FBI^7: %s ^7has been kicked for highly suspected laming." % player.name)
            self.jaserver.ban_manager.kick(player, " for possible laming", True)
        elif score >= 3:
            print("[LamingManager] Lamer: %d" % player.id)
            self.jaserver.ban_manager.ban(player, " for laming", True)
