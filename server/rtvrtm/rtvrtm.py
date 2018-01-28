#!/usr/bin/python -uSOO

from __future__ import with_statement
from sys import platform, setcheckinterval, argv, exit
from optparse import OptionParser, OptionGroup
from os import fsync
from os.path import getsize, basename, dirname, normpath, normcase, join as join_path
from socket import socket, AF_INET, SOCK_DGRAM, SHUT_RDWR, timeout as socketTimeout, error as socketError
from time import time, sleep
from collections import defaultdict
from datetime import datetime
from random import choice, sample
from tarfile import open as TarFile
from threading import Timer

from config import Config
from jaserver import JAServer
from rcon import Rcon
from features import Features

VERSION = "4.0"
SLEEP_INTERVAL = 0.075
MAPLIST_MAX_SIZE = 750

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
    return self              # on assignment addition operations.

def fix_line(line):
  """Fix for the Client log line missing the \n (newline) character."""
  startswith = str.startswith
  split = str.split
  while startswith(line[8:], "Client "):
    line = split(line, ":", 3)
    if len(line) < 4: # If this bug is ever fixed within the MBII code,
      return ""       # make sure this fix is not processed.
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

def switch_default(default_game, current_mode, current_map, jaserver):
  """Set default game whenever player count drops to 0."""
  if len(default_game) == 2:
    if current_mode != default_game[0] or current_map != default_game[1].lower():
      jaserver.rcon.mbmode("%i %s" % (default_game[0], default_game[1]))
      return True
  elif isinstance(default_game[0], int):
    if current_mode != default_game[0]:
      jaserver.rcon.mbmode(default_game[0])
      return True
  elif current_map != default_game[0].lower():
    jaserver.rcon.mbmode("%i %s" % (current_mode, default_game[0]))
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

def say_timed_messages(jaserver, cvars):
  Timer(21.0, jaserver.rcon.sayNewRoundMessage).start()
  Timer(45.0, jaserver.rcon.sayRandomTip).start()
  if int(cvars["g_authenticity"]) == 3:
    Timer(60.0, jaserver.rcon.sayLamingWarning).start()

