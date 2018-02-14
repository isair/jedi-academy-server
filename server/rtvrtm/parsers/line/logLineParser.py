from __future__ import with_statement


class LogLine:

    def __init__(self, line):
        assert isinstance(line, str)
        timeString = line[0:7].strip()
        minutesAndSeconds = timeString.split(":")
        self.time = int(minutesAndSeconds[0]) * 60 + int(minutesAndSeconds[1])
        self.data = line[7:-1]


class LogLineParser:

    @classmethod
    def can_parse(cls, line):
        assert isinstance(line, str)
        try:
            return cls._can_parse_line(LogLine(line))
        except Exception as e:
            print(e)
            return False

    @classmethod
    def _can_parse_line(cls, line):
        raise NotImplementedError

    def parse(self, line):
        assert isinstance(line, str)
        if not self.can_parse(line):
            raise Exception("")  # TODO: Our own exception
        self._parse_compliant_line(LogLine(line))

    def _parse_compliant_line(self, line):
        raise NotImplementedError
