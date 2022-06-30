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
  subprocess.check_call(
      "npm ci", shell=True, cwd="grr_response_server/gui/static")
  subprocess.check_call(
      "npx gulp compile", shell=True, cwd="grr_response_server/gui/static")
  # Compile UI v2.
  subprocess.check_call("npm ci", shell=True, cwd="grr_response_server/gui/ui")
  subprocess.check_call(
      "npm run ng build --prod", shell=True, cwd="grr_response_server/gui/ui")


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
  config.read(ini_path)
  return config


IGNORE_GUI_DIRS = ["node_modules", "tmp"]

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# If you run setup.py from the root GRR dir you get very different results since
# setuptools uses the MANIFEST.in from the root dir.  Make sure we are in the
# package dir.
os.chdir(THIS_DIRECTORY)

VERSION = get_config()


class Develop(develop):
  """Build developer version (pip install -e)."""

  user_options = develop.user_options + [
      # TODO: This has to be `bytes` on Python 2. Remove this `str`
      # call once support for Python 2 is dropped.
      (str("no-make-ui-files"), None, "Don't build UI JS/CSS bundles."),
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
      # TODO: This has to be `bytes` on Python 2. Remove this `str`
      # call once support for Python 2 is dropped.
      (str("no-make-ui-files"), None, "Don't build UI JS/CSS bundles."),
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
            "grr_response_server/gui/static", ignore_dirs=IGNORE_GUI_DIRS),
        find_data_files(
            "grr_response_server/gui/local/static",
            ignore_dirs=IGNORE_GUI_DIRS),
        # TODO: This has to be `bytes` on Python 2. Remove this
        # `str` call once support for Python 2 is dropped.
        [str("version.ini")],
    ))

setup_args = dict(
    name="grr-response-server",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response Server.",
    license="Apache License, Version 2.0",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    url="https://github.com/google/grr",
    cmdclass={
        "sdist": Sdist,
        "develop": Develop
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "grr_console = "
            "grr_response_server.distro_entry:Console",
            "grr_api_shell_raw_access = "
            "grr_response_server.distro_entry:ApiShellRawAccess",
            "grr_config_updater = "
            "grr_response_server.distro_entry:ConfigUpdater",
            "grr_frontend = "
            "grr_response_server.distro_entry:GrrFrontend",
            "grr_server = "
            "grr_response_server.distro_entry:GrrServer",
            "grr_worker = "
            "grr_response_server.distro_entry:Worker",
            "grr_admin_ui = "
            "grr_response_server.distro_entry:AdminUI",
            "fleetspeak_server = "
            "grr_response_server.distro_entry:FleetspeakServer",
        ]
    },
    install_requires=[
        "google-api-python-client==1.9.3",
        "google-auth==1.18.0",
        "grr-api-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-client-builder==%s" %
        VERSION.get("Version", "packagedepends"),
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "ipython==7.15.0",
        "Jinja2==2.11.3",
        # TODO: This should be 2.1
        # If the version of MarkupSafe with Jinja2 dependency is greater than
        # 2.0.1 an issue occurs. Therefore, we are currently fixing the version
        # to 2.0.1, but it will be fixed later when the issue is resolved.
        "MarkupSafe==2.0.1",
        "pexpect==4.8.0",
        "portpicker==1.3.1",
        "prometheus_client==0.8.0",
        "pyjwt==1.7.1",
        "pyOpenSSL==20.0.0",  # https://github.com/google/grr/issues/704
        "python-crontab==2.5.1",
        "python-debian==0.1.37",
        "Werkzeug==1.0.1",
    ],
    extras_require={
        # This is an optional component. Install to get MySQL data
        # store support: pip install grr-response[mysqldatastore]
        # When installing from .deb, the python-mysqldb package is used as
        # dependency instead of this pip dependency. This is because we run into
        # incompatibilities between the system mysqlclient/mariadbclient and the
        # Python library otherwise. Thus, this version has to be equal to the
        # python-mysqldb version of the system we support. This is currently
        # Ubuntu Xenial, see https://packages.ubuntu.com/xenial/python-mysqldb
        #
        # NOTE: the Xenial-provided 1.3.7 version is not properly Python 3
        # compatible. Versions 1.3.13 or later are API-compatible with 1.3.7
        # when running on Python 2 and work correctly on Python 3. However,
        # they don't have Python 2 wheels released, which makes GRR packaging
        # for Python 2 much harder if one of these versions is used.
        #
        # TODO(user): Find a way to use the latest mysqlclient version
        # in GRR server DEB.
        "mysqldatastore": ["mysqlclient==1.3.10"],
        # TODO: We currently release fleetspeak-server-bin packages
        # for Linux only.
        ":sys_platform==\"linux\"": ["fleetspeak-server-bin==0.1.11",],
    },
    data_files=data_files)

setup(**setup_args)
