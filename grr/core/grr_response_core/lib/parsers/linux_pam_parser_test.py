#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for the linux pam config parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_pam_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import config_file as rdf_config_file
from grr.test_lib import artifact_test_lib
from grr.test_lib import test_lib

ETC_PAM_CONF_EMPTY = b"""
# Nothing to do here.
   # white space

# ^ blank line
"""
ETC_PAM_CONF_SIMPLE = b"""
ssh auth required test.so
telnet auth required unix.so
ssh session    required     pam_limits.so
"""
ETC_PAM_CONF_COMPLEX = ETC_PAM_CONF_SIMPLE + b"""
telnet account include filt_include
ssh @include full_include
"""
ETC_PAMD_FILT_INCLUDE = b"""
account    required     pam_nologin.so
auth       required     pam_env.so envfile=/etc/default/locale
"""
ETC_PAMD_FULL_INCLUDE = ETC_PAMD_FILT_INCLUDE
ETC_PAMD_SSH = b"""
auth required test.so  # Comment
session    required     pam_limits.so random=option  # Comment
account include filt_include  # only include 'account' entries from file.
@include full_include  # Include everything from file 'full_include'
"""
ETC_PAMD_TELNET = b"""
# Blank line

# Multi line and 'type' with a leading '-'.
-auth [success=ok new_authtok_reqd=ok ignore=ignore default=bad] \
  testing.so module arguments  # Comments
"""
ETC_PAMD_EXTERNAL = b"""
password substack nonexistant
auth optional testing.so
@include /external/nonexistant
"""

TELNET_ONLY_CONFIG = {'/etc/pam.d/telnet': ETC_PAMD_TELNET}
TELNET_ONLY_CONFIG_EXPECTED = [
    ('telnet', 'auth',
     '[success=ok new_authtok_reqd=ok ignore=ignore default=bad]', 'testing.so',
     'module arguments')
]

TELNET_WITH_PAMCONF = {
    '/etc/pam.conf': ETC_PAM_CONF_EMPTY,
    '/etc/pam.d/telnet': ETC_PAMD_TELNET
}
TELNET_WITH_PAMCONF_EXPECTED = TELNET_ONLY_CONFIG_EXPECTED

PAM_CONF_SIMPLE = {'/etc/pam.conf': ETC_PAM_CONF_SIMPLE}
PAM_CONF_SIMPLE_EXPECTED = [('ssh', 'auth', 'required', 'test.so', ''),
                            ('telnet', 'auth', 'required', 'unix.so', ''),
                            ('ssh', 'session', 'required', 'pam_limits.so', '')]

PAM_CONF_OVERRIDE = {
    '/etc/pam.conf': ETC_PAM_CONF_SIMPLE,
    '/etc/pam.d/telnet': ETC_PAMD_TELNET
}
PAM_CONF_OVERRIDE_EXPECTED = PAM_CONF_SIMPLE_EXPECTED

PAM_CONF_OVERRIDE_COMPLEX = {
    '/etc/pam.conf': ETC_PAM_CONF_COMPLEX,
    '/etc/pam.d/ssh': ETC_PAMD_SSH,
    '/etc/pam.d/full_include': ETC_PAMD_FULL_INCLUDE,
    '/etc/pam.d/filt_include': ETC_PAMD_FILT_INCLUDE,
    '/etc/pam.d/telnet': ETC_PAMD_TELNET
}
PAM_CONF_OVERRIDE_COMPLEX_EXPECTED = PAM_CONF_SIMPLE_EXPECTED + [
    ('telnet', 'account', 'required', 'pam_nologin.so', ''),
    ('ssh', 'account', 'required', 'pam_nologin.so', ''),
    ('ssh', 'auth', 'required', 'pam_env.so', 'envfile=/etc/default/locale')
]

PAM_CONF_TYPICAL = {
    '/etc/pam.conf': ETC_PAM_CONF_EMPTY,
    '/etc/pam.d/ssh': ETC_PAMD_SSH,
    '/etc/pam.d/full_include': ETC_PAMD_FULL_INCLUDE,
    '/etc/pam.d/filt_include': ETC_PAMD_FILT_INCLUDE,
    '/etc/pam.d/telnet': ETC_PAMD_TELNET
}
PAM_CONF_TYPICAL_EXPECTED = TELNET_ONLY_CONFIG_EXPECTED + [
    ('ssh', 'auth', 'required', 'test.so', ''),
    ('ssh', 'session', 'required', 'pam_limits.so', 'random=option'),
    ('ssh', 'account', 'required', 'pam_nologin.so', ''),
    ('ssh', 'account', 'required', 'pam_nologin.so', ''),
    ('ssh', 'auth', 'required', 'pam_env.so', 'envfile=/etc/default/locale'),
    ('filt_include', 'account', 'required', 'pam_nologin.so', ''),
    ('filt_include', 'auth', 'required', 'pam_env.so',
     'envfile=/etc/default/locale'),
    ('full_include', 'account', 'required', 'pam_nologin.so', ''),
    ('full_include', 'auth', 'required', 'pam_env.so',
     'envfile=/etc/default/locale')
]

