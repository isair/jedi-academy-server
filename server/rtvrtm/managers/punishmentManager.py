from __future__ import with_statement

from fileConfigurable import JSONFileConfigurable
from ..models.player import Player


class PunishmentManager(JSONFileConfigurable):

    def __init__(self, jaserver):
        self.jaserver = jaserver
        self.banned_names = set()
        self.banned_ips = set()
        # TODO: Read path from the config
        JSONFileConfigurable.__init__(self, "/jedi-academy/bans.json")

    def load_configuration(self):
        super(PunishmentManager, self).load_configuration()
        try:
            self.banned_names = set(self.json_dict["names"])
        except Exception as e:
            print("WARNING: No names key defined in %s" % self.configuration_file_path)
            print(e)
        try:
            self.banned_ips = set(self.json_dict["ips"])
        except Exception as e:
            print("WARNING: No ips key defined in %s" % self.configuration_file_path)
            print(e)

    def synchronize(self):
        self.json_dict["names"] = list(self.banned_names)
        self.json_dict["ips"] = list(self.banned_ips)
        super(PunishmentManager, self).synchronize()

    def is_banned(self, player):
        return player.ip in self.banned_ips or player.clean_name in self.banned_names

    def kick(self, player, automatic):
        assert isinstance(player, Player)
        assert isinstance(automatic, bool)
        print("[PunishmentManager] Kick: %s %s %s" % (player.identifier, player.name, player.ip))
        say_method = self.jaserver.say if automatic else self.jaserver.svsay
        say_method("^7%s ^1has been %skicked." % (player.name, "automatically " if automatic else ""))
        self.jaserver.clientkick(player.identifier)

    def mute(self, player, duration, automatic):
        assert isinstance(player, Player)
        assert isinstance(duration, int)
        assert isinstance(automatic, bool)
        print("[PunishmentManager] Mute: %s %s %s" % (player.identifier, player.name, player.ip))
        say_method = self.jaserver.say if automatic else self.jaserver.svsay
        say_method("%s ^7has been %smuted for %d minutes." % (player.name,
                                                              "automatically " if automatic else "",
                                                              duration))
        self.jaserver.mute(player.identifier, duration)

    def ban(self, player, automatic):
        assert isinstance(player, Player)
        assert isinstance(automatic, bool)
        print("[PunishmentManager] Ban: %s %s %s" % (player.identifier, player.name, player.ip))
        self.jaserver.svsay("^7%s ^1has been %sbanned." % (player.name, "automatically " if automatic else ""))
        self.kick(player, automatic=True)
        if player.ip not in self.banned_ips:
            print("[PunishmentManager] Ban list updated.")
            self.banned_ips.add(player.ip)
            self.synchronize()

    def unban_ip(self, ip):
        assert isinstance(ip, str)
        if ip in self.banned_ips:
            self.banned_ips.remove(ip)
            self.synchronize()
            print("[PunishmentManager] Unban: %s" % ip)
            self.jaserver.say("^7%s has been removed from banned IPs." % ip)
        else:
            self.jaserver.say("^7IP not in banned IPs.")
