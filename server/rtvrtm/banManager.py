from __future__ import with_statement

def remove_color(item):
  """Remove Quake3 color codes from a str object."""
  for i in xrange(10):
    item = str.replace(item, "^%i" % (i), "")
  return item

class BanManager(object):
  """Maintains an IP list and auto-kicks banned IPs."""

  def __init__(self, jaserver, config):
    self.jaserver = jaserver
    self.config = config
    # TODO: Read this from the config
    self.banListPath = "/jedi-academy/banIP.dat"
    self.banList = []
    self.update_list_from_file()

  def update_list_from_file(self):
    try:
      with open(self.banListPath) as f:
        self.banList = [line.strip() for line in f]
    except Exception as e:
      print("WARNING: Failed to read ban list at %s" % self.banListPath)
      print(e)

  def kick(self, player, kick_reason):
    print("[BanManager] id: %d name: %s ip: %s kicked." % (player.id, player.name, player.ip))
    self.jaserver.rcon.say("^7%s ^1has been kicked because %s." % (player.name, kick_reason))
    self.jaserver.rcon.clientkick(player.id)

  def ban(self, player):
    self.kick(player, "they are in the ban list")
    if player.ip not in self.banList:
      print("[BanManager] Ban list updated.")
      self.banList.append(player.ip)
      try:
        with open(self.banListPath, "a") as f:
          f.write(player.ip + "\n")
      except Exception as e:
        print("WARNING: Failed to write to ban list at %s" % self.banListPath)
        print(e)

  def check_player(self, player):
    # If player is in the ban list, call ban method on them again for the proper message.
    if player.ip in self.banList:
      self.ban(player)
    # Check if their name is allowed. Only kick them if it's not.
    if self.config.name_protection:
      stripped_name = remove_color(player.name).lower().strip()
      if stripped_name in ("admin", "server"):
        self.kick(player, "they are trying to impersonate an admin")
