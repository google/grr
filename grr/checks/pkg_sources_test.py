#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for package source checks."""


from grr.lib import flags
from grr.lib.parsers import config_file
from grr.server.grr_response_server.checks import checks_test_lib
from grr.test_lib import test_lib


class PkgSourceCheckTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    super(PkgSourceCheckTests, cls).setUpClass()

    cls.LoadCheck("pkg_sources.yaml")

  def testAPTDetectUnsupportedTransport(self):
    artifact = "APTSources"
    parser = config_file.APTPackageSourceParser()
    sources = {
        "/etc/apt/sources.list":
            r"""
            # APT sources.list providing the default Ubuntu packages
            #
            deb https://httpredir.debian.org/debian jessie-updates main
            deb https://security.debian.org/ wheezy/updates main
            # comment 2
            """,
        "/etc/apt/sources.list.d/test.list":
            r"""
            deb file:/tmp/debs/ distro main
            deb [arch=amd64,blah=blah] [meh=meh] https://securitytestasdf.debian.org/ wheezy/updates main contrib non-free
            deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main
            """,
        "/etc/apt/sources.list.d/test2.list":
            r"""
            deb http://dl.google.com/linux/chrome/deb/ stable main
            """,
        "/etc/apt/sources.list.d/test3.list":
            r"""
            deb https://security.debian.org/ wheezy/updates main contrib non-free
            """,
        "/etc/apt/sources.list.d/file-test.list":
            r"""
            deb file:/mnt/debian/debs/ distro main
            """,
        "/etc/apt/sources.list.d/rfc822.list":
            r"""
            Type: deb deb-src
            URI: http://security.example.com
              https://dl.google.com
            Suite: testing
            Section: main contrib
            """
    }

    chk_id = "CIS-PKG-SOURCE-UNSUPPORTED-TRANSPORT"
    sym = "Found: APT sources use unsupported transport."
    found = [
        "/etc/apt/sources.list.d/test.list: transport: file,https,https",
        "/etc/apt/sources.list.d/test2.list: transport: http",
        "/etc/apt/sources.list.d/file-test.list: transport: file",
        "/etc/apt/sources.list.d/rfc822.list: transport: http,https"
    ]
    results = self.GenResults([artifact], [sources], [parser])
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testYumDetectUnsupportedTransport(self):
    artifact = "YumSources"
    parser = config_file.YumPackageSourceParser()
    sources = {
        "/etc/yum.repos.d/noproblems.repo":
            r"""
            # comment 1
            [centosdvdiso]
            name=CentOS DVD ISO
            baseurl=https://mirror1.centos.org/CentOS/6/os/i386/
            enabled=1
            gpgcheck=1
            gpgkey=file:///mnt/RPM-GPG-KEY-CentOS-6

            # comment2
            [examplerepo]
            name=Example Repository
            baseurl = https://mirror3.centos.org/CentOS/6/os/i386/
            enabled=1
            gpgcheck=1
            gpgkey=http://mirror.centos.org/CentOS/6/os/i386/RPM-GPG-KEY
            """,
        "/etc/yum.repos.d/test.repo":
            r"""
            [centosdvdiso]
            name=CentOS DVD ISO
            baseurl=file:///mnt/
            https://mirror1.centos.org/CentOS/6/os/i386/
            """,
        "/etc/yum.repos.d/test2.repo":
            r"""
            [centosdvdiso]
            name=CentOS DVD ISO
            baseurl=http://mirror1.centos.org/CentOS/6/os/i386/
            """,
        "/etc/yum.repos.d/file-test.repo":
            r"""
            [centosdvdiso]
            name=CentOS DVD ISO
            baseurl=file:///mnt/
            """
    }

    chk_id = "CIS-PKG-SOURCE-UNSUPPORTED-TRANSPORT"
    sym = "Found: Yum sources use unsupported transport."
    found = [
        "/etc/yum.repos.d/test.repo: transport: file,https",
        "/etc/yum.repos.d/test2.repo: transport: http",
        "/etc/yum.repos.d/file-test.repo: transport: file"
    ]
    results = self.GenResults([artifact], [sources], [parser])
    self.assertCheckDetectedAnom(chk_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
