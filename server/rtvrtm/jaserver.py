from __future__ import with_statement

from socket import (socket, AF_INET, SOCK_DGRAM, SHUT_RDWR, timeout as socketTimeout, error as socketError)


class JAServer(object):
    """Communication interface with a JA server."""

    def __init__(self, address, bindaddr, rcon_pwd, use_say_only):
        self.gamemodes = ("open", "semi authentic", "full authentic", "duel")
        self.cvars = None

        self.address = address
        self.bindaddr = bindaddr
        self.rcon_pwd = rcon_pwd
        self.use_say_only = use_say_only

    @property
    def gamemode(self):
        if self.cvars is not None:
            return self.gamemodes[self.cvars["g_authenticity"]]
        else:
            return None

    def send(self, payload, buffer_size=1024, retry=True):
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.bind((self.bindaddr, 0))
        sock.settimeout(1)
        sock.connect(self.address)

        error = None
        reply = ""

        while (True):
            try:
                sock.send("\xff\xff\xff\xff" + payload)
                reply = sock.recv(buffer_size)
                break
            except socketTimeout:
                if not retry:
                    error = socketTimeout
                    break
                else:
                    continue
            except socketError:
                error = socketError
                break

        sock.shutdown(SHUT_RDWR)
        sock.close()

        if error != None:
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

    def test_connection(self):
        reply = self.status()
        if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):
            raise Exception("Incorrect rcon password.")
        elif reply != "\xff\xff\xff\xffprint":
            raise Exception("Unexpected error while contacting the server.")
