from __future__ import with_statement

from datetime import datetime
from time import time

SLEEP_INTERVAL = 0.075


class Features(object):
    """Feature (RTV/RTM) handler and container class."""

    def __init__(self, jaserver):
        self.rtv = self.rtm = False
        self.times = [0, 0]
        self.jaserver = jaserver

    def check(self):
        current_time = time()
        if not self.rtv and not self.rtm:
            if self.times[0] <= current_time and self.times[1] <= current_time:
                self._enable_all()
                return 0
            elif self.times[0] <= current_time:
                self._enable_rtv()
                return 0
            elif self.times[1] <= current_time:
                self._enable_rtm()
                return 0
        elif not self.rtv:
            if self.times[0] <= current_time:
                self._enable_rtv()
                return 0
        elif not self.rtm and self.times[1] <= current_time:
            self._enable_rtm()
            return 0
        return SLEEP_INTERVAL

    def _enable_rtv(self):
        self.rtv = True
        self.jaserver.svsay("^2[Status] ^7RTV is now enabled.")
        print("CONSOLE: (%s) [Status] RTV is now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

    def _enable_rtm(self):
        self.rtm = True
        self.jaserver.svsay("^2[Status] ^7RTM is now enabled.")
        print("CONSOLE: (%s) [Status] RTM is now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

    def _enable_all(self):
        self.rtv = self.rtm = True
        self.jaserver.svsay("^2[Status] ^7RTV and RTM are now enabled.")
        print("CONSOLE: (%s) [Status] RTV and RTM are now enabled." % (datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
