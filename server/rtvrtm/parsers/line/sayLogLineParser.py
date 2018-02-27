from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...managers.pushNotificationManager import PushNotificationManager
from ...models.logLine import LogLine
from ...models.sayLogLine import SayLogLine


class SayLogLineParser(LogLineParser):

    def __init__(self, jaserver, is_simulation=False):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver
        self.is_simulation = is_simulation
        # TODO: Read from a configuration file.
        self.watched_words = ["lame", "lamin", "ban", "admin", "glitch"]

    @classmethod
    def _can_parse_line(cls, line):
        assert isinstance(line, LogLine)
        line_after_id = line.data[3:].strip()
        return line_after_id.startswith("say:") or line_after_id.startswith("teamsay:")

    def _parse_compliant_line(self, line):
        assert isinstance(line, LogLine)
        say_line = SayLogLine(line)
        self.__send_push_notification_if_needed(say_line)
        if self.__handle_spam(say_line):
            return
        # TODO: Move parsing of all say commands here.

    def __handle_spam(self, say_line):
        assert isinstance(say_line, SayLogLine)
        player = self.jaserver.players.get(say_line.player_id, None)
        if player is not None:
            player.say_info.add_message(say_line.message)
            return self.jaserver.judgment_manager.check_say_info(player)
        return False

    def __send_push_notification_if_needed(self, say_line):
        assert isinstance(say_line, SayLogLine)
        if any(watched_word in say_line.message for watched_word in self.watched_words):
            player = self.jaserver.players.get(say_line.player_id, None)
            if player is None:
                return
            push_message = "[%s] %s (%d|%s): %s" % (self.jaserver.gamemode,
                                                    player.clean_name,
                                                    player.identifier,
                                                    player.ip,
                                                    say_line.message)
            last_killer = player.kill_info.last_killer
            if last_killer is not None:
                push_message += "\nLast killer: %s (%d|%s)" % (last_killer.clean_name,
                                                               last_killer.identifier,
                                                               last_killer.ip)
            if not self.is_simulation:
                PushNotificationManager.send(push_message)
