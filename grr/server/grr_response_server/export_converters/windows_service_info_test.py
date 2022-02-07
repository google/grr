#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.export_converters import windows_service_info
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class WindowsServiceInformationConverterTest(export_test_lib.ExportTestBase):
  """Tests for WindowsServiceInformationConverter."""

  def testExportsValueCoorrectly(self):
    sample = rdf_client.WindowsServiceInformation(
        name="foo",
        description="bar",
        state="somestate",
        wmi_information={
            "c": "d",
            "a": "b"
        },
        display_name="some name",
        driver_package_id="1234",
        error_control=rdf_client.WindowsServiceInformation.ErrorControl.NORMAL,
        image_path="/foo/bar",
        object_name="an object",
        startup_type=rdf_client.WindowsServiceInformation.ServiceMode
        .SERVICE_AUTO_START,
        service_type=rdf_client.WindowsServiceInformation.ServiceType
        .SERVICE_FILE_SYSTEM_DRIVER,
        group_name="somegroup",
        service_dll="somedll",
        registry_key="somekey",
    )

    converter = windows_service_info.WindowsServiceInformationConverter()
    converted = list(converter.Convert(self.metadata, sample))
    self.assertLen(converted, 1)
    c = converted[0]

    self.assertIsInstance(
        c, windows_service_info.ExportedWindowsServiceInformation)
    self.assertEqual(c.metadata, self.metadata)

    self.assertEqual(c.name, "foo")
    self.assertEqual(c.description, "bar")
    self.assertEqual(c.state, "somestate")
    self.assertEqual(c.wmi_information, "a=b,c=d")
    self.assertEqual(c.display_name, "some name")
    self.assertEqual(c.driver_package_id, "1234")
    self.assertEqual(c.error_control, 1)
    self.assertEqual(c.image_path, "/foo/bar")
    self.assertEqual(c.object_name, "an object")
    self.assertEqual(c.startup_type, 2)
    self.assertEqual(c.service_type, 0x2)
    self.assertEqual(c.group_name, "somegroup")
    self.assertEqual(c.service_dll, "somedll")
    self.assertEqual(c.registry_key, "somekey")

  def testExportsEmptyValueCorrectly(self):
    sample = rdf_client.WindowsServiceInformation()

    converter = windows_service_info.WindowsServiceInformationConverter()
    converted = list(converter.Convert(self.metadata, sample))
    self.assertLen(converted, 1)
    c = converted[0]

    self.assertEqual(c.metadata, self.metadata)
    self.assertEqual(c.name, "")
    self.assertEqual(c.description, "")
    self.assertEqual(c.state, "")
    self.assertEqual(c.wmi_information, "")
    self.assertEqual(c.display_name, "")
    self.assertEqual(c.driver_package_id, "")
    self.assertEqual(c.error_control, 0)
    self.assertEqual(c.image_path, "")
    self.assertEqual(c.object_name, "")
    self.assertEqual(c.startup_type, 0)
    self.assertEqual(c.service_type, 0)
    self.assertEqual(c.group_name, "")
    self.assertEqual(c.service_dll, "")
    self.assertEqual(c.registry_key, "")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
