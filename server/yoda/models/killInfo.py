from yoda.models.kill import Kill


class KillInfo:
    # region Types

    class Status:
        NONE, SUSPECTED_LAMER, POSSIBLE_LAMER, BAITED = range(4)

        def __init__(self):
            pass

    # endregion

    # region Class Properties

    double_kill_delay = 3
    double_kill_decay_delay = 300
    double_kill_count_tolerance = 2  # Shouldn't change at the moment due to how baiting detection works.

    latest_kills_time_frame = 20
    latest_kills_count_tolerance = 4

    # endregion

    # region Initialization

    def __init__(self):
        self.status = KillInfo.Status.NONE
        self.baiter_ids = set()

        self.__waiting_for_baiting_proof_since = 0

        self.__double_kills = []
        self.__double_kill_tracker = []

        self.__latest_kills = []

        self.__unique_kill_ids = set()

    # endregion

    # region Public API

    def add_kill(self, kill, player_count):
        """Logs given kill then updates status and baiter_ids."""
        assert isinstance(kill, Kill)
        assert isinstance(player_count, int)
        if kill.victim_id >= 40 or kill.victim_id == kill.killer_id:
            # Only log if another player is killed.
            return
        self.__update_unique_kills(kill)
        self.__update_double_kills(kill)
        self.__update_latest_kills(kill)
        self.__update_status(player_count)

    def get_latest_kills(self):
        return self.__latest_kills[:]

    def reset(self, shallow=True):
        assert isinstance(shallow, bool)
        self.status = KillInfo.Status.NONE
        self.baiter_ids = set()
        self.__waiting_for_baiting_proof_since = 0
        self.__double_kills = []
        self.__latest_kills = []
        if not shallow:
            self.__double_kill_tracker = []
            self.__unique_kill_ids = set()

    # endregion

    # region Private Methods

    def __update_unique_kills(self, kill):
        assert isinstance(kill, Kill)
        self.__unique_kill_ids.add(kill.victim_id)

    def __update_double_kills(self, kill):
        assert isinstance(kill, Kill)
        if len(self.__double_kill_tracker) == 0:
            self.__double_kill_tracker.append(kill)
        else:
            time_since_last_kill = kill.time - self.__double_kill_tracker[0].time
            if KillInfo.double_kill_delay >= time_since_last_kill >= 0:
                self.__double_kill_tracker.append(kill)
                self.__double_kills.append(self.__double_kill_tracker)
                self.__double_kill_tracker = []
            elif time_since_last_kill >= 0:
                self.__double_kill_tracker[0] = kill
            else:
                self.__double_kill_tracker[0] = kill
                self.__double_kills = []

    def __decay_double_kills(self):
        """Needs latest_kills to be up-to-date."""
        if len(self.__latest_kills) == 0:
            return
        latest_kill = self.__latest_kills[-1]
        self.__double_kills = filter(lambda dk: KillInfo.double_kill_decay_delay >= latest_kill.time - dk[1].time >= 0,
                                     self.__double_kills)

    def __update_latest_kills(self, kill):
        assert isinstance(kill, Kill)
        self.__latest_kills = filter(lambda k: kill.time - KillInfo.latest_kills_time_frame <= k.time <= kill.time,
                                     self.__latest_kills)
        self.__latest_kills.append(kill)

    def __update_status(self, player_count):
        assert isinstance(player_count, int)
        # Decay double kills only if not waiting for baiting proof.
        if self.__waiting_for_baiting_proof_since == 0:
            self.__decay_double_kills()
        # Store counts.
        double_kills_count = len(self.__double_kills)
        latest_kills_count = len(self.__latest_kills)
        # Check for baiting first.
        if self.__waiting_for_baiting_proof_since == 0:
            # Check if we need to wait for baiting proof, or an immediate situation has happened where we don't need
            # further proof.
            if player_count <= 5:
                # Small player counts mess with our probabilistic approach.
                pass
            elif double_kills_count == 2:
                # Check for two double kills with reoccurring victims.
                for first_kill in self.__double_kills[0]:
                    for second_kill in self.__double_kills[1]:
                        if first_kill.victim_id == second_kill.victim_id:
                            # Could be a case of baiting. Wait so that double kills can accumulate to 3, or a
                            # killing streak happens with the suspected baiters appearing a lot in it.
                            self.__waiting_for_baiting_proof_since = int(self.__latest_kills[-1].time)
                            self.__latest_kills = []
                            return
            elif double_kills_count == 1 and latest_kills_count >= KillInfo.latest_kills_count_tolerance:
                # Check if someone in our double kill also appeared in the spree outside of the double kill.
                for kill in self.__double_kills[0]:
                    if len(filter(lambda vid: vid == kill.victim_id,
                                  map(lambda k: k.victim_id, self.__latest_kills))) > 1:
                        self.status = KillInfo.Status.BAITED
                        self.baiter_ids.add(kill.victim_id)
                if self.status == KillInfo.Status.BAITED:
                    return
        elif self.__waiting_for_baiting_proof_since > 0:
            # Check for further proof on baiting having happened or not, or give up if it is too ambiguous.
            if int(self.__latest_kills[-1].time) - self.__waiting_for_baiting_proof_since >= 180:
                # If they haven't done a double kill since three minutes have passed, let go of the
                # past double kill record as it is ambiguous. Then continue judging as usual.
                self.__double_kills = [self.__double_kills[2]]
                double_kills_count = 1
                self.__waiting_for_baiting_proof_since = 0
            elif latest_kills_count >= KillInfo.latest_kills_count_tolerance:
                # If while we were waiting for proof, they went on a killing rampage then judge as usual unless we see
                # enough occurrences from the past double kills.
                self.__waiting_for_baiting_proof_since = 0
                repeat_count = 0
                for first_kill in self.__double_kills[0]:
                    for second_kill in self.__double_kills[1]:
                        if first_kill.victim_id == second_kill.victim_id:
                            continue
                        for kill in self.__latest_kills:
                            repeating_id = None
                            if first_kill.victim_id == kill.victim_id:
                                repeating_id = first_kill.victim_id
                            elif second_kill.victim_id == kill.victim_id:
                                repeating_id = second_kill.victim_id
                            if repeating_id is not None:
                                repeat_count += 1
                                self.baiter_ids.add(repeating_id)
                if repeat_count > 1:
                    self.status = KillInfo.Status.BAITED
                    return
            elif double_kills_count == 3:
                # Another double kill has happened since we were waiting for clarification on what happened in the
                # first 2. We should be able to determine if it was a baiting case by seeing if a player was involved
                # in all three.
                for first_kill in self.__double_kills[0]:
                    for third_kill in self.__double_kills[2]:
                        if first_kill.victim_id == third_kill.victim_id:
                            self.status = KillInfo.Status.BAITED
                            self.__waiting_for_baiting_proof_since = 0
                            self.baiter_ids.add(first_kill)
                if self.status == KillInfo.Status.BAITED:
                    return
            else:
                return
        # If there are no indications of a baiting case having happened, update status as usual.
        if latest_kills_count >= KillInfo.latest_kills_count_tolerance:
            self.status = KillInfo.Status.POSSIBLE_LAMER
        elif double_kills_count >= KillInfo.double_kill_count_tolerance:
            self.status = KillInfo.Status.POSSIBLE_LAMER
        elif double_kills_count == 1:
            self.status = KillInfo.Status.SUSPECTED_LAMER
        else:
            self.status = KillInfo.Status.NONE
        # TODO: Check victim ids against reported ids. Should preferably be implemented along with reputable kills.

    # endregion

# TODO: Reputable kills system.
# In a baiting scenario we can check the reputable kills of a victim to see if they are a baiter or not?

# equipped weapon at time of kill would be helpful, and what state it is in (active/inactive).

# assumptions:
# if two people are baiting, they are going to be killed fairly closely to each other and trigger a double kill
# if two people are being lamed, they will put up a fight and not get killed 3 times in a row in a double kill
# if one person is baiting, it's very unlikely for them to get killed 4 times in 20 seconds

# blackboard:
# -- two double kills
# ab ab ab    - ab baiters, even if there are 3 people on the server it should be almost impossible to do for a lamer
# ab ac ad    - a baiter, should be almost impossible to do 3 times if killer is hunting a
# ab ab a b   - ab baiters?
# ab ac a d   - a baiter?
# -- one double kill within a spree
# a ab c - a baiter?
# -- one double kill then a spree
# ab, a b a b  - ab baiters?
# ab, a c a d  - a baiter?
# ab, a c b d  - ab baiters?
# -- no double kills - problems with detecting actual lamers! so far double kills have been being abused though
# a b a b a b - ab baiters?
# a b a b a c - a baiter?
