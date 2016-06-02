#!/usr/bin/env python
"""A client component management tool.

Documentation of using this tool is available in
grr/client/components/README.txt.
"""



import imp
import logging
import os
import shutil
import StringIO
import subprocess
import zipfile


import pip

from grr.lib import config_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client


def _PathStartsWithSkippedModules(path, modules):
  for mod in modules:
    if path.startswith(mod):
      return True

# These are modules which already exist on the client and do not need to be
# packaged in a component.
SKIPPED_MODULES = [
    "_markerlib",
    "pip",
    "setuptools",
    "wheel",
    "pkg_resources",
    "easy_install",
    "python_dateutil",
    "python-dateutil",
    "yaml",
    "pytz",
    "six",
    "PyYAML",
    "pyyaml",

    # This is a core package but it is sometimes installed via pip.
    "argparse",

    # The following are introduced by pypiwin32.
    "pypiwin32",
    "win32comext",
    "win32com",
    "adobeapi",
    "PyWin32",
    "isapi",
    "pythoncom",
    "pythonwin",
    "pywin32",
    "win32",
]


def GetCleanEnvironment():
  """Restore environment to pre-virtualenv activate.

  If we are already running inside a virtualenv and we shell out to another
  virtualenv this wont work because the new activate script will add the second
  virtualenv to the path _after_ the current virtualenv. We therefore need to
  restore the environment to what it was before the current virtualenv was
  running before we launch another one.

  The code below is essentially implementing the virtualenv deactivate script.

  Returns:
    A clean environment.
  """
  env = os.environ.copy()
  old_virtual_prompt = env.pop("_OLD_VIRTUAL_PROMPT", None)
  if old_virtual_prompt:
    env["PROMPT"] = old_virtual_prompt

  old_virtual_path = env.pop("_OLD_VIRTUAL_PATH", None)
  if old_virtual_path:
    env["PATH"] = old_virtual_path

  return env


def CheckUselessComponentModules(virtualenv_interpreter):
  """Log warnings about useless client components modules.

  When we package the client component it may also include python modules which
  already exist on the client. These modules will not actually be imported in
  the client when the component loads - they are already imported into the
  client process and Python caches imports.

  We may decide not to include those modules (by adding them to
  SKIPPPED_MODULES) but this decision can only be made with cosideration to the
  age of the clients already deployed. For example, a newer client might include
  a module which does not exist in an older client, and therefore it is safer
  for the component to also bring this module.

  For this reason we just log the conflict for consideration.

  Args:
    virtualenv_interpreter: The path to the component virtualenv interpreter.
  """
  virtualenv_pip = os.path.join(os.path.dirname(virtualenv_interpreter), "pip")
  component_modules = set(subprocess.check_output(
      [virtualenv_pip, "freeze"],
      env=GetCleanEnvironment()).splitlines(),)

  client_modules = dict((x.key, x.version)
                        for x in pip.get_installed_distributions())

  for component_name in component_modules:
    dist_name, version = component_name.split("==")
    # We already know about it - it will not be packaged.
    if dist_name in SKIPPED_MODULES:
      continue

    client_mod_version = client_modules.get(dist_name)
    if client_mod_version is not None:
      print "Useless client module %s" % dist_name

      if client_mod_version != version:
        print("Conflicting component module version (%s)"
              "with client version (%s):") % (version, client_mod_version)


def BuildComponents(output_dir=None):

  components_dir = config_lib.CONFIG["ClientBuilder.components_source_dir"]

  for root, _, files in os.walk(components_dir):
    if "setup.py" in files:
      BuildComponent(os.path.join(root, "setup.py"), output_dir=output_dir)


def GetVirtualEnvBinary(virtual_env_path, name):
  interpreter = os.path.join(virtual_env_path, "bin", name)
  if not os.access(interpreter, os.X_OK):
    interpreter = os.path.join(virtual_env_path, "Scripts", name)

  return interpreter


def BuildComponent(setup_path, output_dir=None):
  """Builds a single component."""

  if not output_dir:
    output_dir = config_lib.CONFIG["ClientBuilder.components_dir"]

  # Get component configuration from setup.py.
  module = imp.load_source("setup", setup_path)
  setup_args = module.setup_args

  with utils.TempDirectory() as tmp_dirname:
    print "Building component %s, Version %s" % (setup_args["name"],
                                                 setup_args["version"])
    print "Creating Virtual Env %s" % tmp_dirname
    subprocess.check_call(["virtualenv", tmp_dirname],
                          env=GetCleanEnvironment())

    subprocess.check_call([GetVirtualEnvBinary(tmp_dirname, "pip"), "install",
                           "--upgrade", "setuptools", "wheel"])

    # Pip installs data files dependencies in the root of the virtualenv. We
    # need to find them and move them into the component.
    root_dirs = set(os.listdir(tmp_dirname))
    subprocess.check_call(
        [GetVirtualEnvBinary(tmp_dirname, "pip"), "install", "."],
        cwd=os.path.dirname(module.__file__),
        env=GetCleanEnvironment())

    component_path = os.path.join(tmp_dirname, "lib/python2.7/site-packages")
    if not os.access(component_path, os.R_OK):
      component_path = os.path.join(tmp_dirname, "lib/site-packages")

    for directory in os.listdir(tmp_dirname):
      if directory not in root_dirs:
        logging.debug("Copying new directories %s", directory)
        shutil.copytree(
            os.path.join(tmp_dirname, directory),
            os.path.join(component_path, directory))

    out_fd = StringIO.StringIO()
    component_archive = zipfile.ZipFile(out_fd,
                                        "w",
                                        compression=zipfile.ZIP_DEFLATED)

    # Warn about incompatible modules.
    interpreter = GetVirtualEnvBinary(tmp_dirname, "python")
    CheckUselessComponentModules(interpreter)

    # These modules are assumed to already exist in the client and therefore do
    # not need to be re-packaged in the component.
    skipped_modules = SKIPPED_MODULES
    for root, dirs, files in os.walk(component_path):
      for file_name in files:
        filename = os.path.join(root, file_name)
        # Unzip egg files to keep it simple.
        if filename.endswith(".egg"):
          data = StringIO.StringIO(open(filename, "rb").read())
          os.unlink(filename)
          zipfile.ZipFile(data).extractall(filename)
          dirs.append(filename)
          continue

        archive_filename = os.path.relpath(filename, component_path)
        if archive_filename.endswith(".pyc"):
          continue

        if _PathStartsWithSkippedModules(archive_filename, skipped_modules):
          continue

        component_archive.write(filename, archive_filename)

    component_archive.close()

    result = rdf_client.ClientComponent(
        summary=rdf_client.ClientComponentSummary(
            name=setup_args["name"],
            version=setup_args["version"],
            modules=setup_args["py_modules"],),
        build_system=rdf_client.Uname.FromCurrentSystem(),)

    # Components will be encrypted using AES128CBC
    result.summary.cipher.SetAlgorithm("AES128CBC")

    # Clear these non important fields about the build box.
    result.build_system.fqdn = None
    result.build_system.node = None
    result.build_system.kernel = None

    print "Built component:"
    print result

    result.raw_data = out_fd.getvalue()

    utils.EnsureDirExists(output_dir)

    output = os.path.join(output_dir,
                          "%s_%s_%s.bin" % (result.summary.name,
                                            result.summary.version,
                                            result.build_system.signature()))

    with open(output, "wb") as fd:
      fd.write(result.SerializeToString())

    print "Component saved as %s" % output

    return result
