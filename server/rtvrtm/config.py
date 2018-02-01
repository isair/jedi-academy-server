from __future__ import with_statement
from sys import platform, exit
from os import listdir
from os.path import basename, dirname, normpath, realpath, normcase, join as join_path
from zipfile import ZipFile, BadZipfile
from socket import socket, AF_INET, SOCK_DGRAM, SHUT_RDWR, timeout as socketTimeout, error as socketError, gethostbyname_ex
from time import sleep
from collections import defaultdict

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

        except IOError as err:

          errno = err.errno

          if errno == 2:

            raise Exception("Map file directory does not exist.")

          if errno == 13:

            raise Exception("Cannot write to map file. Permission denied.")

          else:

            raise Exception("Unexpected error while creating map file (ERRNO: %i)." % (errno))

        try:

          secondary_mapfile = open(self.secondary_maps, "at")

        except IOError as err:

          mapfile.close()
          errno = err.errno

          if errno == 2:

            raise Exception("Secondary map file directory does not exist.")

          elif errno == 13:

            raise Exception("Cannot write to secondary map file. Permission denied.")

          elif errno == 21:

            raise Exception("Secondary map file is set to a directory.")

          elif errno == 22:

            raise Exception("Invalid secondary map file.")

          else:

            raise Exception("Unexpected error while creating secondary map file (ERRNO: %i)." % (errno))

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

          raise Exception("The map list is empty.")

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

    except IOError as err:

      errno = err.errno

      if errno == 2:

        raise Exception("Configuration file does not exist.")

      elif errno == 13:

        raise Exception("Cannot read configuration file. Permission denied.")

      elif errno == 21:

        raise Exception("Configuration file is set to a directory.")

      elif errno == 22:

        raise Exception("Invalid configuration file.")

      else:

        raise Exception("Unexpected error while reading configuration file (ERRNO: %i)." % (errno))

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

        raise Exception("Log file is not defined.")

      except IndexError:

        raise Exception("Invalid log file.")

      except IOError as err:

        errno = err.errno

        if errno == 2:

          raise Exception("Log file does not exist.")

        elif errno == 13:

          raise Exception("Cannot open log file. Permission denied.")

        elif errno == 21:

          raise Exception("Log file is set to a directory.")

        elif errno == 22:

          raise Exception("Invalid log file.")

        else:

          raise Exception("Unexpected error while reading log file (ERRNO: %i)." % (errno))

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

          except IOError as err:

            warning("Error while trying to read %s (ERRNO: %i)." % (pk3, err.errno))
            print("[*] Checking options for errors..."),

          except BadZipfile:

            warning("%s is not a valid pk3 file." % (pk3))
            print("[*] Checking options for errors..."),

        if not bsps:

          raise Exception("No BSP map files detected. Make sure MBII folder path is correct.")

        map_duplicates = defaultdict(bool)
        bsps = [bsp for bsp in iter(bsps)
                if (lower(bsp) not in map_duplicates and
                    not map_duplicates[lower(bsp)])] # Ensure that we don't get duplicates from replacements.
        lower_bsps = tuple((lower(bsp) for bsp in iter(bsps)))

      except AttributeError:

        raise Exception("MBII folder is not defined.")

      except (WindowsError if platform == "win32" else OSError) as err:

        errno = err.errno

        if errno == 2:

          raise Exception("MBII folder does not exist.")

        elif errno == 13:

          raise Exception("Cannot list MBII folder. Permission denied.")

        elif errno == 20:

          raise Exception("MBII folder is not a directory.")

        elif errno == 22:

          raise Exception("Invalid MBII folder.")

        else:

          raise Exception("Unexpected error while listing MBII folder (ERRNO: %i)." % (errno))

      try:

        self.address = split(strip(self.address), ":")

        if len(self.address) != 2:

          raise Exception("Incorrect server address format.")

        self.address = (gethostbyname_ex(self.address[0])[2][0], int(self.address[1]))

        if self.address[1] < 1 or self.address[1] > 65535:

          raise ValueError

      except AttributeError:

        raise Exception("Server address is not defined.")

      except gaierror:

        raise Exception("Invalid server address.")

      except ValueError:

        raise Exception("Incorrect server port (1-65535).")

      self.bindaddr = strip(self.bindaddr)

      try:

        self.bindaddr = gethostbyname_ex(self.bindaddr)[2][0] if self.bindaddr else "0.0.0.0"

      except gaierror:

        raise Exception("Invalid bind address.")

      try:

        self.rcon_pwd = strip(self.rcon_pwd)

        if not self.rcon_pwd:

          raise Exception("Rcon password is empty.")

      except AttributeError:

        raise Exception("Rcon password is not defined.")

      try:

        self.flood_protection = float(self.flood_protection)

        if self.flood_protection < 0:

          raise Exception("Flood protection must be greater than or equal 0 seconds.")

      except AttributeError:

        raise Exception("Flood protection is not defined.")

      except ValueError:

        raise Exception("Flood protection is neither an integer nor a floating point.")

      try:

        self.use_say_only = int(self.use_say_only)

        if self.use_say_only not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        raise Exception("Use say only is not defined.")

      except ValueError:

        raise Exception("Use say only must be either 0 (disabled) or 1 (enabled).")

      try:

        self.name_protection = int(self.name_protection)

        if self.name_protection not in (0, 1): # Non boolean.

          raise ValueError

      except AttributeError:

        raise Exception("Name protection is not defined.")

      except ValueError:

        raise Exception("Name protection must be either 0 (disabled) or 1 (enabled).")

      self.default_game = split(self.default_game)

      if not self.default_game:

        self.default_game = False

      elif len(self.default_game) <= 3:

        try:

          self.default_game[0] = int(self.default_game[0])

          if self.default_game[0] not in (0, 1, 2, 3):

            raise Exception("Invalid mode for default game (0, 1, 2, 3).")

          elif lower(self.default_game[1]) not in lower_bsps:

            raise Exception("Default map %s is not in the server." % (self.default_game[1]))

        except ValueError:

          if len(self.default_game) == 2:

            raise Exception("Default game mode is not an integer.")

          elif lower(self.default_game[0]) not in lower_bsps:

            raise Exception("Default map %s is not in the server." % (self.default_game[0]))

        except IndexError:

          pass

        self.default_game = tuple(self.default_game)

      else:

        raise Exception("Too many options for default game (mode map or map/mode).")

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

            raise Exception("Log size for cleaning must be greater than or equal 1 megabyte.")

          self.clean_log = (self.clean_log[0], (self.clean_log[1] * 1048576))

        else:

          raise Exception("Invalid value for clean log (0, 1, 2).")

      except AttributeError:

        raise Exception("Clean log is not defined.")

      except ValueError:

        raise Exception("Clean log contains a non integer value.")

      except IndexError:

        raise Exception("Incorrect format for clean log.")

