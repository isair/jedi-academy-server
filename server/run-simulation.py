#!/usr/bin/python -uSOO

import os
from sys import argv

from rtvrtm.parsers.file.simulationLogFileParser import SimulationLogFileParser

if __name__ == "__main__":
    directory = argv[1]
    for root, dirs, file_names in os.walk(directory):
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
