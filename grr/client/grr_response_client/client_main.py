#!/usr/bin/env python
"""This is the entry point for the GRR client."""

import pdb
import platform
import sys

from absl import app
from absl import flags

from grr_response_client import client_plugins
from grr_response_client import client_startup
from grr_response_client import fleetspeak_client
from grr_response_client import installer
from grr_response_client.unprivileged import sandbox
from grr_response_core import config
from grr_response_core.config import contexts


_INSTALL = flags.DEFINE_bool(
    "install", False, "Specify this to install the client."
)

_BREAK_ON_START = flags.DEFINE_bool(
    "break_on_start",
    False,
    "If True break into a pdb shell immediately on startup. This"
    " can be used for debugging the client manually.",
)

_DEBUG_CLIENT_ACTIONS = flags.DEFINE_bool(
    "debug_client_actions",
    False,
    "If True break into a pdb shell before executing any client action.",
)

_REMOTE_DEBUGGING_PORT = flags.DEFINE_integer(
    "remote_debugging_port",
    0,
    "If set to a non-zero port, pydevd is started to allow remote debugging "
    "(e.g. using PyCharm).",
)


def _start_remote_debugging(port):
  """Sets up remote debugging using pydevd, connecting to localhost:`port`."""
  try:
    print("Connecting to remote debugger on localhost:{}.".format(port))
    # pytype: disable=import-error
    import pydevd  # pylint: disable=g-import-not-at-top
    # pytype: enable=import-error
    pydevd.settrace(
        "localhost",
        port=port,
        stdoutToServer=True,
        stderrToServer=True,
        suspend=_BREAK_ON_START.value,
    )
  except ImportError:
    print(
        "pydevd is required for remote debugging. Please follow the PyCharm"
        "manual or run `pip install pydevd-pycharm` to install.",
        file=sys.stderr,
    )


def main(unused_args):
  client_plugins.RegisterPlugins()

  if _REMOTE_DEBUGGING_PORT.value:
    _start_remote_debugging(_REMOTE_DEBUGGING_PORT.value)
  elif _BREAK_ON_START.value:
    pdb.set_trace()

  # Allow per platform configuration.
  config.CONFIG.AddContext(
      contexts.CLIENT_CONTEXT, "Context applied when we run the client process."
  )

  client_startup.ClientInit()

  if _INSTALL.value:
    installer.RunInstaller()
    sys.exit(0)

  is_pyinstaller_binary = getattr(sys, "frozen", False)
  if is_pyinstaller_binary and platform.system() == "Windows":
    # Since `Client.install_path` is shared with the Sandbox, Sandbox
    # initialization makes only sense if we run from a proper installation.
    # This is the case if this is a PyInstaller binary.
    sandbox.InitSandbox(
        "{}_{}".format(
            config.CONFIG["Client.name"], config.CONFIG["Source.version_string"]
        ),
        [config.CONFIG["Client.install_path"]],
    )

  fleetspeak_client.GRRFleetspeakClient().Run()


if __name__ == "__main__":
  app.run(main)
