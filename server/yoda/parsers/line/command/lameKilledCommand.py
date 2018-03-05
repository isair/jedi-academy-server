from __future__ import with_statement

from ....parsers.line.logLineParser import LogLineParser


class LameKilledCommand(LogLineParser):

    @classmethod
    def can_parse(cls, line):
        return line.startswith("!lamekilled") or line.startswith("lamekilled")

    @classmethod
    def _parse_compliant_line(cls, line):
        pass
