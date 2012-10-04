#!/usr/bin/env python
"""A quick script to inject keys into the client installation binaries."""

import os

from grr.client import conf
from grr.client import conf as flags

FLAGS = flags.FLAGS

flags.DEFINE_string("location", None,
                    "The server location.")

flags.DEFINE_string("ca_cert", None,
                    "The ca certificate file.")

flags.DEFINE_string("driver_key", None,
                    "The driver signing key file.")

flags.DEFINE_string("exe_key", None,
                    "The executable signing key file.")

flags.DEFINE_string("installer_template", None,
                    "Path to the install.vbs.template.")

flags.DEFINE_string("client_dir", None,
                    "The directory to put the install.vbs script.")

flags.DEFINE_string("agent_version", None,
                    "The version string of this client.")

flags.DEFINE_integer("package_build", None,
                     "32 or 64 bits.")

flags.DEFINE_bool("debug", False,
                  "Debug mode.")


def MakeLongVBSString(s):
  lines = s.split("\n")

  lines = ["\"" + line + "\"" for line in lines if line]

  return " & _ \r\n".join(lines)


def main(unused_argv):

  location = FLAGS.location
  if not location:
    print "Need a server location!"
    exit(1)

  if "http://" not in location or "/control" not in location:
    print "Location is malformed..."
    print ("The server location has to be given in the form "
           "http://server:port/control")
    exit(1)

  in_fd = open(FLAGS.installer_template)
  installer = in_fd.read()

  cacert = open(FLAGS.ca_cert).read()
  vbs_cert = MakeLongVBSString(cacert)

  exekey = open(FLAGS.exe_key).read()
  vbs_exekey = MakeLongVBSString(exekey)

  driverkey = open(FLAGS.driver_key).read()
  vbs_driverkey = MakeLongVBSString(driverkey)

  installer = installer.replace("XX_CACERT_XX", vbs_cert)
  installer = installer.replace("XX_EXEKEY_XX", vbs_exekey)
  installer = installer.replace("XX_DRIVERKEY_XX", vbs_driverkey)
  installer = installer.replace("XX_LOCATION_XX", FLAGS.location)
  installer = installer.replace("XX_PACKAGE_BUILD_XX", str(FLAGS.package_build))
  installer = installer.replace("XX_AGENT_VERSION_XX", FLAGS.agent_version)

  out_fd = open(os.path.join(FLAGS.client_dir, "installer.vbs"), "w")
  out_fd.write(installer)

if __name__ == "__main__":
  conf.StartMain(main)
