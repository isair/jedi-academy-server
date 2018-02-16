from .kill import Kill


class KillInfo:
    chain_kill_delay = 3
    chain_kill_decay_delay = 300

    def __init__(self):
        self.lamer_suspicion_score = 0
        self.double_kills = []
        self.double_kill_tracker = []
        self.latest_kills = []
        self.unique_kill_ids = set()

    def add_kill(self, kill):
        """Logs given kill and returns a suspicion score. 2 should be kickable, 3 and above should be bannable."""
        assert isinstance(kill, Kill)
        if kill.victim_id >= 50 or kill.victim_id == kill.killer_id:
            # Only log if another player is killed.
            return self.lamer_suspicion_score
        self.unique_kill_ids.add(kill.victim_id)
        double_kill_count = self.update_double_kills(kill)
        self.lamer_suspicion_score = max(double_kill_count, self.update_latest_kills(kill))
        return self.lamer_suspicion_score

    def update_double_kills(self, kill):
        """
        Updates double kills and returns a suspicion score which is the same as the double kill count. Double kills
        decay in a certain amount of time.
        """
        assert isinstance(kill, Kill)
        bonus = 0
        if len(self.double_kill_tracker) == 0:
            self.double_kill_tracker.append(kill)
        else:
            time_since_last_kill = kill.time - self.double_kill_tracker[0].time
            if time_since_last_kill <= KillInfo.chain_kill_delay and time_since_last_kill >= 0:
                self.double_kill_tracker.append(kill)
                self.double_kills.append(self.double_kill_tracker)
                self.double_kill_tracker = []
                # Decay mechanic.
                new_double_kills = []
                for double_kill in self.double_kills:
                    time_difference = kill.time - double_kill[1].time
                    if time_difference <= KillInfo.chain_kill_decay_delay and time_difference >= 0:
                        new_double_kills.append(double_kill)
                self.double_kills = new_double_kills
            elif time_since_last_kill >= 0:
                self.double_kill_tracker[0] = kill
            else:
                self.double_kill_tracker[0] = kill
                self.double_kills = []
        return len(self.double_kills) + bonus

    def update_latest_kills(self, kill):
        """Updates last four kills and returns a suspicion score based on the time intervals of these kills."""
        assert isinstance(kill, Kill)
        # Check for 4 or more kills within 20.
        new_latest_kills = []
        for older_kill in self.latest_kills:
            if older_kill.time >= kill.time - 20 and older_kill <= kill.time:
                new_latest_kills.append(older_kill)
        self.latest_kills = new_latest_kills
        self.latest_kills.append(kill)
        if len(self.latest_kills) >= 4:
            return 3
        return 0
        # TODO
        # self.latest_kills.append(kill)
        # Let kills accumulate.
        # if kill.time - self.latest_kills[0].time < 20:
        #    return

        # .    ..|.     .|.   .   .|
        # ...                     .|
        # . . . .|

        # also check killing methods to see if a user's kills are not by saber usually.

        # killstreak_4in20 = []
        # killstreak_3in15 = []
        # killstreak_3in10 = []
        # killstreak_2in2 = []
        # for kill in kills:
        #     # Check for 4 or more kills within 20.
        #     new_killstreak_4in20 = []
        #     for olderKill in killstreak_4in20:
        #         if olderKill.time >= kill.time - 20 and olderKill <= kill.time:
        #             new_killstreak_4in20.append(olderKill)
        #     killstreak_4in20 = new_killstreak_4in20
        #     killstreak_4in20.append(kill)
        #     if len(killstreak_4in20) >= 4:
        #         self.jaserver.ban_manager.ban(player, " for laming.", True)
        #     # Check for 3 kills within 15 seconds.
        #     new_killstreak_3in15 = []
        #     for olderKill in killstreak_3in15:
        #         if olderKill.time >= kill.time - 15 and olderKill <= kill.time:
        #             new_killstreak_3in15.append(olderKill)
        #     killstreak_3in15 = new_killstreak_3in15
        #     killstreak_3in15.append(kill)
        #     if len(killstreak_3in15) == 3:
        #         self.jaserver.ban_manager.kick(player, " for possible laming.", True)
        #     # Check for 2 kills within 2 seconds and this occuring >= 2 times.
        #     # Check for 3 kills within 10 seconds and a report by one of the victims.
        #     # TODO
        #     # Check for 2 kills within 2 seconds and a report by one of the victims.
        #     # TODO
        #     # TODO: Ganking protection.
