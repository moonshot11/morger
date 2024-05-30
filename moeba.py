#!/usr/bin/env python

import argparse
import os
import re
import sys
from virterm import col


ORIG_FOLDER = "ORIGINAL_FILES_BACKUP"
MOD_FOLDER = "PUT_MOD_FILES_IN_THIS_FOLDER"

class Entry:
    def __init__(self, title, basepath, active, dependencies):
        self.title = title
        self.basepath = basepath
        self.active = active
        self.deps = dependencies
        self.depends_on_me = list()

    @property
    def dep_titles(self):
        return " ".join([en.title for en in self.deps])

    @property
    def dom_titles(self):
        return " ".join([en.title for en in self.depends_on_me])

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
                    entry = Entry(title, basepath, active, dependencies)
                    self.entries[title] = entry
                    if active not in ("Yes", "No"):
                        print("-W- Invalid active status found:", active)
                    title, basepath, active = None, None, None
                    dependencies = list()

        # Re-initialize dependencies with objects
        for entry in self.entries.values():
            dep_objs = list()
            for dep_title in entry.deps:
                if dep_title not in self.entries:
                    print(f'Error: Invalid dependency "{dep}" found in entry: {entry.title}')
                    sys.exit(1)
                dep_objs.append(self.entries[dep_title])
            entry.deps = dep_objs

        # Validate dependencies
        for entry in self.entries.values():
            circular_check(entry, set())
            if not entry.deps:
                continue
            for dep in entry.deps:
                self.entries[dep.title].depends_on_me.append(entry)

    def write(self):
        """Write out config file"""
        with open(self.filename, "w") as fout:
            for title, entry in self.entries.items():
                fout.write(f"[{title}]\n")
                fout.write(f"    GamePath = {entry.basepath}\n")
                fout.write(f"    Active   = {entry.active}\n")
                fout.write(f"    Dependencies = {entry.dep_titles}\n")
                fout.write("\n")
            fout.write(f"queue = {' '.join(self.queue)}")

def circular_check(entry, visited):
    """Check for circular dependencies in mod tree"""
    if entry in visited:
        print("Error: circular dependency in config")
        sys.exit(1)
    visited.add(entry)
    for dep in entry.deps:
        circular_check(dep, visited)

