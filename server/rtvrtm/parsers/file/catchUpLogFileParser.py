from __future__ import with_statement

from logFileParser import LogFileParser
from ..line.clientConnectLogLineParser import ClientConnectLogLineParser
from ..line.clientDisconnectLogLineParser import ClientDisconnectLogLineParser
from ..line.clientUserinfoChangedLogLineParser import ClientUserinfoChangedLogLineParser
from ..line.initGameLogLineParser import InitGameLogLineParser
from ..line.serverStartLogLineParser import ServerStartLogLineParser
from ...jaserver import JAServer
from ...utility import fix_line


class CatchUpLogFileParser(LogFileParser):

    def __init__(self, jaserver):
        LogFileParser.__init__(self)
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver

    def parse(self, log):
        """Parses every line of the log file, updating jaserver. Returns whether a start line was found or not."""
        assert isinstance(log, file)
        start_line_exists = False
        server_start_log_line_parser = ServerStartLogLineParser(self.jaserver)
        client_connect_log_line_parser = ClientConnectLogLineParser(self.jaserver)
        client_userinfo_changed_log_line_parser = ClientUserinfoChangedLogLineParser(self.jaserver)
        client_disconnect_log_line_parser = ClientDisconnectLogLineParser(self.jaserver)
        init_game_log_line_parser = InitGameLogLineParser(self.jaserver)
        for line in log:
            if not line.endswith("\n"):
                continue
            line = fix_line(line)
            if ServerStartLogLineParser.can_parse(line):
                server_start_log_line_parser.parse(line)
                start_line_exists = True
            elif ClientConnectLogLineParser.can_parse(line):
                client_connect_log_line_parser.parse(line)
            elif ClientUserinfoChangedLogLineParser.can_parse(line):
                client_userinfo_changed_log_line_parser.parse(line)
            elif ClientDisconnectLogLineParser.can_parse(line):
                client_disconnect_log_line_parser.parse(line)
            elif InitGameLogLineParser.can_parse(line):
                init_game_log_line_parser.parse(line)
        return start_line_exists
