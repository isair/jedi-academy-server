from __future__ import with_statement

from fileConfigurable import ListFileConfigurable


def remove_color(item):
    """Remove Quake3 color codes from a str object."""
    for i in xrange(10):
        item = str.replace(item, "^%i" % (i), "")
    return item


class BanManager(ListFileConfigurable):
    """Maintains an IP list and auto-kicks banned IPs."""

    def __init__(self, jaserver):
        self.jaserver = jaserver
        # TODO: Read path from the config
        ListFileConfigurable.__init__(self, "/jedi-academy/banIP.dat")

    def kick(self, player, kick_reason):
        print("[BanManager] id: %d name: %s ip: %s kicked." % (player.id, player.name, player.ip))
        self.jaserver.say("^7%s ^1has been kicked because %s." % (player.name, kick_reason))
        self.jaserver.clientkick(player.id)

    def ban(self, player):
        self.kick(player, "they are in the ban list")
        if player.ip not in self.list:
            print("[BanManager] Ban list updated.")
            self.list.append(player.ip)
            self.synchronize()

    def check_player(self, player):
        # If player is in the ban list, call ban method on them again for the proper message.
        if player.ip in self.list:
            self.ban(player)
        # Check if their name is allowed. Kick them if it's not.
        clean_name = remove_color(player.name).lower().strip()
        if clean_name in ("admin", "server"):
            self.kick(player, "they are trying to impersonate an admin")
