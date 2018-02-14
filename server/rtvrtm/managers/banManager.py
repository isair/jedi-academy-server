from __future__ import with_statement

from fileConfigurable import ListFileConfigurable
from ..models.player import Player


class BanManager(ListFileConfigurable):
    """Maintains an IP list and auto-kicks banned IPs."""

    def __init__(self, jaserver):
        self.jaserver = jaserver
        # TODO: Read path from the config
        ListFileConfigurable.__init__(self, "/jedi-academy/banIP.dat")

    def kick(self, player, kick_reason, automatic=False):
        assert isinstance(player, Player)
        assert isinstance(kick_reason, str)
        assert isinstance(automatic, bool)
        print("[BanManager] Kick: %s %s %s" % (player.id, player.name, player.ip))
        self.jaserver.say(
            "^7%s ^1has been %skicked because %s." % (player.name, "automatically " if automatic else "", kick_reason))
        self.jaserver.clientkick(player.id)

    def ban(self, player, ban_reason="", automatic=False):
        assert isinstance(player, Player)
        assert isinstance(ban_reason, str)
        assert isinstance(automatic, bool)
        print("[BanManager] Ban: %s %s %s" % (player.id, player.name, player.ip))
        self.jaserver.svsay(
            "^7%s ^1has been %sbanned%s." % (player.name, "automatically " if automatic else "", ban_reason))
        self.kick(player, "they are in the ban list")
        if player.ip not in self.list:
            print("[BanManager] Ban list updated.")
            self.list.append(player.ip)
            self.synchronize()

    def check_player(self, player):
        assert isinstance(player, Player)
        # If player is in the ban list, kick them.
        if player.ip in self.list:
            print("[BanManager] Banned player login attempt: %s" % player.ip)
            self.kick(player, "they are in the ban list", automatic=True)
        # Check if their name is allowed. Kick them if it's not.
        if player.clean_name in ("admin", "server"):
            print("[BanManager] Admin impostor attempt: %s" % player.ip)
            self.kick(player, "they are trying to impersonate an admin")
