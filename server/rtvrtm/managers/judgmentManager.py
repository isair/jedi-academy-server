import datetime
import os
import threading

from pushNotificationManager import PushNotificationManager
from ..models.killInfo import KillInfo
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
            self._log_incident("banned-entry-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)
        # Check if their name is allowed. Kick them if it's not.
        if player.clean_name in ("admin", "server"):
            print("[JudgmentManager] Admin impersonation attempt: %s" % player.ip)
            self._log_incident("admin-impersonation-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)

    def check_kill_info(self, player, previous_lamer_status):
        assert isinstance(player, Player)
        assert isinstance(previous_lamer_status, int)
        # Check baited status.
        if player.kill_info.is_baited:
            # Kick baiters.
            for baiter_id in player.kill_info.baiter_ids:
                player = self.jaserver.players.get(baiter_id, None)
                if player is None:
                    continue
                self._notify_about(player,
                                   public_message="has been kicked for possible baiting. An admin has been notified.",
                                   private_message="has been kicked for possible baiting.",
                                   log_message="Possible baiter")
                self._log_incident("baiter-kick", player=player, log_length=300)
                self.jaserver.punishment_manager.kick(player, automatic=True)
            # Reset kill info.
            player.kill_info.is_baited = False
            player.kill_info.baiter_ids = []
            player.kill_info.double_kills = []
            # No need to check lamer status.
            return
        # Check lamer status.
        status = player.kill_info.lamer_status
        if status == KillInfo.LAMER_STATUS_NONE:
            # TODO: Check reports.
            return
        elif status == KillInfo.LAMER_STATUS_SUSPECTED:
            if status != previous_lamer_status:
                self._notify_about(player,
                                   public_message="is now suspected of laming. To prevent baiting, victims are also being watched. An admin has been notified",
                                   private_message="has been warned",
                                   log_message="Suspect",
                                   include_latest_kills=True)
                self._log_incident("lamer-warning", player=player, log_length=300)
            # TODO: Check reports.
        elif status == KillInfo.LAMER_STATUS_KICKABLE:
            self._notify_about(player,
                               public_message="has been kicked for possible laming. An admin has been notified",
                               private_message="has been kicked for possible laming.",
                               log_message="Possible lamer")
            self._log_incident("lamer-kick", player=player, log_length=300)
            self.jaserver.punishment_manager.kick(player, automatic=True)

    def check_say_info(self, player):
        assert isinstance(player, Player)
        # If player is spamming, mute them.
        if player.say_info.is_spamming:
            duration = JudgmentManager.spammer_mute_duration
            private_message = "has been muted for spamming\nLast message: %s" % player.say_info.last_message
            self._notify_about(player,
                               public_message="has been muted for %d minutes for spamming" % duration,
                               private_message=private_message,
                               log_message="Spammer")
            self._log_incident("mute", player=player, log_length=100)
            player.say_info.reset()
            self.jaserver.punishment_manager.mute(player, duration=duration, automatic=True)
            return True
        return False

    def _notify_about(self, player, public_message, private_message, log_message, include_latest_kills=False):
        print("[JudgmentManager] %s: %d" % (log_message, player.identifier))
        self.jaserver.svsay("^7%s ^3%s." % (player.name, public_message))
        notification_message = "[%s] %s (%d|%s) %s." % (self.jaserver.gamemode,
                                                        player.clean_name,
                                                        player.identifier,
                                                        player.ip,
                                                        private_message)
        if include_latest_kills:
            latest_killed_players = map(lambda kill: self.jaserver.players.get(kill.victim_id, None),
                                        reversed(player.kill_info.latest_kills))
            latest_kills = map(lambda player: "%s (%d|%s)" % (player.clean_name, player.identifier, player.ip),
                               filter(lambda p: p is not None, latest_killed_players))
            notification_message += "\nLatest kills: " + ", ".join(latest_kills)
        PushNotificationManager.send(notification_message)

    @staticmethod
    def _log_incident(incident_type, player, log_length):
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


class DummyJudgmentManager(JudgmentManager):

    def __init__(self, jaserver):
        JudgmentManager.__init__(self, jaserver)

    def _notify_about(self, player, public_message, private_message, log_message, include_latest_kills=False):
        print("[JudgmentManager] %s: %d" % (log_message, player.identifier))
        self.jaserver.svsay("^7%s ^3%s." % (player.name, public_message))

    @staticmethod
    def _log_incident(incident_type, player, log_length):
        return
