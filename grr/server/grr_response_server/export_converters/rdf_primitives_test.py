#!/usr/bin/env python
from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server.export_converters import rdf_primitives
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class RDFBytesToExportedBytesConverterTest(export_test_lib.ExportTestBase):

  def testRDFBytesConverter(self):
    data = rdfvalue.RDFBytes(b"foobar")

    converter = rdf_primitives.RDFBytesToExportedBytesConverter()
    results = list(converter.Convert(self.metadata, data))

    self.assertNotEmpty(results)

    exported_bytes = [
        r for r in results if r.__class__.__name__ == "ExportedBytes"
    ]
    self.assertLen(exported_bytes, 1)

    self.assertEqual(exported_bytes[0].data, data)
    self.assertEqual(exported_bytes[0].length, 6)


class RDFStringToExportedStringConverterTest(export_test_lib.ExportTestBase):

  def testRDFStringConverter(self):
    data = rdfvalue.RDFString("foobar")

    converter = rdf_primitives.RDFStringToExportedStringConverter()
    results = list(converter.Convert(self.metadata, data))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_primitives.ExportedString)
    self.assertEqual(results[0].data, str(data))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
