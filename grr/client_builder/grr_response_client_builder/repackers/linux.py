#!/usr/bin/env python
"""Linux client repackers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import logging
import os
import shutil
import subprocess
import zipfile

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers

from grr_response_core import config
from grr_response_core.lib import utils


class LinuxClientRepacker(build.ClientRepacker):
  """Repackage Linux templates."""

  # TODO(user):pytype: incorrect shutil.move() definition in typeshed.
  # pytype: disable=wrong-arg-types
  def _GenerateDPKGFiles(self, template_path):
    """Generates the files needed by dpkg-buildpackage."""

    fleetspeak_enabled = config.CONFIG.Get(
        "Client.fleetspeak_enabled", context=self.context)
    fleetspeak_bundled = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_bundled", context=self.context)

    if fleetspeak_bundled and not fleetspeak_enabled:
      raise build.BuildError("ClientBuilder.fleetspeak_bundled requires "
                             "Client.fleetspeak_enabled to be set.")

    # Rename the generated binaries to the correct name.
    template_binary_dir = os.path.join(template_path, "dist/debian/grr-client")
    package_name = config.CONFIG.Get(
        "ClientBuilder.package_name", context=self.context)
    target_binary_dir = os.path.join(
        template_path, "dist/debian/%s%s" %
        (package_name,
         config.CONFIG.Get("ClientBuilder.target_dir", context=self.context)))
    if package_name == "grr-client":
      # Need to rename the template path or the move will fail.
      shutil.move(template_binary_dir, "%s-template" % template_binary_dir)
      template_binary_dir = "%s-template" % template_binary_dir

    utils.EnsureDirExists(os.path.dirname(target_binary_dir))
    shutil.move(template_binary_dir, target_binary_dir)

    shutil.move(
        os.path.join(target_binary_dir, "grr-client"),
        os.path.join(
            target_binary_dir,
            config.CONFIG.Get("Client.binary_name", context=self.context)))

    deb_in_dir = os.path.join(template_path, "dist/debian/debian.in/")

    if not os.path.isdir(deb_in_dir):
      # This is an universal (fleetspeak + legacy) template.
      # In prior versions, debian.in used to contain different files for a
      # fleetspeak-enabled and legacy template respectively.
      if fleetspeak_enabled:
        deb_in_dir = os.path.join(template_path,
                                  "dist/debian/fleetspeak-debian.in/")
      else:
        deb_in_dir = os.path.join(template_path,
                                  "dist/debian/legacy-debian.in/")

    build_helpers.GenerateDirectory(
        deb_in_dir,
        os.path.join(template_path, "dist/debian"),
        [("grr-client", package_name)],
        context=self.context)

    # Generate directories for the /usr/sbin link.
    utils.EnsureDirExists(
        os.path.join(template_path, "dist/debian/%s/usr/sbin" % package_name))

    if os.path.exists(os.path.join(target_binary_dir, "wrapper.sh.in")):
      build_helpers.GenerateFile(
          os.path.join(target_binary_dir, "wrapper.sh.in"),
          os.path.join(target_binary_dir, "wrapper.sh"),
          context=self.context)
      os.chmod(os.path.join(target_binary_dir, "wrapper.sh"), 0o755)

    if fleetspeak_enabled:
      if fleetspeak_bundled:
        self._GenerateFleetspeakConfig(template_path,
                                       "/etc/fleetspeak-client/textservices")
        self._GenerateBundledFleetspeakFiles(
            os.path.join(template_path, "dist/bundled-fleetspeak"),
            os.path.join(template_path, "dist/debian", package_name))

        shutil.copy(
            config.CONFIG.Get(
                "ClientBuilder.fleetspeak_client_config", context=self.context),
            os.path.join(template_path, "dist", "debian", package_name,
                         "etc/fleetspeak-client/client.config"))

        for filename in (package_name + ".postinst", package_name + ".postrm"):
          os.remove(os.path.join(template_path, "dist", "debian", filename))

      else:
        fleetspeak_service_dir = config.CONFIG.Get(
            "ClientBuilder.fleetspeak_service_dir", context=self.context)
        self._GenerateFleetspeakConfig(template_path, fleetspeak_service_dir)
    else:
      # Generate the nanny template.
      # This exists from client version 3.1.2.5 onwards.
      build_helpers.GenerateFile(
          os.path.join(target_binary_dir, "nanny.sh.in"),
          os.path.join(target_binary_dir, "nanny.sh"),
          context=self.context)

      # Generate the upstart template.
      build_helpers.GenerateFile(
          os.path.join(template_path, "dist/debian/upstart.in/grr-client.conf"),
          os.path.join(template_path, "dist/debian/%s.upstart" % package_name),
          context=self.context)

      # Generate the initd template. The init will not run if it detects upstart
      # is present.
      build_helpers.GenerateFile(
          os.path.join(template_path, "dist/debian/initd.in/grr-client"),
          os.path.join(template_path, "dist/debian/%s.init" % package_name),
          context=self.context)

      # Generate the systemd unit file.
      build_helpers.GenerateFile(
          os.path.join(template_path,
                       "dist/debian/systemd.in/grr-client.service"),
          os.path.join(template_path, "dist/debian/%s.service" % package_name),
          context=self.context)

    # Clean up the template dirs.
    # Some of the dirs might be missing in older template versions, so removing
    # conditionally.
    self._RmTreeIfExists(os.path.join(template_path, "dist/debian/debian.in"))
    self._RmTreeIfExists(
        os.path.join(template_path, "dist/debian/fleetspeak-debian.in"))
    self._RmTreeIfExists(
        os.path.join(template_path, "dist/debian/legacy-debian.in"))
    self._RmTreeIfExists(os.path.join(template_path, "dist/debian/upstart.in"))
    self._RmTreeIfExists(os.path.join(template_path, "dist/debian/initd.in"))
    self._RmTreeIfExists(os.path.join(template_path, "dist/debian/systemd.in"))
    self._RmTreeIfExists(os.path.join(template_path, "dist/fleetspeak"))
    self._RmTreeIfExists(os.path.join(template_path, "dist/bundled-fleetspeak"))

  def _RmTreeIfExists(self, path):
    if os.path.exists(path):
      shutil.rmtree(path)

  # pytype: enable=wrong-arg-types

  def _GenerateFleetspeakConfig(self, build_dir, dest_config_dir):
    """Generates a Fleetspeak config for GRR in the debian build dir."""
    # We need to strip leading /'s or .join will ignore everything that comes
    # before it.
    dest_config_dir = dest_config_dir.lstrip("/")
    source_config = os.path.join(
        build_dir, "dist", "fleetspeak",
        os.path.basename(
            config.CONFIG.Get(
                "ClientBuilder.fleetspeak_config_path", context=self.context)))
    dest_config = os.path.join(
        build_dir, "dist", "debian",
        config.CONFIG.Get("ClientBuilder.package_name", context=self.context),
        dest_config_dir,
        config.CONFIG.Get(
            "Client.fleetspeak_unsigned_config_fname", context=self.context))
    utils.EnsureDirExists(os.path.dirname(dest_config))
    build_helpers.GenerateFile(
        input_filename=source_config,
        output_filename=dest_config,
        context=self.context)

  def _GenerateBundledFleetspeakFiles(self, src_dir, dst_dir):
    files = [
        "etc/fleetspeak-client/communicator.txt",
        "lib/systemd/system/fleetspeak-client.service",
        "usr/bin/fleetspeak-client",
    ]
    for filename in files:
      src = os.path.join(src_dir, filename)
      dst = os.path.join(dst_dir, filename)
      utils.EnsureDirExists(os.path.dirname(dst))
      shutil.copy(src, dst)

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template and create a .deb."""
    buildpackage_binary = "/usr/bin/dpkg-buildpackage"
    if not os.path.exists(buildpackage_binary):
      logging.error("dpkg-buildpackage not found, unable to repack client.")
      return None

    with utils.TempDirectory() as tmp_dir:
      template_dir = os.path.join(tmp_dir, "dist")
      utils.EnsureDirExists(template_dir)

      zf = zipfile.ZipFile(template_path)
      for name in zf.namelist():
        dirname = os.path.dirname(name)
        utils.EnsureDirExists(os.path.join(template_dir, dirname))
        with io.open(os.path.join(template_dir, name), "wb") as fd:
          fd.write(zf.read(name))

      # Generate the dpkg files.
      self._GenerateDPKGFiles(tmp_dir)

      # Create a client config.
      client_context = ["Client Context"] + self.context
      client_config_content = build_helpers.GetClientConfig(client_context)

      # We need to strip leading /'s or .join will ignore everything that comes
      # before it.
      target_dir = config.CONFIG.Get(
          "ClientBuilder.target_dir", context=self.context).lstrip("/")
      agent_dir = os.path.join(
          template_dir, "debian",
          config.CONFIG.Get("ClientBuilder.package_name", context=self.context),
          target_dir)

      with io.open(
          os.path.join(
              agent_dir,
              config.CONFIG.Get(
                  "ClientBuilder.config_filename", context=self.context)),
          "w",
          encoding="utf-8") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(
          os.path.join(
              agent_dir,
              config.CONFIG.Get("Client.binary_name", context=self.context)),
          0o755)

      arch = config.CONFIG.Get("Template.arch", context=self.context)

      try:
        old_working_dir = os.getcwd()
      except OSError:
        old_working_dir = os.environ.get("HOME", "/tmp")

      try:
        os.chdir(template_dir)
        command = [buildpackage_binary, "-uc", "-d", "-b", "-a%s" % arch]

        try:
          subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
          if b"Failed to sign" not in e.output:
            logging.error("Error calling %s.", command)
            logging.error(e.output)
            raise

        filename_base = config.CONFIG.Get(
            "ClientBuilder.debian_package_base", context=self.context)
        output_base = config.CONFIG.Get(
            "ClientRepacker.output_basename", context=self.context)
      finally:
        try:
          os.chdir(old_working_dir)
        except OSError:
          pass

      utils.EnsureDirExists(os.path.dirname(output_path))

      for extension in [
          ".changes",
          config.CONFIG.Get(
              "ClientBuilder.output_extension", context=self.context)
      ]:
        input_name = "%s%s" % (filename_base, extension)
        output_name = "%s%s" % (output_base, extension)

        # TODO(user):pytype: incorrect move() definition in typeshed.
        # pytype: disable=wrong-arg-types
        shutil.move(
            os.path.join(tmp_dir, input_name),
            os.path.join(os.path.dirname(output_path), output_name))
        # pytype: enable=wrong-arg-types

      logging.info("Created package %s", output_path)
      return output_path


