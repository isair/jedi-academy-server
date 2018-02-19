from logLineParser import LogLineParser
from ...jaserver import JAServer
from ...managers.pushNotificationManager import PushNotificationManager
from ...models.logLine import LogLine
from ...models.sayLogLine import SayLogLine


class SayLogLineParser(LogLineParser):

    def __init__(self, jaserver):
        LogLineParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver
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
        if self.jaserver.gamemode != "duel":
            # Since spamming is not an issue in duel servers, don't bother on one.
            player = self.jaserver.players.get(say_line.player_id, None)
            if player is not None:
                player.say_info.add_message(say_line.message)
                self.jaserver.ban_manager.check_say(player)
        # TODO: Move parsing of all say commands here.

    def __send_push_notification_if_needed(self, say_line):
        assert isinstance(say_line, SayLogLine)
        if any(watched_word in say_line.message for watched_word in self.watched_words):
            player = self.jaserver.players.get(say_line.player_id, None)
            if player is None:
                return
            push_message = "[%s] %s (%d|%s): %s" % (self.jaserver.gamemode,
                                                    player.clean_name,
                                                    player.id,
                                                    player.ip,
                                                    say_line.message)
            last_killer = player.kill_info.last_killer
            if last_killer is not None:
                push_message += "\nLast killer: %s (%s)" % (last_killer.clean_name, last_killer.ip)
            PushNotificationManager.send(push_message)
