#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Util for modifying the GRR server configuration."""



# pylint: disable=W0611
import os
import readline
import sys


from grr.client import conf
from grr.client import conf as flags

from grr.lib import aff4

from grr.lib import data_store
from grr.lib import fake_data_store
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import maintenance_utils
from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr

from grr.proto import jobs_pb2
# pylint: enable=W0611

flags.DEFINE_string("signing_key",
                    "/etc/grr/keys/driver_sign.pem",
                    "Key for signing uploaded blobs.")

flags.DEFINE_string("verification_key",
                    "/etc/grr/keys/driver_sign_pub.pem",
                    "Key for verifying signed blobs.")

flags.DEFINE_string("aff4_path", "/config/drivers",
                    "Path to upload the file to")

flags.DEFINE_string("upload_name", None,
                    "Name of the file once uploaded, defaults to basename of"
                    " local path.")

flags.DEFINE_string("file", None,
                    "The file to upload.")

flags.DEFINE_string("local_output", None,
                    "If set, the file will not be uploaded but will be written "
                    " to disk at this file path.")

flags.DEFINE_string("install_driver_name",
                    "pmem",
                    "The name of this driver.")

flags.DEFINE_string("install_device_path",
                    "\\\\.\\pmem",
                    "The device this driver creates.")

flags.DEFINE_string("install_write_path",
                    None,
                    "The file we write the driver to before loading.")

flags.DEFINE_string("driver_display_name",
                    "pmem",
                    "The driver display name.")

flags.DEFINE_enum("install_rewrite_mode",
                  "DISABLE", ["DISABLE", "ENABLE", "FORCE"],
                  "The kernel object rewrite mode for linux.")

flags.DEFINE_enum("type",
                  "DRIVER", ["DRIVER", "PYTHON", "EXE"],
                  "The type of object we are signing.")

flags.DEFINE_enum("platform",
                  None, ["OSX", "WINDOWS", "LINUX"],
                  "The platform the file is destined for (helps determines aff4"
                  " path.")

flags.DEFINE_enum("action",
                  "BOTH", ["SIGN", "UPLOAD", "BOTH", "RAWUPLOAD"],
                  "Are we signing a file, uploading, both or uploading raw?")

flags.DEFINE_bool("interactive", False, "Ignore flags and ask the user"
                  " questions instead.")


FLAGS = flags.FLAGS


MAX_FILE_SIZE = 1024*1024*30  # 30MB


def Usage():

  print "\nThis tool is used to sign and upload code and binaries to the GRR"
  print " datastore.\n"
  print "Normally you should run this tool with --interactive and follow the"
  print " interactive prompts\n"
  print "However, if you want to script it it can be run in three key ways:"
  print """
1. Sign and upload (used in test).
2. Sign offline (used for production/staging).
3. Upload offline signed to datastore (production/staging).

Running the command in interactive mode will output the command line options at
completion to run it non-interactively.
"""


def Interactive():
  """Run an interactive prompt to set the FLAGS intelligently."""
  cmd = "%s " % __file__
  prompt = "> "
  print "Do you want to SIGN or UPLOAD a file? or BOTH? [%s]" % FLAGS.action
  FLAGS.action = raw_input(prompt) or FLAGS.action
  cmd += " --action=%s" % FLAGS.action
  if FLAGS.action not in ["SIGN", "BOTH", "UPLOAD"]:
    raise Exception("Invalid action %s" % FLAGS.action)

  def_file = FLAGS.file or ""
  def_file = " [%s]" % def_file
  if FLAGS.action in ["SIGN", "BOTH"]:
    print "Which is the file you want to sign?%s" % def_file
  else:
    print "Which is the file you want to upload?%s" % def_file
  FLAGS.file = raw_input(prompt) or FLAGS.file
  cmd += " --file=%s" % FLAGS.file

  if FLAGS.action == "SIGN":
    default_out = FLAGS.file + ".signed"
    print "Which file should we write the output to? [%s]" % default_out
    FLAGS.local_output = raw_input(prompt) or default_out
    cmd += " --local_output=%s" % FLAGS.local_output

  print "Is this a DRIVER, EXE or PYTHON file? [%s]" % FLAGS.type
  FLAGS.type = raw_input(prompt) or FLAGS.type
  cmd += " --type=%s" % FLAGS.type

  # Driver specific options.
  if FLAGS.type == "DRIVER" and FLAGS.action != "SIGN":
    print "What is the name of the driver? [%s]" % FLAGS.install_driver_name
    FLAGS.install_driver_name = raw_input(prompt) or FLAGS.install_driver_name
    cmd += " --install_driver_name=%s" % FLAGS.install_driver_name

    print ("What file should we write the driver file to to install it? [%s]" %
           FLAGS.install_write_path)
    FLAGS.install_write_path = raw_input(prompt) or FLAGS.install_write_path
    if FLAGS.install_write_path:
      cmd += " --install_write_path=%s" % FLAGS.install_write_path

    print "What is the driver object name? [%s]" % FLAGS.install_device_path
    FLAGS.install_device_path = raw_input(prompt) or FLAGS.install_device_path
    cmd += " --install_device_path=%s" % FLAGS.install_device_path

    print ("What is the driver rewrite mode? DISABLE, ENABLE or FORCE [%s]" %
           FLAGS.install_rewrite_mode)
    FLAGS.install_rewrite_mode = raw_input(prompt) or FLAGS.install_rewrite_mode
    cmd += " --install_rewrite_mode=%s" % FLAGS.install_rewrite_mode

  key_base = os.path.dirname(FLAGS.signing_key)
  print "Which directory are your signing keys in? [%s]" % key_base
  key_base = raw_input(prompt) or key_base

  if FLAGS.type in ["PYTHON", "EXE"]:
    # Guess default key values better if not a driver.
    FLAGS.signing_key = os.path.join(key_base, "exe_sign.pem")
    FLAGS.verification_key = os.path.join(key_base, "exe_sign_pub.pem")
  elif FLAGS.type in ["DRIVER"]:
    FLAGS.signing_key = os.path.join(key_base, "driver_sign.pem")
    FLAGS.verification_key = os.path.join(key_base, "driver_sign_pub.pem")

  if FLAGS.action in ["SIGN", "BOTH"]:
    print "Which key is being used for signing? [%s]" % FLAGS.signing_key
    FLAGS.signing_key = raw_input(prompt) or FLAGS.signing_key
    cmd += " --signing_key=%s" % FLAGS.signing_key

  print ("Which key is being used for verification? [%s]" %
         FLAGS.verification_key)
  FLAGS.verification_key = raw_input(prompt) or FLAGS.verification_key

  cmd += " --verification_key=%s" % FLAGS.verification_key
  if FLAGS.action in ["UPLOAD", "BOTH"]:
    # We need to determine the path to upload the file to.

    if FLAGS.type in ["DRIVER", "EXE"]:
      print "Which platform is it for? WINDOWS, OSX or LINUX [WINDOWS]"
      FLAGS.platform = raw_input(prompt) or "WINDOWS"
      cmd += " --platform=%s" % FLAGS.platform

    upload_name = os.path.basename(FLAGS.file)
    print "Which name should the file have on the server? [%s]" % upload_name
    FLAGS.upload_name = raw_input(prompt) or upload_name
    cmd += " --upload_name=%s" % FLAGS.upload_name

    def_path = GetPathForFile(FLAGS.type, FLAGS.platform)
    print "Which path should the file be uploaded to? [%s]" % def_path
    FLAGS.aff4_path = raw_input(prompt) or def_path
    cmd += " --aff4_path=%s" % FLAGS.aff4_path

  print "######################################################################"
  print "  Effective command being run:"
  print ""
  print cmd
  print "######################################################################"


