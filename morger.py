#!/usr/bin/env python3

import argparse
import os
import re
import sys

ORIG_FOLDER = "ORIGINAL_FILES_BACKUP"
MOD_FOLDER = "PUT_MOD_FILES_IN_THIS_FOLDER"

class Entry:
    def __init__(self, basepath, active):
        self.basepath = basepath
        self.active = active

class Config:
    """Class to store config data"""

    def __init__(self, filename):
        """Init"""
        self.filename = filename
        self.entries = dict()
        entry = None
        title, base, active = None, None, None
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
                    elif k == "Active":
                        active = v

                if not line and title:
                    entry = Entry(basepath, active)
                    self.entries[title] = entry
                    if active not in ("Yes", "No"):
                        print("-W- Invalid active status found:", active)
                    title, basepath, active = None, None, None

    def write(self):
        """Write out config file"""
        with open(self.filename, "w") as fout:
            for title, entry in self.entries.items():
                fout.write(f"[{title}]\n")
                fout.write(f"    GamePath = {entry.basepath}\n")
                fout.write(f"    Active   = {entry.active}\n")
                fout.write("\n")

def modswap(title, modpath, entry):
    """Install or uninstall a mod"""
    bakpath = os.path.join(modpath, title, MOD_FOLDER)
    origpath = os.path.join(modpath, title, ORIG_FOLDER)
    gamepath = entry.basepath
    filelist = os.path.join(modpath, title, "modfiles.list")

    if entry.active == "Yes":
        dest1 = bakpath
        src2 = origpath
        str_src = "mod"
        str_dest = "original"
    elif entry.active == "No":
        dest1 = origpath
        src2 = bakpath
        str_src = "original"
        str_dest = "mod"
    src1 = dest2 = gamepath

    fpaths = []

    if entry.active == "No":
        print("Scanning filelist")
        with open(filelist, "w") as fout:
            for dpath, dnames, fnames in os.walk(src2):
                for fname in fnames:
                    fpath = os.path.join(dpath, fname)
                    fpath = os.path.relpath(fpath, start=src2)
                    fpaths.append(fpath)
                    fout.write(fpath + "\n")
    elif entry.active == "Yes":
        with open(filelist, "r") as fin:
            fpaths = [ln.strip() for ln in fin.readlines()]

    print(f"Backing up {str_src} files")
    for fpath in fpaths:
        src1_fpath = os.path.join(src1, fpath)
        if os.path.isfile(src1_fpath):
            os.renames(
                src1_fpath,
                os.path.join(dest1, fpath)
            )

    print(f"Installing {str_dest} files")
    for fpath in fpaths:
        src2_fpath = os.path.join(src2, fpath)
        if os.path.isfile(src2_fpath):
            os.renames(
                src2_fpath,
                os.path.join(dest2, fpath)
            )

    entry.active = "No" if entry.active == "Yes" else "Yes"
    print("Done!")

def setup_args():
    """Initialize arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", "-c",
        default="mods.cfg", dest="config",
        help="The config file to use")
    parser.add_argument("--modpath", default="mods",
        help="The root path to store mods")

    meg_mode = parser.add_mutually_exclusive_group(required=True)

    meg_mode.add_argument("--list", action="store_true",
        help="List out mods currently stored in config")
    meg_mode.add_argument("--init",
        help="Initialize a new mod entry")
    meg_mode.add_argument("--install", "-i",
        help="Install a mod", metavar="MODNAME")
    meg_mode.add_argument("--uninstall", "-u",
        help="Uninstall a mod", metavar="MODNAME")

    return parser.parse_args()

if __name__ == "__main__":
    args = setup_args()
    config = Config(args.config)
    if args.list:
        for k, v in config.entries.items():
            print(k)
            print("    Game Path = " + v.basepath)
            print("    Mod active? " + v.active)
            print()
    elif args.init:
        title = args.init.lower()
        if title in config.entries:
            print("Error: Config already contains that entry!")
            sys.exit(1)
        entry = Entry("Put game path here", "No")
        config.entries[title] = entry
        config.write()
        os.makedirs(os.path.join(args.modpath, title, MOD_FOLDER))
    elif args.install or args.uninstall:
        title = (args.install or args.uninstall).lower()
        entry = config.entries[title]
        if args.install and entry.active == "Yes":
            print("Error: Mod is already installed!")
            sys.exit(1)
        elif args.uninstall and entry.active == "No":
            print("Error: Mod is not currently installed!")
            sys.exit(1)
        modswap(title, args.modpath, config.entries[title])
        config.write()
