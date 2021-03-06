#!/usr/bin/env python3
import functools
import json
import os
import re
import shutil
import sys

config_path = os.path.expanduser('~') + '/.xclmrc'

try:
    with open(config_path, 'r') as f:
        config = json.loads(f.read())
except FileNotFoundError:
    config = json.loads("{}")
    config['__INSTALL_PATH'] = input('Path to compiler root: ')
    with open(config_path, 'w+') as f:
        f.write(json.dumps(config))
# A small utility to allow functional chaining
class Stream(object):
    def __init__(self, x):
        self.x = x
    def do(self, func, arg):
        self.x = func(arg, self.x)
        return self
    def reduce(self, func, init):
        self.x = functools.reduce(func, self.x, init)
        return self
    def list(self):
        return list(self.x)

install_dir = config['__INSTALL_PATH']
def get_file(directory, prefix = ""):
    if not os.path.exists(directory):
        return []
    members = os.listdir(directory)
    def concat(path, x):
        if len(path) > 0:
            return path + os.sep + x
        else:
            return x
    files = (Stream(members)
            .do(filter, lambda x: os.path.isfile(concat(directory, x)))
            .do(map, lambda x: concat(prefix, x))
            .list())
    subdirs = (Stream(members)
            .do(filter, lambda x: os.path.isdir(concat(directory, x)))
            .do(map, lambda x: get_file(concat(directory, x), concat(prefix, x)))
            .reduce(lambda x, y: x + y, [])
            .list())
    return files + subdirs
#Install/remove/update return True if they have affected the installation
def install(name, path):
    if name in config:
        return False
    else:
        includes = get_file(path + os.sep + 'include')
        libs = get_file(path + os.sep + 'lib')
        bins = get_file(path + os.sep + 'bin')
        config[name] = { 'include' : includes, 'lib' : libs, 'bin' : bins }
        def cpy(fname, src, dest):
            src = path + os.sep + src + os.sep + fname
            dest = install_dir + os.sep + dest
            folders = re.sub('(/|\\\\)+', '/', fname).split('/') #Deduplicate all the slashes
            if len(folders) > 1:
                del folders[-1]
                folders.insert(0, dest)
                try:
                    os.makedirs(os.sep.join(folders))
                except OSError:
                    pass
            if os.path.isfile(src):
                shutil.copy(src, dest + os.sep + fname)
        for x in includes:
            cpy(x, 'include', 'include')
        for x in libs:
            cpy(x, 'lib', 'lib')
        for x in bins:
            cpy(x, 'bin', 'lib')
        with open(config_path, 'w') as f:
            f.write(json.dumps(config))
        return True
def remove(name):
    if not name in config:
        return False
    else:
        def rem(fname, dst):
            dst = install_dir + os.sep + dst + os.sep + fname
            if os.path.isfile(dst):
                os.remove(dst)
            elif os.path.exists(dst):
                shutil.rmtree(dst)
        for x in config[name]['include']:
            rem(x, 'include')
        for x in config[name]['lib']:
            rem(x, 'lib')
        for x in config[name]['bin']:
            rem(x, 'lib')
        del config[name]
        with open(config_path, 'w') as f:
            f.write(json.dumps(config))
        return True
def update(name, path):
    if remove(name):
        return install(name, path)
    return False
def has(name):
    return name in config
def getlib(name):
	if name in config:
		for lib in config[name]['lib']:
			src = install_dir + os.sep + 'lib' + os.sep + lib
			shutil.copy(src, lib)
	return name in config
def getbin(name):
	if name in config:
		for lib in config[name]['bin']:
			src = install_dir + os.sep + 'lib' + os.sep + lib
			shutil.copy(src, lib)
	return name in config

#check for sudo access (required for many commands)
if sys.platform != "win32" and os.geteuid() != 0:
	class NotSudo(Exception):
		pass
	raise NotSudo("This program must be run as the root user on a *nix system.")

if len(sys.argv) < 2:
    command = "null"
else:
    command = sys.argv[1]
if len(sys.argv) < 3:
    package = "null"
else:
    package = sys.argv[2]

if command == "install":
    modified = install(package, '.')
    if not modified:
        print("Package " + package + " is already installed.")
    else:
        print(package + " installed successfully.")
elif command == "remove":
    modified = remove(package)
    if not modified:
        print("Package " + package + " is not installed.")
    else:
        print(package + " has been removed succesfully.")
elif command == "update":
    modified = update(package, '.')
    if not modified:
        print("Package " + package + " has not been updated. Is it installed?")
    else:
        print(package + " has been updated succesfully.")
elif command == "has":
    if has(package):
        print(package + " is installed.")
    else:
        print(package + " is not installed.")
elif command == 'list':
    for pack in config.keys():
        if pack != "__INSTALL_PATH":
            print(pack)
elif command == 'getbin':
	if getbin(package):
		print(package + " binary files have been placed in the current directory.")
	else:
		print("Package " + package + " is not installed.")
elif command == 'getlib':
	if getlib(package):
		print(package + " library files have been placed in the current directory.")
	else:
		print("Package " + package + " is not installed.")
else:
    print('Please enter a command. Command syntax is xclm [install/remove/has/update/getlib/getbin] [package name] | list')
