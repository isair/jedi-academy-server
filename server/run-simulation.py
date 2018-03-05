#!/usr/bin/python

import os
import sys

from yoda.parsers.file.simulationLogFileParser import SimulationLogFileParser

if __name__ == "__main__":
    logs_directory = sys.argv[1]
    for root, directories, file_names in os.walk(logs_directory):
        for file_name in file_names:
            if not file_name.lower().endswith('.txt'):
                continue
            full_file_path = os.path.join(root, file_name)
            print("---------------------------------")
            print("Simulating: %s" % full_file_path)
            print("---------------------------------")
            with open(full_file_path, "rt") as f:
                simulation_log_file_parser = SimulationLogFileParser()
                try:
                    simulation_log_file_parser.parse(f)
                except Exception as e:
                    print(repr(e))
