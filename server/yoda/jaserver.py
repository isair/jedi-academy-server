from __future__ import with_statement

from socket import (socket, AF_INET, SOCK_DGRAM, SHUT_RDWR, timeout as socket_timeout, error as socket_error)

import managers.judgmentManager
import managers.messageManager
import managers.punishmentManager


class JAServer(object):
    """Communication interface with a JA server."""

    gamemodes = ["open", "semi authentic", "full authentic", "duel"]

    def __init__(self, address, bindaddr, rcon_pwd, use_say_only):
        self.cvars = None
        self.players = {}

        self.address = address
        self.bindaddr = bindaddr
        self.rcon_pwd = rcon_pwd
        self.use_say_only = use_say_only

        self.message_manager = managers.messageManager.MessageManager(self)
        self.judgment_manager = managers.judgmentManager.JudgmentManager(self)
        self.punishment_manager = managers.punishmentManager.PunishmentManager(self)

    @property
    def gamemode(self):
        if self.cvars is not None:
            return JAServer.gamemodes[self.cvars["g_authenticity"]]
        else:
            return None

    def send(self, payload, buffer_size=1024, retry=True):
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.bind((self.bindaddr, 0))
        sock.settimeout(1)
        sock.connect(self.address)

        error = None
        reply = ""

        while True:
            try:
                sock.send("\xff\xff\xff\xff" + payload)
                reply = sock.recv(buffer_size)
                break
            except socket_timeout:
                if not retry:
                    error = socket_timeout
                    break
                else:
                    continue
            except socket_error:
                error = socket_error
                break

        sock.shutdown(SHUT_RDWR)
        sock.close()

        if error is not None:
            raise error

        return reply

    def rcon(self, payload, buffer_size=1024, retry=True):
        return self.send("rcon %s %s" % (self.rcon_pwd, payload), buffer_size, retry)

    def status(self):
        return self.rcon("status")

    def sets(self, key, value):
        return self.rcon("sets %s %s" % (key, value))

    def say(self, msg):
        return self.rcon("say %s" % msg, 2048)

    def svsay(self, msg):
        if self.use_say_only or len(msg) > 141:  # Message is too big for "svsay". Use "say" instead.
            return self.say(msg)
        else:
            return self.rcon("svsay %s" % msg)

    def mbmode(self, mode):
        return self.rcon("mbmode %s" % mode)

    def clientkick(self, player_id):
        return self.rcon("clientkick %i" % player_id)

    def mute(self, player_id, duration):
        return self.rcon("mute %i %i" % (player_id, duration))

    def test_connection(self):
        reply = self.status()
        if reply.startswith("\xff\xff\xff\xffprint\nbad rconpassword"):
            raise Exception("Incorrect rcon password.")
        elif reply != "\xff\xff\xff\xffprint":
            raise Exception("Unexpected error while contacting the server.")


class DummyJAServer(JAServer):

    def __init__(self, use_say_only):
        self.cvars = None
        self.players = {}
        self.address = "127.0.0.1"
        self.bindaddr = "127.0.0.1"
        self.rcon_pwd = "dummy"
        self.use_say_only = use_say_only
        self.message_manager = managers.messageManager.DummyMessageManager(self)
        self.judgment_manager = managers.judgmentManager.DummyJudgmentManager(self)
        self.punishment_manager = managers.punishmentManager.DummyPunishmentManager(self)

    def send(self, payload, buffer_size=1024, retry=True):
        print(payload)
        return "\xff\xff\xff\xffprint"