# Admin voting settings.

      try:

        self.admin_voting = tuple((int(i) for i in iter(split(self.admin_voting))))

        if len(self.admin_voting) != 2:

          raise Exception("Incorrect format for admin voting.")

        elif self.admin_voting[0] not in (0, 1):

          raise Exception("Invalid value for admin voting (0, 1).")

        elif self.admin_voting[1] < 1:

          raise Exception("Number of %s for admin voting must be greater than or equal 1."
                % ("minutes" if not self.admin_voting[0] else "rounds"))

      except AttributeError:

        raise Exception("Admin voting is not defined.")

      except ValueError:

        raise Exception("Admin voting contains a non integer value.")

      try:

        self.admin_minimum_votes = float(self.admin_minimum_votes)

        if self.admin_minimum_votes < 0 or self.admin_minimum_votes > 100:

          raise Exception("Admin minimum votes must range from 0 to 100 percent.")

      except AttributeError:

        raise Exception("Admin minimum votes is not defined.")

      except ValueError:

        raise Exception("Admin minimum votes is neither an integer nor a floating point.")

      try:

        self.admin_skip_voting = int(self.admin_skip_voting)

        if self.admin_skip_voting not in (0, 1, 2):

          raise Exception("Invalid value for admin skip voting (0, 1, 2).")

      except AttributeError:

        raise Exception("Admin skip voting is not defined.")

      except ValueError:

        raise Exception("Admin skip voting is not an integer.")

