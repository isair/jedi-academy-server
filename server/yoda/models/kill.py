class Kill:

    def __init__(self, time, killer_id, victim_id):
        assert isinstance(time, int)
        assert isinstance(killer_id, int)
        assert isinstance(victim_id, int)
        self.time = time
        self.killer_id = killer_id
        self.victim_id = victim_id
