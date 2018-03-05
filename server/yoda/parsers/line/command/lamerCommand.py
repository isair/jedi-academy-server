from __future__ import with_statement

from ....parsers.line.logLineParser import LogLineParser
from ....utility import remove_color


class LamerCommand(LogLineParser):

    @classmethod
    def _can_parse_ascii_line(cls, line):
        return line.startswith("!lamer") or line.startswith("lamer")

    @classmethod
    def _parse_compliant_line(cls, line):
        lamer_name = remove_color(line[6:].strip().lower())
        # TODO
