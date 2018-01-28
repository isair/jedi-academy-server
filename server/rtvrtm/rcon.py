from __future__ import with_statement
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)
from random import choice

class Rcon(object):
  """Send commands to the server via rcon. Wrapper class."""

  def __init__(self, jaserver):
    self.jaserver = jaserver

  def send(self, payload, buffer_size=1024, retry=True):
    return self.jaserver.send("rcon %s %s" % (self.jaserver.rcon_pwd, payload), buffer_size, retry)

  def status(self):
    return self.send("status")

  def sets(self, key, value):
    return self.send("sets %s %s" % (key, value))

  def say(self, msg):
    return self.send("say %s" % msg, 2048)

  def svsay(self, msg):
    if len(msg) > 141: # Message is too big for "svsay". Use "say" instead.
      return self.say(msg)
    else:
      return self.send("svsay %s" % msg)

  def mbmode(self, mode):
    return self.send("mbmode %s" % mode)

  def clientkick(self, player_id):
    return self.send("clientkick %i" % player_id)

  def test_connection(self):
    reply = self.status()
    if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):
      raise Exception("Incorrect rcon password.")
    elif reply != "\xff\xff\xff\xffprint":
      raise Exception("Unexpected error while contacting the server.")

  def sayNewRoundMessage(self):
    self.svsay("^7Join our discord server for player reporting, guides, and more!")
    self.svsay("^3discordapp.com/invite/Naj4Tyx")
    self.svsay("^7New players: Make sure you configure your class. For the key, check: controls > moviebattles")

  def sayRandomTip(self):
    tips = [
      "Make sure you assign keys to controls > moviebattles > class special 1 & 2.",
      "You can swingblock by releasing attack and immediately holding block.",
      "Jumping around will make you lose block points.",
      "You only regenerate block points while walking or standing.",
      "Hold block while looking at your enemy's swing location to not lose any block points. This is called a pblock.",
      "If you successfully pblock, your cursor will turn green.",
      "You can parry by hitting your enemy's lightsaber with yours to lose less block poits.",
      "Parry by attacking in the opposite direction to not lose any block points. This is called a perfect parry.",
      "If you perfect parry, your cursor will turn blue.",
      "You can press Shift + ~ to check any messages you might have missed.",
      "Use your seatbelt to open beers whilst you drive.",
      "Press ESC and click Library to learn all about the game mechanics.",
      "Say !rtv to vote for a map change.",
      "You can say !maplist 1 or 2 and !nominate the ones you see for the next voting round."
    ]

    self.svsay("^2[Tip] ^7" + choice(tips))

  def sayLamingWarning(self):
    self.svsay("^1No laming! Do not interrupt duels. Do not kill AFK people.")
    self.svsay("^1Fight people who want to fight you.")
