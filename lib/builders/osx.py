#!/usr/bin/env python
"""An implementation of an OSX client builder."""
import os
import shutil
import subprocess

from grr.lib import build
from grr.lib import config_lib


class DarwinClientBuilder(build.ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  def __init__(self, context=None):
    """Initialize the Mac OS X client builder."""
    super(DarwinClientBuilder, self).__init__(context=context)
    self.context.append("Target:Darwin")
    self.build_src_dir = config_lib.CONFIG.Get("ClientBuilder.build_src_dir",
                                               context=self.context)

  def MakeExecutableTemplate(self):
    """Create the executable template.

    This technique allows the client build to be carried out once on the
    supported platform (e.g. windows with MSVS), but the deployable installer
    can be build on any platform which supports python.
    """
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.BuildInstallerPkg()

  # WARNING: change with care since the PackageMaker files are fragile!
  def BuildInstallerPkg(self):
    """Builds a package (.pkg) using PackageMaker."""
    build_files_dir = os.path.join(self.build_src_dir,
                                   "config", "macosx", "client")
    pmdoc_dir = os.path.join(build_files_dir, "grr.pmdoc")

    plist_dir = config_lib.CONFIG.Get(
        "ClientBuilder.plist_binary_directory", context=self.context)
    plist_name = config_lib.CONFIG.Get("ClientBuilder.plist_filename",
                                       context=self.context)

    out_build_files_dir = build_files_dir.replace(self.build_src_dir,
                                                  self.build_dir)
    out_pmdoc_dir = os.path.join(self.build_dir, "%s.pmdoc" % plist_dir)

    self.EnsureDirExists(out_build_files_dir)
    self.EnsureDirExists(out_pmdoc_dir)
    self.EnsureDirExists(config_lib.CONFIG.Get("ClientBuilder.package_dir",
                                               context=self.context))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "grr.plist.in"),
        output_filename=os.path.join(self.build_dir, plist_name))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "index.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "index.xml"))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "01%s.xml" % plist_dir))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr-contents.xml"),
        output_filename=os.path.join(out_pmdoc_dir,
                                     "01%s-contents.xml" % plist_dir))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "02com.xml.in"),
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

    deployer = build.ClientDeployer(context=self.context)
    deployer.context = self.context

    self.EnsureDirExists(os.path.join(
        config_lib.CONFIG.Get("PyInstaller.build_dir", context=self.context),
        config_lib.CONFIG.Get("PyInstaller.output_basename",
                              context=self.context)))
    # Generate a config file.
    with open(os.path.join(
        config_lib.CONFIG.Get("PyInstaller.build_dir", context=self.context),
        config_lib.CONFIG.Get("ClientBuilder.plist_binary_name",
                              context=self.context),
        config_lib.CONFIG.Get("PyInstaller.config_name",
                              context=self.context)), "wb") as fd:
      fd.write(deployer.GetClientConfig(("Client Context", "Platform:Darwin"),
                                        validate=False))

    print "Fixing file ownership and permissions"
    command = ["sudo", "chown", "-R", "root:wheel", self.build_dir]

    # Change the owner, group and permissions of the binaries
    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    command = ["sudo", "chmod", "-R", "755", self.build_dir]

    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    print "Building a package with PackageMaker"
    pkg = "%s-%s.pkg" % (
        config_lib.CONFIG.Get("ClientBuilder.package_maker_name",
                              context=self.context),
        config_lib.CONFIG.Get("Client.version_string", context=self.context))

    output_pkg_path = os.path.join(config_lib.CONFIG.Get(
        "ClientBuilder.package_dir", context=self.context), pkg)
    command = [
        config_lib.CONFIG.Get("ClientBuilder.package_maker_path",
                              context=self.context),
        "--doc", out_pmdoc_dir, "--out", output_pkg_path]

    print "Running: %s " % " ".join(command)
    subprocess.call(command)

    output_tmpl_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                             context=self.context)
    print "Copying output to templates location: %s -> %s" % (output_pkg_path,
                                                              output_tmpl_path)
    self.EnsureDirExists(os.path.dirname(output_tmpl_path))
    shutil.copyfile(output_pkg_path, output_tmpl_path)