def modswap(entry, modpath, config, mode):
    """Install or uninstall a mod"""
    is_playlist = False
    def say(*msg):
        color = "cyan-bright" if is_playlist else "yellow-bright"
        print(col(color), f"[{entry.title}]:", col(), *msg)

    if mode not in ("install", "uninstall"):
        print("Error: Invalid mode!")
        sys.exit(1)

    if mode == "install":
        dependencies = entry.deps
    elif mode == "uninstall":
        dependencies = entry.depends_on_me

    for dep in dependencies:
        dep_entry = config.entries[dep.title]
        if mode == "install":
            modswap(dep, modpath, config, mode)
        elif mode == "uninstall" and dep_entry.active == "Yes":
            say("Error: Tried to uninstall mod prematurely")
            sys.exit(1)

    if mode == "install" and entry.active == "Yes":
        say("Already installed")
        print()
        return
    elif mode == "uninstall" and entry.active == "No":
        say("Already uninstalled")
        print()
        return

    bakpath = os.path.join(modpath, entry.title, MOD_FOLDER)
    origpath = os.path.join(modpath, entry.title, ORIG_FOLDER)
    gamepath = entry.basepath
    filelist = os.path.join(modpath, entry.title, "modfiles.txt")

    if mode == "install":
        dest1 = origpath
        src2 = bakpath
        str_dest = "mod"
    elif mode == "uninstall":
        dest1 = bakpath
        src2 = origpath
        str_dest = "original game"
    src1 = dest2 = gamepath

    fpaths = []

    if mode == "install":
        say("Scanning mod files")
        with open(filelist, "w") as fout:
            for dpath, dnames, fnames in os.walk(src2):
                for fname in fnames:
                    fpath = os.path.join(dpath, fname)
                    fpath = os.path.relpath(fpath, start=src2)
                    fpaths.append(fpath)
                    fout.write(fpath + "\n")
        if fpaths:
            say("Backing up original game files")
        else:
            is_playlist = True
            say("No files - mod is a playlist")
    elif mode == "uninstall":
        with open(filelist, "r") as fin:
            fpaths = [ln.strip() for ln in fin.readlines()]
        if fpaths:
            say(f"Uninstalling mod files")
        else:
            is_playlist = True
            say(f"Uninstalling playlist")

    if fpaths:
        for fpath in fpaths:
            src1_fpath = os.path.join(src1, fpath)
            if os.path.isfile(src1_fpath) or os.path.islink(src1_fpath):
                os.renames(
                    src1_fpath,
                    os.path.join(dest1, fpath)
                )

        say(f"Installing {str_dest} files")
        for fpath in fpaths:
            src2_fpath = os.path.join(src2, fpath)
            if os.path.isfile(src2_fpath) or os.path.islink(src2_fpath):
                os.renames(
                    src2_fpath,
                    os.path.join(dest2, fpath)
                )

    if mode == "install":
        entry.active = "Yes"
        config.queue.append(entry.title)
    elif mode == "uninstall":
        entry.active = "No"
        popped = config.queue.pop()
        # Final sanity check
        if popped != entry.title:
            say("Error: Uh-oh...I uninstalled the wrong mod!")
            config.write()
            sys.exit(1)
    mod_type = "Mod" if fpaths else "Playlist"
    say(f"{mod_type} {mode}ed!")
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

    meg_mode.add_argument("--list", "-l", action="store_true",
        help="List mods currently stored in config")
    meg_mode.add_argument("--long-list", "-ll", action="store_true",
        help="Display full mod config details")
    meg_mode.add_argument("--init",
        help="Initialize a new mod entry")
    meg_mode.add_argument("--install", "-i",
        nargs="+",
        help="Install a mod", metavar="MODNAMES",
        dest="install_modlist")
    meg_mode.add_argument("--uninstall", "-u",
        help="Uninstall a mod (one at a time!)", metavar="MODNAME")
    meg_mode.add_argument("--reset", "-r", action="store_true",
        help="Uninstall all mods")

    return parser.parse_args()

if __name__ == "__main__":
    args = setup_args()
    config = Config(args.config)
    if args.list or args.long_list:
        def active_color(word):
            if word == "Yes":
                return col("green-bright", "Yes")
            return "No"
        print()
        for k in sorted(config.entries.keys()):
            v = config.entries[k]
            print(col("ylw-bright", f"[{k}]"))
            if args.long_list:
                print(col("cyan-bright", "    Game Path: ") + v.basepath)
            print(col("cyan-bright", "    Mod active? ") + active_color(v.active))
            if args.long_list:
                print(col("cyan-bright", "    Dependencies? ") + v.dep_titles)
                print(col("cyan-bright", "    Depends on me? ") + v.dom_titles)
                print()

        if args.long_list:
            print(f"Installation history queue ({len(config.queue)})")
            for i, item in enumerate(config.queue):
                ordinal = f"{i+1}. ".rjust(4)
                print("   " + ordinal + item)
        print()

    elif args.init:
        title = args.init.lower()
        if title in config.entries:
            print("Error: Config already contains that entry!")
            sys.exit(1)
        entry = Entry(title, "Put game path here", "No", list())
        config.entries[title] = entry
        config.write()
        os.makedirs(os.path.join(args.modpath, title, MOD_FOLDER))

    elif args.install_modlist:
        # First, verify that all provided mods exist
        badmods = []
        for modname in args.install_modlist:
            if modname.lower() not in config.entries:
                badmods.append(modname)
        if badmods:
            print("Error: Mod(s) not recognized:", ",".join(badmods))
            sys.exit(1)
        for modname in args.install_modlist:
            modname = modname.lower()
            modswap(config.entries[modname], args.modpath, config, "install")
        config.write()

    elif args.uninstall or args.reset:
        if args.uninstall and args.uninstall not in config.entries:
            print("Error: I don't recognize that mod!")
            sys.exit(1)
        if not config.queue or (args.uninstall and args.uninstall not in config.queue):
            print("Nothing to do!")
            sys.exit(0)
        target = args.uninstall if args.uninstall else config.queue[0]
        while target in config.queue:
            title = config.queue[-1]
            modswap(config.entries[title], args.modpath, config, "uninstall")
        config.write()

    sys.exit(0)
