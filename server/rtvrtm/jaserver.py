from __future__ import with_statement
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)

from rcon import Rcon

class JAServer(object):
  """Sends UDP packets to a JA server."""

  def __init__(self, address, bindaddr, rcon_pwd):
    self.address = address
    self.bindaddr = bindaddr
    self.rcon_pwd = rcon_pwd
    self.rcon = Rcon(self)

  def send(self, payload, buffer_size=1024, retry=True):
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((self.bindaddr, 0))
    sock.settimeout(1)
    sock.connect(self.address)

    error = None
    reply = ""

    while(True):
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
