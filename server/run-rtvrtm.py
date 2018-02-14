#!/usr/bin/python -uSOO

from sys import argv

from rtvrtm.rtvrtm import main

if __name__ == "__main__":
    try:
        main(argv)
    except KeyboardInterrupt:
        exit(2)
