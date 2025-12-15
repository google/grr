#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
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
        installed_by="user",
        epoch=7,
        source_rpm="foo-1.3.3.7.fc39.src.rpm",
        source_deb="java-common (0.75)",
    )

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
            install_state=software_package.ExportedSoftwarePackage.InstallState.PENDING,
            description="desc",
            installed_on=42,
            installed_by="user",
            epoch=7,
            source_rpm="foo-1.3.3.7.fc39.src.rpm",
            source_deb="java-common (0.75)",
        ),
    )


class SoftwarePackageConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testConvertsCorrectly(self):
    result = sysinfo_pb2.SoftwarePackage(
        name="foo",
        version="ver1",
        architecture="i386",
        publisher="somebody",
        install_state=sysinfo_pb2.SoftwarePackage.InstallState.PENDING,
        description="desc",
        installed_on=42,
        installed_by="user",
        epoch=7,
        source_rpm="foo-1.3.3.7.fc39.src.rpm",
        source_deb="java-common (0.75)",
    )

    converter = software_package.SoftwarePackageConverterProto()
    converted = list(converter.Convert(self.metadata_proto, result))

    self.assertLen(converted, 1)
    self.assertEqual(
        converted[0],
        export_pb2.ExportedSoftwarePackage(
            metadata=self.metadata_proto,
            name="foo",
            version="ver1",
            architecture="i386",
            publisher="somebody",
            install_state=export_pb2.ExportedSoftwarePackage.InstallState.PENDING,
            description="desc",
            installed_on=42,
            installed_by="user",
            epoch=7,
            source_rpm="foo-1.3.3.7.fc39.src.rpm",
            source_deb="java-common (0.75)",
        ),
    )


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
              installed_by="user_%d" % i,
              epoch=i,
              source_rpm=f"foo_{i}.src.rpm",
              source_deb=f"foo-{i}",
          )
      )

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
              install_state=software_package.ExportedSoftwarePackage.InstallState.PENDING,
              description="desc_%d" % i,
              installed_on=42 + i,
              installed_by="user_%d" % i,
              epoch=i,
              source_rpm=f"foo_{i}.src.rpm",
              source_deb=f"foo-{i}",
          ),
      )


class SoftwarePackagesConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testConvertsCorrectly(self):
    result = sysinfo_pb2.SoftwarePackages()
    for i in range(10):
      result.packages.append(
          sysinfo_pb2.SoftwarePackage(
              name=f"foo_{i}",
              version=f"ver_{i}",
              architecture=f"i386_{i}",
              publisher=f"somebody_{i}",
              install_state=sysinfo_pb2.SoftwarePackage.InstallState.PENDING,
              description=f"desc_{i}",
              installed_on=42 + i,
              installed_by=f"user_{i}",
              epoch=i,
              source_rpm=f"foo_{i}.src.rpm",
              source_deb=f"foo-{i}",
          )
      )

    converter = software_package.SoftwarePackagesConverterProto()
    converted = list(converter.Convert(self.metadata_proto, result))

    self.assertLen(converted, 10)
    for i, r in enumerate(converted):
      self.assertEqual(
          r,
          export_pb2.ExportedSoftwarePackage(
              metadata=self.metadata_proto,
              name=f"foo_{i}",
              version=f"ver_{i}",
              architecture=f"i386_{i}",
              publisher=f"somebody_{i}",
              install_state=export_pb2.ExportedSoftwarePackage.InstallState.PENDING,
              description=f"desc_{i}",
              installed_on=42 + i,
              installed_by=f"user_{i}",
              epoch=i,
              source_rpm=f"foo_{i}.src.rpm",
              source_deb=f"foo-{i}",
          ),
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
