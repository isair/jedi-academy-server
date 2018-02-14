from __future__ import with_statement

import json
import threading
import time


class FileConfigurable:
    """A base class for all classes that read configuration data from a file."""

    def __init__(self, configuration_file_path):
        self.configuration_file_path = configuration_file_path
        self.__start_trying_to_load_configuration__()

    def __start_trying_to_load_configuration__(self):
        attempt_count = 3
        threading.Thread(target=self.__try_to_load_configuration__, args=(attempt_count,)).start()

    def __try_to_load_configuration__(self, remaining_attempts=0, attempt_delay_in_seconds=1):
        try:
            self.load_configuration()
        except Exception as e:
            if remaining_attempts > 0:
                time.sleep(attempt_delay_in_seconds)
                threading.Thread(target=self.__try_to_load_configuration__, args=(remaining_attempts - 1,)).start()
            else:
                print("WARNING: Failed to load configuration file at %s" % self.configuration_file_path)
                print(e)

    def load_configuration(self):
        raise NotImplementedError

    def synchronize(self):
        raise NotImplementedError


class ListFileConfigurable(FileConfigurable):

    def __init__(self, configuration_file_path):
        self.list = []
        FileConfigurable.__init__(self, configuration_file_path)

    @staticmethod
    def parse_line(line):
        return line.strip().lower()

    def load_configuration(self):
        with open(self.configuration_file_path) as f:
            self.list = [self.parse_line(line) for line in f]

    def synchronize(self):
        try:
            with open(self.configuration_file_path, "wt") as f:
                for item in self.list:
                    f.write("%s\n" % item)
        except Exception as e:
            print("WARNING: Failed to write to list at %s" % self.configuration_file_path)
            print(e)


class JSONFileConfigurable(FileConfigurable):

    def __init__(self, configuration_file_path):
        self.json_dict = {}
        FileConfigurable.__init__(self, configuration_file_path)

    @classmethod
    def __json_load_byteified__(cls, file_handle):
        return cls.__byteify__(
            json.load(file_handle, object_hook=cls.__byteify__),
            ignore_dicts=True
        )

    @classmethod
    def __json_loads_byteified__(cls, json_text):
        return cls.__byteify__(
            json.loads(json_text, object_hook=cls.__byteify__),
            ignore_dicts=True
        )

    @classmethod
    def __byteify__(cls, data, ignore_dicts=False):
        # if this is a unicode string, return its string representation
        if isinstance(data, unicode):
            return data.encode('utf-8')
        # if this is a list of values, return list of byteified values
        if isinstance(data, list):
            return [cls.__byteify__(item, ignore_dicts=True) for item in data]
        # if this is a dictionary, return dictionary of byteified keys and values
        # but only if we haven't already byteified it
        if isinstance(data, dict) and not ignore_dicts:
            return {
                cls.__byteify__(key, ignore_dicts=True): cls.__byteify__(value, ignore_dicts=True)
                for key, value in data.iteritems()
            }
        # if it's anything else, return it in its original form
        return data

    def load_configuration(self):
        with open(self.configuration_file_path) as f:
            self.json_dict = self.__json_load_byteified__(f)

    def synchronize(self):
        try:
            with open('data.json', 'w') as f:
                # TODO: merge with existing data and deduplicate
                json.dump(self.json_dict, f, sort_keys=True, indent=2)
        except Exception as e:
            print("WARNING: Failed to write to json at %s" % self.configuration_file_path)
            print(e)
