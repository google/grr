#!/usr/bin/env python
"""Classes for exporting CheckResult."""

from typing import Iterator

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.check_lib import checks
from grr_response_server.export_converters import base


class ExportedAnomaly(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedAnomaly


class ExportedCheckResult(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedCheckResult
  rdf_deps = [
      ExportedAnomaly,
      base.ExportedMetadata,
  ]


class CheckResultConverter(base.ExportConverter):
  """Converts CheckResult into ExportedCheckResult."""

  input_rdf_type = checks.CheckResult

  def Convert(self, metadata: base.ExportedMetadata,
              checkresult: checks.CheckResult) -> Iterator[ExportedCheckResult]:
    """Converts a single CheckResult.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      checkresult: CheckResult to be converted.

    Yields:
      Resulting ExportedCheckResult. Empty list is a valid result and means that
      conversion wasn't possible.
    """

    if checkresult.HasField("anomaly"):
      for anomaly in checkresult.anomaly:
        exported_anomaly = ExportedAnomaly(
            type=anomaly.type,
            severity=anomaly.severity,
            confidence=anomaly.confidence)
        if anomaly.symptom:
          exported_anomaly.symptom = anomaly.symptom
        if anomaly.explanation:
          exported_anomaly.explanation = anomaly.explanation
        if anomaly.generated_by:
          exported_anomaly.generated_by = anomaly.generated_by
        if anomaly.anomaly_reference_id:
          exported_anomaly.anomaly_reference_id = "\n".join(
              anomaly.anomaly_reference_id)
        if anomaly.finding:
          exported_anomaly.finding = "\n".join(anomaly.finding)
        yield ExportedCheckResult(
            metadata=metadata,
            check_id=checkresult.check_id,
            anomaly=exported_anomaly)
    else:
      yield ExportedCheckResult(
          metadata=metadata, check_id=checkresult.check_id)
