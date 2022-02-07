#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_server.check_lib import checks
from grr_response_server.export_converters import check_result
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class CheckResultConverterTest(export_test_lib.ExportTestBase):

  def testNoAnomaly(self):
    checkresult = checks.CheckResult(check_id="check-id-1")
    converter = check_result.CheckResultConverter()
    results = list(converter.Convert(self.metadata, checkresult))

    self.assertLen(results, 1)
    self.assertEqual(results[0].check_id, checkresult.check_id)
    self.assertFalse(results[0].HasField("anomaly"))

  def testWithAnomaly(self):
    checkresult = checks.CheckResult(
        check_id="check-id-2",
        anomaly=[
            rdf_anomaly.Anomaly(
                type="PARSER_ANOMALY",
                symptom="something was wrong on the system"),
            rdf_anomaly.Anomaly(
                type="MANUAL_ANOMALY",
                symptom="manually found wrong stuff",
                anomaly_reference_id=["id1", "id2"],
                finding=["file has bad permissions: /tmp/test"]),
        ])
    converter = check_result.CheckResultConverter()
    results = list(converter.Convert(self.metadata, checkresult))

    self.assertLen(results, 2)
    self.assertEqual(results[0].check_id, checkresult.check_id)
    self.assertEqual(results[0].anomaly.type, checkresult.anomaly[0].type)
    self.assertEqual(results[0].anomaly.symptom, checkresult.anomaly[0].symptom)
    self.assertEqual(results[1].check_id, checkresult.check_id)
    self.assertEqual(results[1].anomaly.type, checkresult.anomaly[1].type)
    self.assertEqual(results[1].anomaly.symptom, checkresult.anomaly[1].symptom)
    self.assertEqual(results[1].anomaly.anomaly_reference_id,
                     "\n".join(checkresult.anomaly[1].anomaly_reference_id))
    self.assertEqual(results[1].anomaly.finding,
                     checkresult.anomaly[1].finding[0])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
