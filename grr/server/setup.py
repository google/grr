#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
full grr server.
"""

import configparser
import itertools
import os
import shutil
import subprocess

from setuptools import find_packages
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist

GRR_NO_MAKE_UI_FILES_VAR = "GRR_NO_MAKE_UI_FILES"


def find_data_files(source, ignore_dirs=None):
  ignore_dirs = ignore_dirs or []
  result = []
  for directory, dirnames, files in os.walk(source):
    dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

    files = [os.path.join(directory, x) for x in files]
    result.append((directory, files))

  return result


def make_ui_files():
  """Builds necessary assets from sources."""

  # Install node_modules, but keep package(-lock).json frozen.
  # Using shell=True, otherwise npm is not found in a nodeenv-built
  # virtualenv on Windows.
  subprocess.check_call("npm ci", shell=True, cwd="grr_response_server/gui/ui")
  subprocess.check_call(
      "npm run ng build --prod", shell=True, cwd="grr_response_server/gui/ui")


def get_config():
  """Get relative path to version.ini file and the INI parser with its data."""
  rel_ini_path = "version.ini"
  ini_path = os.path.join(THIS_DIRECTORY, rel_ini_path)
  if not os.path.exists(ini_path):
    rel_ini_path = os.path.join("..", "..", "version.ini")
    ini_path = os.path.join(THIS_DIRECTORY, rel_ini_path)
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
  config.read(ini_path)
  return rel_ini_path, config


IGNORE_GUI_DIRS = ["node_modules", "tmp"]

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# If you run setup.py from the root GRR dir you get very different results since
# setuptools uses the MANIFEST.in from the root dir.  Make sure we are in the
# package dir.
os.chdir(THIS_DIRECTORY)

REL_INI_PATH, VERSION = get_config()


class Develop(develop):
  """Build developer version (pip install -e)."""

  user_options = develop.user_options + [
      ("no-make-ui-files", None, "Don't build UI JS/CSS bundles."),
  ]

  def initialize_options(self):
    self.no_make_ui_files = None
    develop.initialize_options(self)

  def run(self):
    # pip install -e . --install-option="--no-make-ui-files" passes the
    # --no-make-ui-files flag to all GRR dependencies, which doesn't make
    # much sense. Checking an environment variable to have an easy way
    # to set the flag for grr-response-server package only.
    if (not self.no_make_ui_files and
        not os.environ.get(GRR_NO_MAKE_UI_FILES_VAR)):
      make_ui_files()

    develop.run(self)


class Sdist(sdist):
  """Build sdist."""

  user_options = sdist.user_options + [
      ("no-make-ui-files", None, "Don't build UI JS/CSS bundles."),
  ]

  def initialize_options(self):
    self.no_make_ui_files = None
    sdist.initialize_options(self)

  def run(self):
    # For consistency, respsecting GRR_NO_MAKE_UI_FILES variable just like
    # Develop command does.
    if (not self.no_make_ui_files and
        not os.environ.get(GRR_NO_MAKE_UI_FILES_VAR)):
      make_ui_files()

    sdist.run(self)

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


data_files = list(
    itertools.chain(
        find_data_files("grr_response_server/checks"),
        find_data_files("grr_response_server/databases/mysql_migrations"),
        find_data_files("grr_response_server/gui/templates"),
        find_data_files(
            "grr_response_server/gui/static", ignore_dirs=IGNORE_GUI_DIRS
        ),
        find_data_files(
            "grr_response_server/gui/local/static", ignore_dirs=IGNORE_GUI_DIRS
        ),
        [REL_INI_PATH],
    )
)

setup_args = dict(
    name="grr-response-server",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response Server.",
    license="Apache License, Version 2.0",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    url="https://github.com/google/grr",
    cmdclass={"sdist": Sdist, "develop": Develop},
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "grr_console = grr_response_server.distro_entry:Console",
            (
                "grr_api_shell_raw_access = "
                "grr_response_server.distro_entry:ApiShellRawAccess"
            ),
            (
                "grr_config_updater = "
                "grr_response_server.distro_entry:ConfigUpdater"
            ),
            (
                "grr_command_signer = "
                "grr_response_server.distro_entry:CommandSigner"
            ),
            "grr_frontend = grr_response_server.distro_entry:GrrFrontend",
            "grr_server = grr_response_server.distro_entry:GrrServer",
            "grr_worker = grr_response_server.distro_entry:Worker",
            "grr_admin_ui = grr_response_server.distro_entry:AdminUI",
            (
                "fleetspeak_server = "
                "grr_response_server.distro_entry:FleetspeakServer"
            ),
        ]
    },
    install_requires=[
        "google-api-python-client==1.12.11",
        "google-auth==2.23.3",
        "google-cloud-storage==2.13.0",
        "google-cloud-pubsub==2.18.4",
        "grr-api-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-client-builder==%s"
        % VERSION.get("Version", "packagedepends"),
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "ipython==7.15.0",
        "Jinja2==3.1.2",
        "pexpect==4.8.0",
        "portpicker==1.6.0b1",
        "prometheus_client==0.16.0",
        "pyjwt==2.6.0",
        "pyOpenSSL==21.0.0",  # https://github.com/google/grr/issues/704
        "python-crontab==2.5.1",
        "python-debian==0.1.49",
        "Werkzeug==2.1.2",
    ],
    extras_require={
        # This is an optional component. Install to get MySQL data
        # store support: pip install grr-response[mysqldatastore]
        # When installing from .deb, the python-mysqldb package is used as
        # dependency instead of this pip dependency. This is because we run into
        # incompatibilities between the system mysqlclient/mariadbclient and the
        # Python library otherwise. Thus, this version has to be equal to the
        # python-mysqldb version of the system we support. This is currently
        # Ubuntu Jammy, see
        # https://packages.ubuntu.com/en/jammy/python3-mysqldb
        "mysqldatastore": ["mysqlclient>=1.3.10,<=1.4.6"],
        # TODO: We currently release fleetspeak-server-bin packages
        # for Linux only.
        ':sys_platform=="linux"': [
            "fleetspeak-server-bin==0.1.13",
        ],
    },
    data_files=data_files,
)

setup(**setup_args)
