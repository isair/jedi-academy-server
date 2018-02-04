from __future__ import with_statement


class Player(object):
    """Represents an in-game player."""

    def __init__(self, id, ip):
        self.id = id
        self.ip = ip
        self.name = ""

        self.timer = 0
        self.rtv = False
        self.rtm = False
        self.nomination = None
        self.vote_option = None

    def force_rtv(self, should_enable):
        self.rtv = should_enable
        self.vote_option = None

    def reset_rtv(self):
        self.force_rtv(False)
        self.nomination = None

    def force_rtm(self, should_enable):
        self.rtm = should_enable
        self.vote_option = None

    def reset_rtm(self):
        self.force_rtm(False)
        self.nomination = None

    def reset_voting_options(self, should_reset_timer=False):
        if should_reset_timer:
            self.timer = 0
        self.reset_rtv()
        self.reset_rtm()
