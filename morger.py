#!/usr/bin/env python3

import argparse
import os
import re
import sys

ORIG_FOLDER = "ORIGINAL_FILES_BACKUP"
MOD_FOLDER = "PUT_MOD_FILES_IN_THIS_FOLDER"

class Entry:
    def __init__(self, basepath, active, dependencies):
        self.basepath = basepath
        self.active = active
        self.deps = dependencies
        self.depends_on_me = list()

class Config:
    """Class to store config data"""

    def __init__(self, filename):
        """Init"""
        self.filename = filename
        self.entries = dict()
        self.queue = list()
        if not os.path.isfile(filename):
            return
        entry = None
        title, base, active = None, None, None
        dependencies = list()
        with open(filename, "r") as fin:
            for line in fin.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                elif line.startswith("queue ="):
                    self.queue = line[line.index("=")+1:].split()
                    continue
                match = re.match(r"\[\s*(\S+)\s*\]", line)
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
                    elif k == "Dependencies":
                        dependencies = v.split()

                if not line and title:
                    entry = Entry(basepath, active, dependencies)
                    self.entries[title] = entry
                    if active not in ("Yes", "No"):
                        print("-W- Invalid active status found:", active)
                    title, basepath, active = None, None, None
                    dependencies = list()

        # Validate dependencies
        for title, entry in self.entries.items():
            if not entry.deps:
                continue
            for dep in entry.deps:
                if dep not in self.entries:
                    print(f'Error: Invalid dependency "{dep}" found in entry: {title}')
                    sys.exit(1)
                self.entries[dep].depends_on_me.append(title)

    def write(self):
        """Write out config file"""
        with open(self.filename, "w") as fout:
            for title, entry in self.entries.items():
                fout.write(f"[{title}]\n")
                fout.write(f"    GamePath = {entry.basepath}\n")
                fout.write(f"    Active   = {entry.active}\n")
                fout.write(f"    Dependencies = {' '.join(entry.deps)}\n")
                fout.write("\n")
            fout.write(f"queue = {' '.join(self.queue)}")

def modswap(title, modpath, config, mode):
    """Install or uninstall a mod"""
    def say(*msg):
        print(f"[{title}]:", *msg)

    if mode not in ("install", "uninstall"):
        print("Error: Invalid mode!")
        sys.exit(1)
    entry = config.entries[title]

    if mode == "install":
        dependencies = entry.deps
    elif mode == "uninstall":
        dependencies = entry.depends_on_me

    for dep in dependencies:
        dep_entry = config.entries[dep]
        if mode == "install":
            modswap(dep, modpath, config, mode)
        elif mode == "uninstall" and dep_entry.active == "Yes":
            say("Error: Dependent mod installed - use reset mode")
            sys.exit(1)

    if mode == "install" and entry.active == "Yes":
        say("Already installed")
        return
    elif mode == "uninstall" and entry.active == "No":
        say("Already uninstalled")
        return

    bakpath = os.path.join(modpath, title, MOD_FOLDER)
    origpath = os.path.join(modpath, title, ORIG_FOLDER)
    gamepath = entry.basepath
    filelist = os.path.join(modpath, title, "modfiles.list")

    if mode == "install":
        dest1 = origpath
        src2 = bakpath
        str_src = "original"
        str_dest = "mod"
    elif mode == "uninstall":
        dest1 = bakpath
        src2 = origpath
        str_src = "mod"
        str_dest = "original"
    src1 = dest2 = gamepath

    fpaths = []

    if mode == "install":
        say("Scanning filelist")
        with open(filelist, "w") as fout:
            for dpath, dnames, fnames in os.walk(src2):
                for fname in fnames:
                    fpath = os.path.join(dpath, fname)
                    fpath = os.path.relpath(fpath, start=src2)
                    fpaths.append(fpath)
                    fout.write(fpath + "\n")
    elif mode == "uninstall":
        with open(filelist, "r") as fin:
            fpaths = [ln.strip() for ln in fin.readlines()]

    say(f"Backing up {str_src} files")
    for fpath in fpaths:
        src1_fpath = os.path.join(src1, fpath)
        if os.path.isfile(src1_fpath):
            os.renames(
                src1_fpath,
                os.path.join(dest1, fpath)
            )

    say(f"Installing {str_dest} files")
    for fpath in fpaths:
        src2_fpath = os.path.join(src2, fpath)
        if os.path.isfile(src2_fpath):
            os.renames(
                src2_fpath,
                os.path.join(dest2, fpath)
            )

    if mode == "install":
        entry.active = "Yes"
        config.queue.append(title)
    elif mode == "uninstall":
        entry.active = "No"
        popped = config.queue.pop()
        # Final sanity check
        if popped != title:
            say("Error: Uh-oh...I uninstalled the wrong mod!")
            config.write()
            sys.exit(1)
    say("Done!")
    print()

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
    meg_mode.add_argument("--reset", "-r", action="store_true",
        help="Uninstall all mods")

    return parser.parse_args()

if __name__ == "__main__":
    args = setup_args()
    config = Config(args.config)
    if args.list:
        for k, v in config.entries.items():
            print(k)
            print("    Game Path = " + v.basepath)
            print("    Mod active? " + v.active)
            print("    Dependencies? " + ", ".join(v.deps))
            print("    Depends on me? " + ", ".join(v.depends_on_me))
            print()
        print(f"Queue ({len(config.queue)})")
        for item in config.queue:
            print("    " + item)

    elif args.init:
        title = args.init.lower()
        if title in config.entries:
            print("Error: Config already contains that entry!")
            sys.exit(1)
        entry = Entry("Put game path here", "No", list())
        config.entries[title] = entry
        config.write()
        os.makedirs(os.path.join(args.modpath, title, MOD_FOLDER))

    elif args.install or args.uninstall:
        title = (args.install or args.uninstall).lower()
        if args.install:
            modswap(title, args.modpath, config, "install")
        elif args.uninstall:
            modswap(title, args.modpath, config, "uninstall")
        config.write()

    elif args.reset:
        if not config.queue:
            print("Nothing to do!")
        while config.queue:
            title = config.queue[-1]
            modswap(title, args.modpath, config, "uninstall")
        config.write()
