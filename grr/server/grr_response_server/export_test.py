#!/usr/bin/env python
"""Tests for export converters."""
from typing import Optional
from unittest import mock

from absl import app
from absl.testing import absltest

from google.protobuf import wrappers_pb2
from google.protobuf import message
from grr_response_core.lib import rdfvalue
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.export_converters import base
from grr_response_server.export_converters import proto_wrappers
from grr.test_lib import db_test_lib
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class GetExportedMetadataProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    assert data_store.REL_DB is not None
    self.db: abstract_db.Database = data_store.REL_DB
    self.test_user = db_test_utils.InitializeUser(self.db)
    self.client_id = db_test_utils.InitializeClient(self.db)

  def testGetExportedMetadataProtoWithSingleUserLabel(self):
    label_owner = self.test_user
    data_store.REL_DB.AddClientLabels(
        self.client_id, label_owner, ["client-label"]
    )

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(metadata.labels, "client-label")
    self.assertEqual(metadata.user_labels, "client-label")
    self.assertEqual(metadata.system_labels, "")

  def testGetExportedMetadataProtoWithTwoUserLabels(self):
    label_owner = self.test_user
    data_store.REL_DB.AddClientLabels(self.client_id, label_owner, ["a", "b"])

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(metadata.labels, "a,b")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "")

  def testGetExportedMetadataProtoWithSystemLabels(self):
    data_store.REL_DB.WriteGRRUser("GRR")
    label_owner = self.test_user
    data_store.REL_DB.AddClientLabels(self.client_id, label_owner, ["a", "b"])
    data_store.REL_DB.AddClientLabels(self.client_id, "GRR", ["c"])

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(metadata.labels, "a,b,c")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "c")

  def testGetExportedMetadataProtoMissingKB(self):
    client_id = "C.3421081084815162"
    data_store.REL_DB.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(42)
    )

    metadata = export.GetExportedMetadataProto(
        client_id, data_store.REL_DB.ReadClientFullInfo(client_id)
    )
    self.assertFalse(metadata.usernames)

  def testGetExportedMetadataProtoClientInfo(self):
    # We use a new client that has `first_seen` metadata set.
    client_id = "C.4815162342108108"
    data_store.REL_DB.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(42)
    )
    snapshot = objects_pb2.ClientSnapshot(client_id=client_id)
    snapshot.os_release = "7"
    snapshot.os_version = "1.1.1111"
    snapshot.kernel = "2.2.2222"
    snapshot.knowledge_base.os = "Windows"
    snapshot.knowledge_base.fqdn = "Host-1.example.com"
    snapshot.knowledge_base.users.add(username="Local")
    snapshot.knowledge_base.users.add(username="user")
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetExportedMetadataProto(
        client_id, data_store.REL_DB.ReadClientFullInfo(client_id)
    )
    self.assertEqual(metadata.client_urn, f"aff4:/{client_id}")
    self.assertEqual(metadata.client_id, client_id)
    self.assertEqual(metadata.client_age, 42)
    self.assertEqual(metadata.hostname, "Host-1.example.com")
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.os_release, "7")
    self.assertEqual(metadata.os_version, "1.1.1111")
    self.assertEqual(metadata.kernel_version, "2.2.2222")
    self.assertEqual(metadata.usernames, "Local,user")

  def testGetExportedMetadataProtoWithoutCloudInstanceSet(self):
    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertFalse(metadata.HasField("cloud_instance_type"))
    self.assertFalse(metadata.HasField("cloud_instance_id"))

  def testGetExportedMetadataProtoWithGoogleCloudInstanceID(self):
    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.cloud_instance.cloud_type = jobs_pb2.CloudInstance.GOOGLE
    snapshot.cloud_instance.google.unique_id = "foo/bar"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(
        metadata.cloud_instance_type,
        export_pb2.ExportedMetadata.CloudInstanceType.GOOGLE,
    )
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")

  def testGetExportedMetadataProtoWithAmazonCloudInstanceID(self):
    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.cloud_instance.cloud_type = jobs_pb2.CloudInstance.AMAZON
    snapshot.cloud_instance.amazon.instance_id = "foo/bar"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(
        metadata.cloud_instance_type,
        export_pb2.ExportedMetadata.CloudInstanceType.AMAZON,
    )
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")

  def testGetExportedMetadataProtoNoMacAddress(self):
    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEmpty(metadata.mac_address)

  def testGetExportedMetadataProtoSingleMacAddress(self):
    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.interfaces.add(mac_address=b"\x00\x01\x02\x03\x04\x05")
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(metadata.mac_address, "000102030405")

  def testGetExportedMetadataProtoMultipleMacAddresses(self):
    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.interfaces.add(mac_address=b"\x00\x01\x02\x03\x04\x05")
    snapshot.interfaces.add(mac_address=b"\x06\x07\x08\x09\x0a\x0b")
    # This empty MAC address should be ignored.
    snapshot.interfaces.add(mac_address=b"\x00\x00\x00\x00\x00\x00")
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetExportedMetadataProto(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id)
    )
    self.assertEqual(metadata.mac_address, "000102030405\n060708090a0b")


