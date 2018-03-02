import datetime
import os
import threading

from pushNotificationManager import PushNotificationManager
from ..models.killInfo import KillInfo
from ..models.player import Player
from ..utility import tail


class JudgmentManager:
    spammer_mute_duration = 10  # in minutes

    lookalike_characters = {
        "i": "1", "|": "1", "l": "1",
        "o": "0"
    }

    def __init__(self, jaserver):
        self.jaserver = jaserver

    def check_entry(self, player):
        assert isinstance(player, Player)
        # If player is in the ban list, kick them.
        if self.jaserver.punishment_manager.is_banned(player):
            print("[JudgmentManager] Banned player login attempt: %s" % player.ip)
            self._log_incident("banned-entry-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)

    def check_info(self, player):
        clean_name = player.clean_name
        # Check if their name is allowed. Kick them if it's not.
        if clean_name in ("admin", "server"):
            print("[JudgmentManager] Admin impersonation attempt: %s" % player.ip)
            self._log_incident("admin-impersonation-attempt", player=player, log_length=5)
            self.jaserver.punishment_manager.kick(player, automatic=True)
        # Check for impostors.
        for other_player in self.jaserver.players.values():
            if player.identifier == other_player.identifier:
                continue
            elif len(clean_name) > 0:
                other_clean_name = other_player.clean_name
                if len(clean_name) != len(other_clean_name):
                    # Don't bother checking if clean names aren't the same length.
                    continue
                for key, value in JudgmentManager.lookalike_characters.items():
                    clean_name = clean_name.replace(key, value)
                    other_clean_name = other_clean_name.replace(key, value)
                if clean_name != other_clean_name:
                    continue
                # If we are here, the names look visually same as each other.
                impersonator = player
                if player.name_change_time < other_player.name_change_time:
                    impersonator = other_player
                self._notify_about(impersonator,
                                   public_message="has been kicked for trying to impersonate a player. An admin has been notified",
                                   private_message="has been kicked for trying to impersonate a player",
                                   log_message="Impersonator")
                self._log_incident("player-impersonation-attempt", player=impersonator, log_length=5)
                self.jaserver.punishment_manager.kick(impersonator, automatic=True)

    def check_kill_info(self, player, previous_status):
        assert isinstance(player, Player)
        assert isinstance(previous_status, int)
        if player.kill_info.status == KillInfo.Status.BAITED:
            # Forgive baited player.
            self._notify_about(player,
                               public_message="has been forgiven due to possible baiting. An admin has been notified",
                               private_message="has been forgiven due to possible baiting",
                               log_message="Forgiven")
            for baiter_id in player.kill_info.baiter_ids:
                baiter = self.jaserver.players.get(baiter_id, None)
                if baiter is None:
                    continue
                self._notify_about(baiter,
                                   public_message=None,
                                   private_message="is possibly baiting",
                                   log_message="Possible baiter")
                self._log_incident("baiting", player=player, log_length=400)
            # Reset kill info.
            player.kill_info.reset()
        elif player.kill_info.status == KillInfo.Status.NONE:
            # TODO: Check reports.
            pass
        elif player.kill_info.status == KillInfo.Status.SUSPECTED_LAMER:
            if player.kill_info.status != previous_status:
                self._notify_about(player,
                                   public_message="is now suspected of laming. To prevent baiting, victims are also being watched. An admin has been notified",
                                   private_message="has been warned",
                                   log_message="Suspect",
                                   include_latest_kills=True)
                self._log_incident("lamer-warning", player=player, log_length=300)
            # TODO: Check reports.
        elif player.kill_info.status == KillInfo.Status.POSSIBLE_LAMER:
            self._notify_about(player,
                               public_message="has been kicked for possible laming. An admin has been notified",
                               private_message="has been kicked for possible laming",
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
        assert isinstance(player, Player)
        assert isinstance(log_message, str)
        print("[JudgmentManager] %s: %d" % (log_message, player.identifier))
        if public_message is not None:
            assert isinstance(public_message, str)
            self.jaserver.svsay("^7%s ^3%s." % (player.name, public_message))
        if private_message is not None:
            assert isinstance(private_message, str)
            notification_message = "[%s] %s (%d|%s) %s." % (self.jaserver.gamemode,
                                                            player.clean_name,
                                                            player.identifier,
                                                            player.ip,
                                                            private_message)
            if include_latest_kills:
                latest_killed_players = map(lambda k: self.jaserver.players.get(k.victim_id, None),
                                            reversed(player.kill_info.get_latest_kills()))
                latest_kills = map(lambda p: "%s (%d|%s)" % (p.clean_name, p.identifier, p.ip),
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
        JudgmentManager._notify_about(self,
                                      player,
                                      public_message=public_message,
                                      private_message=None,
                                      log_message=log_message,
                                      include_latest_kills=include_latest_kills)

    @staticmethod
    def _log_incident(incident_type, player, log_length):
        return
