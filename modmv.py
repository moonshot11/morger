#!/d/Python37/python

import argparse
import os
import sys

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
    print("main")
