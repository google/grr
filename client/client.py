#!/usr/bin/env python
"""This is the GRR client."""


import pdb
import platform


from grr.client import conf
from grr.client import conf as flags

# pylint: disable=W0611
from grr.client import client_plugins
# pylint: enable=W0611

from grr.client import comms
from grr.client import installer
from grr.lib import config_lib
from grr.lib import startup


flags.DEFINE_bool("install", False,
                  "Specify this to install the client.")

flags.DEFINE_bool("break_on_start", False,
                  "If True break into a pdb shell immediately on startup. This"
                  " can be used for debugging the client manually.")

config_lib.DEFINE_list("Client.plugins", [],
                       help="Plugins loaded by the client.")


class GRRClient(object):
  """A stand alone GRR client, which uses the HTTP mechanism."""

  stop = False

  def __init__(self, ca_cert=None, private_key=None):
    super(GRRClient, self).__init__()
    ca_cert = ca_cert or config_lib.CONFIG["CA.certificate"]
    private_key = private_key or config_lib.CONFIG["Client.private_key"]
    self.client = comms.GRRHTTPClient(ca_cert=ca_cert, private_key=private_key)

  def Run(self):
    """The client main loop - never exits."""
    # Generate the client forever.
    for _ in self.client.Run():
      pass


def main(unused_args):
  # Allow per platform configuration.
  config_lib.CONFIG.SetEnv("Environment.component",
                           "Client%s" % platform.system().title())
  startup.ClientInit()

  if flags.FLAGS.install:
    installer.RunInstaller()

  errors = config_lib.CONFIG.Validate(["Client", "CA", "Logging"])

  if not errors:
    client = GRRClient()
  elif errors.keys() == ["Client.private_key"]:
    client = GRRClient()
    client.client.InitiateEnrolment(comms.Status())
  else:
    raise config_lib.ConfigFormatError(errors)

  if flags.FLAGS.break_on_start:
    pdb.set_trace()
  else:
    client.Run()


if __name__ == "__main__":
  conf.StartMain(main)
