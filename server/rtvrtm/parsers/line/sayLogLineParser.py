from logLineParser import LogLineParser, LogLine
from ...managers.pushNotificationManager import PushNotificationManager
from ...jaserver import JAServer
from ...utility import remove_color


class SayLogLine():

    def __init__(self, log_line):
        assert isinstance(log_line, LogLine)
        self.parts = log_line.data.split(":", 2)
        self.player_id = int(self.parts[0])
        name_and_message = self.parts[2].split('"', 1)
        self.message = remove_color(name_and_message[1][:-1]).strip().lower()


class SayLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver
        # TODO: Read from configuration file?
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

    def __send_push_notification_if_needed(self, say_line):
        assert isinstance(say_line, SayLogLine)
        if any(watched_word in say_line.message for watched_word in self.watched_words):
            player = self.jaserver.players.get(say_line.player_id, None)
            if player is None:
                return
            push_message = "%s (%s): %s" % (player.clean_name, player.ip, say_line.message)
            last_killer = player.kill_info.last_killer
            if last_killer is not None:
                push_message += "\nLast killer: %s (%s)" % (last_killer.clean_name, last_killer.ip)
            PushNotificationManager.send(push_message)

