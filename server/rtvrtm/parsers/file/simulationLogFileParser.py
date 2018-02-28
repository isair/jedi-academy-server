from __future__ import with_statement

from logFileParser import LogFileParser
from ..line.clientConnectLogLineParser import ClientConnectLogLineParser
from ..line.clientDisconnectLogLineParser import ClientDisconnectLogLineParser
from ..line.clientUserinfoChangedLogLineParser import ClientUserinfoChangedLogLineParser
from ..line.initGameLogLineParser import InitGameLogLineParser
from ..line.killLogLineParser import KillLogLineParser
from ..line.sayLogLineParser import SayLogLineParser
from ...jaserver import DummyJAServer
from ...utility import fix_line


class SimulationLogFileParser(LogFileParser):

    def __init__(self):
        LogFileParser.__init__(self)
        self.jaserver = DummyJAServer(use_say_only=False)

    def parse(self, log):
        assert isinstance(log, file)
        client_connect_log_line_parser = ClientConnectLogLineParser(self.jaserver)
        client_userinfo_changed_log_line_parser = ClientUserinfoChangedLogLineParser(self.jaserver)
        say_log_line_parser = SayLogLineParser(self.jaserver, is_simulation=True)
        kill_log_line_parser = KillLogLineParser(self.jaserver)
        client_disconnect_log_line_parser = ClientDisconnectLogLineParser(self.jaserver)
        init_game_log_line_parser = InitGameLogLineParser(self.jaserver)
        for line in log:
            line = fix_line(line)
            if InitGameLogLineParser.can_parse(line):
                init_game_log_line_parser.parse(line)
            elif ClientConnectLogLineParser.can_parse(line):
                client_connect_log_line_parser.parse(line)
            elif ClientUserinfoChangedLogLineParser.can_parse(line):
                client_userinfo_changed_log_line_parser.parse(line)
            elif SayLogLineParser.can_parse(line):
                say_log_line_parser.parse(line)
            elif KillLogLineParser.can_parse(line):
                kill_log_line_parser.parse(line)
            elif ClientDisconnectLogLineParser.can_parse(line):
                client_disconnect_log_line_parser.parse(line)
