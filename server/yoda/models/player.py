from __future__ import with_statement

from ..models.killInfo import KillInfo
from ..models.sayInfo import SayInfo
from ..utility import remove_color


class Player(object):
    """Represents an in-game player."""

    def __init__(self, identifier, ip):
        assert isinstance(identifier, int)
        assert isinstance(ip, str)

        self.identifier = identifier
        self.ip = ip
        self.name = ""
        self.clean_name = ""
        self.name_change_time = 0

        self.kill_info = KillInfo()
        self.last_killer = None

        self.say_info = SayInfo()

        self.timer = 0
        self.rtv = False
        self.rtm = False
        self.nomination = None
        self.vote_option = None

    def change_name(self, new_name, time):
        assert isinstance(new_name, str)
        assert isinstance(time, int)
        previous_clean_name = self.clean_name
        self.name = new_name
        self.clean_name = remove_color(self.name).lower().strip()
        if self.clean_name != previous_clean_name:
            self.name_change_time = time

    def force_rtv(self, should_enable):
        assert isinstance(should_enable, bool)
        self.rtv = should_enable
        self.vote_option = None

    def reset_rtv(self):
        self.force_rtv(False)
        self.nomination = None

    def force_rtm(self, should_enable):
        assert isinstance(should_enable, bool)
        self.rtm = should_enable
        self.vote_option = None

    def reset_rtm(self):
        self.force_rtm(False)
        self.nomination = None

    def reset_voting_options(self, should_reset_timer=False):
        assert isinstance(should_reset_timer, bool)
        if should_reset_timer:
            self.timer = 0
        self.reset_rtv()
        self.reset_rtm()
