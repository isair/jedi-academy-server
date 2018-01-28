#!/usr/bin/python -uSOO
# Copyright (c) 2012-2013, klax / Cthulhu@GBITnet.com.br
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#################################################
#          Movie Battles II RTV/RTM             #
#                                               #
#      Rock the Vote and Rock the Mode tool     #
#      for Jedi Knight: Jedi Academy            #
#      Movie Battles II MOD.                    #
#      Original plugin and idea by:             #
#      AlliedModders LLC. All rights reserved.  #
#################################################

from __future__ import with_statement
from sys import platform, setcheckinterval, argv, exit
from optparse import OptionParser, OptionGroup
from os import listdir, fsync
from os.path import getsize, basename, dirname, normpath, realpath, normcase, join as join_path
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)
from time import time, sleep
from collections import defaultdict
from datetime import datetime
from random import choice, sample
from zipfile import ZipFile, BadZipfile
from tarfile import open as TarFile
from traceback import format_exc

import random
import threading

VERSION = "3.6b"
CFG = "3.6b"
SLEEP_INTERVAL = 0.075
MAPLIST_MAX_SIZE = 750
REPORT_UNHANDLED_EXCEPTION = False

def error(msg):

  """Error handling function."""

  print("Failed!\n")
  print("ERROR: %s" % (msg))

  if platform == "win32":

    raw_input("\nPress ENTER to continue...")

  exit(1)

def warning(msg, rehash=False):

  """Warning function (NON CRITICAL ERROR)."""

  print("Failed!\n")
  print("WARNING: %s" % (msg))

  if rehash:

    print("WARNING: Rehash aborted!")

  print

class SortableDict(dict):

  """Dictionary subclass that can return sorted items."""

  def sorteditems(self):

    return iter(sorted(self.iteritems()))

class DummyTime(object):

  """Dummy class to be used as a replacement for a float time object returned by time.time() on round-based votings."""

  def __iadd__(self, *args): # Operator overload will return the object itself without any changes
                             # on assignment addition operations.
    return self

def report_unhandled_exception(bugreport):

  """Report an unhandled exception to a remote server."""

  print("\nERROR: Caught unhandled exception!")
  print("-> Sending bug report..."),
  bugreport = "%s\\%s" % (VERSION, bugreport)

  for i in xrange(3): # Attempt to send the bug report for a maximum of 3 times.

    sock = socket(AF_INET, SOCK_STREAM) # TCP layer.
    sock.settimeout(3.5)

    try:

      sock.connect(("rtvrtm.gatetogames.net", 22998))
      sock.send(bugreport)
      status = "Sent!"
      break

    except gaierror:

      status = "Unresolvable hostname!"

    except socketTimeout:

      status = "Timeout!"

    except socketError:

      status = "Refused/Unreachable!"

      if i < 2:

        sleep(3.5)

    finally:

      try:

        sock.shutdown(SHUT_RDWR)

      except socketError:

        pass

      sock.close()

  print("%s\n" % (status))

def updater(filename, filecode):

  """Built-in Updater."""

  strip = str.strip
  lower = str.lower
  print("[*] Checking for updates..."),
  sock = socket(AF_INET, SOCK_STREAM) # TCP layer.
  sock.settimeout(5)

  try:

    sock.connect(("rtvrtm.gatetogames.net", 22999))
    sock.settimeout(5)
    send = sock.send
    recv = sock.recv
    send(hex(filecode))
    new_version = recv(32)

    if not new_version:

      raise ValueError

    elif new_version == VERSION:

      print("Up to date!")

    else:

      print("Found!")

      while(True): # Infinite loop until we get [Y]es or [N]o.

        update = lower(strip(raw_input("-> Update %s to %s? [Y]es/[N]o: " % (VERSION,
                                                                             new_version))))

        if update in ("y", "yes"):

          break

        elif update in ("n", "no"):

          return

      print("[*] Getting file information..."),
      send("CFG") # Check whether a new configuration file is necessary.
      update_cfg = recv(32)

      if not update_cfg:

        raise ValueError

      send("SIZE") # Get total size of the file we want to download. In bytes.
      total_data = int(recv(128))

      if total_data >= 1073741824: # Convert bytes to gigabytes.

        update_size = ((total_data / 1073741824.0), "%.2f GB")

      elif total_data >= 1048576: # Convert bytes to megabytes.

        update_size = ((total_data / 1048576.0), "%.2f MB")

      elif total_data >= 1024: # Convert bytes to kilobytes.

        update_size = ((total_data / 1024.0), "%.2f KB")

      else:

        update_size = (total_data, "%i B")

      newfile = []
      append_data = newfile.append
      data_size = download_offset = av_rates = av_total_rates = char_pos = 0
      rotating_chars = ("|", "/", "-", "\\")
      moving_dots = 1
      send("GET")
      update_time = download_time = time()
      print("Done!")
      print("-> Update size: %s%s" % (update_size[1] % (update_size[0]),
                                      ("" if update_size[0] == 1 else
                                       "s")))
      print("\r[|] %s [%s] 0%%." % ((" " * 11), (" " * 36))), # Progress bar at 0%.

      while data_size < total_data: # Download packets on a 512-bytes base.

        data = recv(512)

        if not data:

          raise ValueError

        append_data(data)
        data_size += len(data)
        packet_time = time()
        download_divisor = (packet_time - download_time)

        if download_divisor >= 0.2:

          download_rate = ((data_size - download_offset) / download_divisor) # Calculate download rate in bytes/s.
          av_rates += 1
          av_total_rates += download_rate
          download_offset = data_size
          download_time = packet_time

          if download_rate >= 1073741824: # Convert bytes/s to gigabytes/s.

            download_rate = "%6.1f GB" % ((download_rate / 1073741824.0))

          elif download_rate >= 1048576: # Convert bytes/s to megabytes/s.

            download_rate = "%6.1f MB" % ((download_rate / 1048576.0))

          elif download_rate >= 1024: # Convert bytes/s to kilobytes/s.

            download_rate = "%6.1f KB" % ((download_rate / 1024.0))

          else:

            download_rate = "%7i B" % (int(round(download_rate)))

          char_pos = ((char_pos + 1) % 4)
          percent = ((data_size * 100) / total_data)
          bar = ((35 * percent) / 100)
          bar = "%s%s" % (("=" * bar), (">" * bool(bar)))
          moving_dots = ((moving_dots % 3) + 1)
          print("\r[%c] %s/s [%-36s] %i%%%-3s" %
                (rotating_chars[char_pos],
                 download_rate, bar, percent, ("." * moving_dots))), # Progress bar.

      try:

        download_rate = (av_total_rates / av_rates) # Calculate average download rate in bytes/s.

        if download_rate >= 1073741824: # Convert bytes/s to gigabytes/s.

          download_rate = "%6.1f GB/s" % ((download_rate / 1073741824.0))

        elif download_rate >= 1048576: # Convert bytes/s to megabytes/s.

          download_rate = "%6.1f MB/s" % ((download_rate / 1048576.0))

        elif download_rate >= 1024: # Convert bytes/s to kilobytes/s.

          download_rate = "%6.1f KB/s" % ((download_rate / 1024.0))

        else:

          download_rate = "%7i B/s" % (int(round(download_rate)))

      except ZeroDivisionError: # No rate was registered.

        download_rate = (" " * 11)

      print("\r[*] %s [%s] 100%%   " % (download_rate, ("=" * 36))) # Progress bar at 100%.
      print("[*] Flushing downloaded content to disk..."),

      try:

        with open(filename, ("at" if not filecode else "ab")) as rtvrtm:

          write = rtvrtm.write
          rtvrtm.truncate(0)

          for data in iter(newfile):

            write(data)

      except IOError, err:

        if err.errno == 13:

          error("Cannot write new file. Permission denied.")

        else:

          error("Unexpected error while writting update to disk (ERRNO: %i)." % (err.errno))

      print("Done!")

      if update_cfg != CFG:

        print("-> A new configuration file is available at http://rtvrtm.gatetogames.net/rtvrtm.cfg")

      print("-> Update completed in %s.\n" % (calculate_time(update_time, time())))
      raw_input("Press ENTER to continue...")
      exit(0)

  except gaierror:

    print("Unresolvable hostname!")

  except ValueError:

    print("Connection terminated!")

  except socketTimeout:

    print("Timeout!")

  except socketError:

    print("Refused/Unreachable!")

  finally:

    try:

      sock.shutdown(SHUT_RDWR)

    except socketError:

      pass

    sock.close()

class Config(object):

  """RTV/RTM configuration class."""

  def __init__(self, config_path):

    self.config_path = config_path
    self.fields = {
                   # General settings.
                   "log": "logfile",
                   "mbii folder": "MBII_Folder",
                   "address": "address",
                   "bind": "bindaddr",
                   "password": "rcon_pwd",
                   "flood protection": "flood_protection",
                   "use say only": "use_say_only",
                   "name protection": "name_protection",
                   "default game": "default_game",
                   "clean log": "clean_log",
                   # Admin voting settings.
                   "admin voting": "admin_voting",
                   "admin minimum votes": "admin_minimum_votes",
                   "admin skip voting": "admin_skip_voting",
                   # Map limit settings.
                   "roundlimit": "roundlimit",
                   "timelimit": "timelimit",
                   "limit voting": "limit_voting",
                   "limit minimum votes": "limit_minimum_votes",
                   "limit extend": "limit_extend",
                   "limit successful wait time": "limit_s_wait_time",
                   "limit failed wait time": "limit_f_wait_time",
                   "limit skip voting": "limit_skip_voting",
                   "limit second turn": "limit_second_turn",
                   "limit change immediately": "limit_change_immediately",
                   # Rock the Vote settings.
                   "rtv": "rtv",
                   "rtv rate": "rtv_rate",
                   "rtv voting": "rtv_voting",
                   "rtv minimum votes": "rtv_minimum_votes",
                   "rtv extend": "rtv_extend",
                   "rtv successful wait time": "rtv_s_wait_time",
                   "rtv failed wait time": "rtv_f_wait_time",
                   "rtv skip voting": "rtv_skip_voting",
                   "rtv second turn": "rtv_second_turn",
                   "rtv change immediately": "rtv_change_immediately",
                   # Map settings.
                   "automatic maps": "automatic_maps",
                   "maps": "maps",
                   "secondary maps": "secondary_maps",
                   "pick secondary maps": "pick_secondary_maps",
                   "map priority": "map_priority",
                   "nomination type": "nomination_type",
                   "enable recently played maps": "enable_recently_played",
                   # Rock the Mode settings.
                   "rtm": "rtm",
                   "mode priority": "mode_priority",
                   "rtm rate": "rtm_rate",
                   "rtm voting": "rtm_voting",
                   "rtm minimum votes": "rtm_minimum_votes",
                   "rtm extend": "rtm_extend",
                   "rtm successful wait time": "rtm_s_wait_time",
                   "rtm failed wait time": "rtm_f_wait_time",
                   "rtm skip voting": "rtm_skip_voting",
                   "rtm second turn": "rtm_second_turn",
                   "rtm change immediately": "rtm_change_immediately"
                  }
    self.bindaddr = self.default_game = self.maps = self.secondary_maps = "" # Optional configuration.
    self.cvar = 0

  def create_maplist(self, bsps):

    """Interactive map list creation."""

    strip = str.strip
    lower = str.lower

    while(True): # Infinite loop until we get [Y]es or [N]o.

      create = lower(strip(raw_input("-> Enter interactive map list creation? [Y]es/[N]o: ")))

      if create in ("y", "yes"):

        bsps.sort(key=lower) # Sort BSP list so we get it displayed in an ascending order.
        print("\n[*] Checking map files write permission..."),

        try:

          mapfile = open(self.maps, "at")

        except IOError, err:

          errno = err.errno

          if errno == 2:

            error("Map file directory does not exist.")

          if errno == 13:

            error("Cannot write to map file. Permission denied.")

          else:

            error("Unexpected error while creating map file (ERRNO: %i)." % (errno))

        try:

          secondary_mapfile = open(self.secondary_maps, "at")

        except IOError, err:

          mapfile.close()
          errno = err.errno

          if errno == 2:

            error("Secondary map file directory does not exist.")

          elif errno == 13:

            error("Cannot write to secondary map file. Permission denied.")

          elif errno == 21:

            error("Secondary map file is set to a directory.")

          elif errno == 22:

            error("Invalid secondary map file.")

          else:

            error("Unexpected error while creating secondary map file (ERRNO: %i)." % (errno))

        print("Done!\n")
        write_map = mapfile.write
        mapfile.truncate(0) # Making sure to truncate the map file.
        self.maps = []
        append_map = self.maps.append
        write_secondary_map = secondary_mapfile.write
        secondary_mapfile.truncate(0) # Making sure to truncate the secondary map file.
        self.secondary_maps = []
        append_secondary_map = self.secondary_maps.append

        for mapname in iter(bsps):

          while(True):# Infinite loop until we get a valid choice.

            add_map = lower(strip(raw_input("-> %s? [P]rimary/[S]econdary/[I]gnore: " % (mapname))))

            if add_map in ("p", "primary"):

              write_map("%s\n" % (mapname))
              append_map(mapname)
              break

            elif add_map in ("s", "secondary"):

              write_secondary_map("%s\n" % (mapname))
              append_secondary_map(mapname)
              break

            elif add_map in ("i", "ignore"):

              break

        mapfile.close()
        secondary_mapfile.close()
        self.maps = tuple(self.maps)
        self.secondary_maps = tuple(self.secondary_maps)
        print("\n[*] Checking options for errors..."),

        if not self.maps:

          error("The map list is empty.")

        break

      elif create in ("n", "no"):

        exit(1)

  def create(self, tries):

    """Create the configuration for the first time."""

    startswith = str.startswith
    endswith = str.endswith
    lower = str.lower
    strip = str.strip
    lstrip = str.lstrip
    rstrip = str.rstrip
    split = str.split
    namelist = ZipFile.namelist
    pk3close = ZipFile.close
    bind = socket.bind
    settimeout = socket.settimeout
    connect = socket.connect
    shutdown = socket.shutdown
    close = socket.close
    print("[*] Checking configuration file..."),

    try:

# Read configuration file and set each configuration attribute.

      with open(self.config_path, "rt") as cfg:

        print("Done!")
        print("[*] Reading configuration..."),

        for line in cfg:

          line = lstrip(line)

          if line and not startswith(line, "*"): # Ignore empty lines and comments.

            try:

              attr, value = split(line, ":", 1)
              attr = self.fields[lower(rstrip(attr))]
              setattr(self, attr, value)

            except (ValueError, KeyError):

              continue

    except IOError, err:

      errno = err.errno

      if errno == 2:

        error("Configuration file does not exist.")

      elif errno == 13:

        error("Cannot read configuration file. Permission denied.")

      elif errno == 21:

        error("Configuration file is set to a directory.")

      elif errno == 22:

        error("Invalid configuration file.")

      else:

        error("Unexpected error while reading configuration file (ERRNO: %i)." % (errno))

    else:

# Configuration and general error checks.

      print("Done!")
      print("[*] Checking options for errors..."),

# General settings.

      try:

        self.logfile = strip(self.logfile)

        while self.logfile[-1] in (" ", "\\", "/"):

          self.logfile = self.logfile[:-1]

        self.logfile = normpath(self.logfile)

        with open(self.logfile, "rt+") as log:

          pass

      except AttributeError:

        error("Log file is not defined.")

      except IndexError:

        error("Invalid log file.")

      except IOError, err:

        errno = err.errno

        if errno == 2:

          error("Log file does not exist.")

        elif errno == 13:

          error("Cannot open log file. Permission denied.")

        elif errno == 21:

          error("Log file is set to a directory.")

        elif errno == 22:

          error("Invalid log file.")

        else:

          error("Unexpected error while reading log file (ERRNO: %i)." % (errno))

      try:

        self.MBII_Folder = normpath(strip(self.MBII_Folder))
        pk3s = (pk3 for pk3 in iter(listdir(self.MBII_Folder))
                if endswith(lower(pk3), ".pk3")) # Get all PK3 files within the MBII folder.
        bsps = []

        for pk3 in pk3s:

          try:

            pk3zip = ZipFile(join_path(self.MBII_Folder, pk3), "r")
            bsps += [basename(bsp)[:-4] for bsp in iter(namelist(pk3zip)) if endswith(lower(bsp), ".bsp")] # Get all BSP files.
            pk3close(pk3zip)

          except IOError, err:

            warning("Error while trying to read %s (ERRNO: %i)." % (pk3, err.errno))
            print("[*] Checking options for errors..."),

          except BadZipfile:

            warning("%s is not a valid pk3 file." % (pk3))
            print("[*] Checking options for errors..."),

        if not bsps:

          error("No BSP map files detected. Make sure MBII folder path is correct.")

        map_duplicates = defaultdict(bool)
        bsps = [bsp for bsp in iter(bsps)
                if (lower(bsp) not in map_duplicates and
                    not map_duplicates[lower(bsp)])] # Ensure that we don't get duplicates from replacements.
        lower_bsps = tuple((lower(bsp) for bsp in iter(bsps)))

      except AttributeError:

        error("MBII folder is not defined.")

      except (WindowsError if platform == "win32" else OSError), err:

        errno = err.errno

        if errno == 2:

          error("MBII folder does not exist.")

        elif errno == 13:

          error("Cannot list MBII folder. Permission denied.")

        elif errno == 20:

          error("MBII folder is not a directory.")

        elif errno == 22:

          error("Invalid MBII folder.")

        else:

          error("Unexpected error while listing MBII folder (ERRNO: %i)." % (errno))

      try:

        self.address = split(strip(self.address), ":")

        if len(self.address) != 2:

          error("Incorrect server address format.")

        self.address = (gethostbyname_ex(self.address[0])[2][0], int(self.address[1]))

        if self.address[1] < 1 or self.address[1] > 65535:

          raise ValueError

      except AttributeError:

        error("Server address is not defined.")

      except gaierror:

        error("Invalid server address.")

      except ValueError:

        error("Incorrect server port (1-65535).")

      self.bindaddr = strip(self.bindaddr)

      try:

        self.bindaddr = gethostbyname_ex(self.bindaddr)[2][0] if self.bindaddr else "0.0.0.0"

      except gaierror:

        error("Invalid bind address.")

      try:

        self.rcon_pwd = strip(self.rcon_pwd)

        if not self.rcon_pwd:

          error("Rcon password is empty.")

      except AttributeError:

        error("Rcon password is not defined.")

      try:

        self.flood_protection = float(self.flood_protection)

        if self.flood_protection < 0:

          error("Flood protection must be greater than or equal 0 seconds.")

      except AttributeError:

        error("Flood protection is not defined.")

      except ValueError:

        error("Flood protection is neither an integer nor a floating point.")

      try:

        self.use_say_only = int(self.use_say_only)

        if self.use_say_only not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        error("Use say only is not defined.")

      except ValueError:

        error("Use say only must be either 0 (disabled) or 1 (enabled).")

      try:

        self.name_protection = int(self.name_protection)

        if self.name_protection not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        error("Name protection is not defined.")

      except ValueError:

        error("Name protection must be either 0 (disabled) or 1 (enabled).")

      self.default_game = split(self.default_game)

      if not self.default_game:

        self.default_game = False

      elif len(self.default_game) <= 3:

        try:

          self.default_game[0] = int(self.default_game[0])

          if self.default_game[0] not in (0, 1, 2, 3):

            error("Invalid mode for default game (0, 1, 2, 3).")

          elif lower(self.default_game[1]) not in lower_bsps:

            error("Default map %s is not in the server." % (self.default_game[1]))

        except ValueError:

          if len(self.default_game) == 2:

            error("Default game mode is not an integer.")

          elif lower(self.default_game[0]) not in lower_bsps:

            error("Default map %s is not in the server." % (self.default_game[0]))

        except IndexError:

          pass

        self.default_game = tuple(self.default_game)

      else:

        error("Too many options for default game (mode map or map/mode).")

      try:

        self.clean_log = tuple((int(i) for i in iter(split(self.clean_log))))

        if not self.clean_log[0]:

          if len(self.clean_log) > 1:

            raise IndexError

          self.clean_log = False

        elif self.clean_log[0] in (1, 2):

          if len(self.clean_log) != 2:

            raise IndexError

          elif self.clean_log[1] < 1:

            error("Log size for cleaning must be greater than or equal 1 megabyte.")

          self.clean_log = (self.clean_log[0], (self.clean_log[1] * 1048576))

        else:

          error("Invalid value for clean log (0, 1, 2).")

      except AttributeError:

        error("Clean log is not defined.")

      except ValueError:

        error("Clean log contains a non integer value.")

      except IndexError:

        error("Incorrect format for clean log.")

