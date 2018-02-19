from __future__ import with_statement

import os
import threading
from datetime import datetime

from ..managers.pushNotificationManager import PushNotificationManager
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
                print("[LamingManager] Suspect: %d" % player.identifier)
                self.jaserver.svsay(
                    "^2[Fairplay] ^7%s ^7is now a laming suspect. An admin has been notified." % player.name)
                PushNotificationManager.send("[%s] %s (%d|%s) has been warned." % (self.jaserver.gamemode,
                                                                                   player.clean_name,
                                                                                   player.identifier,
                                                                                   player.ip))
                self.log_incident(player)
            # TODO: Check reports.
        elif score >= 2:
            print("[LamingManager] Possible lamer: %d" % player.identifier)
            self.jaserver.svsay(
                "^2[Fairplay] ^7%s ^7has been kicked for possible laming. An admin has been notified." % player.name)
            self.jaserver.ban_manager.kick(player, " for possible laming", True)
            PushNotificationManager.send("[%s] %s (%d|%s) has been kicked with score %d." % (self.jaserver.gamemode,
                                                                                             player.clean_name,
                                                                                             player.identifier,
                                                                                             player.ip,
                                                                                             score))
            self.log_incident(player)
        # elif score >= 3:
        #     print("[LamingManager] Lamer: %d" % player.id)
        #     self.jaserver.ban_manager.ban(player, " for laming", True)
        #     self.log_incident(player)

    @staticmethod
    def log_incident(player):
        threading.Thread(target=LamingManager.__log_incident, args=(player,)).start()

    @staticmethod
    def __log_incident(player):
        directory_name = "/jedi-academy/laming-manager-logs/"
        directory_name += player.ip if player.name == "" else player.name
        if not os.path.exists(directory_name):
            os.makedirs(directory_name)
        file_name = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        file_name += "-" + str(player.kill_info.lamer_suspicion_score) + ".txt"
        destination = directory_name + "/" + file_name
        # TODO: Read log path from config.
        with open("/root/.ja/MBII/log.txt", "rt") as f:
            log_lines = tail(f, lines=300)
        with open(destination, "wt") as f:
            f.write(log_lines)