class Int64Converter(base.ExportConverterProto):
  input_proto_type = wrappers_pb2.Int64Value
  output_proto_types = (
      export_pb2.ExportedString,
      export_pb2.ExportedBytes,
  )

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.Int64Value,
  ) -> list[export_pb2.ExportedString | export_pb2.ExportedBytes]:
    del metadata  # Unused.
    str_value = str(value.value)
    return [
        export_pb2.ExportedString(data=str_value),
        export_pb2.ExportedBytes(
            data=str_value.encode("utf-8"), length=len(str_value)
        ),
    ]


class FetchMetadataAndConvertFlowResultsTest(absltest.TestCase):

  def _GetPackedFlowResult(
      self, payload: message.Message, client_id: Optional[str] = None
  ) -> flows_pb2.FlowResult:
    flow_result = flows_pb2.FlowResult()
    flow_result.payload.Pack(payload)
    if client_id:
      flow_result.client_id = client_id
    return flow_result

  @db_test_lib.WithDatabase
  def testNoConverter(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.BoolValue(value=True), client_id
    )

    results = list(
        export.FetchMetadataAndConvertFlowResults(
            source_urn=rdfvalue.RDFURN(f"aff4:/clients/{client_id}/flows/F:1"),
            options=export_pb2.ExportOptions(),
            flow_results=[flow_result],
        )
    )
    self.assertEmpty(results)

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testMetadataAppendsAnnotations(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foobar"), client_id
    )
    with mock.patch.object(
        export, "GetExportedMetadataProto"
    ) as mock_get_metadata:
      mock_get_metadata.return_value = export_pb2.ExportedMetadata(
          client_id=client_id,
          annotations="existing",
      )
      results = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
              options=export_pb2.ExportOptions(annotations=["new"]),
              flow_results=[flow_result],
          )
      )
      self.assertEqual(results[0].metadata.annotations, "existing,new")

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testMetadataDoesNotOverwriteTimestamp(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foobar"), client_id
    )

    with mock.patch.object(
        export, "GetExportedMetadataProto"
    ) as mock_get_metadata:
      mock_get_metadata.return_value = export_pb2.ExportedMetadata(
          client_id=client_id,
          timestamp=123,  # shouldn't be overwritten
      )
      results = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
              options=export_pb2.ExportOptions(),
              flow_results=[flow_result],
          )
      )
    self.assertEqual(results[0].metadata.timestamp, 123)

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testMetadataEnrichmentForFetchedClientSetsMissingFields(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foobar"), client_id
    )
    with mock.patch.object(
        rdfvalue.RDFDatetime,
        "Now",
        return_value=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(42),
    ):
      with mock.patch.object(
          export, "GetExportedMetadataProto"
      ) as mock_get_metadata:
        mock_get_metadata.return_value = export_pb2.ExportedMetadata(
            client_id=client_id
            # FetchMetadataAndConvertFlowResults should set both timestamp
            # and annotations missing from here.
        )
        results = list(
            export.FetchMetadataAndConvertFlowResults(
                source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
                options=export_pb2.ExportOptions(
                    annotations=["hello", "world"]
                ),
                flow_results=[flow_result],
            )
        )
    self.assertEqual(
        results[0].metadata.timestamp,
        42,
    )
    self.assertEqual(results[0].metadata.annotations, "hello,world")

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  def testMetadataEnrichmentForUnfetchedClient(self):
    client_id = "C.1234567890123456"
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foobar"), client_id
    )
    with mock.patch.object(
        rdfvalue.RDFDatetime,
        "Now",
        return_value=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(42),
    ):
      results = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
              options=export_pb2.ExportOptions(annotations=["new"]),
              flow_results=[flow_result],
          )
      )

    self.assertEqual(
        results[0].metadata.timestamp,
        42,
    )
    self.assertEqual(results[0].metadata.annotations, "new")
    self.assertEqual(results[0].metadata.client_id, client_id)
    self.assertEqual(results[0].metadata.source_urn, "aff4:/hunts/H:123456")

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testSingleClient(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foobar"), client_id
    )

    now = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(42)
    with mock.patch.object(rdfvalue.RDFDatetime, "Now", return_value=now):
      results = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=rdfvalue.RDFURN(f"aff4:/clients/{client_id}"),
              options=export_pb2.ExportOptions(annotations=["annotation1"]),
              flow_results=[flow_result],
          )
      )

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedString)
    self.assertEqual(results[0].data, "foobar")
    self.assertEqual(
        results[0].metadata.source_urn,
        f"aff4:/clients/{client_id}",
    )
    self.assertEqual(results[0].metadata.client_id, client_id)
    self.assertEqual(results[0].metadata.timestamp, 42)
    self.assertEqual(results[0].metadata.annotations, "annotation1")

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testMultipleClients(self, db: abstract_db.Database):
    client_id_1 = db_test_utils.InitializeClient(db)
    client_id_2 = db_test_utils.InitializeClient(db)

    flow_result_1 = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foo"), client_id_1
    )
    flow_result_2 = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="bar"), client_id_2
    )

    results = list(
        export.FetchMetadataAndConvertFlowResults(
            source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
            options=export_pb2.ExportOptions(),
            flow_results=[flow_result_1, flow_result_2],
        )
    )

    self.assertLen(results, 2)
    self.assertEqual(results[0].metadata.client_id, client_id_1)
    self.assertEqual(results[0].metadata.source_urn, "aff4:/hunts/H:123456")
    self.assertEqual(results[0].data, "foo")
    self.assertEqual(results[1].metadata.client_id, client_id_2)
    self.assertEqual(results[1].metadata.source_urn, "aff4:/hunts/H:123456")
    self.assertEqual(results[1].data, "bar")

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @export_test_lib.WithExportConverterProto(Int64Converter)
  @db_test_lib.WithDatabase
  def testMultipleResultTypes(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    str_flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foo"), client_id
    )
    int64_flow_result = self._GetPackedFlowResult(
        wrappers_pb2.Int64Value(value=123), client_id
    )

    results = list(
        export.FetchMetadataAndConvertFlowResults(
            source_urn=rdfvalue.RDFURN(f"aff4:/clients/{client_id}/flows/F:1"),
            options=export_pb2.ExportOptions(),
            flow_results=[
                str_flow_result,
                int64_flow_result,
            ],
            cached_metadata={
                client_id: export_pb2.ExportedMetadata(client_id=client_id)
            },
        )
    )
    self.assertLen(results, 3)
    self.assertCountEqual(
        results,
        [
            export_pb2.ExportedString(
                metadata=export_pb2.ExportedMetadata(client_id=client_id),
                data="foo",
            ),
            export_pb2.ExportedString(
                data="123",
            ),
            export_pb2.ExportedBytes(
                data=b"123",
                length=3,
            ),
        ],
    )

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  def testClientNotInDB(self):
    client_id = "C.1111222233334444"

    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foo"), client_id
    )
    results = list(
        export.FetchMetadataAndConvertFlowResults(
            source_urn=rdfvalue.RDFURN("aff4:/hunts/H:123456"),
            options=export_pb2.ExportOptions(),
            flow_results=[flow_result],
        )
    )
    self.assertLen(results, 1)
    self.assertEqual(results[0].data, "foo")
    self.assertEqual(results[0].metadata.client_id, client_id)

  @export_test_lib.WithExportConverterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  @db_test_lib.WithDatabase
  def testCachedMetadata(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    source_urn = rdfvalue.RDFURN(f"aff4:/clients/{client_id}/flows/F:123")

    flow_result = self._GetPackedFlowResult(
        wrappers_pb2.StringValue(value="foo"), client_id
    )

    cached_metadata = {}
    with mock.patch.object(
        data_store.REL_DB,
        "MultiReadClientFullInfo",
        wraps=data_store.REL_DB.MultiReadClientFullInfo,
    ) as mock_read:
      # First call should call DB and fill cache.
      results1 = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=source_urn,
              options=export_pb2.ExportOptions(),
              flow_results=[flow_result],
              cached_metadata=cached_metadata,
          )
      )
      self.assertLen(results1, 1)
      mock_read.assert_called_once()
      self.assertIn(client_id, cached_metadata)

      mock_read.reset_mock()

      # Second call should use cache.
      results2 = list(
          export.FetchMetadataAndConvertFlowResults(
              source_urn=source_urn,
              options=export_pb2.ExportOptions(),
              flow_results=[flow_result],
              cached_metadata=cached_metadata,
          )
      )
      self.assertLen(results2, 1)
      mock_read.assert_not_called()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
