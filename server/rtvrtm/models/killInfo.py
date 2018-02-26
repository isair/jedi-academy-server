from .kill import Kill


class KillInfo:
    LAMER_STATUS_NONE = 0
    LAMER_STATUS_SUSPECTED = 1
    LAMER_STATUS_KICKABLE = 2

    double_kill_delay = 3
    double_kill_decay_delay = 300
    double_kill_count_tolerance = 2  # Can't change at the moment due to how baiting detection works.

    latest_kills_timeframe = 20
    latest_kills_count_tolerance = 4

    def __init__(self):
        self.lamer_status = KillInfo.LAMER_STATUS_NONE
        self.waiting_for_baiting_proof_since = 0
        self.is_baited = False
        self.baiter_ids = []

        self.double_kills = []
        self.double_kill_tracker = []
        self.double_kill_victim_kill_counts = {}

        self.latest_kills = []

        self.unique_kill_ids = set()

        self.last_killer = None

    def add_kill(self, kill, player_count):
        """Logs given kill and updates lamer_status, is_baited, and baiters."""
        assert isinstance(kill, Kill)
        assert isinstance(player_count, int)
        if kill.victim_id >= 40 or kill.victim_id == kill.killer_id:
            # Only log if another player is killed.
            return
        self.__update_unique_kills(kill)
        self.__update_double_kills(kill)
        self.__update_latest_kills(kill)
        self.__update_status(player_count)

    def __update_unique_kills(self, kill):
        self.unique_kill_ids.add(kill.victim_id)

    def __update_double_kills(self, kill):
        assert isinstance(kill, Kill)
        if len(self.double_kill_tracker) == 0:
            self.double_kill_tracker.append(kill)
        else:
            time_since_last_kill = kill.time - self.double_kill_tracker[0].time
            if KillInfo.double_kill_delay >= time_since_last_kill >= 0:
                self.double_kill_tracker.append(kill)
                self.double_kills.append(self.double_kill_tracker)
                self.double_kill_tracker = []
            elif time_since_last_kill >= 0:
                self.double_kill_tracker[0] = kill
            else:
                self.double_kill_tracker[0] = kill
                self.double_kills = []

    def __decay_double_kills(self):
        """Needs latest_kills to be up-to-date."""
        if len(self.latest_kills) == 0:
            return
        new_double_kills = []
        latest_kill = self.latest_kills[-1]
        for double_kill in self.double_kills:
            time_difference = latest_kill.time - double_kill[1].time
            if KillInfo.double_kill_decay_delay >= time_difference >= 0:
                new_double_kills.append(double_kill)
        self.double_kills = new_double_kills

    def __update_latest_kills(self, kill):
        assert isinstance(kill, Kill)
        new_latest_kills = []
        for older_kill in self.latest_kills:
            if older_kill.time >= kill.time - KillInfo.latest_kills_timeframe and older_kill <= kill.time:
                new_latest_kills.append(older_kill)
        self.latest_kills = new_latest_kills
        self.latest_kills.append(kill)

    def __update_status(self, player_count):
        assert isinstance(player_count, int)
        # Decay double kills only if not waiting for baiting proof.
        if self.waiting_for_baiting_proof_since == 0:
            self.__decay_double_kills()
        # Store counts.
        double_kills_count = len(self.double_kills)
        latest_kills_count = len(self.latest_kills)
        # Check for baiting first.
        if self.waiting_for_baiting_proof_since == 0 and double_kills_count == 2:
            for first_kill in self.double_kills[0]:
                for second_kill in self.double_kills[1]:
                    if first_kill.victim_id == second_kill.victim_id and player_count > 5:
                        # Could be a case of baiting. Return so that double kills can accumulate to 3.
                        self.waiting_for_baiting_proof_since = int(self.latest_kills[-1].time)
                        self.latest_kills = []  # If not baited, they'll be kicked because of double kills. So use latest_kills for tracking kills after double kills.
                        print("[KillInfo] %d could have been baited by %d." % (first_kill.killer_id,
                                                                               first_kill.victim_id))
                        return
        elif self.waiting_for_baiting_proof_since > 0 and int(
                self.latest_kills[-1].time) - self.waiting_for_baiting_proof_since >= 180:
            # If they haven't done a double kill since three minutes have passed, let go of the
            # past double kill record as it is ambiguous. Then continue judging as usual.
            self.double_kills = [self.double_kills[2]]
            double_kills_count = 1
            self.waiting_for_baiting_proof_since = 0
        elif self.waiting_for_baiting_proof_since > 0 and latest_kills_count >= KillInfo.latest_kills_count_tolerance:
            # If while we were waiting for proof, they went on a killing rampage that
            # doesn't include double kills, judge as usual.
            # TODO: May be wise to check who these killing rampages included and what the server population was.
            self.waiting_for_baiting_proof_since = 0
        elif self.waiting_for_baiting_proof_since > 0 and double_kills_count == 3:
            # Another double kill has happened since we were waiting for clarification on what happened in the first 2.
            # We should be able to determine if it was a baiting case by seeing if a player was involved in all three.
            for first_kill in self.double_kills[0]:
                for third_kill in self.double_kills[2]:
                    if first_kill.victim_id == third_kill.victim_id:
                        self.lamer_status = KillInfo.LAMER_STATUS_NONE
                        self.is_baited = True
                        self.waiting_for_baiting_proof_since = 0
                        self.baiter_ids.append(first_kill)
            if self.is_baited:
                return
        elif self.waiting_for_baiting_proof_since > 0:
            return
        # If there are no indications of a baiting case having happened, update status as usual.
        if latest_kills_count >= KillInfo.latest_kills_count_tolerance:
            self.lamer_status = KillInfo.LAMER_STATUS_KICKABLE
        elif double_kills_count >= KillInfo.double_kill_count_tolerance:
            self.lamer_status = KillInfo.LAMER_STATUS_KICKABLE
        elif double_kills_count == 1:
            self.lamer_status = KillInfo.LAMER_STATUS_SUSPECTED
        else:
            self.lamer_status = KillInfo.LAMER_STATUS_NONE

# TODO: Reputable kills system.
# In a baiting scenario we can check the reputable kills of a victim to see if they are a baiter or not?

# equipped weapon at time of kill would be helpful, and what state it is in.

# assumptions:
# if two people are baiting, they are going to be killed fairly closely to each other and trigger a double kill
# in contrast if two people are being lamed, they will put up a fight and not get killed 3 times in a row in a double kill
# if one person is baiting, they can't get killed 4 times in 20 seconds

# baiting:
# -- two double kills
# ab ab ab    - ab baiters, even if there are 3 people on the server it should be almost impossible to do for a lamer
# ab ac ad    - a baiter, should be almost impossible to do 3 times if killer is hunting a
# ab ab a b   - ab baiters?
# ab ac a d   - a baiter?
# -- one double kill within a spree NOT COVERED YET! TODO: COVER IT!
# a ab c - a baiter?
# -- one double kill
# ab, a b a b  - ab baiters?
# ab, a c a d  - a baiter?
# ab, a c b d  - ab baiters?
# -- no double kills - problems with detecting actual lamers! so far double kills have been being abused though
# a b a b a b - ab baiters? if playercount > 3
# a b a b a c - a baiter?