def main(argv):
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
  parser = OptionParser(usage="Usage: %s [-c <configuration file> -t <tries>]" % (argv[0]))
  parser.add_option("-c", dest="config_path",
                    help="Set the path of the configuration file. Default: rtvrtm.cfg", metavar="<configuration file>",
                    default=join_path(dirname(normpath(argv[0])), "rtvrtm.cfg"))
  parser.add_option("-t", type="int", dest="tries",
                    help="Set the amount of server connection tries before giving up (0 = infinite). Default: 5",
                    metavar="<0-100>", default=5)
  opts, args = parser.parse_args()

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

  config = Config(config_path)
  try:
    config.create(opts.tries)
  except Exception as e:
    error(e)

  parser.destroy()
  del (filecode, parser, opts, args, config_path)

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
  jaserver = JAServer(config.address, config.bindaddr, config.rcon_pwd)
  svsay = jaserver.rcon.svsay if not config.use_say_only else say
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
      reset = switch_default(config.default_game, current_mode, current_map, jaserver)

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

                      reset = switch_default(config.default_game, current_mode, current_map, jaserver)

                  elif config.default_game:

                    switch_default(config.default_game, current_mode, current_map, jaserver)

                elif not start_voting:

                  check_votes = True

              except KeyError:

                pass

            elif startswith(line, "InitGame: "):

              cvars = split(lower(line[11:]), "\\")
              cvars = dict(cvars[i:i+2] for i in xrange(0, len(cvars), 2)) # Create cvar dictionary through the dict constructor.
              cvars["g_authenticity"] = int(cvars["g_authenticity"])

              say_timed_messages(jaserver, cvars)

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

                  jaserver.rcon.mbmode(("%i %s" % (current_mode, change_instructions[0]) if voting_type == "map" else
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

                  jaserver.rcon.say("^3Restricted nickname in use. Kicking player %i (^7%s^3)..."
                      % (player_id, player_name))
                  jaserver.rcon.clientkick(player_id)

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

                    jaserver.address = config.address
                    jaserver.bindaddr = config.bindaddr
                    jaserver.rcon_pwd = config.rcon_pwd

                    if not config.use_say_only:

                      svsay = status.svsay = jaserver.rcon.svsay

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

                        jaserver.rcon.say("^2[Admin] ^7%s is already present within the admin voting options." % (voting_choice))

                      else:

                        admin_choice(voting_choice)
                        svsay("^2[Admin] ^7%s was added as an admin voting option." % (voting_choice))

                    else:

                      jaserver.rcon.say("^2[Admin] ^7Admin voting is full.")

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
                  jaserver.rcon.mbmode(("%i %s" % (current_mode, change_instructions[0]) if voting_type == "map" else
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

                        jaserver.rcon.say("^2[RTV] ^7Rock the vote is unavailable.")

                      elif not status.rtv:

                        if isinstance(status.times[0], float):

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[0])))

                        else:

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is temporarily disabled.")

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

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is disabled because no map is currently available.")
                          players = dict((player_id, [timer, False, rtm_vote, None, None])
                                         for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                         in players_items()) # Reset RTV votes.
                          players_values = players.itervalues
                          players_items = players.iteritems

                        elif players[player_id][1]:

                          jaserver.rcon.say("^2[RTV] ^7%s ^7already wanted to rock the vote (%i/%i)."
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

                        jaserver.rcon.say("^2[RTV] ^7Rock the vote is unavailable.")

                      elif not status.rtv:

                        if isinstance(status.times[0], float):

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[0])))

                        else:

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is temporarily disabled.")

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

                          jaserver.rcon.say("^2[RTV] ^7Rock the vote is disabled because no map is currently available.")
                          players = dict((player_id, [timer, False, rtm_vote, None, None])
                                         for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                         in players_items()) # Reset RTV votes.
                          players_values = players.itervalues
                          players_items = players.iteritems

                        elif not players[player_id][1]:

                          jaserver.rcon.say("^2[RTV] ^7%s ^7didn't want to rock the vote yet (%i/%i)."
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

                        jaserver.rcon.say("^2[RTM] ^7Rock the mode is unavailable.")

                      elif not status.rtm:

                        if isinstance(status.times[1], float):

                          jaserver.rcon.say("^2[RTM] ^7Rock the mode is currently disabled. Time remaining: %s"
                                            % (calculate_time(current_time, status.times[1])))

                        else:

                          jaserver.rcon.say("^2[RTM] ^7Rock the mode is temporarily disabled.")

                      elif not [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]:

                        jaserver.rcon.say("^2[RTV] ^7Rock the mode is disabled because no mode is currently available.")
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                      elif players[player_id][2]:

                        jaserver.rcon.say("^2[RTM] ^7%s ^7already wanted to rock the mode (%i/%i)."
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

                        jaserver.rcon.say("^2[RTM] ^7Rock the mode is unavailable.")

                      elif not status.rtm:

                        if isinstance(status.times[1], float):

                          jaserver.rcon.say("^2[RTM] ^7Rock the mode is currently disabled. Time remaining: %s"
                              % (calculate_time(current_time, status.times[1])))

                        else:

                          jaserver.rcon.say("^2[RTM] ^7Rock the mode is temporarily disabled.")

                      elif not [gamemode for gamemode in iter(config.rtm) if gamemode != current_mode]:

                        jaserver.rcon.say("^2[RTV] ^7Rock the mode is disabled because no mode is currently available.")
                        players = dict((player_id, [timer, rtv_vote, False, nomination, None])
                                       for (player_id, (timer, rtv_vote, rtm_vote, nomination, vote_option))
                                       in players_items()) # Reset RTM votes.
                        players_values = players.itervalues
                        players_items = players.iteritems

                      elif not players[player_id][2]:

                        jaserver.rcon.say("^2[RTM] ^7%s ^7didn't want to rock the mode yet (%i/%i)."
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

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        jaserver.rcon.say("^2[Nominate] ^7Usage: %s mapname" % (original_msg))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "nominate ") or startswith(msg, "!nominate "):

                      if not config.maps:

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        nominated_map = lstrip(msg[9:])
                        compare_map = [mapname for mapname in iter(config.maps + config.secondary_maps)
                                       if lower(mapname) == nominated_map] # Compare nominated mapname against both map lists.
                        nominated_maps = [nomination
                                          for (timer, rtv_vote, rtm_vote, nomination, vote_option)
                                          in players_values() if nomination]

                        if config.nomination_type:

                          if not compare_map:

                            jaserver.rcon.say("^2[Nominate] ^7Invalid map. Please use <!>maplist or <!>search expression.")

                          elif nominated_map == current_map:

                            jaserver.rcon.say("^2[Nominate] ^7%s cannot be nominated (current map)."
                                % (compare_map[0]))

                          elif recently_played[nominated_map] > current_time:

                            jaserver.rcon.say("^2[Nominate] ^7%s cannot be nominated (recently played) (%s left)."
                                % (compare_map[0], calculate_time(current_time, recently_played[nominated_map])))

                          else:

                            nominations = count(nominated_maps, compare_map[0])

                            if players[player_id][3] == compare_map[0]:

                              jaserver.rcon.say("^2[Nominate] ^7%s ^7already nominated %s (%i nomination%s)."
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

                            jaserver.rcon.say("^2[Nominate] ^7Invalid map. Please use <!>maplist or <!>search expression.")

                          elif nominated_map == current_map:

                            jaserver.rcon.say("^2[Nominate] ^7%s cannot be nominated (current map)."
                                % (compare_map[0]))

                          elif recently_played[nominated_map] > current_time:

                            jaserver.rcon.say("^2[Nominate] ^7%s cannot be nominated (recently played) (%s left)."
                                % (compare_map[0], calculate_time(current_time, recently_played[nominated_map])))

                          elif compare_map[0] in nominated_maps:

                            jaserver.rcon.say("^2[Nominate] ^7%s cannot be nominated (already nominated)."
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

                          jaserver.rcon.say("^2[Nominate] ^7Maximum number of nominations (5) reached.")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("revoke", "!revoke"):

                      if not config.maps:

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      elif not players[player_id][3]:

                        jaserver.rcon.say("^2[Revoke] ^7%s ^7has no nominated map." %
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

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

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

                          jaserver.rcon.say("^2[Maplist] ^7No map is currently available for nomination.")

                        elif len(maplist) > 1:

                          jaserver.rcon.say("^2[Maplist] ^7Usage: %s number (Available map lists: %i)" %
                              (original_msg, len(maplist)))

                        else:

                          jaserver.rcon.say("^2[Maplist] ^7%s" % (join(", ", maplist[1])))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "maplist ") or startswith(msg, "!maplist "):

                      if not config.maps:

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

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

                          jaserver.rcon.say("^2[Maplist] ^7No map is currently available for nomination.")

                        else:

                          try:

                            maplist_number = int(msg[8:])
                            jaserver.rcon.say("^2[Maplist %i] ^7%s" % (maplist_number, join(", ", maplist[maplist_number])))

                          except (ValueError, KeyError):

                            jaserver.rcon.say("^2[Maplist] ^7Invalid map list number (Available map lists: %i)."
                                % (len(maplist)))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("search", "!search"):

                      if not config.maps:

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        jaserver.rcon.say("^2[Search] ^7Usage: %s expression" % (original_msg))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "search ") or startswith(msg, "!search "):

                      if not config.maps:

                        jaserver.rcon.say("^2[Voting] ^7Map voting is unavailable.")

                      elif config.nomination_type is None:

                        jaserver.rcon.say("^2[Nominate] ^7Map nomination is unavailable because the number of maps is less than or equal 5.")

                      else:

                        search_expression = lstrip(msg[7:])

                        if search_expression != "*": # No wildcard.
                                                     # Search for given expression.
                          maplist = [mapname for mapname in iter(config.maps + config.secondary_maps)
                                     if search_expression in lower(mapname)]

                        else:

                          maplist = list(config.maps + config.secondary_maps)

                        if not maplist:

                          jaserver.rcon.say("^2[Search] ^7No matches found for expression ''%s''."
                              % (lstrip(original_msg[7:])))

                        else:

                          sort(maplist, key=lower)
                          maplist = join(", ", maplist)

                          if (len(maplist) + 13) > MAPLIST_MAX_SIZE:

                            jaserver.rcon.say("^2[Search] ^7Result for expression ''%s'' is too long (greater than %i characters)." %
                                (lstrip(original_msg[7:]), MAPLIST_MAX_SIZE))

                          else:

                            jaserver.rcon.say("^2[Search] ^7%s" % (maplist))

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("elapsed", "!elapsed"):

                      jaserver.rcon.say("^2[Elapsed] ^7Usage: %s map/mode" % (original_msg))
                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "elapsed ") or startswith(msg, "!elapsed "):

                      elapse = lstrip(msg[8:])

                      try:

                        jaserver.rcon.say("^2[Elapsed] ^7Time elapsed for the current %s: %s%s" %
                            (elapse, calculate_time(gameinfo[elapse][0], current_time),
                             (" (%i extension%s)" % (gameinfo[elapse][1],
                                                     ("" if gameinfo[elapse][1] == 1 else "s"))
                              if gameinfo[elapse][1] else "")))

                      except KeyError:

                        jaserver.rcon.say("^2[Elapsed] ^7Incorrect format (map/mode).")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("nextgame", "!nextgame"):

                      jaserver.rcon.say("^2[Nextgame] ^7No next game is set.")
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

                      jaserver.rcon.say("^2[Elapsed] ^7Usage: %s map/mode" % (original_msg))
                      players[player_id][0] = (current_time + config.flood_protection)

                    elif startswith(msg, "elapsed ") or startswith(msg, "!elapsed "):

                      elapse = lstrip(msg[8:])

                      try:

                        jaserver.rcon.say("^2[Elapsed] ^7Time elapsed for the current %s: %s%s" %
                            (elapse, calculate_time(gameinfo[elapse][0], current_time),
                             (" (%i extension%s)" % (gameinfo[elapse][1],
                                                     ("" if gameinfo[elapse][1] == 1 else "s"))
                              if gameinfo[elapse][1] else "")))

                      except KeyError:

                        jaserver.rcon.say("^2[Elapsed] ^7Incorrect format (map/mode).")

                      players[player_id][0] = (current_time + config.flood_protection)

                    elif msg in ("nextgame", "!nextgame"):

                      jaserver.rcon.say("^2[Nextgame] ^7Next %s: %s" %
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
                jaserver.rcon.mbmode(("%i %s" % (current_mode, votes[1][2]) if voting_type == "map" else votes[1][2])) # Switch to new map/mode.
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
                      jaserver.rcon.mbmode(("%i %s" % (current_mode, votes[most_voted_options][2]) if voting_type == "map" else
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
