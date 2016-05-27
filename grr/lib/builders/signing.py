#!/usr/bin/env python
"""Library for client code signing."""

import cStringIO
import os
import platform
import subprocess
import tempfile

# pexpect cannot be installed on windows, and this code is only designed to run
# on linux anyway
# pylint: disable=g-import-not-at-top
if platform.system() == "Linux":
  import pexpect

import logging

# pylint: enable=g-import-not-at-top


class Error(Exception):
  pass


class SigningError(Error):
  pass


class CodeSigner(object):
  pass


class WindowsCodeSigner(CodeSigner):
  """Class to handle windows code signing."""

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
      return open(outfile, "r").read()

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
      output_log = cStringIO.StringIO()
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

  def AddSignatureToRPM(self, rpm_filename):
    """Sign RPM with rpmsign."""
    # The horrible second argument here is necessary to get a V3 signature to
    # support CentOS 5 systems. See:
    # http://ilostmynotes.blogspot.com/2016/03/the-horror-of-signing-rpms-that-support.html
    args = [
        "--define=%%_gpg_name %s" % self.gpg_name,
        ("--define=__gpg_sign_cmd %%{__gpg} gpg --force-v3-sigs "
         "--digest-algo=sha1 --batch --no-verbose --no-armor --passphrase-fd 3 "
         "--no-secmem-warning -u '%s' -sbo %%{__signature_filename} "
         "%%{__plaintext_filename}" % self.gpg_name), "--addsign", rpm_filename
    ]

    try:
      output_log = cStringIO.StringIO()
      rpmsign = pexpect.spawn("rpmsign", args)
      # Use logfile_read so we don't get the password we're injecting.
      rpmsign.logfile_read = output_log
      rpmsign.expect("Enter pass phrase:")
      rpmsign.sendline(self.password)
      rpmsign.wait()
    except pexpect.ExceptionPexpect:
      output_log.seek(0)
      logging.exception(output_log.read())
      raise

    try:
      # Expected output is: filename.rpm: rsa sha1 (md5) pgp md5 OK
      output = subprocess.check_output(["rpm", "--checksig", rpm_filename])
      if "pgp" not in output:
        raise SigningError("PGP missing checksig %s" % rpm_filename)
    except subprocess.CalledProcessError:
      logging.exception("Bad signature verification on %s", rpm_filename)
      raise SigningError("Bad signature verification on %s" % rpm_filename)
