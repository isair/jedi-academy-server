from __future__ import with_statement

from ...models.logLine import LogLine


class LogLineParser:

    def __init__(self):
        pass

    @classmethod
    def can_parse(cls, line):
        assert isinstance(line, str)
        try:
            return cls._can_parse_line(LogLine(line))
        except Exception as e:
            print(repr(e))
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