# Admin voting settings.

      try:

        self.admin_voting = tuple((int(i) for i in iter(split(self.admin_voting))))

        if len(self.admin_voting) != 2:

          error("Incorrect format for admin voting.")

        elif self.admin_voting[0] not in (0, 1):

          error("Invalid value for admin voting (0, 1).")

        elif self.admin_voting[1] < 1:

          error("Number of %s for admin voting must be greater than or equal 1."
                % ("minutes" if not self.admin_voting[0] else "rounds"))

      except AttributeError:

        error("Admin voting is not defined.")

      except ValueError:

        error("Admin voting contains a non integer value.")

      try:

        self.admin_minimum_votes = float(self.admin_minimum_votes)

        if self.admin_minimum_votes < 0 or self.admin_minimum_votes > 100:

          error("Admin minimum votes must range from 0 to 100 percent.")

      except AttributeError:

        error("Admin minimum votes is not defined.")

      except ValueError:

        error("Admin minimum votes is neither an integer nor a floating point.")

      try:

        self.admin_skip_voting = int(self.admin_skip_voting)

        if self.admin_skip_voting not in (0, 1, 2):

          error("Invalid value for admin skip voting (0, 1, 2).")

      except AttributeError:

        error("Admin skip voting is not defined.")

      except ValueError:

        error("Admin skip voting is not an integer.")

# Map limit settings.

      try:

        self.roundlimit = int(self.roundlimit)

        if self.roundlimit == 1:

          self.cvar += 1879

        elif self.roundlimit: # No boolean value.

          raise ValueError

      except AttributeError:

        error("Roundlimit is not defined.")

      except ValueError:

        error("Roundlimit must be either 0 (disabled) or 1 (enabled).")

      try:

        self.timelimit = int(self.timelimit)

        if self.timelimit == 1:

          self.cvar += 1890

        elif self.timelimit: # No boolean value.

          raise ValueError

      except AttributeError:

        error("Timelimit is not defined.")

      except ValueError:

        error("Timelimit must be either 0 (disabled) or 1 (enabled).")

      if self.roundlimit or self.timelimit:

        try:

          self.limit_voting = tuple((int(i) for i in iter(split(self.limit_voting))))

          if len(self.limit_voting) != 2:

            error("Incorrect format for map limit voting.")

          elif self.limit_voting[0] not in (0, 1):

            error("Invalid value for map limit voting (0, 1).")

          elif self.limit_voting[1] < 1:

            error("Number of %s for map limit voting must be greater than or equal 1."
                  % ("minutes" if not self.limit_voting[0] else "rounds"))

        except AttributeError:

          error("Map limit voting is not defined.")

        except ValueError:

          error("Map limit voting contains a non integer value.")

        try:

          self.limit_minimum_votes = float(self.limit_minimum_votes)

          if self.limit_minimum_votes < 0 or self.limit_minimum_votes > 100:

            error("Map limit minimum votes must range from 0 to 100 percent.")

        except AttributeError:

          error("Map limit minimum votes is not defined.")

        except ValueError:

          error("Map limit minimum votes is neither an integer nor a floating point.")

        try:

          self.limit_extend = tuple((int(i) for i in iter(split(self.limit_extend))))

          if self.limit_extend[0] in (0, 2):

            if len(self.limit_extend) > 1:

              raise IndexError

          elif self.limit_extend[0] == 1:

            if len(self.limit_extend) != 2:

              raise IndexError

            elif self.limit_extend[1] < 1:

              error("Map limit number of extensions must be greater than or equal 1.")

          else:

            error("Invalid value for map limit extend (0, 1, 2).")

        except AttributeError:

          error("Map limit extend is not defined.")

        except ValueError:

          error("Map limit extend contains a non integer value.")

        except IndexError:

          error("Incorrect format for map limit extend.")

        try:

          self.limit_s_wait_time = int(self.limit_s_wait_time)

          if self.limit_s_wait_time < 0:

            error("Map limit successful wait time must be greater than or equal 0 seconds.")

        except AttributeError:

          error("Map limit successful wait time is not defined.")

        except ValueError:

          error("Map limit successful wait time is not an integer.")

        try:

          self.limit_f_wait_time = int(self.limit_f_wait_time)

          if self.limit_f_wait_time < 0:

            error("Map limit failed wait time must be greater than or equal 0 seconds.")

        except AttributeError:

          error("Map limit failed wait time is not defined.")

        except ValueError:

          error("Map limit failed wait time is not an integer.")

        try:

          self.limit_skip_voting = int(self.limit_skip_voting)

          if self.limit_skip_voting not in (0, 1, 2):

            error("Invalid value for map limit skip voting (0, 1, 2).")

        except AttributeError:

          error("Map limit skip voting is not defined.")

        except ValueError:

          error("Map limit skip voting is not an integer.")

        try:

          self.limit_second_turn = int(self.limit_second_turn)

          if self.limit_second_turn not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          error("Map limit second turn is not defined.")

        except ValueError:

          error("Map limit second turn must be either 0 (disabled) or 1 (enabled).")

        try:

          self.limit_change_immediately = int(self.limit_change_immediately)

          if self.limit_change_immediately not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          error("Map limit change immediately is not defined.")

        except ValueError:

          error("Map limit change immediately must be either 0 (disabled) or 1 (enabled).")

      else:

        self.limit_voting = self.limit_minimum_votes = \
        self.limit_extend = self.limit_s_wait_time = self.limit_f_wait_time = \
        self.limit_skip_voting = self.limit_second_turn = self.limit_change_immediately = None

