#!/usr/bin/env python
"""A quick script to verify that setup.py actually installs all files."""

# pylint: disable=g-import-not-at-top

import os
import re

try:
  import setuptools
  setuptools.setup = lambda *args, **kw: None
except ImportError:
  from distutils import core
  core.setup = lambda *args, **kw: None

import setup

grr_packages = setup.GRRFindPackages()
setup_files = set()
walk_files = set()

for package, files in setup.GRRFindDataFiles(setup.grr_all_files).iteritems():
  package_path = package.replace(".", "/").replace("grr", "")
  if package_path.startswith("/"):
    package_path = package_path[1:]
  for f in files:
    file_path = os.path.join(package_path, f)
    setup_files.add(file_path)

for directory, _, files in os.walk("."):
  directory = directory.replace("./", "")
  if directory == ".":
    package = "grr"
  else:
    package = "grr." + directory.replace("/", ".")

  for f in files:
    if package in grr_packages and f.endswith(".py"):
      continue
    file_path = os.path.join(directory, f)
    walk_files.add(file_path)


whitelist = ["test_data/.*\\.py"]
for filename in sorted(setup_files - walk_files):
  if any([re.match(regex, filename) for regex in whitelist]):
    continue
  print "File found by setup.py but not by os.walk:", filename

whitelist = [
    # For building the server. Those files should probably be copied since we
    # have them in the .deb too but it's not possible to build from an
    # installed server anyways so we ignore them.
    "config/.*",

    # Just test keys, don't overwrite anything.
    "keys/.*",

    # Those go in /usr/share/grr, not along with the code.
    "binaries/.*",
    "executables/.*",
    "scripts/.*",

    # Metadata.
    "./AUTHORS",
    "./LICENSE",
    "./README",
    "./.*pyc",
    ]
for filename in sorted(walk_files - setup_files):
  if any([re.match(regex, filename) for regex in whitelist]):
    continue
  print "File found by os.walk but not by setup.py:", filename
