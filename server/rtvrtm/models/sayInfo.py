import time


class SayInfo:
    same_messages_repeat_limit = 6
    same_messages_decay_duration = 60
    same_message_tolerant_words = {'lol', 'gf', 'gf!', 'gg', 'gz', 'good fight'}
    same_message_tolerant_word_limit_multiplier = 1.5
    latest_messages_limit = 15
    latest_messages_decay_duration = 60

    def __init__(self):
        self.is_spamming = False
        self.same_messages = {}
        self.latest_message_timestamps = []
        self.last_message = ""

    def reset(self):
        self.is_spamming = False
        self.same_messages = {}
        self.latest_message_timestamps = []

    def add_message(self, message):
        """Logs given message said by user and returns if the user is spamming or not."""
        assert isinstance(message, str)
        self.last_message = message
        self.is_spamming = self.update_same_messages(message) or self.update_latest_message_timestamps()
        return self.is_spamming

    def update_same_messages(self, message):
        current_timestamp = int(time.time())
        # Clean up old messages.
        new_same_messages = {}
        for old_message in self.same_messages:
            if current_timestamp - self.same_messages[old_message][-1] <= SayInfo.same_messages_decay_duration:
                new_same_messages[old_message] = self.same_messages[old_message]
        self.same_messages = new_same_messages
        # Update timestamps for our message.
        old_timestamps = self.same_messages.get(message, [])
        new_timestamps = []
        for old_timestamp in old_timestamps:
            if current_timestamp - old_timestamp <= SayInfo.same_messages_decay_duration:
                new_timestamps.append(old_timestamp)
        new_timestamps.append(current_timestamp)
        self.same_messages[message] = new_timestamps
        # Return if repeating messages count as spam.
        limit = SayInfo.same_messages_repeat_limit
        if message in SayInfo.same_message_tolerant_words:
            limit *= SayInfo.same_message_tolerant_word_limit_multiplier
        return len(new_timestamps) >= limit

    def update_latest_message_timestamps(self):
        current_timestamp = int(time.time())
        # Clean up older timestamps.
        new_latest_message_timestamps = []
        for old_timestamp in self.latest_message_timestamps:
            if current_timestamp - old_timestamp <= SayInfo.latest_messages_decay_duration:
                new_latest_message_timestamps.append(old_timestamp)
        new_latest_message_timestamps.append(current_timestamp)
        self.latest_message_timestamps = new_latest_message_timestamps
        # Return if latest messages indicate spam.
        return len(self.latest_message_timestamps) >= SayInfo.latest_messages_limit