# Rock the Vote settings.

      try:

        self.rtv = int(self.rtv)

        if self.rtv == 1:

          self.cvar += 1928

          try:

            self.rtv_rate = float(self.rtv_rate)

            if self.rtv_rate < 0 or self.rtv_rate > 100:

              error("RTV rate must range from 0 to 100 percent.")

          except AttributeError:

            error("RTV rate is not defined.")

          except ValueError:

            error("RTV rate is neither an integer nor a floating point.")

          try:

            self.rtv_voting = tuple((int(i) for i in iter(split(self.rtv_voting))))

            if len(self.rtv_voting) != 2:

              error("Incorrect format for RTV voting.")

            elif self.rtv_voting[0] not in (0, 1):

              error("Invalid value for RTV voting (0, 1).")

            elif self.rtv_voting[1] < 1:

              error("Number of %s for RTV voting must be greater than or equal 1."
                    % ("minutes" if not self.rtv_voting[0] else "rounds"))

          except AttributeError:

            error("RTV voting is not defined.")

          except ValueError:

            error("RTV voting contains a non integer value.")

          try:

            self.rtv_minimum_votes = float(self.rtv_minimum_votes)

            if self.rtv_minimum_votes < 0 or self.rtv_minimum_votes > 100:

              error("RTV minimum votes must range from 0 to 100 percent.")

          except AttributeError:

            error("RTV minimum votes is not defined.")

          except ValueError:

            error("RTV minimum votes is neither an integer nor a floating point.")

          try:

            self.rtv_extend = tuple((int(i) for i in iter(split(self.rtv_extend))))

            if self.rtv_extend[0] in (0, 2):

              if len(self.rtv_extend) > 1:

                raise IndexError

            elif self.rtv_extend[0] == 1:

              if len(self.rtv_extend) != 2:

                raise IndexError

              elif self.rtv_extend[1] < 1:

                error("RTV number of extensions must be greater than or equal 1.")

            else:

              error("Invalid value for RTV extend (0, 1, 2).")

          except AttributeError:

            error("RTV extend is not defined.")

          except ValueError:

            error("RTV extend contains a non integer value.")

          except IndexError:

            error("Incorrect format for RTV extend.")

          try:

            self.rtv_s_wait_time = int(self.rtv_s_wait_time)

            if self.rtv_s_wait_time < 0:

              error("RTV successful wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            error("RTV successful wait time is not defined.")

          except ValueError:

            error("RTV successful wait time is not an integer.")

          try:

            self.rtv_f_wait_time = int(self.rtv_f_wait_time)

            if self.rtv_f_wait_time < 0:

              error("RTV failed wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            error("RTV failed wait time is not defined.")

          except ValueError:

            error("RTV failed wait time is not an integer.")

          try:

            self.rtv_skip_voting = int(self.rtv_skip_voting)

            if self.rtv_skip_voting not in (0, 1, 2):

              error("Invalid value for RTV skip voting (0, 1, 2).")

          except AttributeError:

            error("RTV skip voting is not defined.")

          except ValueError:

            error("RTV skip voting is not an integer.")

          try:

            self.rtv_second_turn = int(self.rtv_second_turn)

            if self.rtv_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            error("RTV second turn is not defined.")

          except ValueError:

            error("RTV second turn must be either 0 (disabled) or 1 (enabled).")

          try:

            self.rtv_change_immediately = int(self.rtv_change_immediately)

            if self.rtv_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            error("RTV change immediately is not defined.")

          except ValueError:

            error("RTV change immediately must be either 0 (disabled) or 1 (enabled).")

        elif not self.rtv:

          self.rtv_rate = self.rtv_voting = self.rtv_minimum_votes = \
          self.rtv_extend = self.rtv_s_wait_time = self.rtv_f_wait_time = \
          self.rtv_skip_voting = self.rtv_second_turn = self.rtv_change_immediately = None

        else: # No boolean value.

          raise ValueError

      except AttributeError:

        error("RTV is not defined.")

      except ValueError:

        error("RTV must be either 0 (disabled) or 1 (enabled).")

# Map settings.

      if self.roundlimit or self.timelimit or self.rtv:

        try:

          self.automatic_maps = int(self.automatic_maps)

          if not self.automatic_maps:

            self.maps = strip(self.maps)

            if not self.maps:

              self.maps = join_path(dirname(self.config_path), "maps.txt")

            else:

              try:

                while self.maps[-1] in (" ", "\\", "/"):

                  self.maps = self.maps[:-1]

                self.maps = normpath(self.maps)

              except IndexError:

                error("Invalid map file.")

            self.secondary_maps = strip(self.secondary_maps)

            if not self.secondary_maps:

              self.secondary_maps = join_path(dirname(self.config_path), "secondary_maps.txt")

            else:

              try:

                while self.secondary_maps[-1] in (" ", "\\", "/"):

                  self.secondary_maps = self.secondary_maps[:-1]

                self.secondary_maps = normpath(self.secondary_maps)

              except IndexError:

                error("Invalid secondary map file.")

            if normcase(realpath(self.maps)) == normcase(realpath(self.secondary_maps)):

              error("Map and secondary map files are the same.")

            try:

              with open(self.maps, "rt") as mapfile:

# Remove map duplicates.
# Only the first occurrence of a map will be added.

                map_duplicates = defaultdict(bool)
                maps = tuple((strip(line) for line in mapfile
                              if (strip(line) and
                                  lower(strip(line)) not in map_duplicates and
                                  not map_duplicates[lower(strip(line))])))

              if not maps:

                warning("The map list is empty.")
                self.create_maplist(bsps)

                if self.secondary_maps:

                  try:

                    self.pick_secondary_maps = int(self.pick_secondary_maps)

                    if self.pick_secondary_maps not in (0, 1, 2):

                      error("Invalid value for pick secondary maps (0, 1, 2).")

                  except AttributeError:

                    error("Pick secondary maps is not defined.")

                  except ValueError:

                    error("Pick secondary maps is not an integer.")

                else:

                  self.pick_secondary_maps = None

              else:

# Check whether the map has a BSP file.

                non_bsps = tuple((mapname for mapname in iter(maps)
                                  if lower(mapname) not in lower_bsps))

                if non_bsps:

                  error("Map%s not found in the server:\n\n%s" %
                        (("s" if len(non_bsps) > 1 else ""),
                         "\n".join(non_bsps)))

                self.maps = maps

                try:

                  with open(self.secondary_maps, "rt") as secondary_mapfile:

# Remove map duplicates.
# Only the first occurrence of a map will be added.

                    map_duplicates = defaultdict(bool)
                    self.secondary_maps = tuple((strip(line) for line in secondary_mapfile
                                                 if (strip(line) and
                                                     lower(strip(line)) not in map_duplicates and
                                                     not map_duplicates[lower(strip(line))])))

                  if self.secondary_maps:

# Check whether the map has a BSP file.

                    non_bsps = tuple((mapname for mapname in iter(self.secondary_maps)
                                      if lower(mapname) not in lower_bsps))

                    if non_bsps:

                      error("Secondary map%s not found in the server:\n\n%s" %
                            (("s" if len(non_bsps) > 1 else ""),
                             "\n".join(non_bsps)))

                    repeated_maps = tuple((lower(mapname) for mapname in iter(self.maps)))
                    repeated_maps = tuple((mapname for mapname in iter(self.secondary_maps)
                                           if lower(mapname) in repeated_maps)) # Compare primary and secondary maps.

                    if repeated_maps:

                      error("Map%s found in both primary and secondary files:\n\n%s" %
                            (("s" if len(repeated_maps) > 1 else ""),
                             "\n".join(repeated_maps)))

                    try:

                      self.pick_secondary_maps = int(self.pick_secondary_maps)

                      if self.pick_secondary_maps not in (0, 1, 2):

                        error("Invalid value for pick secondary maps (0, 1, 2).")

                    except AttributeError:

                      error("Pick secondary maps is not defined.")

                    except ValueError:

                      error("Pick secondary maps is not an integer.")

                  else:

                    self.pick_secondary_maps = None

                except IOError, err:

                  errno = err.errno

                  if errno == 2:

                    self.secondary_maps = ()
                    self.pick_secondary_maps = None

                  elif errno == 13:

                    error("Cannot read secondary map file. Permission denied.")

                  elif errno == 21:

                    error("Secondary map file is set to a directory.")

                  elif errno == 22:

                    error("Invalid secondary map file.")

                  else:

                    error("Unexpected error while reading secondary map file (ERRNO: %i)." % (errno))

            except IOError, err:

              errno = err.errno

              if errno == 2:

                warning("Map file does not exist.")
                self.create_maplist(bsps)

                if self.secondary_maps:

                  try:

                    self.pick_secondary_maps = int(self.pick_secondary_maps)

                    if self.pick_secondary_maps not in (0, 1, 2):

                      error("Invalid value for pick secondary maps (0, 1, 2).")

                  except AttributeError:

                    error("Pick secondary maps is not defined.")

                  except ValueError:

                    error("Pick secondary maps is not an integer.")

                else:

                  self.pick_secondary_maps = None

              elif errno == 13:

                error("Cannot read map file. Permission denied.")

              elif errno == 21:

                error("Map file is set to a directory.")

              elif errno == 22:

                error("Invalid map file.")

              else:

                error("Unexpected error while reading map file (ERRNO: %i)." % (errno))

          elif self.automatic_maps == 1: # Use all available maps from BSP files.

            self.maps = tuple(bsps)
            self.secondary_maps = ()
            self.pick_secondary_maps = None

          else: # No boolean value.

            raise ValueError

        except AttributeError:

          error("Automatic maps is not defined.")

        except ValueError:

          error("Automatic maps must be either 0 (disabled) or 1 (enabled).")

        try:

          self.map_priority = tuple((int(i) for i in iter(split(self.map_priority))))

          if len(self.map_priority) == 3:

            if self.map_priority[0] not in (0, 1, 2):

              error("Invalid value for map priority/primary maps (0, 1, 2).")

            elif self.map_priority[1] not in (0, 1, 2):

              error("Invalid value for map priority/secondary maps (0, 1, 2).")

            elif self.map_priority[2] not in (0, 1, 2):

              error("Invalid value for map priority/extend map (0, 1, 2).")

          else:

            error("Incorrect format for map priority.")

        except AttributeError:

          error("Map priority is not defined.")

        except ValueError:

          error("Map priority contains a non integer value.")

        if (len(self.maps) + len(self.secondary_maps)) > 5:

          try:

            self.nomination_type = int(self.nomination_type)

            if self.nomination_type not in (0, 1):

              error("Invalid value for nomination type (0, 1).")

          except AttributeError:

            error("Nomination type is not defined.")

          except ValueError:

            error("Nomination type is not an integer.")

        elif self.pick_secondary_maps == 0:

          error("Pick secondary maps must be enabled whether secondary maps are present and nominations are disabled.")

        else:

          self.nomination_type = None

        try:

          self.enable_recently_played = int(self.enable_recently_played)

          if self.enable_recently_played < 0:

            error("Enable recently played maps must be greater than or equal 0 seconds.")

        except AttributeError:

          error("Enable recently played maps is not defined.")

        except ValueError:

          error("Enable recently played maps is not an integer.")

      else:

        self.automatic_maps = self.maps = self.secondary_maps = \
        self.pick_secondary_maps = self.map_priority = self.nomination_type = None
        self.enable_recently_played = 0

# Rock the Mode settings.

      try:

        self.rtm = {
                    0: False,
                    1: (0,),
                    2: (1,),
                    3: (2,),
                    4: (0, 1),
                    5: (0, 2),
                    6: (1, 2),
                    7: (0, 1, 2),
					8: (3),
					9: (0, 3),
					10: (1, 3),
					11: (2, 3),
					12: (0,2,3),
					13: (1,2,3),
					14: (0,1,2,3),
                   }[int(self.rtm)]

        if self.rtm:

          self.cvar += 2000

          try:

            self.mode_priority = tuple((int(i) for i in iter(split(self.mode_priority))))

            if len(self.mode_priority) == 5:

              if self.mode_priority[0] not in (0, 1, 2):

                error("Invalid value for mode priority/open mode (0, 1, 2).")

              elif self.mode_priority[1] not in (0, 1, 2, 3):

                error("Invalid value for mode priority/semi authentic mode (0, 1, 2).")

              elif self.mode_priority[2] not in (0, 1, 2):

                error("Invalid value for mode priority/full authentic mode (0, 1, 2).")

              elif self.mode_priority[3] not in (0, 1, 2):

                error("Invalid value for mode priority/duel mode (0, 1, 2).")

              elif self.mode_priority[4] not in (0, 1, 2):

                error("Invalid value for mode priority/extend mode (0, 1, 2).")

            else:

              error("Incorrect format for mode priority.")

          except AttributeError:

            error("Mode priority is not defined.")

          except ValueError:

            error("Mode priority contains a non integer value.")

          try:

            self.rtm_rate = float(self.rtm_rate)

            if self.rtm_rate < 0 or self.rtm_rate > 100:

              error("RTM rate must range from 0 to 100 percent.")

          except AttributeError:

            error("RTM rate is not defined.")

          except ValueError:

            error("RTM rate is neither an integer nor a floating point.")

          try:

            self.rtm_voting = tuple((int(i) for i in iter(split(self.rtm_voting))))

            if len(self.rtm_voting) != 2:

              error("Incorrect format for RTM voting.")

            elif self.rtm_voting[0] not in (0, 1):

              error("Invalid value for RTM voting (0, 1).")

            elif self.rtm_voting[1] < 1:

              error("Number of %s for RTM voting must be greater than or equal 1."
                    % ("minutes" if not self.rtm_voting[0] else "rounds"))

          except AttributeError:

            error("RTM voting is not defined.")

          except ValueError:

            error("RTM voting contains a non integer value.")

          try:

            self.rtm_minimum_votes = float(self.rtm_minimum_votes)

            if self.rtm_minimum_votes < 0 or self.rtm_minimum_votes > 100:

              error("RTM minimum votes must range from 0 to 100 percent.")

          except AttributeError:

            error("RTM minimum votes is not defined.")

          except ValueError:

            error("RTM minimum votes is neither an integer nor a floating point.")

          try:

            self.rtm_extend = tuple((int(i) for i in iter(split(self.rtm_extend))))

            if self.rtm_extend[0] in (0, 2):

              if len(self.rtm_extend) > 1:

                raise IndexError

            elif self.rtm_extend[0] == 1:

              if len(self.rtm_extend) != 2:

                raise IndexError

              elif self.rtm_extend[1] < 1:

                error("RTM number of extensions must be greater than or equal 1.")

            else:

              error("Invalid value for RTM extend (0, 1, 2).")

          except AttributeError:

            error("RTM extend is not defined.")

          except ValueError:

            error("RTM extend contains a non integer value.")

          except IndexError:

            error("Incorrect format for RTM extend.")

          try:

            self.rtm_s_wait_time = int(self.rtm_s_wait_time)

            if self.rtm_s_wait_time < 0:

              error("RTM successful wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            error("RTM successful wait time is not defined.")

          except ValueError:

            error("RTM successful wait time is not an integer.")

          try:

            self.rtm_f_wait_time = int(self.rtm_f_wait_time)

            if self.rtm_f_wait_time < 0:

              error("RTM failed wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            error("RTM failed wait time is not defined.")

          except ValueError:

            error("RTM failed wait time is not an integer.")

          try:

            self.rtm_skip_voting = int(self.rtm_skip_voting)

            if self.rtm_skip_voting not in (0, 1, 2):

              error("Invalid value for RTM skip voting (0, 1, 2).")

          except AttributeError:

            error("RTM skip voting is not defined.")

          except ValueError:

            error("RTM skip voting is not an integer.")

          try:

            self.rtm_second_turn = int(self.rtm_second_turn)

            if self.rtm_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            error("RTM second turn is not defined.")

          except ValueError:

            error("RTM second turn must be either 0 (disabled) or 1 (enabled).")

          try:

            self.rtm_change_immediately = int(self.rtm_change_immediately)

            if self.rtm_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            error("RTM change immediately is not defined.")

          except ValueError:

            error("RTM change immediately must be either 0 (disabled) or 1 (enabled).")

        else:

          self.mode_priority = self.rtm_rate = self.rtm_voting = \
          self.rtm_minimum_votes = self.rtm_extend = \
          self.rtm_s_wait_time = self.rtm_f_wait_time = \
          self.rtm_skip_voting = self.rtm_second_turn = self.rtm_change_immediately = None

      except AttributeError:

        error("RTM is not defined.")

      except ValueError:

        error("RTM is not an integer.")

      except KeyError:

        error("Invalid value for RTM (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14).")

# Connection test.

      if tries:

        for i in xrange(1, (tries+1)):

          sock = socket(AF_INET, SOCK_DGRAM)

          try:

            bind(sock, (self.bindaddr, 0))

          except socketError:

            close(sock)
            error("Bind address is unavailable.")

          try:

            settimeout(sock, 12)
            connect(sock, self.address)
            sock.send("\xff\xff\xff\xffrcon %s sets RTVRTM %i/%s" % (self.rcon_pwd, self.cvar, VERSION))
            reply = lower(strip(sock.recv(1024)))

            if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):

              error("Incorrect rcon password.")

            elif reply != "\xff\xff\xff\xffprint":

              error("Unexpected error while contacting server for the first time.")

            break

          except socketTimeout:

            if i == tries:

              error("Could not contact the server after %i tr%s (TIMEOUT)."
                    % (tries,
                       ("ies" if tries > 1 else "y")))

          except socketError:

            if i == tries:

              error("Could not contact the server after %i tr%s (REFUSED/UNREACHABLE)."
                    % (tries,
                       ("ies" if tries > 1 else "y")))

            sleep(12)

          finally:

            shutdown(sock, SHUT_RDWR)
            close(sock)

      else:

        while(True):

          sock = socket(AF_INET, SOCK_DGRAM)

          try:

            bind(sock, (self.bindaddr, 0))

          except socketError:

            close(sock)
            error("Bind address is unavailable.")

          try:

            settimeout(sock, 12)
            connect(sock, self.address)
            sock.send("\xff\xff\xff\xffrcon %s sets RTVRTM %i/%s" % (self.rcon_pwd, self.cvar, VERSION))
            reply = lower(strip(sock.recv(1024)))

            if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):

              error("Incorrect rcon password.")

            elif reply != "\xff\xff\xff\xffprint":

              error("Unexpected error while contacting server for the first time.")

            break

          except socketTimeout:

            continue

          except socketError:

            sleep(12)

          finally:

            shutdown(sock, SHUT_RDWR)
            close(sock)

      print("Done!")

  def rehash(self):

    """Rehash the configuration."""

    startswith = str.startswith
    endswith = str.endswith
    lower = str.lower
    strip = str.strip
    lstrip = str.lstrip
    rstrip = str.rstrip
    split = str.split
    namelist = ZipFile.namelist
    pk3close = ZipFile.close
    bind = socket.bind
    settimeout = socket.settimeout
    connect = socket.connect
    shutdown = socket.shutdown
    close = socket.close
    self._bindaddr = self._default_game = self._maps = self._secondary_maps = "" # Optional configuration.
    cvar = 0
    print("[*] Checking configuration file..."),

    try:

# Read configuration file and set each temporary configuration attribute.

      with open(self.config_path, "rt") as cfg:

        print("Done!")
        print("[*] Reading configuration..."),

        for line in cfg:

          line = lstrip(line)

          if line and not startswith(line, "*"): # Ignore empty lines and comments.

            try:

              attr, value = split(line, ":", 1)
              attr = self.fields[lower(rstrip(attr))]
              setattr(self, "_%s" % (attr), value)

            except (ValueError, KeyError):

              continue

    except IOError, err:

      errno = err.errno

      if errno == 2:

        warning("Configuration file does not exist.", rehash=True)

      elif errno == 13:

        warning("Cannot read configuration file. Permission denied.", rehash=True)

      elif errno == 21:

        warning("Configuration file is set to a directory.", rehash=True)

      elif errno == 22:

        warning("Invalid configuration file.", rehash=True)

      else:

        warning("Unexpected error while reading configuration file (ERRNO: %i)." % (errno), rehash=True)

      return False

    else:

# Configuration and general error checks.

      print("Done!")
      print("[*] Checking options for errors..."),

# General settings.

      try:

        self._MBII_Folder = normpath(strip(self._MBII_Folder))
        pk3s = (pk3 for pk3 in iter(listdir(self._MBII_Folder))
                if endswith(lower(pk3), ".pk3")) # Get all PK3 files within the MBII folder.
        bsps = []

        for pk3 in pk3s:

          try:

            pk3zip = ZipFile(join_path(self._MBII_Folder, pk3), "r")
            bsps += [basename(bsp)[:-4] for bsp in iter(namelist(pk3zip)) if endswith(lower(bsp), ".bsp")] # Get all BSP files.
            pk3close(pk3zip)

          except IOError, err:

            warning("Error while trying to read %s (ERRNO: %i)." % (pk3, err.errno))
            print("[*] Checking options for errors..."),

          except BadZipfile:

            warning("%s is not a valid pk3 file." % (pk3))
            print("[*] Checking options for errors..."),

        if not bsps:

          warning("No BSP map files detected. Make sure MBII folder path is correct.", rehash=True)
          return False

        map_duplicates = defaultdict(bool)
        bsps = tuple((bsp for bsp in iter(bsps)
                      if (lower(bsp) not in map_duplicates and
                          not map_duplicates[lower(bsp)]))) # Ensure that we don't get duplicates from replacements.
        lower_bsps = tuple((lower(bsp) for bsp in iter(bsps)))

      except AttributeError:

        warning("MBII folder is not defined.", rehash=True)
        return False

      except (WindowsError if platform == "win32" else OSError), err:

        errno = err.errno

        if errno == 2:

          warning("MBII folder does not exist.", rehash=True)

        elif errno == 13:

          warning("Cannot list MBII folder. Permission denied.", rehash=True)

        elif errno == 20:

          warning("MBII folder is not a directory.", rehash=True)

        elif errno == 22:

          warning("Invalid MBII folder.", rehash=True)

        else:

          warning("Unexpected error while listing MBII folder (ERRNO: %i)." % (errno), rehash=True)

        return False

      try:

        self._address = split(strip(self._address), ":")

        if len(self._address) != 2:

          warning("Incorrect server address format.", rehash=True)
          return False

        self._address = (gethostbyname_ex(self._address[0])[2][0], int(self._address[1]))

        if self._address[1] < 1 or self._address[1] > 65535:

          raise ValueError

      except AttributeError:

        warning("Server address is not defined.", rehash=True)
        return False

      except gaierror:

        warning("Invalid server address.", rehash=True)
        return False

      except ValueError:

        warning("Incorrect server port (1-65535).", rehash=True)
        return False

      self._bindaddr = strip(self._bindaddr)

      try:

        self._bindaddr = gethostbyname_ex(self._bindaddr)[2][0] if self._bindaddr else "0.0.0.0"

      except gaierror:

        warning("Invalid bind address.", rehash=True)
        return False

      try:

        self._rcon_pwd = strip(self._rcon_pwd)

        if not self._rcon_pwd:

          warning("Rcon password is empty.", rehash=True)
          return False

      except AttributeError:

        warning("Rcon password is not defined.", rehash=True)
        return False

      try:

        self._flood_protection = float(self._flood_protection)

        if self._flood_protection < 0:

          warning("Flood protection must be greater than or equal 0 seconds.", rehash=True)
          return False

      except AttributeError:

        warning("Flood protection is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Flood protection is neither an integer nor a floating point.", rehash=True)
        return False

      try:

        self._use_say_only = int(self._use_say_only)

        if self._use_say_only not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        warning("Use say only is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Use say only must be either 0 (disabled) or 1 (enabled).", rehash=True)
        return False

      try:

        self._name_protection = int(self._name_protection)

        if self._name_protection not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        warning("Name protection is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Name protection must be either 0 (disabled) or 1 (enabled).", rehash=True)
        return False

      self._default_game = split(self._default_game)

      if not self._default_game:

        self._default_game = False

      elif len(self._default_game) <= 2:

        try:

          self._default_game[0] = int(self._default_game[0])

          if self._default_game[0] not in (0, 1, 2, 3):

            warning("Invalid mode for default game (0, 1, 2, 3).", rehash=True)
            return False

          elif lower(self._default_game[1]) not in lower_bsps:

            warning("Default map %s is not in the server." % (self._default_game[1]), rehash=True)
            return False

        except ValueError:

          if len(self._default_game) == 2:

            warning("Default game mode is not an integer.", rehash=True)
            return False

          elif lower(self._default_game[0]) not in lower_bsps:

            warning("Default map %s is not in the server." % (self._default_game[0]), rehash=True)
            return False

        except IndexError:

          pass

        self._default_game = tuple(self._default_game)

      else:

        warning("Too many options for default game (mode map or map/mode).", rehash=True)
        return False

      try:

        self._clean_log = tuple((int(i) for i in iter(split(self._clean_log))))

        if not self._clean_log[0]:

          if len(self._clean_log) > 1:

            raise IndexError

          self._clean_log = False

        elif self._clean_log[0] in (1, 2):

          if len(self._clean_log) != 2:

            raise IndexError

          elif self._clean_log[1] < 1:

            warning("Log size for cleaning must be greater than or equal 1 megabyte.", rehash=True)
            return False

          self._clean_log = (self._clean_log[0], (self._clean_log[1] * 1048576))

        else:

          warning("Invalid value for clean log (0, 1, 2).", rehash=True)
          return False

      except AttributeError:

        warning("Clean log is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Clean log contains a non integer value.", rehash=True)
        return False

      except IndexError:

        warning("Incorrect format for clean log.", rehash=True)
        return False

# Admin voting settings.

      try:

        self._admin_voting = tuple((int(i) for i in iter(split(self._admin_voting))))

        if len(self._admin_voting) != 2:

          warning("Incorrect format for admin voting.", rehash=True)
          return False

        elif self._admin_voting[0] not in (0, 1):

          warning("Invalid value for admin voting (0, 1).", rehash=True)
          return False

        elif self._admin_voting[1] < 1:

          warning("Number of %s for admin voting must be greater than or equal 1."
                  % ("minutes" if not self._admin_voting[0] else "rounds"),
                  rehash=True)
          return False

      except AttributeError:

        warning("Admin voting is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Admin voting contains a non integer value.", rehash=True)
        return False

      try:

        self._admin_minimum_votes = float(self._admin_minimum_votes)

        if self._admin_minimum_votes < 0 or self._admin_minimum_votes > 100:

          warning("Admin minimum votes must range from 0 to 100 percent.", rehash=True)
          return False

      except AttributeError:

        warning("Admin minimum votes is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Admin minimum votes is neither an integer nor a floating point.", rehash=True)
        return False

      try:

        self._admin_skip_voting = int(self._admin_skip_voting)

        if self._admin_skip_voting not in (0, 1, 2):

          warning("Invalid value for admin skip voting (0, 1, 2).", rehash=True)
          return False

      except AttributeError:

        warning("Admin skip voting is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Admin skip voting is not an integer.", rehash=True)
        return False

# Map limit settings.

      try:

        self._roundlimit = int(self._roundlimit)

        if self._roundlimit == 1:

          cvar += 1879

        elif self._roundlimit: # No boolean value.

          raise ValueError

      except AttributeError:

        warning("Roundlimit is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Roundlimit must be either 0 (disabled) or 1 (enabled).", rehash=True)
        return False

      try:

        self._timelimit = int(self._timelimit)

        if self._timelimit == 1:

          cvar += 1890

        elif self._timelimit: # No boolean value.

          raise ValueError

      except AttributeError:

        warning("Timelimit is not defined.", rehash=True)
        return False

      except ValueError:

        warning("Timelimit must be either 0 (disabled) or 1 (enabled).", rehash=True)
        return False

      if self._roundlimit or self._timelimit:

        try:

          self._limit_voting = tuple((int(i) for i in iter(split(self._limit_voting))))

          if len(self._limit_voting) != 2:

            warning("Incorrect format for map limit voting.", rehash=True)
            return False

          elif self._limit_voting[0] not in (0, 1):

            warning("Invalid value for map limit voting (0, 1).", rehash=True)
            return False

          elif self._limit_voting[1] < 1:

            warning("Number of %s for map limit voting must be greater than or equal 1."
                    % ("minutes" if not self._limit_voting[0] else "rounds"),
                    rehash=True)
            return False

        except AttributeError:

          warning("Map limit voting is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit voting contains a non integer value.", rehash=True)
          return False

        try:

          self._limit_minimum_votes = float(self._limit_minimum_votes)

          if self._limit_minimum_votes < 0 or self._limit_minimum_votes > 100:

            warning("Map limit minimum votes must range from 0 to 100 percent.", rehash=True)
            return False

        except AttributeError:

          warning("Map limit minimum votes is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit minimum votes is neither an integer nor a floating point.", rehash=True)
          return False

        try:

          self._limit_extend = tuple((int(i) for i in iter(split(self._limit_extend))))

          if self._limit_extend[0] in (0, 2):

            if len(self._limit_extend) > 1:

              raise IndexError

          elif self._limit_extend[0] == 1:

            if len(self._limit_extend) != 2:

              raise IndexError

            elif self._limit_extend[1] < 1:

              warning("Map limit number of extensions must be greater than or equal 1.", rehash=True)
              return False

          else:

            warning("Invalid value for map limit extend (0, 1, 2).", rehash=True)
            return False

        except AttributeError:

          warning("Map limit extend is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit extend contains a non integer value.", rehash=True)
          return False

        except IndexError:

          warning("Incorrect format for map limit extend.", rehash=True)
          return False

        try:

          self._limit_s_wait_time = int(self._limit_s_wait_time)

          if self._limit_s_wait_time < 0:

            warning("Map limit successful wait time must be greater than or equal 0 seconds.", rehash=True)
            return False

        except AttributeError:

          warning("Map limit successful wait time is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit successful wait time is not an integer.", rehash=True)
          return False

        try:

          self._limit_f_wait_time = int(self._limit_f_wait_time)

          if self._limit_f_wait_time < 0:

            warning("Map limit failed wait time must be greater than or equal 0 seconds.", rehash=True)
            return False

        except AttributeError:

          warning("Map limit failed wait time is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit failed wait time is not an integer.", rehash=True)
          return False

        try:

          self._limit_skip_voting = int(self._limit_skip_voting)

          if self._limit_skip_voting not in (0, 1, 2):

            warning("Invalid value for map limit skip voting (0, 1, 2).", rehash=True)
            return False

        except AttributeError:

          warning("Map limit skip voting is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit skip voting is not an integer.", rehash=True)
          return False

        try:

          self._limit_second_turn = int(self._limit_second_turn)

          if self._limit_second_turn not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          warning("Map limit second turn is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit second turn must be either 0 (disabled) or 1 (enabled).", rehash=True)
          return False

        try:

          self._limit_change_immediately = int(self._limit_change_immediately)

          if self._limit_change_immediately not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          warning("Map limit change immediately is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map limit change immediately must be either 0 (disabled) or 1 (enabled).", rehash=True)
          return False

      else:

        self._limit_voting = self._limit_minimum_votes = \
        self._limit_extend = self._limit_s_wait_time = self._limit_f_wait_time = \
        self._limit_skip_voting = self._limit_second_turn = self._limit_change_immediately = None

# Rock the Vote settings.

      try:

        self._rtv = int(self._rtv)

        if self._rtv == 1:

          cvar += 1928

          try:

            self._rtv_rate = float(self._rtv_rate)

            if self._rtv_rate < 0 or self._rtv_rate > 100:

              warning("RTV rate must range from 0 to 100 percent.", rehash=True)
              return False

          except AttributeError:

            warning("RTV rate is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV rate is neither an integer nor a floating point.", rehash=True)
            return False

          try:

            self._rtv_voting = tuple((int(i) for i in iter(split(self._rtv_voting))))

            if len(self._rtv_voting) != 2:

              warning("Incorrect format for RTV voting.", rehash=True)
              return False

            elif self._rtv_voting[0] not in (0, 1):

              warning("Invalid value for RTV voting (0, 1).", rehash=True)
              return False

            elif self._rtv_voting[1] < 1:

              warning("Number of %s for RTV voting must be greater than or equal 1."
                      % ("minutes" if not self._rtv_voting[0] else "rounds"),
                      rehash=True)
              return False

          except AttributeError:

            warning("RTV voting is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV voting contains a non integer value.", rehash=True)
            return False

          try:

            self._rtv_minimum_votes = float(self._rtv_minimum_votes)

            if self._rtv_minimum_votes < 0 or self._rtv_minimum_votes > 100:

              warning("RTV minimum votes must range from 0 to 100 percent.", rehash=True)
              return False

          except AttributeError:

            warning("RTV minimum votes is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV minimum votes is neither an integer nor a floating point.", rehash=True)
            return False

          try:

            self._rtv_extend = tuple((int(i) for i in iter(split(self._rtv_extend))))

            if self._rtv_extend[0] in (0, 2):

              if len(self._rtv_extend) > 1:

                raise IndexError

            elif self._rtv_extend[0] == 1:

              if len(self._rtv_extend) != 2:

                raise IndexError

              elif self._rtv_extend[1] < 1:

                warning("RTV number of extensions must be greater than or equal 1.", rehash=True)
                return False

            else:

              warning("Invalid value for RTV extend (0, 1, 2).", rehash=True)
              return False

          except AttributeError:

            warning("RTV extend is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV extend contains a non integer value.", rehash=True)
            return False

          except IndexError:

            warning("Incorrect format for RTV extend.", rehash=True)
            return False

          try:

            self._rtv_s_wait_time = int(self._rtv_s_wait_time)

            if self._rtv_s_wait_time < 0:

              warning("RTV successful wait time must be greater than or equal 0 seconds.", rehash=True)
              return False

          except AttributeError:

            warning("RTV successful wait time is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV successful wait time is not an integer.", rehash=True)
            return False

          try:

            self._rtv_f_wait_time = int(self._rtv_f_wait_time)

            if self._rtv_f_wait_time < 0:

              warning("RTV failed wait time must be greater than or equal 0 seconds.", rehash=True)
              return False

          except AttributeError:

            warning("RTV failed wait time is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV failed wait time is not an integer.", rehash=True)
            return False

          try:

            self._rtv_skip_voting = int(self._rtv_skip_voting)

            if self._rtv_skip_voting not in (0, 1, 2):

              warning("Invalid value for RTV skip voting (0, 1, 2).", rehash=True)
              return False

          except AttributeError:

            warning("RTV skip voting is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV skip voting is not an integer.", rehash=True)
            return False

          try:

            self._rtv_second_turn = int(self._rtv_second_turn)

            if self._rtv_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            warning("RTV second turn is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV second turn must be either 0 (disabled) or 1 (enabled).", rehash=True)
            return False

          try:

            self._rtv_change_immediately = int(self._rtv_change_immediately)

            if self._rtv_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            warning("RTV change immediately is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTV change immediately must be either 0 (disabled) or 1 (enabled).", rehash=True)
            return False

        elif not self._rtv:

          self._rtv_rate = self._rtv_voting = self._rtv_minimum_votes = \
          self._rtv_extend = self._rtv_s_wait_time = self._rtv_f_wait_time = \
          self._rtv_skip_voting = self._rtv_second_turn = self._rtv_change_immediately = None

        else: # No boolean value.

          raise ValueError

      except AttributeError:

        warning("RTV is not defined.", rehash=True)
        return False

      except ValueError:

        warning("RTV must be either 0 (disabled) or 1 (enabled).", rehash=True)
        return False

# Map settings.

      if self._roundlimit or self._timelimit or self._rtv:

        try:

          self._automatic_maps = int(self._automatic_maps)

          if not self._automatic_maps:

            self._maps = strip(self._maps)

            if not self._maps:

              self._maps = join_path(dirname(self.config_path), "maps.txt")

            else:

              try:

                while self._maps[-1] in (" ", "\\", "/"):

                  self._maps = self._maps[:-1]

                self._maps = normpath(self._maps)

              except IndexError:

                warning("Invalid map file.", rehash=True)
                return False

            self._secondary_maps = strip(self._secondary_maps)

            if not self._secondary_maps:

              self._secondary_maps = join_path(dirname(self.config_path), "secondary_maps.txt")

            else:

              try:

                while self._secondary_maps[-1] in (" ", "\\", "/"):

                  self._secondary_maps = self._secondary_maps[:-1]

                self._secondary_maps = normpath(self._secondary_maps)

              except IndexError:

                warning("Invalid secondary map file.", rehash=True)
                return False

            if normcase(realpath(self._maps)) == normcase(realpath(self._secondary_maps)):

              warning("Map and secondary map files are the same.", rehash=True)
              return False

            try:

              with open(self._maps, "rt") as mapfile:

# Remove map duplicates.
# Only the first occurrence of a map will be added.

                map_duplicates = defaultdict(bool)
                self._maps = tuple((strip(line) for line in mapfile
                                    if (strip(line) and
                                        lower(strip(line)) not in map_duplicates and
                                        not map_duplicates[lower(strip(line))])))

              if not self._maps:

                warning("The map list is empty.", rehash=True)
                return False

# Check whether the map has a BSP file.

              non_bsps = tuple((mapname for mapname in iter(self._maps)
                                if lower(mapname) not in lower_bsps))

              if non_bsps:

                warning("Map%s not found in the server:\n\n%s\n" %
                        (("s" if len(non_bsps) > 1 else ""),
                         "\n".join(non_bsps)),
                        rehash=True)
                return False

            except IOError, err:

              errno = err.errno

              if errno == 2:

                warning("Map file does not exist.", rehash=True)

              elif errno == 13:

                warning("Cannot read map file. Permission denied.", rehash=True)

              elif errno == 21:

                warning("Map file is set to a directory.", rehash=True)

              elif errno == 22:

                warning("Invalid map file.", rehash=True)

              else:

                warning("Unexpected error while reading map file (ERRNO: %i)." % (errno), rehash=True)

              return False

            try:

              with open(self._secondary_maps, "rt") as secondary_mapfile:

# Remove map duplicates.
# Only the first occurrence of a map will be added.

                map_duplicates = defaultdict(bool)
                self._secondary_maps = tuple((strip(line) for line in secondary_mapfile
                                              if (strip(line) and
                                                  lower(strip(line)) not in map_duplicates and
                                                  not map_duplicates[lower(strip(line))])))

              if self._secondary_maps:

# Check whether the map has a BSP file.

                non_bsps = tuple((mapname for mapname in iter(self._secondary_maps)
                                  if lower(mapname) not in lower_bsps))

                if non_bsps:

                  warning("Secondary map%s not found in the server:\n\n%s\n" %
                          (("s" if len(non_bsps) > 1 else ""),
                           "\n".join(non_bsps)),
                          rehash=True)
                  return False

                repeated_maps = tuple((lower(mapname) for mapname in iter(self._maps)))
                repeated_maps = tuple((mapname for mapname in iter(self._secondary_maps)
                                       if lower(mapname) in repeated_maps)) # Compare primary and secondary maps.

                if repeated_maps:

                  warning("Map%s found in both primary and secondary files:\n\n%s\n" %
                          (("s" if len(repeated_maps) > 1 else ""),
                           "\n".join(repeated_maps)),
                          rehash=True)
                  return False

                try:

                  self._pick_secondary_maps = int(self._pick_secondary_maps)

                  if self._pick_secondary_maps not in (0, 1, 2):

                    warning("Invalid value for pick secondary maps (0, 1, 2).", rehash=True)
                    return False

                except AttributeError:

                  warning("Pick secondary maps is not defined.", rehash=True)
                  return False

                except ValueError:

                  warning("Pick secondary maps is not an integer.", rehash=True)
                  return False

              else:

                self._pick_secondary_maps = None

            except IOError, err:

              errno = err.errno

              if errno == 2:

                self._secondary_maps = ()
                self._pick_secondary_maps = None

              elif errno == 13:

                warning("Cannot read secondary map file. Permission denied.", rehash=True)
                return False

              elif errno == 21:

                warning("Secondary map file is set to a directory.", rehash=True)
                return False

              elif errno == 22:

                warning("Invalid secondary map file.", rehash=True)
                return False

              else:

                warning("Unexpected error while reading secondary map file (ERRNO: %i)." % (errno), rehash=True)
                return False

          elif self._automatic_maps == 1: # Use all available maps from BSP files.

            self._maps = bsps
            self._secondary_maps = ()
            self._pick_secondary_maps = None

          else: # No boolean value.

            raise ValueError

        except AttributeError:

          warning("Automatic maps is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Automatic maps must be either 0 (disabled) or 1 (enabled).", rehash=True)
          return False

        try:

          self._map_priority = tuple((int(i) for i in iter(split(self._map_priority))))

          if len(self._map_priority) == 3:

            if self._map_priority[0] not in (0, 1, 2):

              warning("Invalid value for map priority/primary maps (0, 1, 2).", rehash=True)
              return False

            elif self._map_priority[1] not in (0, 1, 2):

              warning("Invalid value for map priority/secondary maps (0, 1, 2).", rehash=True)
              return False

            elif self._map_priority[2] not in (0, 1, 2):

              warning("Invalid value for map priority/extend map (0, 1, 2).", rehash=True)
              return False

          else:

            warning("Incorrect format for map priority.", rehash=True)
            return False

        except AttributeError:

          warning("Map priority is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Map priority contains a non integer value.", rehash=True)
          return False

        if (len(self._maps) + len(self._secondary_maps)) > 5:

          try:

            self._nomination_type = int(self._nomination_type)

            if self._nomination_type not in (0, 1):

              warning("Invalid value for nomination type (0, 1).", rehash=True)
              return False

          except AttributeError:

            warning("Nomination type is not defined.", rehash=True)
            return False

          except ValueError:

            warning("Nomination type is not an integer.", rehash=True)
            return False

        elif self._pick_secondary_maps == 0:

          warning("Pick secondary maps must be enabled whether secondary maps are present and nominations are disabled.",
                  rehash=True)
          return False

        else:

          self._nomination_type = None

        try:

          self._enable_recently_played = int(self._enable_recently_played)

          if self._enable_recently_played < 0:

            warning("Enable recently played maps must be greater than or equal 0 seconds.",
                    rehash=True)
            return False

        except AttributeError:

          warning("Enable recently played maps is not defined.", rehash=True)
          return False

        except ValueError:

          warning("Enable recently played maps is not an integer.", rehash=True)
          return False

      else:

        self._automatic_maps = self._maps = self._secondary_maps = \
        self._pick_secondary_maps = self._map_priority = self._nomination_type = None
        self._enable_recently_played = 0

# Rock the Mode settings.

      try:

        self._rtm = {
                     0: False,
                     1: (0,),
                     2: (1,),
                     3: (2,),
                     4: (0, 1),
                     5: (0, 2),
                     6: (1, 2),
                     7: (0, 1, 2)
                    }[int(self._rtm)]

        if self._rtm:

          cvar += 2000

          try:

            self._mode_priority = tuple((int(i) for i in iter(split(self._mode_priority))))

            if len(self._mode_priority) == 5:

              if self._mode_priority[0] not in (0, 1, 2):

                warning("Invalid value for mode priority/open mode (0, 1, 2).", rehash=True)
                return False

              elif self._mode_priority[1] not in (0, 1, 2):

                warning("Invalid value for mode priority/semi authentic mode (0, 1, 2).", rehash=True)
                return False

              elif self._mode_priority[2] not in (0, 1, 2):

                warning("Invalid value for mode priority/full authentic mode (0, 1, 2).", rehash=True)
                return False

              elif self._mode_priority[3] not in (0, 1, 2):

                warning("Invalid value for mode priority/duel mode (0, 1, 2).", rehash=True)
                return False

              elif self._mode_priority[4] not in (0, 1, 2):

                warning("Invalid value for mode priority/extend mode (0, 1, 2).", rehash=True)
                return False

            else:

              warning("Incorrect format for mode priority.", rehash=True)
              return False

          except AttributeError:

            warning("Mode priority is not defined.", rehash=True)
            return False

          except ValueError:

            warning("Mode priority contains a non integer value.", rehash=True)
            return False

          try:

            self._rtm_rate = float(self._rtm_rate)

            if self._rtm_rate < 0 or self._rtm_rate > 100:

              warning("RTM rate must range from 0 to 100 percent.", rehash=True)
              return False

          except AttributeError:

            warning("RTM rate is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM rate is neither an integer nor a floating point.", rehash=True)
            return False

          try:

            self._rtm_voting = tuple((int(i) for i in iter(split(self._rtm_voting))))

            if len(self._rtm_voting) != 2:

              warning("Incorrect format for RTM voting.", rehash=True)
              return False

            elif self._rtm_voting[0] not in (0, 1):

              warning("Invalid value for RTM voting (0, 1).", rehash=True)
              return False

            elif self._rtm_voting[1] < 1:

              warning("Number of %s for RTM voting must be greater than or equal 1."
                      % ("minutes" if not self._rtm_voting[0] else "rounds"),
                      rehash=True)
              return False

          except AttributeError:

            warning("RTM voting is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM voting contains a non integer value.", rehash=True)
            return False

          try:

            self._rtm_minimum_votes = float(self._rtm_minimum_votes)

            if self._rtm_minimum_votes < 0 or self._rtm_minimum_votes > 100:

              warning("RTM minimum votes must range from 0 to 100 percent.", rehash=True)
              return False

          except AttributeError:

            warning("RTM minimum votes is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM minimum votes is neither an integer nor a floating point.", rehash=True)
            return False

          try:

            self._rtm_extend = tuple((int(i) for i in iter(split(self._rtm_extend))))

            if self._rtm_extend[0] in (0, 2):

              if len(self._rtm_extend) > 1:

                raise IndexError

            elif self._rtm_extend[0] == 1:

              if len(self._rtm_extend) != 2:

                raise IndexError

              elif self._rtm_extend[1] < 1:

                warning("RTM number of extensions must be greater than or equal 1.", rehash=True)
                return False

            else:

              warning("Invalid value for RTM extend (0, 1, 2).", rehash=True)
              return False

          except AttributeError:

            warning("RTM extend is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM extend contains a non integer value.", rehash=True)
            return False

          except IndexError:

            warning("Incorrect format for RTM extend.", rehash=True)
            return False

          try:

            self._rtm_s_wait_time = int(self._rtm_s_wait_time)

            if self._rtm_s_wait_time < 0:

              warning("RTM successful wait time must be greater than or equal 0 seconds.", rehash=True)
              return False

          except AttributeError:

            warning("RTM successful wait time is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM successful wait time is not an integer.", rehash=True)
            return False

          try:

            self._rtm_f_wait_time = int(self._rtm_f_wait_time)

            if self._rtm_f_wait_time < 0:

              warning("RTM failed wait time must be greater than or equal 0 seconds.", rehash=True)
              return False

          except AttributeError:

            warning("RTM failed wait time is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM failed wait time is not an integer.", rehash=True)
            return False

          try:

            self._rtm_skip_voting = int(self._rtm_skip_voting)

            if self._rtm_skip_voting not in (0, 1, 2):

              warning("Invalid value for RTM skip voting (0, 1, 2).", rehash=True)
              return False

          except AttributeError:

            warning("RTM skip voting is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM skip voting is not an integer.", rehash=True)
            return False

          try:

            self._rtm_second_turn = int(self._rtm_second_turn)

            if self._rtm_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            warning("RTM second turn is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM second turn must be either 0 (disabled) or 1 (enabled).", rehash=True)
            return False

          try:

            self._rtm_change_immediately = int(self._rtm_change_immediately)

            if self._rtm_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            warning("RTM change immediately is not defined.", rehash=True)
            return False

          except ValueError:

            warning("RTM change immediately must be either 0 (disabled) or 1 (enabled).", rehash=True)
            return False

        else:

          self._mode_priority = self._rtm_rate = self._rtm_voting = \
          self._rtm_minimum_votes = self._rtm_extend = \
          self._rtm_s_wait_time = self._rtm_f_wait_time = \
          self._rtm_skip_voting = self._rtm_second_turn = self._rtm_change_immediately = None

      except AttributeError:

        warning("RTM is not defined.", rehash=True)
        return False

      except ValueError:

        warning("RTM is not an integer.", rehash=True)
        return False

      except KeyError:

        warning("Invalid value for RTM (0, 1, 2, 3, 4, 5, 6, 7).", rehash=True)
        return False

# Connection test.

      for i in xrange(5):

        sock = socket(AF_INET, SOCK_DGRAM)

        try:

          bind(sock, (self._bindaddr, 0))

        except socketError:

          close(sock)
          warning("Bind address is unavailable.", rehash=True)
          return False

        try:

          settimeout(sock, 12)
          connect(sock, self._address)
          sock.send("\xff\xff\xff\xffrcon %s sets RTVRTM %i/%s" % (self._rcon_pwd, cvar, VERSION))
          reply = lower(strip(sock.recv(1024)))

          if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):

            warning("Incorrect rcon password.", rehash=True)
            return False

          elif reply != "\xff\xff\xff\xffprint":

            warning("Unexpected error while contacting server for the first time.", rehash=True)
            return False

          break

        except socketTimeout:

          if i == 4:

            warning("Could not contact the server after 5 tries (TIMEOUT).", rehash=True)
            return False

        except socketError:

          if i == 4:

            warning("Could not contact the server after 5 tries (REFUSED/UNREACHABLE).", rehash=True)
            return False

          sleep(12)

        finally:

          shutdown(sock, SHUT_RDWR)
          close(sock)

      # General settings.
      self.MBII_Folder = self._MBII_Folder
      self.address = self._address
      self.bindaddr = self._bindaddr
      self.rcon_pwd = self._rcon_pwd
      self.flood_protection = self._flood_protection
      self.use_say_only = self._use_say_only
      self.name_protection = self._name_protection
      self.default_game = self._default_game
      self.clean_log = self._clean_log
      # Admin voting settings.
      self.admin_voting = self._admin_voting
      self.admin_minimum_votes = self._admin_minimum_votes
      self.admin_skip_voting = self._admin_skip_voting
      # Map limit settings.
      self.roundlimit = self._roundlimit
      self.timelimit = self._timelimit
      self.limit_voting = self._limit_voting
      self.limit_minimum_votes = self._limit_minimum_votes
      self.limit_extend = self._limit_extend
      self.limit_s_wait_time = self._limit_s_wait_time
      self.limit_f_wait_time = self._limit_f_wait_time
      self.limit_skip_voting = self._limit_skip_voting
      self.limit_second_turn = self._limit_second_turn
      self.limit_change_immediately = self._limit_change_immediately
      # Rock the Vote settings.
      self.rtv = self._rtv
      self.rtv_rate = self._rtv_rate
      self.rtv_voting = self._rtv_voting
      self.rtv_minimum_votes = self._rtv_minimum_votes
      self.rtv_extend = self._rtv_extend
      self.rtv_s_wait_time = self._rtv_s_wait_time
      self.rtv_f_wait_time = self._rtv_f_wait_time
      self.rtv_skip_voting = self._rtv_skip_voting
      self.rtv_second_turn = self._rtv_second_turn
      self.rtv_change_immediately = self._rtv_change_immediately
      # Map settings.
      self.automatic_maps = self._automatic_maps
      self.maps = self._maps
      self.secondary_maps = self._secondary_maps
      self.pick_secondary_maps = self._pick_secondary_maps
      self.map_priority = self._map_priority
      self.nomination_type = self._nomination_type
      self.enable_recently_played = self._enable_recently_played
      # Rock the Mode settings.
      self.rtm = self._rtm
      self.mode_priority = self._mode_priority
      self.rtm_rate = self._rtm_rate
      self.rtm_voting = self._rtm_voting
      self.rtm_minimum_votes = self._rtm_minimum_votes
      self.rtm_extend = self._rtm_extend
      self.rtm_s_wait_time = self._rtm_s_wait_time
      self.rtm_f_wait_time = self._rtm_f_wait_time
      self.rtm_skip_voting = self._rtm_skip_voting
      self.rtm_second_turn = self._rtm_second_turn
      self.rtm_change_immediately = self._rtm_change_immediately
      # Cvar reset.
      self.cvar = cvar

    finally:

      for attr in iter(self.__dict__.keys()): # Delete temporary fields.

        if startswith(attr, "_"):

          delattr(self, attr)

    print("Done!")
    return True

class Rcon(object):

  """Send commands to the server via rcon. Wrapper class."""

  def __init__(self, address, bindaddr, rcon_pwd):

    self.address = address
    self.bindaddr = bindaddr
    self.rcon_pwd = rcon_pwd

  def _send(self, payload, buffer_size=1024): # This method shouldn't be used outside the scope of this object's
                                              # wrappers.
    sock = socket(AF_INET, SOCK_DGRAM) # Socket descriptor sending/receiving rcon commands to/from the server.
    sock.bind((self.bindaddr, 0)) # Setting port as 0 will let the OS pick an available port for us.
    sock.settimeout(1)
    sock.connect(self.address)
    send = sock.send
    recv = sock.recv

    while(True): # Make sure an infinite loop is placed until
                 # the command is successfully received.
      try:

        send(payload)
        recv(buffer_size)
        break

      except socketTimeout:

        continue

      except socketError:

        break

    sock.shutdown(SHUT_RDWR)
    sock.close()

  def say(self, msg):

    self._send("\xff\xff\xff\xffrcon %s say %s" % (self.rcon_pwd, msg),
               2048)

  def svsay(self, msg):

    if len(msg) > 141: # Message is too big for "svsay".
                       # Use "say" instead.
      self.say(msg)

    else:

      self._send("\xff\xff\xff\xffrcon %s svsay %s" % (self.rcon_pwd, msg))

  def mbmode(self, cmd):

    self._send("\xff\xff\xff\xffrcon %s mbmode %s" % (self.rcon_pwd, cmd))

  def clientkick(self, player_id):

    self._send("\xff\xff\xff\xffrcon %s clientkick %i" % (self.rcon_pwd, player_id))

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

    self.svsay("^2[Tip] ^7" + random.choice(tips))

  def sayLamingWarning(self):

    self.svsay("^1No laming! Do not interrupt duels. Do not kill AFK people.")
    self.svsay("^1Fight people who want to fight you.")

class Features(object):

  """Feature (RTV/RTM) handler and container class."""

  def __init__(self, svsay):

    self.rtv = self.rtm = False
    self.times = [0, 0]
    self.svsay = svsay

  def Check(self):

    current_time = time()

    if not self.rtv and not self.rtm:

      if self.times[0] <= current_time and self.times[1] <= current_time:

        self._enable_all()
        return 0

      elif self.times[0] <= current_time:

        self._enable_rtv()
        return 0

      elif self.times[1] <= current_time:

        self._enable_rtm()
        return 0

    elif not self.rtv:

      if self.times[0] <= current_time:

        self._enable_rtv()
        return 0

    elif not self.rtm and self.times[1] <= current_time:

      self._enable_rtm()
      return 0

    return SLEEP_INTERVAL

  def _enable_rtv(self):

    self.rtv = True
    self.svsay("^2[Status] ^7RTV is now enabled.")
    print("CONSOLE: (%s) [Status] RTV is now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

  def _enable_rtm(self):

    self.rtm = True
    self.svsay("^2[Status] ^7RTM is now enabled.")
    print("CONSOLE: (%s) [Status] RTM is now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

  def _enable_all(self):

    self.rtv = self.rtm = True
    self.svsay("^2[Status] ^7RTV and RTM are now enabled.")
    print("CONSOLE: (%s) [Status] RTV and RTM are now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

def fix_line(line):

  """Fix for the Client log line missing the \n (newline) character."""

  startswith = str.startswith
  split = str.split

  while startswith(line[8:], "Client "):

    line = split(line, ":", 3)

    if len(line) < 4: # If this bug is ever fixed within the MBII code,
                      # make sure this fix is not processed.
      return ""

    line[0] = int(line[0]) # Timestamp.

    for i in xrange(-1, -7, -1):

      substring = int(line[-2][i:])

      if (substring - line[0]) >= 0 or line[-2][(i-1)] == " ":

        line = "%3i:%s" % (substring, line[-1])
        break

  return line

def remove_color(item):

  """Remove Quake3 color codes from a str object."""

  replace = str.replace

  for i in xrange(10):

    item = replace(item, "^%i" % (i), "")

  return item

def switch_default(default_game, current_mode, current_map, mbmode):

  """Set default game whether player count drops to 0."""

  if len(default_game) == 2:

    if current_mode != default_game[0] or current_map != default_game[1].lower():

      mbmode("%i %s" % (default_game[0], default_game[1]))
      return True

  elif isinstance(default_game[0], int):

    if current_mode != default_game[0]:

      mbmode(default_game[0])
      return True

  elif current_map != default_game[0].lower():

    mbmode("%i %s" % (current_mode, default_game[0]))
    return True

  return False

def calculate_time(time1, time2):

  """Calculate time difference in hours:minutes:seconds format."""

  minutes, seconds = divmod(int((time2 - time1)), 60)
  hours, minutes = divmod(minutes, 60)

  if hours:

    time_type = "hour"

  elif minutes:

    time_type = "minute"

  else:

    time_type = "second"

  return ("%02i:%02i:%02i %s%s" % (hours, minutes, seconds, time_type,
                                   ("" if (hours + minutes + seconds) == 1 else "s")))

def send_voting_message(voting_name, countdown, countdown_type, total_votes, total_players, votes_items, svsay):

  """Send voting related messages (countdown and voting options)."""

  svsay("^2[%s] ^7Type !number to vote. Voting will complete in ^2%i ^7%s%s (%i/%i)."
        % (voting_name, countdown, countdown_type, ("" if countdown == 1 else "s"),
           total_votes, total_players))
  svsay("^2[Votes] ^7%s" % (", ".join(("%i(%i): %s" % (vote_id, vote_count, vote_display_value)
                                       for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                       in votes_items()))))

def main(argv):

  global REPORT_UNHANDLED_EXCEPTION

  setcheckinterval(2147483647)
  lower = str.lower
  startswith = str.startswith
  endswith = str.endswith
  split = str.split
  isdigit = str.isdigit
  index = str.index
  strip = str.strip
  lstrip = str.lstrip
  join = str.join
  count = list.count
  remove = list.remove
  sort = list.sort
  clear = dict.clear
  bind = socket.bind
  settimeout = socket.settimeout
  connect = socket.connect
  shutdown = socket.shutdown
  close = socket.close
  timenow = datetime.now
  strftime = datetime.strftime

  if endswith(lower(argv[0]), ".exe"):

    argv[:] = argv[1:]
    filecode = 0x01

  else:

    filecode = 0x00

# Initialize RTV/RTM.

  print("*****************************************************")
  print("*%s*" % ("Movie Battles II RTV/RTM %s" % (VERSION)).center(51))
  print("*****************************************************\n")
  parser = OptionParser(usage="Usage: %s [--noupdate --quit] [-c <configuration file> -t <tries>]" % (argv[0]))
  parser.add_option("-c", dest="config_path",
                    help="Set the path of the configuration file. Default: rtvrtm.cfg", metavar="<configuration file>",
                    default=join_path(dirname(normpath(argv[0])), "rtvrtm.cfg"))
  parser.add_option("-t", type="int", dest="tries",
                    help="Set the amount of server connection tries before giving up (0 = infinite). Default: 5",
                    metavar="<0-100>", default=5)
  parser_updater = OptionGroup(parser, "Built-in Updater Options")
  parser_updater.add_option("--noupdate", action="store_true", dest="noupdate",
                            help="Skip the update check.", default=False)
  parser_updater.add_option("--quit", action="store_true", dest="quit",
                            help="Quit after checking for updates. This option will have no effect if --noupdate is set.",
                            default=False)
  parser_bugreport = OptionGroup(parser, "Bug Report Options")
  parser_bugreport.add_option("--noreport", action="store_false", dest="report",
                              help="Do not send bug reports.", default=True)
  parser.add_option_group(parser_updater)
  parser.add_option_group(parser_bugreport)
  opts, args = parser.parse_args()
  REPORT_UNHANDLED_EXCEPTION = opts.report

  if args:

    parser.error("Too many arguments or invalid arguments.")

  config_path = strip(opts.config_path)

  try:

    while config_path[-1] in (" ", "\\", "/"):

      config_path = config_path[:-1]

    config_path = normpath(config_path)

  except IndexError:

    parser.error("Invalid configuration path.")

  if opts.tries < 0 or opts.tries > 100:

    parser.error("The amount of server connection tries must range from 0 to 100.")

  if not opts.noupdate: # Skip update check?

    updater(normpath(argv[0]), filecode)

    if opts.quit:

      exit(0)

  config = Config(config_path)
  config.create(opts.tries)
  parser.destroy()
  del (filecode, parser, parser_updater, parser_bugreport, opts, args, config_path)
  print("[*] Creating data structures and setting parameters..."),
  players = {}
  nomination_order = []
  add_nomination = nomination_order.append
  remove_nomination = nomination_order.remove
  voting_description = change_instructions = None
  admin_choices = []
  admin_choice = admin_choices.append
  gamemodes = ("Open", "Semi Authentic", "Full Authentic", "Duel")
  recently_played = defaultdict(int)
  check_votes = voting_instructions = start_voting = start_second_turn = \
  reset = recover = start_line = False
  rcon = Rcon(config.address, config.bindaddr, config.rcon_pwd)
  say = rcon.say
  svsay = rcon.svsay if not config.use_say_only else say
  mbmode = rcon.mbmode
  clientkick = rcon.clientkick
  status = Features(svsay)

  if not config.rtv:

    status.times[0] = object()

  if not config.rtm:

    status.times[1] = object()

  Check_Status = status.Check
  print("Done!")
  print("[*] Reading log file until EOF..."),

  with open(config.logfile, "rt+") as log:

    seek = log.seek
    truncate  = log.truncate
    flush = log.flush
    fileno = log.fileno()

# Do a fast iteration over the log file to avoid needing to make getinfo calls
# to get the current status.

    for line in log:

      if endswith(line, "\n"): # Check for valid line.

        line = fix_line(line)

        if line == "  0:00 ------------------------------------------------------------\n": # Server restart.

          players = {}
          cvars = None
          start_line = True

        else:

          line = line[7:-1]

          if startswith(line, "ClientConnect: "):

            players[int(line[15:17])] = [0, False, False, None, None] # Timer, RTV, RTM, Nomination, Vote Option.

          elif startswith(line, "ClientDisconnect: "):

            try:

              del players[int(line[18:])]

            except KeyError:

              pass

          elif startswith(line, "InitGame: "):

            cvars = line

    if not start_line:

      error("Server start line was not detected. Please restart your server and turn RTV/RTM on.")

    elif not cvars:

      error("Lastest cvars values were not retrieved. Please try restarting RTV/RTM.")

    del start_line
    cvars = split(cvars[11:], "\\")
    cvars = dict((lower(cvars[i]), cvars[i+1]) for i in xrange(0, len(cvars), 2)) # Create cvar dictionary through the dict constructor.

    try:

      current_mode = int(cvars["g_authenticity"])

      if current_mode not in (0, 1, 2, 3):

        raise ValueError

    except KeyError:

      error("No current game mode detected.")

    except ValueError:

      error("Invalid value for game mode.")

    try:

      current_map = cvars["mapname"]

    except KeyError:

      error("No current map detected.")

    print("Done!")

    try:

      print("[Server Status] Map: %s | Mode: %s | Players: %i/%i\n"
            % (current_map, gamemodes[current_mode], len(players), int(cvars["sv_maxclients"])))

    except (KeyError, ValueError):

      print("[Server Status] Map: %s | Mode: %s | Players: %i\n"
            % (current_map, gamemodes[current_mode], len(players)))

    current_map = lower(current_map)
    current_time = time()
    gameinfo = { # Time of detection, extensions.
                "mode": [current_time, 0],
                "map": [current_time, 0]
               }
    players_values = players.itervalues
    players_items = players.iteritems

# Initial RTV/RTM calculation.

    rtv_players, rtm_players = [base if base else 1 for base in (((len(players) / 2) + 1) if not rate else
                                                                 int(round(((rate * len(players)) / 100.0)))
                                                                 for rate in (config.rtv_rate, config.rtm_rate))]

    if not players and config.default_game:

      reset = switch_default(config.default_game, current_mode, current_map, mbmode)

    while(True): # Infinite loop and parsing from here.
                 # Ctrl+C or kill to close the process.
      line = None
      seek(0, 1) # Seek relative to the pointer's current position.
                 # Intended to re-create the generator for the file descriptor.
      for line in log:

        if endswith(line, "\n"): # Check for valid line.

          line = fix_line(line)

          if line == "  0:00 ------------------------------------------------------------\n": # Server restart.

            print("CONSOLE: (%s) Server restart detected!" % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
            clear(players)
            nomination_order[:] = []
            current_map = current_mode = voting_description = change_instructions = None
            admin_choices[:] = []
            gameinfo["mode"][1] = gameinfo["map"][1] = 0
            recently_played = defaultdict(int)
            status.rtv = status.rtm = voting_instructions = start_voting = \
            start_second_turn = recover = False
            reset = True

            if config.rtv:

              status.times[0] = 0

            if config.rtm:

              status.times[1] = 0

# Open a new socket descriptor to reset the cvar and
# confirm server status.

            while(True):

              sock = socket(AF_INET, SOCK_DGRAM)
              bind(sock, (config.bindaddr, 0))
              settimeout(sock, 3)
              connect(sock, config.address)
              sock.send("\xff\xff\xff\xffrcon %s sets RTVRTM %i/%s" % (config.rcon_pwd, config.cvar, VERSION))

              try:

                sock.recv(1024)
                break

              except socketTimeout:

                continue

              except socketError:

                sleep(3)

              finally:

                shutdown(sock, SHUT_RDWR)
                close(sock)

          else:

            Check_Status() # Check for the status of each feature (RTV/RTM).
            line = line[7:-1]

            if startswith(line, "ClientConnect: "):

              player_id = int(line[15:17])

              if player_id not in players:

                players[player_id] = [0, False, False, None, None] # Timer, RTV, RTM, Nomination, Vote Option.
                rtv_players, rtm_players = [base if base else 1 for base in (((len(players) / 2) + 1) if not rate else
                                                                             int(round(((rate * len(players)) / 100.0)))
                                                                             for rate in (config.rtv_rate, config.rtm_rate))]

            elif startswith(line, "ClientDisconnect: "):

              player_id = int(line[18:])

              try:

                if players[player_id][4]:

                  votes[players[player_id][4]][0] -= 1 # Remove -1 from the player's voted option.

                if player_id in nomination_order:

                  remove_nomination(player_id)

                del players[player_id]
                rtv_players, rtm_players = [base if base else 1 for base in (((len(players) / 2) + 1) if not rate else
                                                                             int(round(((rate * len(players)) / 100.0)))
                                                                             for rate in (config.rtv_rate, config.rtm_rate))]

                if not players:

                  voting_description = None
                  admin_choices[:] = []

                  if start_voting: # Cancel a running voting or map/mode change
                                   # when player count drops to 0.
                    status.rtv = status.rtm = voting_instructions = start_voting = start_second_turn = False
                    change_instructions = None

                    if config.default_game:

                      reset = switch_default(config.default_game, current_mode, current_map, mbmode)

                  elif config.default_game:

                    switch_default(config.default_game, current_mode, current_map, mbmode)

                elif not start_voting:

                  check_votes = True

              except KeyError:

                pass

            elif startswith(line, "InitGame: "):

              threading.Timer(21.0, rcon.sayNewRoundMessage).start()
              threading.Timer(45.0, rcon.sayRandomTip).start()
              threading.Timer(60.0, rcon.sayLamingWarning).start()

              cvars = split(lower(line[11:]), "\\")
              cvars = dict(cvars[i:i+2] for i in xrange(0, len(cvars), 2)) # Create cvar dictionary through the dict constructor.
              cvars["g_authenticity"] = int(cvars["g_authenticity"])

              if current_mode != cvars["g_authenticity"] or current_map != cvars["mapname"]:

                players = dict((player_id, [timer, False, False, None, None])
                               for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                               in players_items()) # Reset players options with the exception of their timer.
                players_values = players.itervalues
                players_items = players.iteritems
                nomination_order[:] = []
                voting_description = change_instructions = None
                admin_choices[:] = []
                gameinfo["mode"][1] = gameinfo["map"][1] = 0

                if not reset:

                  status.rtv = status.rtm = False

                else:

                  reset = False

                voting_instructions = start_voting = start_second_turn = recover = False
                current_time = time()

                if current_mode != cvars["g_authenticity"]:

                  gameinfo["mode"][0] = current_time
                  current_mode = cvars["g_authenticity"]

                if current_map != cvars["mapname"]:

                  recently_played[current_map] = (current_time + config.enable_recently_played)
                  gameinfo["map"][0] = current_time
                  current_map = cvars["mapname"]

              elif start_voting:

                if not change_instructions:

                  if voting_method: # Round-based voting.

                    if start_second_turn: # Start a second turn voting.

                      start_second_turn = skip_voting = False
                      voting_countdown = _voting_countdown
                      svsay("^2[%s] ^7Second turn voting for the next %s has begun. Type !number to vote. Voting will complete in ^2%i ^7round%s."
                            % (voting_name, voting_type, voting_countdown,
                               ("" if voting_countdown == 1 else "s")))
                      voting_countdown -= 1
                      svsay("^2[Votes] ^71: %s, 2: %s" % (votes[1][3], votes[2][3]))
                      voting_time = object()

                    elif not voting_instructions:

                      if voting_countdown:

                        if voting_type == "admin":

                          svsay("^2[Description] ^7%s" % (voting_description))

                        send_voting_message(voting_name, voting_countdown, "round",
                                            sum((vote_count for (vote_count, priority, vote_value, vote_display_value) in votes_values())),
                                            len(players), votes_items, svsay)
                        voting_countdown -= 1

                      else:

                        voting_time = 0

                elif change_instructions is not True: # Next round map/mode change.

                  mbmode(("%i %s" % (current_mode, change_instructions[0]) if voting_type == "map" else
                          change_instructions[0]))
                  wait_time = (time() + change_instructions[2])

                  if wait_time > status.times[change_instructions[1]]:

                    status.times[change_instructions[1]] = wait_time

                  change_instructions = recover = True

            elif startswith(line, "ClientUserinfoChanged: "):

              if config.name_protection: # Kick players using restricted nicknames.

                line = line[23:]
                player_id = int(line[:2])

                try:

                  player_name = index(line, " n\\")

                except ValueError:

                  try:

                    player_name = index(line, "\\n\\")

                  except ValueError:

                    continue

                player_name = line[(player_name + 3):]
                player_name = player_name[:index(player_name, "\\")]

                if lower(strip(remove_color(player_name))) in ("admin", "server"):

                  say("^3Restricted nickname in use. Kicking player %i (^7%s^3)..."
                      % (player_id, player_name))
                  clientkick(player_id)

            elif startswith(line, "say: Admin: ") or startswith(line, "say: Server: "): # Admin commands (/smod say).

              if not recover:

		if startswith(line, "say: Admin: "):
                	original_admin_cmd = strip(remove_color(line[12:]))
		elif startswith(line, "say: Server: "):
			original_admin_cmd = strip(remove_color(line[13:]))
                admin_cmd = lower(original_admin_cmd)

                if admin_cmd == "!rehash": # Rehash configuration.

                  svsay("^2[Status] ^7Rehashing configuration...")
                  print("CONSOLE: (%s) [Status] Rehashing configuration..." %
                        (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                  sleep(1)

                  if config.rehash():

                    rcon.address = config.address
                    rcon.bindaddr =  config.bindaddr
                    rcon.rcon_pwd = config.rcon_pwd

                    if not config.use_say_only:

                      svsay = status.svsay = rcon.svsay

                    else:

                      svsay = status.svsay = say

                    svsay("^2[Status] ^7Rehash successful!")

                  else:

                    svsay("^2[Status] ^7Rehash failed!")

                  print("[*] Resetting parameters..."),
                  players = dict((player_id, [0, False, False, None, None])
                                 for player_id in iter(players)) # Reset players data.
                  players_values = players.itervalues
                  players_items = players.iteritems
                  nomination_order[:] = []
                  voting_description = change_instructions = None
                  admin_choices[:] = []
                  gameinfo["mode"][1] = gameinfo["map"][1] = 0
                  recently_played = defaultdict(int)
                  status.rtv = status.rtm = voting_instructions = start_voting = start_second_turn = False
                  status.times[0] = 0 if config.rtv else object()
                  status.times[1] = 0 if config.rtm else object()
                  rtv_players, rtm_players = [base if base else 1 for base in (((len(players) / 2) + 1) if not rate else
                                                                               int(round(((rate * len(players)) / 100.0)))
                                                                               for rate in (config.rtv_rate, config.rtm_rate))]
                  recover = True
                  print("Done!\n")

                elif not start_voting:

                  if admin_cmd == "!erase": # Erase the Admin voting options pool.

                    admin_choices[:] = []
                    svsay("^2[Admin] ^7Admin voting options were erased.")

                  elif startswith(admin_cmd, "!description "): # Set the admin's voting description.

                    if voting_description:

                      svsay("^2[Admin] ^7Admin voting description changed!")

                    else:

                      svsay("^2[Admin] ^7Admin voting description added!")

                    voting_description = lstrip(original_admin_cmd[13:])

                  elif startswith(admin_cmd, "!vote "): # Add a voting option to the Admin voting options pool.

                    if len(admin_choices) < 10: # A total maximum of 10 voting options.

                      voting_choice = lstrip(original_admin_cmd[6:])

                      if lower(voting_choice) in (lower(voting_option) for voting_option in iter(admin_choices)):

                        say("^2[Admin] ^7%s is already present within the admin voting options." % (voting_choice))

                      else:

                        admin_choice(voting_choice)
                        svsay("^2[Admin] ^7%s was added as an admin voting option." % (voting_choice))

                    else:

                      say("^2[Admin] ^7Admin voting is full.")

                  else:

                    admin_cmd = split(admin_cmd)

                    if len(admin_cmd) == 2:

                      if admin_cmd[0] == "!enable": # Enable RTV/RTM/Recently played maps immediately.

                        if admin_cmd[1] == "maps":

                          recently_played = defaultdict(int)

                        elif admin_cmd[1] == "rtv":

                          if config.rtv:

                            status.times[0] = 0

                        elif admin_cmd[1] == "rtm" and config.rtm:

                          status.times[1] = 0

                      elif admin_cmd[0] == "!force": # Force a RTV/RTM/Admin voting immediately.

                        if admin_cmd[1] == "rtv":

                          if config.rtv:

                            players = dict((player_id, [timer, True, rtm_vote, nomination, None])
                                           for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                           in players_items()) # Force RTV for all connected players.
                            players_values = players.itervalues
                            players_items = players.iteritems
                            check_votes = True

                        elif admin_cmd[1] == "rtm":

                          if config.rtm:

                            players = dict((player_id, [timer, rtv_vote, True, nomination, None])
                                           for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                           in players_items()) # Force RTM for all connected players.
                            players_values = players.itervalues
                            players_items = players.iteritems
                            check_votes = True

                        elif admin_cmd[1] == "admin":

                          if not voting_description:

                            svsay("^2[Admin] ^7Admin voting failed to start! No voting description is set.")
                            print("CONSOLE: (%s) [Admin] Admin voting failed to start! No voting description is set."
                                  % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))

                          elif not admin_choices:

                            svsay("^2[Admin] ^7Admin voting failed to start! No voting options were added.")
                            print("CONSOLE: (%s) [Admin] Admin voting failed to start! No voting options were added."
                                  % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))

                          elif len(admin_choices) < 2:

                            svsay("^2[Admin] ^7Admin voting failed to start! Two or more voting options are required.")
                            print("CONSOLE: (%s) [Admin] Admin voting failed to start! Two or more voting options are required."
                                  % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))

                          else:

                            votes = SortableDict(((i+1), [0, None, None, admin_choices[i]])
                                                 for i in xrange(len(admin_choices)))
                            votes_values = votes.itervalues
                            votes_items = votes.sorteditems
                            voting_name = "Admin"
                            voting_type = "admin"
                            voting_method, voting_countdown = config.admin_voting
                            voting_minimum_votes = config.admin_minimum_votes
                            voting_skip_voting = config.admin_skip_voting
                            voting_second_turn = None
                            status.rtv = status.rtm = voting_instructions = start_voting = True

                    elif len(admin_cmd) == 3 and admin_cmd[0] == "!disable" and isdigit(admin_cmd[2]): # Disable RTV/RTM.

                      if admin_cmd[1] == "rtv":

                        if config.rtv:

                          svsay("^2[RTV] ^7Rock the vote was forcefully disabled!")
                          print("CONSOLE: (%s) [RTV] Rock the vote was forcefully disabled!" %
                                (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                          disable_time = int(admin_cmd[2])
                          status.rtv = False
                          status.times[0] = (time() + disable_time) if disable_time else object()
                          players = dict((player_id, [timer, False, rtm_vote, nomination, None])
                                         for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                         in players_items()) # Reset RTV votes.
                          players_values = players.itervalues
                          players_items = players.iteritems

                      elif admin_cmd[1] == "rtm" and config.rtm:

                        svsay("^2[RTM] ^7Rock the mode was forcefully disabled!")
                        print("CONSOLE: (%s) [RTM] Rock the mode was forcefully disabled!" %
                              (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                        disable_time = int(admin_cmd[2])
                        status.rtm = False
                        status.times[1] = (time() + disable_time) if disable_time else object()
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                elif admin_cmd == "!cancel":

                  if not change_instructions: # Cancel current voting.

                    if not voting_instructions and not start_second_turn:

                      svsay("^2[Voting] ^7The %s voting was canceled!" % (voting_type))
                      print("CONSOLE: (%s) [Voting] The %s voting was canceled!" %
                            (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_type))
                      players = dict((player_id, [timer, False, False, None, None])
                                     for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                     in players_items()) # Reset players options with the exception of their timer.
                      players_values = players.itervalues
                      players_items = players.iteritems
                      nomination_order[:] = []
                      voting_description = None
                      admin_choices[:] = []
                      status.rtv = status.rtm = start_voting = False
                      recover = True
                      del votes

                  elif change_instructions is not True: # Cancel next map/mode change.

                    svsay("^2[Nextgame] ^7The next %s (%s) was canceled!" %
                          (voting_type,
                           (change_instructions[0] if voting_type == "map" else
                            gamemodes[change_instructions[0]])))
                    print("CONSOLE: (%s) [Nextgame] The next %s (%s) was canceled!" %
                          (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_type,
                           (change_instructions[0] if voting_type == "map" else
                            gamemodes[change_instructions[0]])))

                    change_instructions = None
                    status.rtv = status.rtm = start_voting = False
                    recover = True

                elif admin_cmd == "!nextgame" and change_instructions > True: # Force a queued map/mode change
                                                                              # before the next round.
                  mbmode(("%i %s" % (current_mode, change_instructions[0]) if voting_type == "map" else
                          change_instructions[0]))
                  wait_time = (time() + change_instructions[2])

                  if wait_time > status.times[change_instructions[1]]:

                    status.times[change_instructions[1]] = wait_time

                  change_instructions = recover = True

            elif not start_voting:

              if line == "Exit: Kill limit hit.":

                if config.roundlimit and players: # Initiate an automatic Roundlimit voting.

                  nominated_maps = [nomination
                                    for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                    in players_values() if nomination]

                  if config.nomination_type:

                    map_duplicates = defaultdict(bool)
                    voting_maps = [(count(nominated_maps, players[player_id][3]),
                                    (config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                    players[player_id][3])
                                   for player_id in iter(nomination_order)
                                   if (players[player_id][3] not in map_duplicates and # Get nominations in nomination order without
                                       not map_duplicates[players[player_id][3]])]     # duplicates and with the amount of nominations received.
                    sort(voting_maps, key=lambda nomination: nomination[0], reverse=True) # Re-order nominations by nomination count.

                    while len(voting_maps) > 5: # Reduce the number of maps to 5 for the voting.

                      min_nominations = min((nomination_count for (nomination_count, priority, nomination) in
                                             iter(voting_maps)))
                      compare_nominations = [(priority, nomination) for (nomination_count, priority, nomination) in
                                             iter(voting_maps) if nomination_count == min_nominations]

                      if (len(voting_maps) - len(compare_nominations)) >= 5:

                        voting_maps[:] = voting_maps[:-len(compare_nominations)]

                      else: # Compare maps with the map priority system
                            # to define which maps remain.
                        for i in xrange(3):

                          decrease_maps = (len(voting_maps) - 5) # Number of remaining maps to remove.

                          if not decrease_maps:

                            break

                          filtered_nominations = [nomination for (priority, nomination) in iter(compare_nominations)
                                                  if priority == i] # Map priority.

                          if filtered_nominations:

                            if len(filtered_nominations) > decrease_maps:

                              filtered_nominations[:] = filtered_nominations[(len(filtered_nominations) - decrease_maps):]

                            voting_maps = [(nomination_count, priority, nomination) for (nomination_count, priority, nomination)
                                           in iter(voting_maps)
                                           if nomination not in filtered_nominations]

                    voting_maps = [(priority, nomination) for (nomination_count, priority, nomination) in iter(voting_maps)]

                  else:

                    voting_maps = [((config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                    players[player_id][3])
                                   for player_id in iter(nomination_order)]

                  missing_maps = (5 - len(voting_maps))

                  if missing_maps: # Not all 5 map slots are filled.

                    available_maps = config.maps
                    available_secondary_maps = []
                    current_time = time()

                    if config.pick_secondary_maps == 2:

                      available_maps += config.secondary_maps

                    elif config.pick_secondary_maps:

                      available_secondary_maps = [mapname for mapname in iter(config.secondary_maps)
                                                  if (mapname not in nominated_maps and
                                                      lower(mapname) != current_map and
                                                      recently_played[lower(mapname)] <= current_time)]

                    available_maps = [mapname for mapname in iter(available_maps)
                                      if (mapname not in nominated_maps and
                                          lower(mapname) != current_map and
                                          recently_played[lower(mapname)] <= current_time)]

                    if missing_maps == 5 and not available_maps and not available_secondary_maps:

                      svsay("^2[Roundlimit] ^7Roundlimit voting failed to start! No map is currently available.")
                      print("CONSOLE: (%s) [Roundlimit] Roundlimit voting failed to start! No map is currently available."
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                      players = dict((player_id, [timer, False, rtm_vote, None, None])
                                     for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                                     players_items()) # Reset RTV votes.
                      players_values = players.itervalues
                      players_items = players.iteritems
                      continue

                    append_map = voting_maps.append
                    remove_map = available_maps.remove

                    try:

                      for i in xrange(missing_maps):

# Fill any remaining map slots with random maps.

                        mapname = choice(available_maps)
                        append_map(((config.map_priority[0] if mapname in config.maps else config.map_priority[1]),
                                    mapname))
                        remove_map(mapname)

                    except IndexError: # Not enough maps to fill all 5 slots.

                      if available_secondary_maps: # Fill with secondary maps if we have no new
                                                   # primary map to use.
                        remove_map = available_secondary_maps.remove

                        try:

                          for i in xrange((5 - len(voting_maps))):

# Fill any remaining map slots with random secondary maps.

                            mapname = choice(available_secondary_maps)
                            append_map((config.map_priority[1], mapname))
                            remove_map(mapname)

                        except IndexError: # Not enough maps to fill remaining slots.

                          pass

# Create voting options.

                  votes = SortableDict(((i+1), [0, voting_maps[i][0], voting_maps[i][1], voting_maps[i][1]])
                                       for i in xrange(len(voting_maps)))

                  if (config.limit_extend[0] == 2 or
                      (config.limit_extend[0] == 1 and gameinfo["map"][1] < config.limit_extend[1])):

                    votes[(len(votes) + 1)] = [0, config.map_priority[2], None, "Don't change"] # Add the "Don't change" option.

                  votes_values = votes.itervalues
                  votes_items = votes.sorteditems
                  voting_name = "Roundlimit"
                  voting_type = "map"
                  voting_method, voting_countdown = config.limit_voting
                  voting_minimum_votes = config.limit_minimum_votes
                  voting_wait_time = 0
                  voting_s_wait_time = config.limit_s_wait_time
                  voting_f_wait_time = config.limit_f_wait_time
                  voting_skip_voting = config.limit_skip_voting
                  voting_second_turn = config.limit_second_turn
                  voting_change_immediately = config.limit_change_immediately
                  status.rtv = status.rtm = voting_instructions = start_voting = True

              elif line == "Exit: Timelimit hit.":

                if config.timelimit and players: # Initiate an automatic Timelimit voting.

                  nominated_maps = [nomination
                                    for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                    in players_values() if nomination]

                  if config.nomination_type:

                    map_duplicates = defaultdict(bool)
                    voting_maps = [(count(nominated_maps, players[player_id][3]),
                                    (config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                    players[player_id][3])
                                   for player_id in iter(nomination_order)
                                   if (players[player_id][3] not in map_duplicates and # Get nominations in nomination order without
                                       not map_duplicates[players[player_id][3]])]     # duplicates and with the amount of nominations received.
                    sort(voting_maps, key=lambda nomination: nomination[0], reverse=True) # Re-order nominations by nomination count.

                    while len(voting_maps) > 5: # Reduce the number of maps to 5 for the voting.

                      min_nominations = min((nomination_count for (nomination_count, priority, nomination) in
                                             iter(voting_maps)))
                      compare_nominations = [(priority, nomination) for (nomination_count, priority, nomination) in
                                             iter(voting_maps) if nomination_count == min_nominations]

                      if (len(voting_maps) - len(compare_nominations)) >= 5:

                        voting_maps[:] = voting_maps[:-len(compare_nominations)]

                      else: # Compare maps with the map priority system
                            # to define which maps remain.
                        for i in xrange(3):

                          decrease_maps = (len(voting_maps) - 5) # Number of remaining maps to remove.

                          if not decrease_maps:

                            break

                          filtered_nominations = [nomination for (priority, nomination) in iter(compare_nominations)
                                                  if priority == i] # Map priority.

                          if filtered_nominations:

                            if len(filtered_nominations) > decrease_maps:

                              filtered_nominations[:] = filtered_nominations[(len(filtered_nominations) - decrease_maps):]

                            voting_maps = [(nomination_count, priority, nomination) for (nomination_count, priority, nomination)
                                           in iter(voting_maps)
                                           if nomination not in filtered_nominations]

                    voting_maps = [(priority, nomination) for (nomination_count, priority, nomination) in iter(voting_maps)]

                  else:

                    voting_maps = [((config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                    players[player_id][3])
                                   for player_id in iter(nomination_order)]

                  missing_maps = (5 - len(voting_maps))

                  if missing_maps: # Not all 5 map slots are filled.

                    available_maps = config.maps
                    available_secondary_maps = []
                    current_time = time()

                    if config.pick_secondary_maps == 2:

                      available_maps += config.secondary_maps

                    elif config.pick_secondary_maps:

                      available_secondary_maps = [mapname for mapname in iter(config.secondary_maps)
                                                  if (mapname not in nominated_maps and
                                                      lower(mapname) != current_map and
                                                      recently_played[lower(mapname)] <= current_time)]

                    available_maps = [mapname for mapname in iter(available_maps)
                                      if (mapname not in nominated_maps and
                                          lower(mapname) != current_map and
                                          recently_played[lower(mapname)] <= current_time)]

                    if missing_maps == 5 and not available_maps and not available_secondary_maps:

                      svsay("^2[Timelimit] ^7Timelimit voting failed to start! No map is currently available.")
                      print("CONSOLE: (%s) [Timelimit] Timelimit voting failed to start! No map is currently available."
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                      players = dict((player_id, [timer, False, rtm_vote, None, None])
                                     for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                                     players_items()) # Reset RTV votes.
                      players_values = players.itervalues
                      players_items = players.iteritems
                      continue

                    append_map = voting_maps.append
                    remove_map = available_maps.remove

                    try:

                      for i in xrange(missing_maps):

# Fill any remaining map slots with random maps.

                        mapname = choice(available_maps)
                        append_map(((config.map_priority[0] if mapname in config.maps else config.map_priority[1]),
                                    mapname))
                        remove_map(mapname)

                    except IndexError: # Not enough maps to fill all 5 slots.

                      if available_secondary_maps: # Fill with secondary maps if we have no new
                                                   # primary map to use.
                        remove_map = available_secondary_maps.remove

                        try:

                          for i in xrange((5 - len(voting_maps))):

# Fill any remaining map slots with random secondary maps.

                            mapname = choice(available_secondary_maps)
                            append_map((config.map_priority[1], mapname))
                            remove_map(mapname)

                        except IndexError: # Not enough maps to fill remaining slots.

                          pass

# Create voting options.

                  votes = SortableDict(((i+1), [0, voting_maps[i][0], voting_maps[i][1], voting_maps[i][1]])
                                       for i in xrange(len(voting_maps)))

                  if (config.limit_extend[0] == 2 or
                      (config.limit_extend[0] == 1 and gameinfo["map"][1] < config.limit_extend[1])):

                    votes[(len(votes) + 1)] = [0, config.map_priority[2], None, "Don't change"] # Add the "Don't change" option.

                  votes_values = votes.itervalues
                  votes_items = votes.sorteditems
                  voting_name = "Timelimit"
                  voting_type = "map"
                  voting_method, voting_countdown = config.limit_voting
                  voting_minimum_votes = config.limit_minimum_votes
                  voting_wait_time = 0
                  voting_s_wait_time = config.limit_s_wait_time
                  voting_f_wait_time = config.limit_f_wait_time
                  voting_skip_voting = config.limit_skip_voting
                  voting_second_turn = config.limit_second_turn
                  voting_change_immediately = config.limit_change_immediately
                  status.rtv = status.rtm = voting_instructions = start_voting = True

              elif not recover: # Standard commands.

                line = split(line, ":", 2)

                if len(line) == 3 and isdigit(line[0]) and line[1] in (" say", " sayteam"):

                  player_id = int(line[0])
                  player_name, original_msg = split(line[2], '"', 1)
                  player_name = player_name[1:-2]
                  original_msg = strip(remove_color(original_msg[:-1]))
                  msg = lower(original_msg)
                  current_time = time()

                  if players[player_id][0] <= current_time: # Flood protection.

                    if msg in ("rtv", "!rtv"):

                      if not config.rtv:

                        say("^2[RTV] ^7Rock the vote is unavailable.")

                      elif not status.rtv:

                        if isinstance(status.times[0], float):

                          say("^2[RTV] ^7Rock the vote is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[0])))

                        else:

                          say("^2[RTV] ^7Rock the vote is temporarily disabled.")

                      else:

                        available_maps = config.maps

                        if config.pick_secondary_maps:

                          available_maps += config.secondary_maps

                        available_maps = (lower(mapname) for mapname in iter(available_maps))
                        available_maps = sum((True for mapname in available_maps
                                              if (mapname != current_map and
                                                  recently_played[mapname] <= current_time)))
                        available_maps += len(nomination_order)

                        if not available_maps:

                          say("^2[RTV] ^7Rock the vote is disabled because no map is currently available.")
                          players = dict((player_id, [timer, False, rtm_vote, None, None])
                                         for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                         in players_items()) # Reset RTV votes.
                          players_values = players.itervalues
                          players_items = players.iteritems

                        elif players[player_id][1]:

                          say("^2[RTV] ^7%s ^7already wanted to rock the vote (%i/%i)."
                              % (player_name,
                                 sum((rtv_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                      in players_values())),
                                 rtv_players))

                        else:

                          players[player_id][1] = check_votes = True
                          svsay("^2[RTV] ^7%s ^7wants to rock the vote (%i/%i)."
                                % (player_name,
                                   sum((rtv_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                        in players_values())),
                                   rtv_players))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("unrtv", "!unrtv"):

                      if not config.rtv:

                        say("^2[RTV] ^7Rock the vote is unavailable.")

                      elif not status.rtv:

                        if isinstance(status.times[0], float):

                          say("^2[RTV] ^7Rock the vote is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[0])))

                        else:

                          say("^2[RTV] ^7Rock the vote is temporarily disabled.")

                      else:

                        available_maps = config.maps

                        if config.pick_secondary_maps:

                          available_maps += config.secondary_maps

                        available_maps = (lower(mapname) for mapname in iter(available_maps))
                        available_maps = sum((True for mapname in available_maps
                                              if (mapname != current_map and
                                                  recently_played[mapname] <= current_time)))
                        available_maps += len(nomination_order)

                        if not available_maps:

                          say("^2[RTV] ^7Rock the vote is disabled because no map is currently available.")
                          players = dict((player_id, [timer, False, rtm_vote, None, None])
                                         for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                         in players_items()) # Reset RTV votes.
                          players_values = players.itervalues
                          players_items = players.iteritems

                        elif not players[player_id][1]:

                          say("^2[RTV] ^7%s ^7didn't want to rock the vote yet (%i/%i)."
                              % (player_name,
                                 sum((rtv_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                      in players_values())),
                                 rtv_players))

                        else:

                          players[player_id][1] = False
                          svsay("^2[RTV] ^7%s ^7no longer wants to rock the vote (%i/%i)."
                                % (player_name,
                                   sum((rtv_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                        in players_values())),
                                   rtv_players))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("rtm", "!rtm"):

                      if not config.rtm:

                        say("^2[RTM] ^7Rock the mode is unavailable.")

                      elif not status.rtm:

                        if isinstance(status.times[1], float):

                          say("^2[RTM] ^7Rock the mode is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[1])))

                        else:

                          say("^2[RTM] ^7Rock the mode is temporarily disabled.")

                      elif not [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]:

                        say("^2[RTV] ^7Rock the mode is disabled because no mode is currently available.")
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                      elif players[player_id][2]:

                        say("^2[RTM] ^7%s ^7already wanted to rock the mode (%i/%i)."
                            % (player_name,
                               sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                    in players_values())),
                               rtm_players))

                      else:

                        players[player_id][2] = check_votes = True
                        svsay("^2[RTM] ^7%s ^7wants to rock the mode (%i/%i)."
                              % (player_name,
                                 sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                      in players_values())),
                                 rtm_players))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("unrtm", "!unrtm"):

                      if not config.rtm:

                        say("^2[RTM] ^7Rock the mode is unavailable.")

                      elif not status.rtm:

                        if isinstance(status.times[1], float):

                          say("^2[RTM] ^7Rock the mode is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[1])))

                        else:

                          say("^2[RTM] ^7Rock the mode is temporarily disabled.")

                      elif not [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]:

                        say("^2[RTV] ^7Rock the mode is disabled because no mode is currently available.")
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                      elif not players[player_id][2]:

                        say("^2[RTM] ^7%s ^7didn't want to rock the mode yet (%i/%i)."
                            % (player_name,
                               sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                    in players_values())),
                               rtm_players))

                      else:

                        players[player_id][2] = False
                        svsay("^2[RTM] ^7%s ^7no longer wants to rock the mode (%i/%i)."
                              % (player_name,
                                 sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                      in players_values())),
                                 rtm_players))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("nominate", "!nominate"):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        say("^2[Nominate] ^7Usage: %s mapname" % (original_msg))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "nominate ") or startswith(msg, "!nominate "):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        nominated_map = lstrip(msg[9:])
                        compare_map = [mapname for mapname in iter(config.maps + config.secondary_maps)
                                       if lower(mapname) == nominated_map] # Compare nominated mapname against both map lists.
                        nominated_maps = [nomination
                                          for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                          in players_values() if nomination]

                        if config.nomination_type:

                          if not compare_map:

                            say("^2[Nominate] ^7Invalid map. Please use <!>maplist or <!>search expression.")

                          elif nominated_map == current_map:

                            say("^2[Nominate] ^7%s cannot be nominated (current map)."
                                % (compare_map[0]))

                          elif recently_played[nominated_map] > current_time:

                            say("^2[Nominate] ^7%s cannot be nominated (recently played) (%s left)."
                                % (compare_map[0], calculate_time(current_time, recently_played[nominated_map])))

                          else:

                            nominations = count(nominated_maps, compare_map[0])

                            if players[player_id][3] == compare_map[0]:

                              say("^2[Nominate] ^7%s ^7already nominated %s (%i nomination%s)."
                                  % (player_name, compare_map[0], nominations,
                                     ("" if nominations == 1 else "s")))

                            else:

                              nominations += 1

                              if players[player_id][3]:

                                remove_nomination(player_id)
                                svsay("^2[Nominate] ^7%s ^7nomination changed to %s (%i nomination%s)."
                                      % (player_name, compare_map[0], nominations,
                                         ("" if nominations == 1 else "s")))

                              else:

                                svsay("^2[Nominate] ^7%s ^7nominated %s (%i nomination%s)!"
                                      % (player_name, compare_map[0], nominations,
                                         ("" if nominations == 1 else "s")))

                              players[player_id][3] = compare_map[0]
                              add_nomination(player_id)

                        elif len(nominated_maps) < 5 or players[player_id][3]:

                          if not compare_map:

                            say("^2[Nominate] ^7Invalid map. Please use <!>maplist or <!>search expression.")

                          elif nominated_map == current_map:

                            say("^2[Nominate] ^7%s cannot be nominated (current map)."
                                % (compare_map[0]))

                          elif recently_played[nominated_map] > current_time:

                            say("^2[Nominate] ^7%s cannot be nominated (recently played) (%s left)."
                                % (compare_map[0], calculate_time(current_time, recently_played[nominated_map])))

                          elif compare_map[0] in nominated_maps:

                            say("^2[Nominate] ^7%s cannot be nominated (already nominated)."
                                % (compare_map[0]))

                          else:

                            if players[player_id][3]:

                              remove_nomination(player_id)
                              svsay("^2[Nominate] ^7%s ^7nomination changed to %s."
                                    % (player_name, compare_map[0]))

                            else:

                              svsay("^2[Nominate] ^7%s ^7nominated %s!"
                                    % (player_name, compare_map[0]))

                            players[player_id][3] = compare_map[0]
                            add_nomination(player_id)

                        else:

                          say("^2[Nominate] ^7Maximum number of nominations (5) reached.")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("revoke", "!revoke"):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      elif not players[player_id][3]:

                        say("^2[Revoke] ^7%s ^7has no nominated map." %
                            (player_name))

                      else:

                        if config.nomination_type:

                          nominations = (count([nomination
                                                for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                                in players_values()], players[player_id][3]) - 1)
                          svsay("^2[Revoke] ^7%s ^7nomination to %s was revoked (%i nomination%s)." %
                                (player_name, players[player_id][3], nominations,
                                 ("" if nominations == 1 else "s")))

                        else:

                          svsay("^2[Revoke] ^7%s ^7nomination revoked!" %
                                (player_name))

                        players[player_id][3] = None
                        remove_nomination(player_id)

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("maplist", "!maplist"):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        sorted_maps = iter(sorted((mapname for mapname in iter(config.maps + config.secondary_maps)
                                                   if (lower(mapname) != current_map and
                                                       recently_played[lower(mapname)] <= current_time)),
                                                  key=lower)) # Create an alphanumeric sorted map list.

                        if not config.nomination_type: # Remove nominated maps.

                          nominated_maps = [nomination
                                            for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                            in players_values() if nomination]
                          sorted_maps = (mapname for mapname in sorted_maps if mapname not in nominated_maps)

# Create split lists for display in the server based on a maximum of MAPLIST_MAX_SIZE bytes per
# list string.

                        maplist = {1: []}
                        append_map = maplist[1].append
                        maplist_number = 1
                        maplist_length = 16

                        for mapname in sorted_maps:

                          maplist_length += len(mapname)

                          if maplist_length > MAPLIST_MAX_SIZE:

                            maplist_number += 1
                            maplist[maplist_number] = []
                            append_map = maplist[maplist_number].append
                            maplist_length = (15 + len(str(maplist_number)) + len(mapname))

                          maplist_length += 2
                          append_map(mapname)

                        if not maplist[1]:

                          say("^2[Maplist] ^7No map is currently available for nomination.")

                        elif len(maplist) > 1:

                          say("^2[Maplist] ^7Usage: %s number (Available map lists: %i)" %
                              (original_msg, len(maplist)))

                        else:

                          say("^2[Maplist] ^7%s" % (join(", ", maplist[1])))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "maplist ") or startswith(msg, "!maplist "):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        sorted_maps = iter(sorted((mapname for mapname in iter(config.maps + config.secondary_maps)
                                                   if (lower(mapname) != current_map and
                                                       recently_played[lower(mapname)] <= current_time)),
                                                  key=lower)) # Create an alphanumeric sorted map list.

                        if not config.nomination_type: # Remove nominated maps.

                          nominated_maps = [nomination
                                            for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                            in players_values() if nomination]
                          sorted_maps = (mapname for mapname in sorted_maps if mapname not in nominated_maps)

# Create split lists for display in the server based on a maximum of MAPLIST_MAX_SIZE bytes per
# list string.

                        maplist = {1: []}
                        append_map = maplist[1].append
                        maplist_number = 1
                        maplist_length = 16

                        for mapname in sorted_maps:

                          maplist_length += len(mapname)

                          if maplist_length > MAPLIST_MAX_SIZE:

                            maplist_number += 1
                            maplist[maplist_number] = []
                            append_map = maplist[maplist_number].append
                            maplist_length = (15 + len(str(maplist_number)) + len(mapname))

                          maplist_length += 2
                          append_map(mapname)

                        if not maplist[1]:

                          say("^2[Maplist] ^7No map is currently available for nomination.")

                        else:

                          try:

                            maplist_number = int(msg[8:])
                            say("^2[Maplist %i] ^7%s" % (maplist_number, join(", ", maplist[maplist_number])))

                          except (ValueError, KeyError):

                            say("^2[Maplist] ^7Invalid map list number (Available map lists: %i)."
                                % (len(maplist)))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("search", "!search"):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        say("^2[Search] ^7Usage: %s expression" % (original_msg))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "search ") or startswith(msg, "!search "):

                      if not config.maps:

                        say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        search_expression = lstrip(msg[7:])

                        if search_expression != "*": # No wildcard.
                                                     # Search for given expression.
                          maplist = [mapname for mapname in iter(config.maps + config.secondary_maps)
                                     if search_expression in lower(mapname)]

                        else:

                          maplist = list(config.maps + config.secondary_maps)

                        if not maplist:

                          say("^2[Search] ^7No matches found for expression ''%s''."
                              % (lstrip(original_msg[7:])))

                        else:

                          sort(maplist, key=lower)
                          maplist = join(", ", maplist)

                          if (len(maplist) + 13) > MAPLIST_MAX_SIZE:

                            say("^2[Search] ^7Result for expression ''%s'' is too long (greater than %i characters)." %
                                (lstrip(original_msg[7:]), MAPLIST_MAX_SIZE))

                          else:

                            say("^2[Search] ^7%s" % (maplist))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("elapsed", "!elapsed"):

                      say("^2[Elapsed] ^7Usage: %s map/mode" % (original_msg))
                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "elapsed ") or startswith(msg, "!elapsed "):

                      elapse = lstrip(msg[8:])

                      try:

                        say("^2[Elapsed] ^7Time elapsed for the current %s: %s%s" %
                            (elapse, calculate_time(gameinfo[elapse][0], current_time),
                             (" (%i extension%s)" % (gameinfo[elapse][1],
                                                     ("" if gameinfo[elapse][1] == 1 else "s"))
                              if gameinfo[elapse][1] else "")))

                      except KeyError:

                        say("^2[Elapsed] ^7Incorrect format (map/mode).")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("nextgame", "!nextgame"):

                      say("^2[Nextgame] ^7No next game is set.")
                      players[player_id][0] = (current_time + config.flood_protection)

            elif not voting_instructions and not start_second_turn and not recover:

              line = split(line, ":", 2)

              if len(line) == 3 and isdigit(line[0]) and line[1] in (" say", " sayteam"):

                player_id = int(line[0])
                original_msg = strip(remove_color(line[2][(index(line[2], '"') + 1):-1]))
                msg = lower(original_msg)

                if not change_instructions: # Voting related commands.

                  if startswith(msg, "!") and isdigit(msg[1:]):

                    vote = int(msg[1:])

                    try:

                      votes[vote][0] += 1 # Add +1 to whichever option the player voted for.

                    except KeyError:

                      pass

                    else:

                      if players[player_id][4]: # Vote change.

                        votes[players[player_id][4]][0] -= 1 # Remove -1 from whichever option the player
                                                             # previously voted for.
                      players[player_id][4] = vote

                  elif msg in ("unvote", "!unvote"):

                    try:

                      votes[players[player_id][4]][0] -= 1 # Remove -1 from whichever option the player
                                                           # voted for.
                    except KeyError:

                      pass

                    else:

                      players[player_id][4] = None

                elif change_instructions is not True:

                  current_time = time()

                  if players[player_id][0] <= current_time: # Flood protection.

                    if msg in ("elapsed", "!elapsed"):

                      say("^2[Elapsed] ^7Usage: %s map/mode" % (original_msg))
                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "elapsed ") or startswith(msg, "!elapsed "):

                      elapse = lstrip(msg[8:])

                      try:

                        say("^2[Elapsed] ^7Time elapsed for the current %s: %s%s" %
                            (elapse, calculate_time(gameinfo[elapse][0], current_time),
                             (" (%i extension%s)" % (gameinfo[elapse][1],
                                                     ("" if gameinfo[elapse][1] == 1 else "s"))
                              if gameinfo[elapse][1] else "")))

                      except KeyError:

                        say("^2[Elapsed] ^7Incorrect format (map/mode).")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("nextgame", "!nextgame"):

                      say("^2[Nextgame] ^7Next %s: %s" %
                          (voting_type,
                           (change_instructions[0] if voting_type == "map" else
                            gamemodes[change_instructions[0]])))
                      players[player_id][0] = (current_time + config.flood_protection)

            if check_votes:

              check_votes = False

              if (sum((rtv_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                       in players_values())) >= rtv_players): # Start a RTV voting.

                nominated_maps = [nomination
                                  for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                  in players_values() if nomination]

                if config.nomination_type:

                  map_duplicates = defaultdict(bool)
                  voting_maps = [(count(nominated_maps, players[player_id][3]),
                                  (config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                  players[player_id][3])
                                 for player_id in iter(nomination_order)
                                 if (players[player_id][3] not in map_duplicates and # Get nominations in nomination order without
                                     not map_duplicates[players[player_id][3]])]     # duplicates and with the amount of nominations received.
                  sort(voting_maps, key=lambda nomination: nomination[0], reverse=True) # Re-order nominations by nomination count.

                  while len(voting_maps) > 5: # Reduce the number of maps to 5 for the voting.

                    min_nominations = min((nomination_count for (nomination_count, priority, nomination) in
                                           iter(voting_maps)))
                    compare_nominations = [(priority, nomination) for (nomination_count, priority, nomination) in
                                           iter(voting_maps) if nomination_count == min_nominations]

                    if (len(voting_maps) - len(compare_nominations)) >= 5:

                      voting_maps[:] = voting_maps[:-len(compare_nominations)]

                    else: # Compare maps with the map priority system
                          # to define which maps remain.
                      for i in xrange(3):

                        decrease_maps = (len(voting_maps) - 5) # Number of remaining maps to remove.

                        if not decrease_maps:

                          break

                        filtered_nominations = [nomination for (priority, nomination) in iter(compare_nominations)
                                                if priority == i] # Map priority.

                        if filtered_nominations:

                          if len(filtered_nominations) > decrease_maps:

                            filtered_nominations[:] = filtered_nominations[(len(filtered_nominations) - decrease_maps):]

                          voting_maps = [(nomination_count, priority, nomination) for (nomination_count, priority, nomination)
                                         in iter(voting_maps)
                                         if nomination not in filtered_nominations]

                  voting_maps = [(priority, nomination) for (nomination_count, priority, nomination) in iter(voting_maps)]

                else:

                  voting_maps = [((config.map_priority[0] if players[player_id][3] in config.maps else config.map_priority[1]),
                                  players[player_id][3])
                                 for player_id in iter(nomination_order)]

                missing_maps = (5 - len(voting_maps))

                if missing_maps: # Not all 5 map slots are filled.

                  available_maps = config.maps
                  available_secondary_maps = []
                  current_time = time()

                  if config.pick_secondary_maps == 2:

                    available_maps += config.secondary_maps

                  elif config.pick_secondary_maps:

                    available_secondary_maps = [mapname for mapname in iter(config.secondary_maps)
                                                if (mapname not in nominated_maps and
                                                    lower(mapname) != current_map and
                                                    recently_played[lower(mapname)] <= current_time)]

                  available_maps = [mapname for mapname in iter(available_maps)
                                    if (mapname not in nominated_maps and
                                        lower(mapname) != current_map and
                                        recently_played[lower(mapname)] <= current_time)]

                  if missing_maps == 5 and not available_maps and not available_secondary_maps:

                    svsay("^2[RTV] ^7Rock the vote failed to start! No map is currently available.")
                    print("CONSOLE: (%s) [RTV] Rock the vote failed to start! No map is currently available."
                          % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                    players = dict((player_id, [timer, False, rtm_vote, None, None])
                                   for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                                   players_items()) # Reset RTV votes.
                    players_values = players.itervalues
                    players_items = players.iteritems

                    if (sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                             in players_values())) >= rtm_players): # Make sure RTM is checked even
                                                                    # if RTV failed to start.
                      voting_modes = [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]

                      if not voting_modes:

                        svsay("^2[RTM] ^7Rock the mode failed to start! No mode is currently available.")
                        print("CONSOLE: (%s) [RTM] Rock the mode failed to start! No mode is currently available."
                              % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                      else: # Create voting options.

                        votes = SortableDict(((i+1), [0, config.mode_priority[voting_modes[i]], voting_modes[i], gamemodes[voting_modes[i]]])
                                             for i in xrange(len(voting_modes)))

                        if (config.rtm_extend[0] == 2 or
                            (config.rtm_extend[0] == 1 and gameinfo["mode"][1] < config.rtm_extend[1])):

                          votes[(len(votes) + 1)] = [0, config.mode_priority[3], None, "Don't change"] # Add the "Don't change" option.

                        votes_values = votes.itervalues
                        votes_items = votes.sorteditems
                        voting_name = "RTM"
                        voting_type = "mode"
                        voting_method, voting_countdown = config.rtm_voting
                        voting_minimum_votes = config.rtm_minimum_votes
                        voting_wait_time = 1
                        voting_s_wait_time = config.rtm_s_wait_time
                        voting_f_wait_time = config.rtm_f_wait_time
                        voting_skip_voting = config.rtm_skip_voting
                        voting_second_turn = config.rtm_second_turn
                        voting_change_immediately = config.rtm_change_immediately
                        status.rtv = status.rtm = voting_instructions = start_voting = True

                    continue

                  append_map = voting_maps.append
                  remove_map = available_maps.remove

                  try:

                    for i in xrange(missing_maps):

# Fill any remaining map slots with random maps.

                      mapname = choice(available_maps)
                      append_map(((config.map_priority[0] if mapname in config.maps else config.map_priority[1]),
                                  mapname))
                      remove_map(mapname)

                  except IndexError: # Not enough maps to fill all 5 slots.

                    if available_secondary_maps: # Fill with secondary maps if we have no new
                                                 # primary map to use.
                      remove_map = available_secondary_maps.remove

                      try:

                        for i in xrange((5 - len(voting_maps))):

# Fill any remaining map slots with random secondary maps.

                          mapname = choice(available_secondary_maps)
                          append_map((config.map_priority[1], mapname))
                          remove_map(mapname)

                      except IndexError: # Not enough maps to fill remaining slots.

                        pass

# Create voting options.

                votes = SortableDict(((i+1), [0, voting_maps[i][0], voting_maps[i][1], voting_maps[i][1]])
                                     for i in xrange(len(voting_maps)))

                if (config.rtv_extend[0] == 2 or
                    (config.rtv_extend[0] == 1 and gameinfo["map"][1] < config.rtv_extend[1])):

                  votes[(len(votes) + 1)] = [0, config.map_priority[2], None, "Don't change"] # Add the "Don't change" option.

                votes_values = votes.itervalues
                votes_items = votes.sorteditems
                voting_name = "RTV"
                voting_type = "map"
                voting_method, voting_countdown = config.rtv_voting
                voting_minimum_votes = config.rtv_minimum_votes
                voting_wait_time = 0
                voting_s_wait_time = config.rtv_s_wait_time
                voting_f_wait_time = config.rtv_f_wait_time
                voting_skip_voting = config.rtv_skip_voting
                voting_second_turn = config.rtv_second_turn
                voting_change_immediately = config.rtv_change_immediately
                status.rtv = status.rtm = voting_instructions = start_voting = True

              elif (sum((rtm_vote for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                         in players_values())) >= rtm_players): # Start a RTM voting.

                voting_modes = [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]

                if not voting_modes:

                  svsay("^2[RTM] ^7Rock the mode failed to start! No mode is currently available.")
                  print("CONSOLE: (%s) [RTM] Rock the mode failed to start! No mode is currently available."
                        % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))
                  players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                 for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                 in players_items()) # Reset RTM votes.
                  players_values = players.itervalues
                  players_items = players.iteritems

                else: # Create voting options.

                  votes = SortableDict(((i+1), [0, config.mode_priority[voting_modes[i]], voting_modes[i], gamemodes[voting_modes[i]]])
                                       for i in xrange(len(voting_modes)))

                  if (config.rtm_extend[0] == 2 or
                      (config.rtm_extend[0] == 1 and gameinfo["mode"][1] < config.rtm_extend[1])):

                    votes[(len(votes) + 1)] = [0, config.mode_priority[3], None, "Don't change"] # Add the "Don't change" option.

                  votes_values = votes.itervalues
                  votes_items = votes.sorteditems
                  voting_name = "RTM"
                  voting_type = "mode"
                  voting_method, voting_countdown = config.rtm_voting
                  voting_minimum_votes = config.rtm_minimum_votes
                  voting_wait_time = 1
                  voting_s_wait_time = config.rtm_s_wait_time
                  voting_f_wait_time = config.rtm_f_wait_time
                  voting_skip_voting = config.rtm_skip_voting
                  voting_second_turn = config.rtm_second_turn
                  voting_change_immediately = config.rtm_change_immediately
                  status.rtv = status.rtm = voting_instructions = start_voting = True

      if line is None:

        if config.clean_log and getsize(config.logfile) >= config.clean_log[1]: # Clean log file.

          if config.clean_log[0] == 2: # Compress log file.

            compressed_log = TarFile(join_path(dirname(config.logfile),
                                               "%s-%s.tar.gz" % (basename(config.logfile),
                                                                 strftime(timenow(), "%Y%m%d%H%M%S"))),
                                     "w:gz")
            compressed_log.add(config.logfile, arcname=basename(config.logfile))
            compressed_log.close()

          truncate(0)
          flush()
          fsync(fileno)
          seek(0)
          print("CONSOLE: (%s) Log file was cleaned." % (strftime(timenow(), "%d/%m/%Y %H:%M:%S")))

        recover = False # Reset recover flag when no line is read.

        if change_instructions:

          sleep(SLEEP_INTERVAL) # Polling "wait" time.
                                # Prevents overloading CPU with I/O polling.
        elif start_voting:

          if voting_instructions: # Check instructions and send the first voting message.

            voting_instructions = False

            if len(votes) == 1: # We just have one option for the voting.
                                # Skip to whatever the voting does instead of running a redundant voting.
              if voting_change_immediately:

                svsay("^2[%s] ^7Changing %s to %s."
                      % (voting_name, voting_type, votes[1][3]))
                print("CONSOLE: (%s) [%s] Changing %s to %s."
                      % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name, voting_type,
                         votes[1][3]))
                mbmode(("%i %s" % (current_mode, votes[1][2]) if voting_type == "map" else votes[1][2])) # Switch to new map/mode.
                wait_time = (time() + voting_s_wait_time)

                if wait_time > status.times[voting_wait_time]:

                  status.times[voting_wait_time] = wait_time

                change_instructions = True

              else:

                svsay("^2[%s] ^7Changing %s to %s next round."
                      % (voting_name, voting_type, votes[1][3]))
                print("CONSOLE: (%s) [%s] Changing %s to %s next round."
                      % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name, voting_type,
                         votes[1][3]))
                change_instructions = (votes[1][2], voting_wait_time, voting_s_wait_time)

              players = dict((player_id, [timer, False, False, None, None])
                             for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                             players_items()) # Reset players options with the exception of their timer.
              players_values = players.itervalues
              players_items = players.iteritems
              nomination_order[:] = []
              voting_description = None
              admin_choices[:] = []
              del votes
              recover = True

            else:

              skip_voting = False

              if not voting_method:

                _voting_countdown = (" Voting will complete in ^2%i ^7minute%s." %
                                     (voting_countdown,
                                      ("" if voting_countdown == 1 else "s")))
                voting_time = (voting_countdown * 60)
                voting_countdown -= 1
                voting_countdown_seconds = (voting_countdown * 60) if voting_countdown else 30

              else:

                _voting_countdown = ""
                voting_time = DummyTime()

              if voting_type == "admin": # Admin voting.

                svsay("^2[Description] ^7%s" % (voting_description))
                svsay("^2[Admin] ^7An admin voting has begun. Type !number to vote.%s" %
                      (_voting_countdown))

              else:

                svsay("^2[%s] ^7Voting for the next %s has begun. Type !number to vote.%s"
                      % (voting_name, voting_type, _voting_countdown))

              _voting_countdown = voting_countdown
              svsay("^2[Votes] ^7%s" % (join(", ", ("%i: %s" % (vote_id, vote_display_value)
                                                    for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                                    in votes_items()))))
              voting_time += time()

          elif start_second_turn: # Start a second turn voting.

            if not voting_method: # Time-based only.

              start_second_turn = skip_voting = False
              voting_countdown = _voting_countdown
              _voting_countdown += 1
              voting_countdown_seconds = (voting_countdown * 60) if voting_countdown else 30
              svsay("^2[%s] ^7Second turn voting for the next %s has begun. Type !number to vote. Voting will complete in ^2%i ^7minute%s."
                    % (voting_name, voting_type, _voting_countdown,
                       ("" if _voting_countdown == 1 else "s")))
              svsay("^2[Votes] ^71: %s, 2: %s" % (votes[1][3], votes[2][3]))
              voting_time = (time() + (_voting_countdown * 60))

            else:

              sleep(SLEEP_INTERVAL)

          else:

            total_players = len(players)
            total_votes = [vote_count for (vote_count, priority, vote_value, vote_display_value) in votes_values()]
            most_voted = max(total_votes)
            remove(total_votes, most_voted)
            second_most_voted = max(total_votes)
            total_votes = sum(total_votes)
            total_votes += most_voted
            percent_total_votes = ((100.0 * total_votes) / total_players)

            if voting_skip_voting:

              if total_votes == total_players:

                skip_voting = True

              elif voting_skip_voting == 2 and percent_total_votes >= voting_minimum_votes:

                if voting_second_turn:

                  if most_voted > (total_players / 2):

                    skip_voting = True

                elif (total_players - total_votes) < (most_voted - second_most_voted):

                  skip_voting = True

            current_time = time()

            if voting_time <= current_time or skip_voting:

              if percent_total_votes >= voting_minimum_votes:

                voting_list = join(", ", ("%i(%i): %s" % (vote_id, vote_count, vote_display_value)
                                          for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                          in votes_items()))

                if voting_type == "admin": # Admin voting result.

                  most_voted_options = [vote_id for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                        in votes_items() if vote_count == most_voted]
                  vote_percentage = ((100.0 * most_voted) / total_players)
                  svsay("^2[Description] ^7%s" % (voting_description))
                  print("CONSOLE: (%s) [Description] %s"
                        % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"),
                           voting_description))

                  if len(most_voted_options) > 1: # We have a draw.

                    svsay("^2[Admin] ^7Draw (%.1f percent) (%i/%i)!"
                          % (vote_percentage, total_votes, total_players))
                    print("CONSOLE: (%s) [Admin] Draw (%.1f percent) (%i/%i)!"
                          % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"),
                             vote_percentage, total_votes, total_players))

                  else:

                    svsay("^2[Admin] ^7%s won (%.1f percent) (%i/%i)!"
                          % (votes[most_voted_options[0]][3], vote_percentage, total_votes, total_players))
                    print("CONSOLE: (%s) [Admin] %s won (%.1f percent) (%i/%i)!"
                          % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"),
                             votes[most_voted_options[0]][3], vote_percentage, total_votes, total_players))

                  svsay("^2[Result] ^7%s" % (voting_list))
                  print("CONSOLE: (%s) [Result] %s"
                        % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_list))
                  status.rtv = status.rtm = start_voting = False

                elif (voting_second_turn and most_voted <= (total_votes / 2) and
                      (most_voted + second_most_voted) != total_votes): # Prepare for second turn.

                  players = dict((player_id, [timer, rtv_vote, rtm_vote, nomination, None])
                                 for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                                 players_items()) # Reset players votes.
                  players_values = players.itervalues
                  players_items = players.iteritems
                  second_turn_options = [vote_id for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                         in votes_items() if vote_count == most_voted]

                  if len(second_turn_options) > 2: # We have too many most voted values for second turn.

                    for i in xrange(3): # Priority selection.

                      decrease_options = (len(second_turn_options) - 2) # Number of remaining options to remove.

                      if not decrease_options:

                        break

                      second_turn_options_filtered = [vote_id for vote_id in iter(second_turn_options)
                                                      if votes[vote_id][1] == i]

                      if second_turn_options_filtered:

                        if len(second_turn_options_filtered) > decrease_options: # Get a random sample with the amount of
                                                                                 # options to remove.
                          second_turn_options_filtered = sample(second_turn_options_filtered, decrease_options)

                        second_turn_options = [vote_id for vote_id in iter(second_turn_options)
                                               if vote_id not in second_turn_options_filtered]

                  elif len(second_turn_options) < 2: # We don't have enough options for second turn.
                                                     # Get the second option from the second most voted values.
                    second_turn_second_most_voted = [vote_id for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                                     in votes_items() if vote_count == second_most_voted]

                    if len(second_turn_second_most_voted) > 1: # We have too many second most voted values.

                      for i in xrange(2, -1, -1): # Priority selection.

                        second_turn_options_filtered = [vote_id for vote_id in iter(second_turn_second_most_voted)
                                                        if votes[vote_id][1] == i]

                        if second_turn_options_filtered: # Get a single random choice.

                          second_turn_options = [second_turn_options[0],
                                                 choice(second_turn_options_filtered)]
                          break

                    else:

                      second_turn_options = [second_turn_options[0],
                                             second_turn_second_most_voted[0]]

                    sort(second_turn_options)

                  votes = SortableDict(( # Vote count, option priority, vote value, vote display value.
                                        (1, [0, votes[second_turn_options[0]][1],
                                                votes[second_turn_options[0]][2], votes[second_turn_options[0]][3]]),
                                        (2, [0, votes[second_turn_options[1]][1],
                                                votes[second_turn_options[1]][2], votes[second_turn_options[1]][3]])
                                      ))
                  votes_values = votes.itervalues
                  votes_items = votes.sorteditems

                  if not voting_method:

                    svsay("^2[%s] ^7A second turn between %s and %s will begin in 5 seconds (%i/%i)." %
                          (voting_name, votes[1][3], votes[2][3], total_votes, total_players))
                    svsay("^2[Result] ^7%s" % (voting_list))
                    sleep(5)

                  else:

                    svsay("^2[%s] ^7A second turn between %s and %s will begin in the next round (%i/%i)." %
                          (voting_name, votes[1][3], votes[2][3], total_votes, total_players))
                    svsay("^2[Result] ^7%s" % (voting_list))

                  start_second_turn = True
                  continue

                else: # Voting result.

                  most_voted_options = [vote_id for (vote_id, (vote_count, priority, vote_value, vote_display_value))
                                        in votes_items() if vote_count == most_voted]
                  vote_percentage = ((100.0 * most_voted) / total_players)

                  if len(most_voted_options) > 1: # Two or more options tied.

                    for i in xrange(2, -1, -1): # Priority selection.

                      most_voted_options_filtered = [vote_id for vote_id in iter(most_voted_options)
                                                     if votes[vote_id][1] == i]

                      if most_voted_options_filtered: # Get a single random choice.

                        most_voted_options = (choice(most_voted_options_filtered),)
                        break

                  most_voted_options = most_voted_options[0]

                  if votes[most_voted_options][2] is not None:

                    if voting_change_immediately:

                      svsay("^2[%s] ^7Changing %s to %s (%.1f percent) (%i/%i)."
                            % (voting_name, voting_type, votes[most_voted_options][3],
                               vote_percentage, total_votes, total_players))
                      print("CONSOLE: (%s) [%s] Changing %s to %s (%.1f percent) (%i/%i)."
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name, voting_type,
                               votes[most_voted_options][3], vote_percentage,
                               total_votes, total_players))
                      svsay("^2[Result] ^7%s" % (voting_list))
                      print("CONSOLE: (%s) [Result] %s"
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_list))
                      mbmode(("%i %s" % (current_mode, votes[most_voted_options][2]) if voting_type == "map" else
                              votes[most_voted_options][2])) # Switch to new map/mode.
                      wait_time = (time() + voting_s_wait_time)

                      if wait_time > status.times[voting_wait_time]:

                        status.times[voting_wait_time] = wait_time

                      change_instructions = True

                    else:

                      svsay("^2[%s] ^7Changing %s to %s next round (%.1f percent) (%i/%i)."
                            % (voting_name, voting_type, votes[most_voted_options][3],
                               vote_percentage, total_votes, total_players))
                      print("CONSOLE: (%s) [%s] Changing %s to %s next round (%.1f percent) (%i/%i)."
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name, voting_type,
                               votes[most_voted_options][3], vote_percentage,
                               total_votes, total_players))
                      svsay("^2[Result] ^7%s" % (voting_list))
                      print("CONSOLE: (%s) [Result] %s"
                            % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_list))
                      change_instructions = (votes[most_voted_options][2], voting_wait_time, voting_s_wait_time)

                  else: # "Don't change" option won.
                        # Extend map/mode.
                    svsay("^2[%s] ^7The voting has failed (extend %s) (%.1f percent) (%i/%i)!"
                          % (voting_name, voting_type, vote_percentage,
                             total_votes, total_players))
                    print("CONSOLE: (%s) [%s] The voting has failed (extend %s) (%.1f percent) (%i/%i)!"
                          % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name, voting_type,
                             vote_percentage, total_votes, total_players))
                    svsay("^2[Result] ^7%s" % (voting_list))
                    print("CONSOLE: (%s) [Result] %s"
                          % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_list))
                    gameinfo[voting_type][1] += 1
                    wait_time = (time() + voting_f_wait_time)

                    if wait_time > status.times[voting_wait_time]:

                      status.times[voting_wait_time] = wait_time

                    status.rtv = status.rtm = start_voting = False

              else: # Not enough votes.

                svsay("^2[%s] ^7The voting has failed (not enough votes)!"
                      % (voting_name))
                print("CONSOLE: (%s) [%s] The voting has failed (not enough votes)!"
                      % (strftime(timenow(), "%d/%m/%Y %H:%M:%S"), voting_name))

                if voting_type != "admin":

                  wait_time = (time() + voting_f_wait_time)

                  if wait_time > status.times[voting_wait_time]:

                    status.times[voting_wait_time] = wait_time

                status.rtv = status.rtm = start_voting = False

              players = dict((player_id, [timer, False, False, None, None])
                             for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option)) in
                             players_items()) # Reset players options with the exception of their timer.
              players_values = players.itervalues
              players_items = players.iteritems
              nomination_order[:] = []
              voting_description = None
              admin_choices[:] = []
              del votes
              recover = True

            elif not voting_method: # Time-based voting.

              voting_remaining_time = (voting_time - current_time)

              if voting_remaining_time <= voting_countdown_seconds:

                if voting_type == "admin":

                  svsay("^2[Description] ^7%s" % (voting_description))

                if voting_countdown_seconds < 60:

                  send_voting_message(voting_name, voting_countdown_seconds, "second",
                                      total_votes, total_players, votes_items, svsay)

                else:

                  send_voting_message(voting_name, voting_countdown, "minute",
                                      total_votes, total_players, votes_items, svsay)

                voting_countdown -= 1
                voting_countdown_seconds = (voting_countdown * 60) if voting_countdown else 30

              else:

                sleep(SLEEP_INTERVAL)

            else:

              sleep(SLEEP_INTERVAL)

        else:

          sleep(Check_Status()) # Polling "wait" time.
                                # Prevents overloading CPU with I/O polling.
if __name__ == "__main__":

  try:

    main(argv)

  except KeyboardInterrupt:

    exit(2)

  except Exception:

    if REPORT_UNHANDLED_EXCEPTION:

      report_unhandled_exception(format_exc())

    raise
