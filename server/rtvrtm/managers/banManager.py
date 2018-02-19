from __future__ import with_statement

from fileConfigurable import JSONFileConfigurable
from ..managers.pushNotificationManager import PushNotificationManager
from ..models.player import Player


class BanManager(JSONFileConfigurable):
    """Maintains an IP list and auto-kicks banned IPs."""

    spammer_mute_duration = 10  # in minutes

    def __init__(self, jaserver):
        self.jaserver = jaserver
        self.banned_names = set()
        self.banned_ips = set()
        # TODO: Read path from the config
        JSONFileConfigurable.__init__(self, "/jedi-academy/bans.json")

    def load_configuration(self):
        super(BanManager, self).load_configuration()
        try:
            self.banned_names = set(self.json_dict["names"])
        except Exception as e:
            print("WARNING: No names key defined under key in %s" % self.configuration_file_path)
            print(e)
        try:
            self.banned_ips = set(self.json_dict["ips"])
        except Exception as e:
            print("WARNING: No ips key defined under key in %s" % self.configuration_file_path)
            print(e)

    def synchronize(self):
        self.json_dict["names"] = list(self.banned_names)
        self.json_dict["ips"] = list(self.banned_ips)
        super(BanManager, self).synchronize()

    def kick(self, player, kick_reason, automatic=False):
        assert isinstance(player, Player)
        assert isinstance(kick_reason, str)
        assert isinstance(automatic, bool)
        print("[BanManager] Kick: %s %s %s" % (player.identifier, player.name, player.ip))
        self.jaserver.say(
            "^7%s ^1has been %skicked%s." % (player.name, "automatically " if automatic else "", kick_reason))
        self.jaserver.clientkick(player.identifier)

    def ban(self, player, ban_reason="", automatic=False):
        assert isinstance(player, Player)
        assert isinstance(ban_reason, str)
        assert isinstance(automatic, bool)
        print("[BanManager] Ban: %s %s %s" % (player.identifier, player.name, player.ip))
        self.jaserver.svsay(
            "^7%s ^1has been %sbanned%s." % (player.name, "automatically " if automatic else "", ban_reason))
        self.kick(player, " because they are in the ban list")
        if player.ip not in self.banned_ips:
            print("[BanManager] Ban list updated.")
            self.banned_ips.add(player.ip)
            self.synchronize()

    def unban_ip(self, ip):
        assert isinstance(ip, str)
        if ip in self.banned_ips:
            self.banned_ips.remove(ip)
            self.synchronize()
            print("[BanManager] Unban: %s" % ip)
            self.jaserver.say("^2[BanManager] ^7%s has been removed from banned IPs." % ip)
        else:
            self.jaserver.say("^2[BanManager] ^7IP not in banned IPs.")

    # Move checks to another class.

    def check_player(self, player):
        assert isinstance(player, Player)
        # If player is in the ban list, kick them.
        if player.ip in self.banned_ips or player.clean_name in self.banned_names:
            print("[BanManager] Banned player login attempt: %s" % player.ip)
            self.kick(player, " because they are in the ban list", automatic=True)
        # Check if their name is allowed. Kick them if it's not.
        if player.clean_name in ("admin", "server"):
            print("[BanManager] Admin impostor attempt: %s" % player.ip)
            self.kick(player, " because they are trying to impersonate an admin")

    def check_say(self, player):
        assert isinstance(player, Player)
        # If player is spamming, mute them for 10 minutes.
        if player.say_info.is_spamming:
            self.jaserver.mute(player.identifier, BanManager.spammer_mute_duration)
            player.say_info.reset()
            self.jaserver.svsay(
                "%s ^7has been automatically muted for %d minutes for spamming." % (player.name,
                                                                                    BanManager.spammer_mute_duration))
            PushNotificationManager.send(
                "[%s] %s (%d|%s) has been muted for spamming.\nLast message: %s" % (self.jaserver.gamemode,
                                                                                    player.clean_name,
                                                                                    player.identifier, player.ip,
                                                                                    player.say_info.last_message))
            return True
        return False
