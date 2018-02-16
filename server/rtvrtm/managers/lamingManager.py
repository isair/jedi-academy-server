from __future__ import with_statement

import os
import threading
from datetime import datetime

from ..models.player import Player
from ..utility import tail


class LamingManager:

    def __init__(self, jaserver):
        self.jaserver = jaserver

    def check_player(self, player, previous_score):
        """Checks a player's laming suspicion score and takes necessary action."""
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
        elif score == 2:
            print("[LamingManager] Possible lamer: %d" % player.id)
            self.jaserver.svsay("^1FBI^7: %s ^7has been kicked for highly suspected laming." % player.name)
            self.jaserver.ban_manager.kick(player, " for possible laming", True)
            self.log_incident(player)
        elif score >= 3:
            print("[LamingManager] Lamer: %d" % player.id)
            self.jaserver.ban_manager.ban(player, " for laming", True)
            self.log_incident(player)

    def log_incident(self, player):
        threading.Thread(target=self.__log_incident__, args=(player,)).start()

    def __log_incident__(self, player):
        directoryName = "/jedi-academy/laming-manager-logs/"
        directoryName += player.ip if player.name == "" else player.name
        if not os.path.exists(directoryName):
            os.makedirs(directoryName)
        fileName = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        fileName += "-" + str(player.kill_info.lamer_suspicion_score) + ".txt"
        destination = directoryName + "/" + fileName
        # TODO: Read log path from config.
        with open("/root/.ja/MBII/log.txt", "rt") as f:
            log_lines = tail(f, lines=200)
        with open(destination, "wt") as f:
            f.write(log_lines)
