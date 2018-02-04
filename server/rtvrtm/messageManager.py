from __future__ import with_statement

import random
import threading

from fileConfigurable import JSONFileConfigurable
from jaserver import JAServer


class MessageManager(JSONFileConfigurable):
    """Handles automated messages to send to a JA server."""

    def __init__(self, jaserver):
        assert isinstance(jaserver, JAServer)
        self.jaserver = jaserver
        # TODO: Read path from the config
        JSONFileConfigurable.__init__(self, "/jedi-academy/messages.json")

    def __say_messages__(self, context, prefix="^7", use_random_choice=False, random_choice_count=1):
        messages = []
        try:
            messages_dict = self.json_dict[context]
            messages = messages_dict.get("common", []) + messages_dict.get(self.jaserver.gamemode, [])
        except Exception as e:
            print("WARNING: No messages defined under key %s in %s" % (context, self.configuration_file_path))
            print(e)
        if use_random_choice:
            random_choice_count = min(random_choice_count, len(messages))
            if random_choice_count > 0:
                messages = random.sample(messages, random_choice_count)
            else:
                messages = []
        for message in messages:
            try:
                self.jaserver.svsay(prefix + message)
            except Exception as e:
                print("ERROR: Failed to say %s message: %s" % (context, message))
                print(e)

    def say_timed_messages(self):
        threading.Timer(21.0, self.say_welcome).start()
        threading.Timer(45.0, self.say_random_tip).start()
        threading.Timer(60.0, self.say_warnings).start()

    def say_welcome(self):
        self.__say_messages__("welcome")

    def say_random_tip(self):
        self.__say_messages__("tips", "^2[Tip] ^7", True)

    def say_warnings(self):
        self.__say_messages__("warnings", "^1")

    # TODO: Move this and other voting logic to a voting manager and properties to a vote class.
    def say_voting_message(self, voting_name, countdown, countdown_type, total_votes, total_players, votes_items):
        self.jaserver.svsay("^2[%s] ^7Type !number to vote. Voting will complete in ^2%i ^7%s%s (%i/%i)."
                            % (voting_name, countdown, countdown_type, ("" if countdown == 1 else "s"),
                               total_votes, total_players))
        self.jaserver.svsay("^2[Votes] ^7%s" % (", ".join(("%i(%i): %s" % (vote_id, vote_count, vote_display_value)
                                                           for
                                                           (vote_id,
                                                            (vote_count, priority, vote_value, vote_display_value))
                                                           in votes_items()))))
