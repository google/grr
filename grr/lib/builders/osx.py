#!/usr/bin/env python
"""An implementation of an OSX client builder."""
import getpass
import logging
import os
import shutil
import StringIO
import subprocess
import zipfile

from grr.lib import build
from grr.lib import config_lib
from grr.lib import utils


class DarwinClientBuilder(build.ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  def __init__(self, context=None):
    """Initialize the Mac OS X client builder."""
    super(DarwinClientBuilder, self).__init__(context=context)
    self.context.append("Target:Darwin")
    self.pkg_dir = config_lib.CONFIG.Get("ClientBuilder.package_dir",
                                         context=self.context)

  def MakeExecutableTemplate(self, output_file=None):
    """Create the executable template."""
    super(DarwinClientBuilder, self).MakeExecutableTemplate(
        output_file=output_file)
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.CopyMissingModules()
    self.BuildInstallerPkg(output_file)
    self.MakeZip(output_file, self.template_file)

  def MakeZip(self, xar_file, output_file):
    """Add a zip to the end of the .xar containing build.yaml.

    The build.yaml is already inside the .xar file, but we can't easily open
    this on linux. To make repacking easier we add a zip to the end of the .xar
    and add in the build.yaml. The repack step will then look at the build.yaml
    and insert the config.yaml. We end up storing the build.yaml twice but it is
    tiny, so this doesn't matter.

    Args:
      xar_file: the name of the xar file.
      output_file: the name of the output ZIP archive.
    """
    logging.info("Generating zip template file at %s", output_file)
    with zipfile.ZipFile(output_file, mode="a") as zf:
      # Get the build yaml
      build_yaml = StringIO.StringIO()
      self.WriteBuildYaml(build_yaml)
      build_yaml.seek(0)
      zf.writestr("build.yaml", build_yaml.read())

  def MakeBuildDirectory(self):
    super(DarwinClientBuilder, self).MakeBuildDirectory()
    self.CleanDirectory(self.pkg_dir)

  # WARNING: change with care since the PackageMaker files are fragile!
  def BuildInstallerPkg(self, output_file):
    """Builds a package (.pkg) using PackageMaker."""
    build_files_dir = config_lib.Resource().Filter("install_data/macosx/client")

    pmdoc_dir = os.path.join(build_files_dir, "grr.pmdoc")

    client_name = config_lib.CONFIG.Get("Client.name", context=self.context)
    plist_name = config_lib.CONFIG.Get("Client.plist_filename",
                                       context=self.context)

    out_build_files_dir = build_files_dir.replace(
        config_lib.Resource().Filter("grr"), self.build_dir)
    out_pmdoc_dir = os.path.join(self.build_dir, "%s.pmdoc" % client_name)

    utils.EnsureDirExists(out_build_files_dir)
    utils.EnsureDirExists(out_pmdoc_dir)
    utils.EnsureDirExists(config_lib.CONFIG.Get("ClientBuilder.package_dir",
                                                context=self.context))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "grr.plist.in"),
        output_filename=os.path.join(self.build_dir, plist_name))
    self.GenerateFile(input_filename=os.path.join(pmdoc_dir, "index.xml.in"),
                      output_filename=os.path.join(out_pmdoc_dir, "index.xml"))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "01%s.xml" % client_name))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr-contents.xml"),
        output_filename=os.path.join(out_pmdoc_dir,
                                     "01%s-contents.xml" % client_name))
    self.GenerateFile(input_filename=os.path.join(pmdoc_dir, "02com.xml.in"),
                      output_filename=os.path.join(out_pmdoc_dir, "02com.xml"))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "02com-contents.xml"),
        output_filename=os.path.join(out_pmdoc_dir, "02com-contents.xml"))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "preinstall.sh.in"),
        output_filename=os.path.join(self.build_dir, "preinstall.sh"))
    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "postinstall.sh.in"),
        output_filename=os.path.join(self.build_dir, "postinstall.sh"))

    output_basename = config_lib.CONFIG.Get("ClientBuilder.output_basename",
                                            context=self.context)

    # Rename the generated binaries to the correct name.
    template_binary_dir = os.path.join(
        config_lib.CONFIG.Get("PyInstaller.distpath",
                              context=self.context),
        "grr-client")
    target_binary_dir = os.path.join(self.build_dir, "%s" % output_basename)

    if template_binary_dir != target_binary_dir:
      shutil.move(template_binary_dir, target_binary_dir)

    shutil.move(
        os.path.join(target_binary_dir, "grr-client"),
        os.path.join(target_binary_dir,
                     config_lib.CONFIG.Get("Client.binary_name",
                                           context=self.context)))

    repacker = build.ClientRepacker(context=self.context)
    repacker.context = self.context

    # Generate a config file.
    with open(
        os.path.join(target_binary_dir,
                     config_lib.CONFIG.Get("ClientBuilder.config_filename",
                                           context=self.context)),
        "wb") as fd:
      fd.write(repacker.GetClientConfig(["Client Context"] + self.context,
                                        validate=False))

    print "Fixing file ownership and permissions"

    command = ["sudo", "/usr/sbin/chown", "-R", "root:wheel", self.build_dir]
    # Change the owner, group and permissions of the binaries
    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    command = ["sudo", "/bin/chmod", "-R", "755", self.build_dir]

    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    print "Building a package with PackageMaker"
    pkg = "%s-%s.pkg" % (
        config_lib.CONFIG.Get("Client.name", context=self.context),
        config_lib.CONFIG.Get("Source.version_string",
                              context=self.context))

    output_pkg_path = os.path.join(self.pkg_dir, pkg)
    command = [
        config_lib.CONFIG.Get("ClientBuilder.package_maker_path",
                              context=self.context), "--doc", out_pmdoc_dir,
        "--out", output_pkg_path
    ]

    print "Running: %s " % " ".join(command)
    ret = subprocess.call(command)
    if ret != 0:
      msg = "PackageMaker returned an error (%d)." % ret
      print msg
      raise RuntimeError(msg)

    print "Copying output to templates location: %s -> %s" % (output_pkg_path,
                                                              output_file)
    utils.EnsureDirExists(os.path.dirname(output_file))
    shutil.copyfile(output_pkg_path, output_file)

    # Change the owner, group and permissions of the binaries back.
    command = ["sudo", "/usr/sbin/chown", "-R", "%s:staff" % getpass.getuser(),
               self.build_dir]
    print "Running: %s" % " ".join(command)
    subprocess.call(command)
