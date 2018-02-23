import datetime
import os
import threading

from pushNotificationManager import PushNotificationManager
from ..models.player import Player
from ..utility import tail


class JudgmentManager:
    spammer_mute_duration = 10  # in minutes

    def __init__(self, jaserver):
        self.jaserver = jaserver

    def check_entry(self, player):
        assert isinstance(player, Player)
        # If player is in the ban list, kick them.
        if self.jaserver.punishment_manager.is_banned(player):
            print("[JudgmentManager] Banned player login attempt: %s" % player.ip)
            self.log_incident("banned-entry-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)
        # Check if their name is allowed. Kick them if it's not.
        if player.clean_name in ("admin", "server"):
            print("[JudgmentManager] Admin impersonation attempt: %s" % player.ip)
            self.log_incident("admin-impersonation-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)

    def check_kill_info(self, player, previous_score):
        assert isinstance(player, Player)
        assert isinstance(previous_score, int)
        score = player.kill_info.lamer_suspicion_score
        if score == 0:
            # TODO: Check reports.
            return
        elif score == 1:
            if score != previous_score:
                self.__notify_about(player,
                                    public_message="is now a laming suspect. An admin has been notified",
                                    private_message="has been warned",
                                    log_message="Suspect")
                self.log_incident("lamer-warning", player=player, log_length=300)
            # TODO: Check reports.
        elif score >= 2:
            self.__notify_about(player,
                                public_message="has been kicked for possible laming. An admin has been notified",
                                private_message="has been kicked with suspicion score %d" % score,
                                log_message="Possible lamer")
            self.log_incident("lamer-kick", player=player, log_length=300)
            self.jaserver.punishment_manager.kick(player, automatic=True)

    def check_say_info(self, player):
        assert isinstance(player, Player)
        # If player is spamming, mute them.
        if player.say_info.is_spamming:
            duration = JudgmentManager.spammer_mute_duration
            private_message = "has been muted for spamming\nLast message: %s" % player.say_info.last_message
            self.__notify_about(player,
                                public_message="has been muted for %d minutes for spamming" % duration,
                                private_message=private_message,
                                log_message="Spammer")
            self.log_incident("mute", player=player, log_length=100)
            player.say_info.reset()
            self.jaserver.punishment_manager.mute(player, duration=duration, automatic=True)
            return True
        return False

    def __notify_about(self, player, public_message, private_message, log_message):
        print("[JudgmentManager] %s: %d" % (log_message, player.identifier))
        self.jaserver.svsay("^7%s ^7%s." % (player.name, public_message))
        PushNotificationManager.send("[%s] %s (%d|%s) %s." % (self.jaserver.gamemode,
                                                              player.clean_name,
                                                              player.identifier,
                                                              player.ip,
                                                              private_message))
        # TODO: Insert last kills info. include_latest_kills=False

    @staticmethod
    def log_incident(incident_type, player, log_length):
        assert isinstance(incident_type, str)
        assert isinstance(player, Player)
        assert isinstance(log_length, int)
        threading.Thread(target=JudgmentManager.__log_incident, args=(incident_type, player, log_length)).start()

    @staticmethod
    def __log_incident(incident_type, player, log_length):
        assert isinstance(incident_type, str)
        assert isinstance(player, Player)
        assert isinstance(log_length, int)
        directory_name = "/jedi-academy/judgment-manager-logs/" + incident_type + "/"
        directory_name += player.ip if player.name == "" else player.name
        if not os.path.exists(directory_name):
            os.makedirs(directory_name)
        file_name = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S") + ".txt"
        destination = directory_name + "/" + file_name
        # TODO: Read log path from config.
        with open("/root/.ja/MBII/log.txt", "rt") as f:
            log_lines = tail(f, lines=log_length)
        with open(destination, "wt") as f:
            f.write(log_lines)
