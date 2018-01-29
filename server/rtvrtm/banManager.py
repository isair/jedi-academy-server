from __future__ import with_statement

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

  def ban(self, player):
    self.jaserver.rcon.say("^3%s has been kicked because they are in the ban list." % player.name)
    self.jaserver.rcon.clientkick(player.id)
    if player.ip not in self.banList:
      self.banList.append(player.ip)
      try:
        with open(self.banListPath, "a") as f:
          f.write(player.ip + "\n")
      except Exception as e:
        print("Warning: Failed to write to ban list at %s" % self.banListPath)
        print(e)

  def check_player(self, player):
    if player.ip in self.banList:
      self.ban(player)