def GetPathForFile(file_type, platform):
  base = "/config"
  if file_type == "PYTHON":
    return "%s/%s" % (base, "python_hacks")
  elif file_type == "DRIVER":
    return "%s/drivers/%s/memory" % (base, platform.lower())
  elif file_type == "EXE":
    return "%s/executables/%s/installers" % (base, platform.lower())


def GetInstallInfo():
  """Gets the corresponding install information for drivers."""
  install_info = jobs_pb2.InstallDriverRequest()
  if FLAGS.install_driver_name:
    install_info.driver_name = FLAGS.install_driver_name
  if FLAGS.driver_display_name:
    install_info.driver_display_name = FLAGS.driver_display_name
  else:
    install_info.driver_display_name = FLAGS.install_driver_name
  if FLAGS.install_write_path:
    install_info.write_path = FLAGS.install_write_path
  if FLAGS.install_device_path:
    install_info.device_path = FLAGS.install_device_path
  if FLAGS.install_rewrite_mode:
    req_desc = jobs_pb2.InstallDriverRequest.DESCRIPTOR.enum_values_by_name
    install_info.mode = req_desc[FLAGS.install_rewrite_mode].number
  return install_info


def RawUpload(path, data):
  fd = aff4.FACTORY.Create(path, "AFF4Image", mode="w")
  fd.Write(data)
  fd.Close()
  return str(fd.urn)


def main(unused_argv):
  """Main."""

  if FLAGS.interactive:
    Interactive()
  else:
    if (not FLAGS.action or not FLAGS.signing_key or not FLAGS.aff4_path
        or not FLAGS.file or not FLAGS.type):
      Usage()
      sys.exit(1)

  registry.Init()

  upload_name = FLAGS.upload_name
  if FLAGS.verification_key:
    verification_key = open(FLAGS.verification_key).read()
  else:
    # Default to using the signing key, often signing key will include public
    # key also.
    verification_key = open(FLAGS.signing_key).read()

  with open(FLAGS.file) as fd:
    data = fd.read(MAX_FILE_SIZE)
    if FLAGS.action == "RAWUPLOAD":
      out_path = RawUpload("%s/%s" % (FLAGS.aff4_path, FLAGS.upload_name), data)
      print "Uploaded successfully to %s" % out_path
    else:
      if FLAGS.action == "UPLOAD":
        # Upload pre-signed protobuf.
        blob_pb = jobs_pb2.SignedBlob.FromString(data)
      else:
        # Sign then upload real data.
        signing_key = open(FLAGS.signing_key).read()
        blob_pb = maintenance_utils.SignConfigBlob(
            data, signing_key=signing_key)
      if not maintenance_utils.VerifySignedBlob(blob_pb, verification_key):
        print "Could not verify blob against key %s." % FLAGS.verification_key
        sys.exit(1)
      if FLAGS.action == "SIGN":
        open(FLAGS.local_output, "wb").write(blob_pb.SerializeToString())
        print "Written successfully to %s" % FLAGS.local_output
      else:
        if FLAGS.install_device_path or FLAGS.install_driver_name:
          install_request = GetInstallInfo()
          out_path = maintenance_utils.UploadSignedDriverBlob(
              blob_pb, upload_name, install_request=install_request,
              aff4_path=FLAGS.aff4_path)
        else:
          out_path = maintenance_utils.UploadSignedConfigBlob(
              blob_pb, upload_name, aff4_path=FLAGS.aff4_path)
        print "Uploaded successfully to %s" % out_path

if __name__ == "__main__":
  conf.StartMain(main)
