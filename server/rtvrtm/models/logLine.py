class LogLine:

    def __init__(self, line):
        assert isinstance(line, str)
        time_string = line[0:7].strip()
        minutes_and_seconds = time_string.split(":")
        self.time = int(minutes_and_seconds[0]) * 60 + int(minutes_and_seconds[1])
        self.data = line[7:-1]