# Map limit settings.

      try:

        self.roundlimit = int(self.roundlimit)

        if self.roundlimit == 1:

          self.cvar += 1879

        elif self.roundlimit: # No boolean value.

          raise ValueError

      except AttributeError:

        raise Exception("Roundlimit is not defined.")

      except ValueError:

        raise Exception("Roundlimit must be either 0 (disabled) or 1 (enabled).")

      try:

        self.timelimit = int(self.timelimit)

        if self.timelimit == 1:

          self.cvar += 1890

        elif self.timelimit: # No boolean value.

          raise ValueError

      except AttributeError:

        raise Exception("Timelimit is not defined.")

      except ValueError:

        raise Exception("Timelimit must be either 0 (disabled) or 1 (enabled).")

      if self.roundlimit or self.timelimit:

        try:

          self.limit_voting = tuple((int(i) for i in iter(split(self.limit_voting))))

          if len(self.limit_voting) != 2:

            raise Exception("Incorrect format for map limit voting.")

          elif self.limit_voting[0] not in (0, 1):

            raise Exception("Invalid value for map limit voting (0, 1).")

          elif self.limit_voting[1] < 1:

            raise Exception("Number of %s for map limit voting must be greater than or equal 1."
                  % ("minutes" if not self.limit_voting[0] else "rounds"))

        except AttributeError:

          raise Exception("Map limit voting is not defined.")

        except ValueError:

          raise Exception("Map limit voting contains a non integer value.")

        try:

          self.limit_minimum_votes = float(self.limit_minimum_votes)

          if self.limit_minimum_votes < 0 or self.limit_minimum_votes > 100:

            raise Exception("Map limit minimum votes must range from 0 to 100 percent.")

        except AttributeError:

          raise Exception("Map limit minimum votes is not defined.")

        except ValueError:

          raise Exception("Map limit minimum votes is neither an integer nor a floating point.")

        try:

          self.limit_extend = tuple((int(i) for i in iter(split(self.limit_extend))))

          if self.limit_extend[0] in (0, 2):

            if len(self.limit_extend) > 1:

              raise IndexError

          elif self.limit_extend[0] == 1:

            if len(self.limit_extend) != 2:

              raise IndexError

            elif self.limit_extend[1] < 1:

              raise Exception("Map limit number of extensions must be greater than or equal 1.")

          else:

            raise Exception("Invalid value for map limit extend (0, 1, 2).")

        except AttributeError:

          raise Exception("Map limit extend is not defined.")

        except ValueError:

          raise Exception("Map limit extend contains a non integer value.")

        except IndexError:

          raise Exception("Incorrect format for map limit extend.")

        try:

          self.limit_s_wait_time = int(self.limit_s_wait_time)

          if self.limit_s_wait_time < 0:

            raise Exception("Map limit successful wait time must be greater than or equal 0 seconds.")

        except AttributeError:

          raise Exception("Map limit successful wait time is not defined.")

        except ValueError:

          raise Exception("Map limit successful wait time is not an integer.")

        try:

          self.limit_f_wait_time = int(self.limit_f_wait_time)

          if self.limit_f_wait_time < 0:

            raise Exception("Map limit failed wait time must be greater than or equal 0 seconds.")

        except AttributeError:

          raise Exception("Map limit failed wait time is not defined.")

        except ValueError:

          raise Exception("Map limit failed wait time is not an integer.")

        try:

          self.limit_skip_voting = int(self.limit_skip_voting)

          if self.limit_skip_voting not in (0, 1, 2):

            raise Exception("Invalid value for map limit skip voting (0, 1, 2).")

        except AttributeError:

          raise Exception("Map limit skip voting is not defined.")

        except ValueError:

          raise Exception("Map limit skip voting is not an integer.")

        try:

          self.limit_second_turn = int(self.limit_second_turn)

          if self.limit_second_turn not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          raise Exception("Map limit second turn is not defined.")

        except ValueError:

          raise Exception("Map limit second turn must be either 0 (disabled) or 1 (enabled).")

        try:

          self.limit_change_immediately = int(self.limit_change_immediately)

          if self.limit_change_immediately not in (0, 1): # Non boolean.

            raise ValueError

        except AttributeError:

          raise Exception("Map limit change immediately is not defined.")

        except ValueError:

          raise Exception("Map limit change immediately must be either 0 (disabled) or 1 (enabled).")

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

              raise Exception("RTV rate must range from 0 to 100 percent.")

          except AttributeError:

            raise Exception("RTV rate is not defined.")

          except ValueError:

            raise Exception("RTV rate is neither an integer nor a floating point.")

          try:

            self.rtv_voting = tuple((int(i) for i in iter(split(self.rtv_voting))))

            if len(self.rtv_voting) != 2:

              raise Exception("Incorrect format for RTV voting.")

            elif self.rtv_voting[0] not in (0, 1):

              raise Exception("Invalid value for RTV voting (0, 1).")

            elif self.rtv_voting[1] < 1:

              raise Exception("Number of %s for RTV voting must be greater than or equal 1."
                    % ("minutes" if not self.rtv_voting[0] else "rounds"))

          except AttributeError:

            raise Exception("RTV voting is not defined.")

          except ValueError:

            raise Exception("RTV voting contains a non integer value.")

          try:

            self.rtv_minimum_votes = float(self.rtv_minimum_votes)

            if self.rtv_minimum_votes < 0 or self.rtv_minimum_votes > 100:

              raise Exception("RTV minimum votes must range from 0 to 100 percent.")

          except AttributeError:

            raise Exception("RTV minimum votes is not defined.")

          except ValueError:

            raise Exception("RTV minimum votes is neither an integer nor a floating point.")

          try:

            self.rtv_extend = tuple((int(i) for i in iter(split(self.rtv_extend))))

            if self.rtv_extend[0] in (0, 2):

              if len(self.rtv_extend) > 1:

                raise IndexError

            elif self.rtv_extend[0] == 1:

              if len(self.rtv_extend) != 2:

                raise IndexError

              elif self.rtv_extend[1] < 1:

                raise Exception("RTV number of extensions must be greater than or equal 1.")

            else:

              raise Exception("Invalid value for RTV extend (0, 1, 2).")

          except AttributeError:

            raise Exception("RTV extend is not defined.")

          except ValueError:

            raise Exception("RTV extend contains a non integer value.")

          except IndexError:

            raise Exception("Incorrect format for RTV extend.")

          try:

            self.rtv_s_wait_time = int(self.rtv_s_wait_time)

            if self.rtv_s_wait_time < 0:

              raise Exception("RTV successful wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            raise Exception("RTV successful wait time is not defined.")

          except ValueError:

            raise Exception("RTV successful wait time is not an integer.")

          try:

            self.rtv_f_wait_time = int(self.rtv_f_wait_time)

            if self.rtv_f_wait_time < 0:

              raise Exception("RTV failed wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            raise Exception("RTV failed wait time is not defined.")

          except ValueError:

            raise Exception("RTV failed wait time is not an integer.")

          try:

            self.rtv_skip_voting = int(self.rtv_skip_voting)

            if self.rtv_skip_voting not in (0, 1, 2):

              raise Exception("Invalid value for RTV skip voting (0, 1, 2).")

          except AttributeError:

            raise Exception("RTV skip voting is not defined.")

          except ValueError:

            raise Exception("RTV skip voting is not an integer.")

          try:

            self.rtv_second_turn = int(self.rtv_second_turn)

            if self.rtv_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            raise Exception("RTV second turn is not defined.")

          except ValueError:

            raise Exception("RTV second turn must be either 0 (disabled) or 1 (enabled).")

          try:

            self.rtv_change_immediately = int(self.rtv_change_immediately)

            if self.rtv_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            raise Exception("RTV change immediately is not defined.")

          except ValueError:

            raise Exception("RTV change immediately must be either 0 (disabled) or 1 (enabled).")

        elif not self.rtv:

          self.rtv_rate = self.rtv_voting = self.rtv_minimum_votes = \
          self.rtv_extend = self.rtv_s_wait_time = self.rtv_f_wait_time = \
          self.rtv_skip_voting = self.rtv_second_turn = self.rtv_change_immediately = None

        else: # No boolean value.

          raise ValueError

      except AttributeError:

        raise Exception("RTV is not defined.")

      except ValueError:

        raise Exception("RTV must be either 0 (disabled) or 1 (enabled).")

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

                raise Exception("Invalid map file.")

            self.secondary_maps = strip(self.secondary_maps)

            if not self.secondary_maps:

              self.secondary_maps = join_path(dirname(self.config_path), "secondary_maps.txt")

            else:

              try:

                while self.secondary_maps[-1] in (" ", "\\", "/"):

                  self.secondary_maps = self.secondary_maps[:-1]

                self.secondary_maps = normpath(self.secondary_maps)

              except IndexError:

                raise Exception("Invalid secondary map file.")

            if normcase(realpath(self.maps)) == normcase(realpath(self.secondary_maps)):

              raise Exception("Map and secondary map files are the same.")

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

                      raise Exception("Invalid value for pick secondary maps (0, 1, 2).")

                  except AttributeError:

                    raise Exception("Pick secondary maps is not defined.")

                  except ValueError:

                    raise Exception("Pick secondary maps is not an integer.")

                else:

                  self.pick_secondary_maps = None

              else:

# Check whether the map has a BSP file.

                non_bsps = tuple((mapname for mapname in iter(maps)
                                  if lower(mapname) not in lower_bsps))

                if non_bsps:

                  raise Exception("Map%s not found in the server:\n\n%s" %
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

                      raise Exception("Secondary map%s not found in the server:\n\n%s" %
                            (("s" if len(non_bsps) > 1 else ""),
                             "\n".join(non_bsps)))

                    repeated_maps = tuple((lower(mapname) for mapname in iter(self.maps)))
                    repeated_maps = tuple((mapname for mapname in iter(self.secondary_maps)
                                           if lower(mapname) in repeated_maps)) # Compare primary and secondary maps.

                    if repeated_maps:

                      raise Exception("Map%s found in both primary and secondary files:\n\n%s" %
                            (("s" if len(repeated_maps) > 1 else ""),
                             "\n".join(repeated_maps)))

                    try:

                      self.pick_secondary_maps = int(self.pick_secondary_maps)

                      if self.pick_secondary_maps not in (0, 1, 2):

                        raise Exception("Invalid value for pick secondary maps (0, 1, 2).")

                    except AttributeError:

                      raise Exception("Pick secondary maps is not defined.")

                    except ValueError:

                      raise Exception("Pick secondary maps is not an integer.")

                  else:

                    self.pick_secondary_maps = None

                except IOError as err:

                  errno = err.errno

                  if errno == 2:

                    self.secondary_maps = ()
                    self.pick_secondary_maps = None

                  elif errno == 13:

                    raise Exception("Cannot read secondary map file. Permission denied.")

                  elif errno == 21:

                    raise Exception("Secondary map file is set to a directory.")

                  elif errno == 22:

                    raise Exception("Invalid secondary map file.")

                  else:

                    raise Exception("Unexpected error while reading secondary map file (ERRNO: %i)." % (errno))

            except IOError as err:

              errno = err.errno

              if errno == 2:

                warning("Map file does not exist.")
                self.create_maplist(bsps)

                if self.secondary_maps:

                  try:

                    self.pick_secondary_maps = int(self.pick_secondary_maps)

                    if self.pick_secondary_maps not in (0, 1, 2):

                      raise Exception("Invalid value for pick secondary maps (0, 1, 2).")

                  except AttributeError:

                    raise Exception("Pick secondary maps is not defined.")

                  except ValueError:

                    raise Exception("Pick secondary maps is not an integer.")

                else:

                  self.pick_secondary_maps = None

              elif errno == 13:

                raise Exception("Cannot read map file. Permission denied.")

              elif errno == 21:

                raise Exception("Map file is set to a directory.")

              elif errno == 22:

                raise Exception("Invalid map file.")

              else:

                raise Exception("Unexpected error while reading map file (ERRNO: %i)." % (errno))

          elif self.automatic_maps == 1: # Use all available maps from BSP files.

            self.maps = tuple(bsps)
            self.secondary_maps = ()
            self.pick_secondary_maps = None

          else: # No boolean value.

            raise ValueError

        except AttributeError:

          raise Exception("Automatic maps is not defined.")

        except ValueError:

          raise Exception("Automatic maps must be either 0 (disabled) or 1 (enabled).")

        try:

          self.map_priority = tuple((int(i) for i in iter(split(self.map_priority))))

          if len(self.map_priority) == 3:

            if self.map_priority[0] not in (0, 1, 2):

              raise Exception("Invalid value for map priority/primary maps (0, 1, 2).")

            elif self.map_priority[1] not in (0, 1, 2):

              raise Exception("Invalid value for map priority/secondary maps (0, 1, 2).")

            elif self.map_priority[2] not in (0, 1, 2):

              raise Exception("Invalid value for map priority/extend map (0, 1, 2).")

          else:

            raise Exception("Incorrect format for map priority.")

        except AttributeError:

          raise Exception("Map priority is not defined.")

        except ValueError:

          raise Exception("Map priority contains a non integer value.")

        if (len(self.maps) + len(self.secondary_maps)) > 5:

          try:

            self.nomination_type = int(self.nomination_type)

            if self.nomination_type not in (0, 1):

              raise Exception("Invalid value for nomination type (0, 1).")

          except AttributeError:

            raise Exception("Nomination type is not defined.")

          except ValueError:

            raise Exception("Nomination type is not an integer.")

        elif self.pick_secondary_maps == 0:

          raise Exception("Pick secondary maps must be enabled whether secondary maps are present and nominations are disabled.")

        else:

          self.nomination_type = None

        try:

          self.enable_recently_played = int(self.enable_recently_played)

          if self.enable_recently_played < 0:

            raise Exception("Enable recently played maps must be greater than or equal 0 seconds.")

        except AttributeError:

          raise Exception("Enable recently played maps is not defined.")

        except ValueError:

          raise Exception("Enable recently played maps is not an integer.")

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

                raise Exception("Invalid value for mode priority/open mode (0, 1, 2).")

              elif self.mode_priority[1] not in (0, 1, 2, 3):

                raise Exception("Invalid value for mode priority/semi authentic mode (0, 1, 2).")

              elif self.mode_priority[2] not in (0, 1, 2):

                raise Exception("Invalid value for mode priority/full authentic mode (0, 1, 2).")

              elif self.mode_priority[3] not in (0, 1, 2):

                raise Exception("Invalid value for mode priority/duel mode (0, 1, 2).")

              elif self.mode_priority[4] not in (0, 1, 2):

                raise Exception("Invalid value for mode priority/extend mode (0, 1, 2).")

            else:

              raise Exception("Incorrect format for mode priority.")

          except AttributeError:

            raise Exception("Mode priority is not defined.")

          except ValueError:

            raise Exception("Mode priority contains a non integer value.")

          try:

            self.rtm_rate = float(self.rtm_rate)

            if self.rtm_rate < 0 or self.rtm_rate > 100:

              raise Exception("RTM rate must range from 0 to 100 percent.")

          except AttributeError:

            raise Exception("RTM rate is not defined.")

          except ValueError:

            raise Exception("RTM rate is neither an integer nor a floating point.")

          try:

            self.rtm_voting = tuple((int(i) for i in iter(split(self.rtm_voting))))

            if len(self.rtm_voting) != 2:

              raise Exception("Incorrect format for RTM voting.")

            elif self.rtm_voting[0] not in (0, 1):

              raise Exception("Invalid value for RTM voting (0, 1).")

            elif self.rtm_voting[1] < 1:

              raise Exception("Number of %s for RTM voting must be greater than or equal 1."
                    % ("minutes" if not self.rtm_voting[0] else "rounds"))

          except AttributeError:

            raise Exception("RTM voting is not defined.")

          except ValueError:

            raise Exception("RTM voting contains a non integer value.")

          try:

            self.rtm_minimum_votes = float(self.rtm_minimum_votes)

            if self.rtm_minimum_votes < 0 or self.rtm_minimum_votes > 100:

              raise Exception("RTM minimum votes must range from 0 to 100 percent.")

          except AttributeError:

            raise Exception("RTM minimum votes is not defined.")

          except ValueError:

            raise Exception("RTM minimum votes is neither an integer nor a floating point.")

          try:

            self.rtm_extend = tuple((int(i) for i in iter(split(self.rtm_extend))))

            if self.rtm_extend[0] in (0, 2):

              if len(self.rtm_extend) > 1:

                raise IndexError

            elif self.rtm_extend[0] == 1:

              if len(self.rtm_extend) != 2:

                raise IndexError

              elif self.rtm_extend[1] < 1:

                raise Exception("RTM number of extensions must be greater than or equal 1.")

            else:

              raise Exception("Invalid value for RTM extend (0, 1, 2).")

          except AttributeError:

            raise Exception("RTM extend is not defined.")

          except ValueError:

            raise Exception("RTM extend contains a non integer value.")

          except IndexError:

            raise Exception("Incorrect format for RTM extend.")

          try:

            self.rtm_s_wait_time = int(self.rtm_s_wait_time)

            if self.rtm_s_wait_time < 0:

              raise Exception("RTM successful wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            raise Exception("RTM successful wait time is not defined.")

          except ValueError:

            raise Exception("RTM successful wait time is not an integer.")

          try:

            self.rtm_f_wait_time = int(self.rtm_f_wait_time)

            if self.rtm_f_wait_time < 0:

              raise Exception("RTM failed wait time must be greater than or equal 0 seconds.")

          except AttributeError:

            raise Exception("RTM failed wait time is not defined.")

          except ValueError:

            raise Exception("RTM failed wait time is not an integer.")

          try:

            self.rtm_skip_voting = int(self.rtm_skip_voting)

            if self.rtm_skip_voting not in (0, 1, 2):

              raise Exception("Invalid value for RTM skip voting (0, 1, 2).")

          except AttributeError:

            raise Exception("RTM skip voting is not defined.")

          except ValueError:

            raise Exception("RTM skip voting is not an integer.")

          try:

            self.rtm_second_turn = int(self.rtm_second_turn)

            if self.rtm_second_turn not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            raise Exception("RTM second turn is not defined.")

          except ValueError:

            raise Exception("RTM second turn must be either 0 (disabled) or 1 (enabled).")

          try:

            self.rtm_change_immediately = int(self.rtm_change_immediately)

            if self.rtm_change_immediately not in (0, 1): # Non boolean.

              raise ValueError

          except AttributeError:

            raise Exception("RTM change immediately is not defined.")

          except ValueError:

            raise Exception("RTM change immediately must be either 0 (disabled) or 1 (enabled).")

        else:

          self.mode_priority = self.rtm_rate = self.rtm_voting = \
          self.rtm_minimum_votes = self.rtm_extend = \
          self.rtm_s_wait_time = self.rtm_f_wait_time = \
          self.rtm_skip_voting = self.rtm_second_turn = self.rtm_change_immediately = None

      except AttributeError:

        raise Exception("RTM is not defined.")

      except ValueError:

        raise Exception("RTM is not an integer.")

      except KeyError:

        raise Exception("Invalid value for RTM (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14).")

# Connection test.

      if tries:
        for i in xrange(1, (tries+1)):
          sock = socket(AF_INET, SOCK_DGRAM)
          try:
            bind(sock, (self.bindaddr, 0))
          except socketError:
            close(sock)
            raise Exception("Bind address is unavailable.")
          try:
            settimeout(sock, 12)
            connect(sock, self.address)
            sock.send("\xff\xff\xff\xffrcon %s status" % self.rcon_pwd)
            reply = lower(strip(sock.recv(1024)))
            if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):
              raise Exception("Incorrect rcon password.")
            elif startswith(reply, "\xff\xff\xff\xffprint") == False:
              raise Exception("Unexpected error while contacting server for the first time.")
            break
          except socketTimeout:
            if i == tries:
              raise Exception("Could not contact the server after %i tr%s (TIMEOUT)."
                    % (tries,
                       ("ies" if tries > 1 else "y")))
          except socketError:
            if i == tries:
              raise Exception("Could not contact the server after %i tr%s (REFUSED/UNREACHABLE)."
                    % (tries,
                       ("ies" if tries > 1 else "y")))
            sleep(12)
          finally:
            shutdown(sock, SHUT_RDWR)
            close(sock)
      else:
        while(True):
          sock = socket(AF_INET, SOCK_DGRA/M)
          try:
            bind(sock, (self.bindaddr, 0))
          except socketError:
            close(sock)
            raise Exception("Bind address is unavailable.")
          try:
            settimeout(sock, 12)
            connect(sock, self.address)
            sock.send("\xff\xff\xff\xffrcon %s status" % self.rcon_pwd)
            reply = lower(strip(sock.recv(1024)))
            if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):
              raise Exception("Incorrect rcon password.")
            elif startswith(reply, "\xff\xff\xff\xffprint") == False:
              raise Exception("Unexpected error while contacting server for the first time.")
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

    except IOError as err:

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

          except IOError as err:

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

      except (WindowsError if platform == "win32" else OSError) as err:

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

            except IOError as err:

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

            except IOError as err:

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
          sock.send("\xff\xff\xff\xffrcon %s status" % self.rcon_pwd)
          reply = lower(strip(sock.recv(1024)))
          if startswith(reply, "\xff\xff\xff\xffprint\nbad rconpassword"):
            warning("Incorrect rcon password.", rehash=True)
            return False
          elif startswith(reply, "\xff\xff\xff\xffprint") == False:
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
