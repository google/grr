#!/usr/bin/env python
"""Simple parsers for configuration files."""

import logging
from grr.lib import lexer
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils
from grr.parsers import config_file


class LSBInitLexer(lexer.Lexer):
  """Parse out upstart configurations from init scripts.

  Runlevels in /etc/init.d are defined in stanzas like:
  ### BEGIN INIT INFO
  # Provides:             sshd
  # Required-Start:       $remote_fs $syslog
  # Required-Stop:        $remote_fs $syslog
  # Default-Start:        2 3 4 5
  # Default-Stop:         1
  # Short-Description:    OpenBSD Secure Shell server
  ### END INIT INFO
  """

  _tokens = [
      lexer.Token("INITIAL", r"### BEGIN INIT INFO", None, "UPSTART"),
      lexer.Token("UPSTART", r"### END INIT INFO", "Finish", "INITIAL"),
      lexer.Token("UPSTART", r"#\s+([-\w]+):\s+([^#\n]*)", "StoreEntry", None),
      lexer.Token("UPSTART", r"\n\s*\w+", "Finish", None),
      lexer.Token("UPSTART", r"[\n\s.]*", None, None),
      lexer.Token(".*", ".", None, None)
  ]

  required = {"provides", "default-start"}

  def __init__(self):
    self.entries = {}

  def StoreEntry(self, match, **_):
    key, val = match.groups()
    setting = key.strip().lower()
    if setting:
      self.entries[setting] = val

  def Finish(self, **_):
    self.buffer = []

  def ParseEntries(self, data):
    self.Reset()
    self.Feed(utils.SmartStr(data))
    self.Close()
    found = set(self.entries)
    if self.required.issubset(found):
      return self.entries


class LinuxLSBInitParser(parsers.FileParser):
  """Parses LSB style /etc/init.d entries."""

  output_types = ["LinuxServiceInformation"]
  supported_artifacts = ["LinuxLSBInit"]

  def _Facilities(self, condition):
    results = []
    for facility in condition.split():
      for expanded in self.insserv.get(facility, []):
        if expanded not in results:
          results.append(expanded)
    return results

  def _ParseInit(self, init_files):
    init_lexer = LSBInitLexer()
    for path, file_obj in init_files:
      init = init_lexer.ParseEntries(file_obj.read(100000))
      if init:
        service = rdfvalue.LinuxServiceInformation()
        service.name = init.get("provides")
        service.start_mode = "INIT"
        service.start_on = init.get("default-start").split()
        if service.start_on:
          service.starts = True
        service.stop_on = init.get("default-stop")
        service.description = init.get("short-description")
        service.start_after = self._Facilities(init.get("required-start", []))
        service.stop_after = self._Facilities(init.get("required-stop", []))
        yield service
      else:
        logging.debug("No runlevel information found in %s" % path)

  def _InsservExpander(self, facilities, val):
    expanded = []
    if val.startswith("$"):
      vals = facilities.get(val, [])
      for v in vals:
        expanded.extend(self._InsservExpander(facilities, v))
    elif val.startswith("+"):
      expanded.append(val[1:])
    else:
      expanded.append(val)
    return expanded

  def _ParseInsserv(self, data):
    """/etc/insserv.conf* entries define system facilities.

    Full format details are in man 8 insserv, but the basic structure is:
      $variable          facility1 facility2
      $second_variable   facility3 $variable

    Any init script that specifies Required-Start: $second_variable needs to be
    expanded to facility1 facility2 facility3.

    Args:
      data: A string of insserv definitions.
    """
    parser = config_file.FieldParser()
    entries = parser.ParseEntries(data)
    raw = {e[0]: e[1:] for e in entries}
    # Now expand out the facilities to services.
    facilities = {}
    for k, v in raw.iteritems():
      # Remove interactive tags.
      k = k.replace("<", "").replace(">", "")
      facilities[k] = v
    for k, vals in facilities.iteritems():
      self.insserv[k] = []
      for v in vals:
        self.insserv[k].extend(self._InsservExpander(facilities, v))

  def ParseMultiple(self, stats, file_objs, _):
    self.insserv = {}
    paths = [s.pathspec.path for s in stats]
    files = dict(zip(paths, file_objs))
    insserv_data = ""
    init_files = []
    for k, v in files.iteritems():
      if k.startswith("/etc/insserv.conf"):
        insserv_data += "%s\n" % v.read(100000)
      else:
        init_files.append((k, v))
    self._ParseInsserv(insserv_data)
    for rslt in self._ParseInit(init_files):
      yield rslt


class LinuxXinetdParser(parsers.FileParser):
  """Parses xinetd entries."""

  output_types = ["LinuxServiceInformation"]
  supported_artifacts = ["LinuxXinetd"]

  def _ParseSection(self, section, cfg):
    parser = config_file.KeyValueParser()
    # Skip includedir, we get this from the artifact.
    if section.startswith("includedir"):
      return
    elif section.startswith("default"):
      for val in parser.ParseEntries(cfg):
        self.default.update(val)
    elif section.startswith("service"):
      svc = section.replace("service", "").strip()
      if not svc:
        return
      self.entries[svc] = {}
      for val in parser.ParseEntries(cfg):
        self.entries[svc].update(val)

  def _ProcessEntries(self, filename, fd):
    """Extract entries from the xinted config files."""
    parser = config_file.KeyValueParser(kv_sep="{", term="}", sep=None)
    data = fd.read(100000)
    entries = parser.ParseEntries(data)
    for entry in entries:
      for section, cfg in entry.items():
        # The parser returns a list of configs. There will only be one.
        if cfg:
          cfg = cfg[0].strip()
        else:
          cfg = ""
        self._ParseSection(section, cfg)

  def _GenConfig(self, cfg):
    """Interpolate configurations with defaults to generate actual configs."""
    # Some setting names may have a + or - suffix. These indicate that the
    # settings modify the default values.
    merged = self.default.copy()
    for setting, vals in cfg.iteritems():
      option, operator = (setting.split(None, 1) + [None])[:2]
      vals = set(vals)
      default = set(self.default.get(option, []))
      # If there is an operator, updated values accordingly.
      if operator == "+":
        vals = default.union(vals)
      elif operator == "-":
        vals = default.difference(vals)
      merged[option] = list(vals)
    return rdfvalue.AttributedDict(**merged)

  def _GenService(self, name, cfg):
    # Merge the config values.
    service = rdfvalue.LinuxServiceInformation(name=name)
    service.config = self._GenConfig(cfg)
    if service.config.disable == ["no"]:
      service.starts = True
      service.start_mode = "XINETD"
      service.start_after = ["xinetd"]
    return service

  def ParseMultiple(self, stats, file_objs, _):
    self.entries = {}
    self.default = {}
    paths = [s.pathspec.path for s in stats]
    files = dict(zip(paths, file_objs))
    for k, v in files.iteritems():
      self._ProcessEntries(k, v)
    for name, cfg in self.entries.iteritems():
      yield self._GenService(name, cfg)

# TODO(user): Other service startup tools, e.g. upstart, systemd, inetd