PAM_CONF_EXTERNAL_REF = {
    '/etc/pam.conf': ETC_PAM_CONF_EMPTY,
    '/etc/pam.d/external': ETC_PAMD_EXTERNAL
}
PAM_CONF_EXTERNAL_REF_EXPECTED = [('external', 'auth', 'optional', 'testing.so',
                                   '')]
PAM_CONF_EXTERNAL_REF_ERRORS = [
    '/etc/pam.d/external -> /etc/pam.d/nonexistant',
    '/etc/pam.d/external -> /external/nonexistant'
]


class LinuxPAMParserTest(test_lib.GRRBaseTest):
  """Test parsing of PAM config files."""

  def setUp(self):
    super(LinuxPAMParserTest, self).setUp()
    self.kb = rdf_client.KnowledgeBase(fqdn='test.example.com', os='Linux')

  def _EntryToTuple(self, entry):
    return (entry.service, entry.type, entry.control, entry.module_path,
            entry.module_args)

  def _EntriesToTuples(self, entries):
    return [self._EntryToTuple(x) for x in entries]

  def testParseMultiple(self):
    """Tests for the ParseMultiple() method."""
    parser = linux_pam_parser.PAMParser()

    # Parse the simplest 'normal' config we can.
    # e.g. a single entry for 'telnet' with no includes etc.
    stats, file_objs = artifact_test_lib.GenStatFileData(TELNET_ONLY_CONFIG)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(TELNET_ONLY_CONFIG_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse the simplest 'normal' config we can but with an effectively
    # empty /etc/pam.conf file.
    # e.g. a single entry for 'telnet' with no includes etc.
    stats, file_objs = artifact_test_lib.GenStatFileData(TELNET_WITH_PAMCONF)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    entry = out[0].entries[0]
    self.assertEqual(
        ('telnet', 'auth',
         '[success=ok new_authtok_reqd=ok ignore=ignore default=bad]',
         'testing.so', 'module arguments'), self._EntryToTuple(entry))
    self.assertCountEqual(TELNET_WITH_PAMCONF_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse a simple old-style pam config. i.e. Just /etc/pam.conf.
    stats, file_objs = artifact_test_lib.GenStatFileData(PAM_CONF_SIMPLE)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(PAM_CONF_SIMPLE_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse a simple old-style pam config overriding a 'new' style config.
    # i.e. Configs in /etc/pam.conf override everything else.
    stats, file_objs = artifact_test_lib.GenStatFileData(PAM_CONF_OVERRIDE)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(PAM_CONF_OVERRIDE_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse a complex old-style pam config overriding a 'new' style config but
    # the /etc/pam.conf includes parts from the /etc/pam.d dir.
    # i.e. Configs in /etc/pam.conf override everything else but imports stuff.
    stats, file_objs = artifact_test_lib.GenStatFileData(
        PAM_CONF_OVERRIDE_COMPLEX)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(PAM_CONF_OVERRIDE_COMPLEX_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse a normal-looking pam configuration.
    # i.e. A no-op of a /etc/pam.conf with multiple files under /etc/pam.d
    #      that have includes etc.
    stats, file_objs = artifact_test_lib.GenStatFileData(PAM_CONF_TYPICAL)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(PAM_CONF_TYPICAL_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertEqual([], out[0].external_config)

    # Parse a config which has references to external or missing files.
    stats, file_objs = artifact_test_lib.GenStatFileData(PAM_CONF_EXTERNAL_REF)
    out = list(parser.ParseMultiple(stats, file_objs, self.kb))
    self.assertLen(out, 1)
    self.assertIsInstance(out[0], rdf_config_file.PamConfig)
    self.assertCountEqual(PAM_CONF_EXTERNAL_REF_EXPECTED,
                          self._EntriesToTuples(out[0].entries))
    self.assertCountEqual(PAM_CONF_EXTERNAL_REF_ERRORS,
                          list(out[0].external_config))


def main(args):
  test_lib.main(args)


if __name__ == '__main__':
  flags.StartMain(main)