class CentosClientRepacker(LinuxClientRepacker):
  """Repackages Linux RPM templates."""

  def _Sign(self, rpm_filename):
    if self.signer:
      return self.signer.AddSignatureToRPMs([rpm_filename])

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template and create a .rpm."""

    rpmbuild_binary = "/usr/bin/rpmbuild"
    if not os.path.exists(rpmbuild_binary):
      logging.error("rpmbuild not found, unable to repack client.")
      return None

    with utils.TempDirectory() as tmp_dir:
      template_dir = os.path.join(tmp_dir, "dist")
      utils.EnsureDirExists(template_dir)

      zf = zipfile.ZipFile(template_path)
      for name in zf.namelist():
        dirname = os.path.dirname(name)
        utils.EnsureDirExists(os.path.join(template_dir, dirname))
        with io.open(os.path.join(template_dir, name), "wb") as fd:
          fd.write(zf.read(name))

      self._ProcessUniversalTemplate(template_dir)

      # Set up a RPM building environment.

      rpm_root_dir = os.path.join(tmp_dir, "rpmbuild")

      rpm_build_dir = os.path.join(rpm_root_dir, "BUILD")
      utils.EnsureDirExists(rpm_build_dir)

      rpm_buildroot_dir = os.path.join(rpm_root_dir, "BUILDROOT")
      utils.EnsureDirExists(rpm_buildroot_dir)

      rpm_rpms_dir = os.path.join(rpm_root_dir, "RPMS")
      utils.EnsureDirExists(rpm_rpms_dir)

      rpm_specs_dir = os.path.join(rpm_root_dir, "SPECS")
      utils.EnsureDirExists(rpm_specs_dir)

      template_binary_dir = os.path.join(tmp_dir, "dist/rpmbuild/grr-client")

      target_binary_dir = "%s%s" % (
          rpm_build_dir,
          config.CONFIG.Get("ClientBuilder.target_dir", context=self.context))

      utils.EnsureDirExists(os.path.dirname(target_binary_dir))
      try:
        shutil.rmtree(target_binary_dir)
      except OSError:
        pass
      # TODO(user):pytype: incorrect move() definition in typeshed.
      # pytype: disable=wrong-arg-types
      shutil.move(template_binary_dir, target_binary_dir)
      # pytype: enable=wrong-arg-types

      client_name = config.CONFIG.Get("Client.name", context=self.context)
      client_binary_name = config.CONFIG.Get(
          "Client.binary_name", context=self.context)
      if client_binary_name != "grr-client":
        # TODO(user):pytype: incorrect move() definition in typeshed.
        # pytype: disable=wrong-arg-types
        shutil.move(
            os.path.join(target_binary_dir, "grr-client"),
            os.path.join(target_binary_dir, client_binary_name))
        # pytype: enable=wrong-arg-types

      if config.CONFIG.Get("Client.fleetspeak_enabled", context=self.context):
        self._GenerateFleetspeakConfig(template_dir, rpm_build_dir)
        if not config.CONFIG.Get(
            "Client.fleetspeak_service_name", context=self.context):
          # The Fleetspeak service name is required when generating the RPM
          # spec file.
          raise build.BuildError("Client.fleetspeak_service_name is not set.")
        if config.CONFIG.Get(
            "ClientBuilder.fleetspeak_bundled", context=self.context):
          self._GenerateBundledFleetspeakFiles(
              os.path.join(template_dir, "bundled-fleetspeak"), rpm_build_dir)
          shutil.copy(
              config.CONFIG.Get(
                  "ClientBuilder.fleetspeak_client_config",
                  context=self.context),
              os.path.join(rpm_build_dir,
                           "etc/fleetspeak-client/client.config"))
      else:
        self._GenerateInitConfigs(template_dir, rpm_build_dir)

      # Generate spec
      spec_filename = os.path.join(rpm_specs_dir, "%s.spec" % client_name)
      build_helpers.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/grr.spec.in"),
          spec_filename,
          context=self.context)

      # Generate prelinking blacklist file
      prelink_target_filename = os.path.join(rpm_build_dir,
                                             "etc/prelink.conf.d",
                                             "%s.conf" % client_name)

      utils.EnsureDirExists(os.path.dirname(prelink_target_filename))
      build_helpers.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/prelink_blacklist.conf.in"),
          prelink_target_filename,
          context=self.context)

      # Create a client config.
      client_context = ["Client Context"] + self.context
      client_config_content = build_helpers.GetClientConfig(client_context)

      with io.open(
          os.path.join(
              target_binary_dir,
              config.CONFIG.Get(
                  "ClientBuilder.config_filename", context=self.context)),
          "w",
          encoding="utf-8") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(os.path.join(target_binary_dir, client_binary_name), 0o755)

      client_arch = config.CONFIG.Get("Template.arch", context=self.context)
      if client_arch == "amd64":
        client_arch = "x86_64"

      # Create wrapper script
      if os.path.exists(os.path.join(target_binary_dir, "wrapper.sh.in")):
        build_helpers.GenerateFile(
            os.path.join(target_binary_dir, "wrapper.sh.in"),
            os.path.join(target_binary_dir, "wrapper.sh"),
            context=self.context)
        os.chmod(os.path.join(target_binary_dir, "wrapper.sh"), 0o755)

      command = [
          rpmbuild_binary, "--define", "_topdir " + rpm_root_dir, "--target",
          client_arch, "--buildroot", rpm_buildroot_dir, "-bb", spec_filename
      ]
      try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError as e:
        logging.error("Error calling %s.", command)
        logging.error(e.output)
        raise

      client_version = config.CONFIG.Get(
          "Template.version_string", context=self.context)
      rpm_filename = os.path.join(
          rpm_rpms_dir, client_arch,
          "%s-%s-1.%s.rpm" % (client_name, client_version, client_arch))

      utils.EnsureDirExists(os.path.dirname(output_path))
      shutil.move(rpm_filename, output_path)

      logging.info("Created package %s", output_path)
      self._Sign(output_path)
      return output_path

  def _GenerateFleetspeakConfig(self, template_dir, rpm_build_dir):
    """Generates a Fleetspeak config for GRR."""
    source_config = os.path.join(
        template_dir, "fleetspeak",
        os.path.basename(
            config.CONFIG.Get(
                "ClientBuilder.fleetspeak_config_path", context=self.context)))
    fleetspeak_service_dir = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_service_dir", context=self.context)
    dest_config_dir = os.path.join(rpm_build_dir, fleetspeak_service_dir[1:])
    utils.EnsureDirExists(dest_config_dir)
    dest_config_path = os.path.join(
        dest_config_dir,
        config.CONFIG.Get(
            "Client.fleetspeak_unsigned_config_fname", context=self.context))
    build_helpers.GenerateFile(
        input_filename=source_config,
        output_filename=dest_config_path,
        context=self.context)

  def _GenerateInitConfigs(self, template_dir, rpm_build_dir):
    """Generates init-system configs."""
    client_name = config.CONFIG.Get("Client.name", context=self.context)
    initd_target_filename = os.path.join(rpm_build_dir, "etc/init.d",
                                         client_name)

    # Generate init.d
    utils.EnsureDirExists(os.path.dirname(initd_target_filename))
    build_helpers.GenerateFile(
        os.path.join(template_dir, "rpmbuild/grr-client.initd.in"),
        initd_target_filename,
        context=self.context)

    # Generate systemd unit
    if config.CONFIG["Template.version_numeric"] >= 3125:
      systemd_target_filename = os.path.join(rpm_build_dir,
                                             "usr/lib/systemd/system/",
                                             "%s.service" % client_name)

      utils.EnsureDirExists(os.path.dirname(systemd_target_filename))
      build_helpers.GenerateFile(
          os.path.join(template_dir, "rpmbuild/grr-client.service.in"),
          systemd_target_filename,
          context=self.context)

  def _ProcessUniversalTemplate(self, dist_dir):
    # An universal teplate contains both fleetspeak and legacy files.
    # If there is a legacy directory, then this is an universal template
    # Depending on the config option, copy only one set of the files into
    # the tree.

    if not os.path.exists(os.path.join(dist_dir, "legacy")):
      return

    if config.CONFIG.Get("Client.fleetspeak_enabled", context=self.context):
      # Since there is fleetspeak/fleetspeak, rename the top-level
      # fleetspeak directory.
      shutil.move(
          os.path.join(dist_dir, "fleetspeak"),
          os.path.join(dist_dir, "_fleetspeak"))
      utils.MergeDirectories(os.path.join(dist_dir, "_fleetspeak"), dist_dir)
    else:
      utils.MergeDirectories(os.path.join(dist_dir, "legacy"), dist_dir)
    self._RmTreeIfExists(os.path.join(dist_dir, "legacy"))
    self._RmTreeIfExists(os.path.join(dist_dir, "_fleetspeak"))
