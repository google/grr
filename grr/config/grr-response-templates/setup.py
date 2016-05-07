#!/usr/bin/env python
"""This package contains GRR client templates and components."""

import glob
import os
import re
from setuptools import setup

from setuptools.command.sdist import sdist


class Sdist(sdist):
  """Make a sdist release."""

  REQUIRED_COMPONENTS = [
      r"grr-chipsec_.+_Linux_CentOS.+i386.bin",
      r"grr-chipsec_.+_Linux_CentOS.+amd64.bin",
      r"grr-chipsec_.+_Linux_debian.+i386.bin",
      r"grr-chipsec_.+_Linux_debian.+amd64.bin",

      r"grr-rekall_.+_Darwin_OSX.+amd64.bin",
      r"grr-rekall_.+_Linux_CentOS.+i386.bin",
      r"grr-rekall_.+_Linux_CentOS.+amd64.bin",
      r"grr-rekall_.+_Linux_debian.+i386.bin",
      r"grr-rekall_.+_Linux_debian.+amd64.bin",
      r"grr-rekall_.+_Windows_7.+amd64.bin",
      r"grr-rekall_.+_Windows_7.+i386.bin",
  ]

  REQUIRED_TEMPLATES = [
      "GRR_maj.minor_amd64.exe.zip",
      "GRR_maj.minor_i386.exe.zip",
      "grr_maj.minor_amd64.deb.zip",
      "grr_maj.minor_amd64.pkg.xar",
      "grr_maj.minor_amd64.rpm.zip",
      "grr_maj.minor_i386.deb.zip",
      "grr_maj.minor_i386.rpm.zip",
  ]

  def CheckTemplates(self, base_dir, version):
    """Verify we have at least one template that matches maj.minor version."""
    major_minor = ".".join(version.split(".")[0:2])
    templates = glob.glob(os.path.join(base_dir,
                                       "templates/*%s*.zip" % major_minor))
    templates.extend(glob.glob(os.path.join(
        base_dir, "templates/*%s*.xar" % major_minor)))

    required_templates = set([x.replace("maj.minor", major_minor) for x in
                              self.REQUIRED_TEMPLATES])

    # Client templates have an extra version digit, e.g. 3.1.0.0
    templates_present = set([
        re.sub(r"_%s[^_]+_" % major_minor, "_%s_" % major_minor,
               os.path.basename(x)) for x in templates])

    difference = required_templates - templates_present
    if difference:
      raise RuntimeError("Missing templates %s" % difference)

  def CheckComponents(self, base_dir):
    """Verify we have components for each supported system."""
    components = [os.path.basename(x) for x in glob.glob(
        os.path.join(base_dir, "components/*.bin"))]
    missing = set()
    for requirement in self.REQUIRED_COMPONENTS:
      for component in components:
        if re.match(requirement, component):
          break
      else:
        missing.add(requirement)
    if missing:
      raise RuntimeError("Missing components: %s" % missing)

  def run(self):
    base_dir = os.getcwd()
    self.CheckTemplates(base_dir, setup_args["version"])
    self.CheckComponents(base_dir)
    sdist.run(self)
    print "To upload a release, run upload.sh [version]"


def find_data_files(source, prefix=None):
  result = []
  for directory, _, files in os.walk(source):
    files = [os.path.join(directory, x) for x in files]
    if prefix:
      result.append((os.path.join(prefix, directory), files))
    else:
      result.append((directory, files))

  return result


setup_args = dict(
    name="grr-response-templates",
    version="3.1.0post1",
    description="GRR Rapid Response client templates and components.",
    long_description=("This PyPi package is just a placeholder. The package"
                      " itself is too large to distribute on PyPi so it is "
                      "available from google cloud storage. See"
                      " https://github.com/google/grr-doc/blob/master/"
                      "installfrompip.adoc for installation instructions."),
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    data_files=(find_data_files("components", prefix="grr-response-templates") +
                find_data_files("templates", prefix="grr-response-templates")),
    cmdclass={
        "sdist": Sdist,
    })

setup(**setup_args)

