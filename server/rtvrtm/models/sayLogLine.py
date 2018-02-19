from ..models.logLine import LogLine
from ..utility import remove_color


class SayLogLine:

    def __init__(self, log_line):
        assert isinstance(log_line, LogLine)
        parts = log_line.data.split(":", 2)
        self.player_id = int(parts[0])
        name_and_message = parts[2].split('"', 1)
        self.message = remove_color(name_and_message[1][:-1]).strip().lower()
