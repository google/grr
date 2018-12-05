#!/usr/bin/env python
"""Library for client code signing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import logging
import os
import platform
import subprocess
import tempfile

# pexpect cannot be installed on windows, and this code is only designed to run
# on linux anyway
# pylint: disable=g-import-not-at-top
if platform.system() == "Linux":
  import pexpect

# pylint: enable=g-import-not-at-top


class Error(Exception):
  pass


class SigningError(Error):
  pass


class CodeSigner(object):
  pass


class WindowsSigntoolCodeSigner(CodeSigner):
  """Class to handle windows code signing on Windows hosts using signtool."""

  def __init__(self, signing_cmdline, verification_cmdline):
    if not signing_cmdline:
      raise ValueError("Need a signing cmd line to use the signtool signer.")

    self._signing_cmdline = signing_cmdline
    self._verification_cmdline = verification_cmdline

  def SignBuffer(self, in_buffer):
    fd, path = tempfile.mkstemp()
    try:
      with os.fdopen(fd, "wb") as temp_in:
        temp_in.write(in_buffer)
      self.SignFile(path)
      with open(path, "rb") as temp_out:
        res = temp_out.read()
      return res
    finally:
      os.unlink(path)

  def SignFile(self, in_filename, out_filename=None):
    """Signs a file."""
    if out_filename:
      raise NotImplementedError(
          "WindowsSigntoolCodeSigner does not support out_filename.")
    return self.SignFiles([in_filename])

  def SignFiles(self, filenames):
    """Signs multiple files at once."""
    file_list = " ".join(filenames)
    subprocess.check_call("%s %s" % (self._signing_cmdline, file_list))
    if self._verification_cmdline:
      subprocess.check_call("%s %s" % (self._verification_cmdline, file_list))


class WindowsOsslsigncodeCodeSigner(CodeSigner):
  """Class to handle windows code signing on Linux hosts using osslsigncode."""

  def __init__(self, cert, key, password, application):
    self.cert = cert
    self.key = key
    self.password = password
    self.application = application

  def SignBuffer(self, in_buffer):
    """Sign a buffer via temp files.

    Our signing tool can't sign a buffer, so we work around it using temporary
    files.

    Args:
      in_buffer: data to sign
    Returns:
      signed data
    """
    with tempfile.NamedTemporaryFile() as temp_in:
      temp_in.write(in_buffer)
      temp_in.seek(0)
      outfile = self.SignFile(temp_in.name)
      return open(outfile, "rb").read()

  def SignFile(self, in_filename, out_filename=None):
    """Sign a file using osslsigncode.

    Args:
      in_filename: file to read from
      out_filename: file to output to, if none we output to the same filename as
                    the input with a .signed suffix.
    Returns:
      output filename string
    Raises:
      pexpect.ExceptionPexpect: if the expect invocation of osslsigncode fails.
      SigningError: for signing failures.
    """
    if out_filename is None:
      out_filename = "%s.signed" % in_filename

    args = [
        "-certs", self.cert, "-key", self.key, "-n", self.application, "-t",
        "http://timestamp.verisign.com/scripts/timestamp.dll", "-h", "sha1",
        "-in", in_filename, "-out", out_filename
    ]

    try:
      output_log = io.StringIO()
      ossl = pexpect.spawn("osslsigncode", args)
      # Use logfile_read so we don't get the password we're injecting.
      ossl.logfile_read = output_log
      ossl.expect("Enter PEM pass phrase")
      ossl.sendline(self.password)
      ossl.wait()
    except pexpect.ExceptionPexpect:
      output_log.seek(0)
      logging.exception(output_log.read())
      raise

    if not os.path.exists(out_filename):
      raise SigningError("Expected output %s not created" % out_filename)

    try:
      subprocess.check_call(["osslsigncode", "verify", "-in", out_filename])
    except subprocess.CalledProcessError:
      logging.exception("Bad signature verification on %s", out_filename)
      raise SigningError("Bad signature verification on %s" % out_filename)

    return out_filename


class RPMCodeSigner(CodeSigner):
  """Class to handle signing built RPMs signing."""

  def __init__(self, password, public_key_file, gpg_name):
    self.password = password
    self.gpg_name = gpg_name
    try:
      subprocess.check_call(["rpm", "--import", public_key_file])
    except subprocess.CalledProcessError:
      logging.exception("Couldn't import public key %s", public_key_file)
      raise SigningError("Couldn't import public key %s" % public_key_file)

  def AddSignatureToRPMs(self, rpm_filenames):
    """Sign RPM with rpmsign."""
    # The horrible second argument here is necessary to get a V3 signature to
    # support CentOS 5 systems. See:
    # http://ilostmynotes.blogspot.com/2016/03/the-horror-of-signing-rpms-that-support.html
    args = [
        "--define=%%_gpg_name %s" % self.gpg_name,
        ("--define=__gpg_sign_cmd %%{__gpg} gpg --force-v3-sigs --yes "
         "--digest-algo=sha1 --no-verbose --no-armor --pinentry-mode loopback "
         "--no-secmem-warning -u '%s' -sbo %%{__signature_filename} "
         "%%{__plaintext_filename}" % self.gpg_name), "--addsign"
    ] + rpm_filenames

    try:
      output_log = io.StringIO()
      rpmsign = pexpect.spawn("rpmsign", args, timeout=1000)
      # Use logfile_read so we don't get the password we're injecting.
      rpmsign.logfile_read = output_log
      rpmsign.expect("phrase:")
      rpmsign.sendline(self.password)
      rpmsign.wait()
    except pexpect.exceptions.EOF:
      # This could have worked using a cached passphrase, we check for the
      # actual signature below and raise if the package wasn't signed after all.
      pass
    except pexpect.ExceptionPexpect:
      logging.error(output_log.getvalue())
      raise

    for rpm_filename in rpm_filenames:
      try:
        # Expected output is: filename.rpm: rsa sha1 (md5) pgp md5 OK
        output = subprocess.check_output(["rpm", "--checksig", rpm_filename])
        if "pgp" not in output:
          raise SigningError("PGP missing checksig %s" % rpm_filename)
      except subprocess.CalledProcessError:
        logging.exception("Bad signature verification on %s", rpm_filename)
        raise SigningError("Bad signature verification on %s" % rpm_filename)
