#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.export_converters import software_package
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class SoftwarePackageConverterTest(export_test_lib.ExportTestBase):

  def testConvertsCorrectly(self):
    result = rdf_client.SoftwarePackage.Pending(
        name="foo",
        version="ver1",
        architecture="i386",
        publisher="somebody",
        description="desc",
        installed_on=42,
        installed_by="user")

    converter = software_package.SoftwarePackageConverter()
    converted = list(converter.Convert(self.metadata, result))

    self.assertLen(converted, 1)
    self.assertEqual(
        converted[0],
        software_package.ExportedSoftwarePackage(
            metadata=self.metadata,
            name="foo",
            version="ver1",
            architecture="i386",
            publisher="somebody",
            install_state=software_package.ExportedSoftwarePackage.InstallState
            .PENDING,
            description="desc",
            installed_on=42,
            installed_by="user"))


class SoftwarePackagesConverterTest(export_test_lib.ExportTestBase):

  def testConvertsCorrectly(self):
    result = rdf_client.SoftwarePackages()
    for i in range(10):
      result.packages.append(
          rdf_client.SoftwarePackage.Pending(
              name="foo_%d" % i,
              version="ver_%d" % i,
              architecture="i386_%d" % i,
              publisher="somebody_%d" % i,
              description="desc_%d" % i,
              installed_on=42 + i,
              installed_by="user_%d" % i))

    converter = software_package.SoftwarePackagesConverter()
    converted = list(converter.Convert(self.metadata, result))

    self.assertLen(converted, 10)
    for i, r in enumerate(converted):
      self.assertEqual(
          r,
          software_package.ExportedSoftwarePackage(
              metadata=self.metadata,
              name="foo_%d" % i,
              version="ver_%d" % i,
              architecture="i386_%d" % i,
              publisher="somebody_%d" % i,
              install_state=software_package.ExportedSoftwarePackage
              .InstallState.PENDING,
              description="desc_%d" % i,
              installed_on=42 + i,
              installed_by="user_%d" % i))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
