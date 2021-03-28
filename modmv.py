#!/d/Python37/python

import argparse
import os
import re
import sys

class Config:
    """Class to store config data"""
    class Entry:
        def __init__(self, basepath, bakpath, status):
            self.basepath = basepath
            self.bakpath = bakpath
            self.status = status

    def __init__(self, filename):
        """Init"""
        self.filename = filename
        self.entries = dict()
        entry = None
        title, base, bak, status = None, None, None, None
        with open(filename, "r") as fin:
            for line in fin.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                match = re.match(r"\[\s*([A-Za-z0-9 ]+)\s*\]", line)
                if match:
                    title = match.group(1)
                    continue
                match = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
                if match:
                    k, v = match.groups()
                    if k == "GamePath":
                        basepath = v
                    elif k == "ModPath":
                        bakpath = v
                    elif k == "Active":
                        status = v

                if not line and title:
                    entry = Config.Entry(basepath, bakpath, status)
                    self.entries[title] = entry
                    title, basepath, bakpath, status = None, None, None, None

def setup_args():
    """Initialize arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", "-c",
        default="mods.cfg",
        dest="config")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--swap")

    return parser.parse_args()

if __name__ == "__main__":
    args = setup_args()
    config = Config(args.config)
    print(config.entries)
