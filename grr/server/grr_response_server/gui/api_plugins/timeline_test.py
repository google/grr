#!/usr/bin/env python
# Lint as: python3
import csv
import io
import random
import stat
from typing import Optional
from typing import Sequence
from typing import Text
import zipfile

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import chunked
from grr_response_server import data_store
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import testing_startup


class ApiGetCollectedTimelineHandlerTest(api_test_lib.ApiCallHandlerTest):

  @classmethod
  def setUpClass(cls):
    super(ApiGetCollectedTimelineHandlerTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super(ApiGetCollectedTimelineHandlerTest, self).setUp()
    self.handler = api_timeline.ApiGetCollectedTimelineHandler()

  def testRaisesOnIncorrectFlowType(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = "A1B3C5D7E"

    flow_obj = rdf_flow_objects.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = flow_id
    flow_obj.flow_class_name = "NotTimelineFlow"
    flow_obj.create_time = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteFlowObject(flow_obj)

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesOnIncorrectFormat(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, [])

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.UNSPECIFIED

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testBodyNoEntries(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, [])

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    result = self.handler.Handle(args)
    content = b"".join(result.GenerateContent()).decode("utf-8")

    rows = list(csv.reader(io.StringIO(content), delimiter="|"))
    self.assertLen(rows, 0)

  def testBodySingleEntry(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "/foo/bar/baz".encode("utf-8")
    entry.ino = 4815162342
    entry.size = 42
    entry.atime_ns = 123 * 10**9
    entry.mtime_ns = 456 * 10**9
    entry.ctime_ns = 789 * 10**9

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, [entry])

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    result = self.handler.Handle(args)
    content = b"".join(result.GenerateContent()).decode("utf-8")

    rows = list(csv.reader(io.StringIO(content), delimiter="|"))
    self.assertLen(rows, 1)
    self.assertEqual(rows[0][1], "/foo/bar/baz")
    self.assertEqual(rows[0][2], "4815162342")
    self.assertEqual(rows[0][6], "42")
    self.assertEqual(rows[0][7], "123")
    self.assertEqual(rows[0][8], "456")
    self.assertEqual(rows[0][9], "789")

  def testBodyMultipleEntries(self):
    entries = []

    for idx in range(1024):
      entry = rdf_timeline.TimelineEntry()
      entry.path = "/foo/bar/baz/quux/norf/thud{}".format(idx).encode("utf-8")
      entry.size = random.randint(0, 1024)
      entries.append(entry)

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, entries)

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    result = self.handler.Handle(args)
    content = b"".join(result.GenerateContent()).decode("utf-8")

    rows = list(csv.reader(io.StringIO(content), delimiter="|"))
    self.assertLen(rows, len(entries))

    for idx, row in enumerate(rows):
      self.assertEqual(row[1].encode("utf-8"), entries[idx].path)
      self.assertEqual(int(row[6]), entries[idx].size)

  def testRawGzchunkedEmpty(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, [])

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED

    content = b"".join(self.handler.Handle(args).GenerateContent())

    buf = io.BytesIO(content)
    self.assertIsNone(chunked.Read(buf))

  def testRawGzchunkedMulipleEntries(self):
    entries = []

    for idx in range(1024):
      entry = rdf_timeline.TimelineEntry()
      entry.path = "/quux/thud/bar/baz/foo{}".format(idx).encode("utf-8")
      entry.size = random.randint(0, 1024)
      entries.append(entry)

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = _WriteTimeline(client_id, entries)

    args = api_timeline.ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED

    content = b"".join(self.handler.Handle(args).GenerateContent())

    buf = io.BytesIO(content)
    chunks = chunked.ReadAll(buf)
    deserialized = list(rdf_timeline.TimelineEntry.DeserializeStream(chunks))

    self.assertEqual(entries, deserialized)


class ApiGetCollectedHuntTimelinesHandlerTest(api_test_lib.ApiCallHandlerTest):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.handler = api_timeline.ApiGetCollectedHuntTimelinesHandler()

  def testRaisesOnIncorrectFlowType(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    hunt_id = "A0B1D2C3E4"

    hunt_obj = rdf_hunt_objects.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.client_ids = [client_id]
    hunt_obj.args.standard.flow_name = "NotTimelineFlow"
    hunt_obj.hunt_state = rdf_hunt_objects.Hunt.HuntState.PAUSED

    data_store.REL_DB.WriteHuntObject(hunt_obj)

    args = api_timeline.ApiGetCollectedHuntTimelinesArgs()
    args.hunt_id = hunt_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesOnIncorrectFormat(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    hunt_id = "B1C2E3D4F5"

    hunt_obj = rdf_hunt_objects.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.client_ids = [client_id]
    hunt_obj.args.standard.flow_name = timeline.TimelineFlow.__name__
    hunt_obj.hunt_state = rdf_hunt_objects.Hunt.HuntState.PAUSED

    data_store.REL_DB.WriteHuntObject(hunt_obj)

    args = api_timeline.ApiGetCollectedHuntTimelinesArgs()
    args.hunt_id = hunt_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.UNSPECIFIED

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testBodyMultipleClients(self):
    client_id_1 = db_test_utils.InitializeClient(data_store.REL_DB)
    client_id_2 = db_test_utils.InitializeClient(data_store.REL_DB)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id_1
    snapshot.knowledge_base.fqdn = "bar.quux.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id_2
    snapshot.knowledge_base.fqdn = "bar.quuz.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    hunt_id = "B1C2E3D4F5"

    hunt_obj = rdf_hunt_objects.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.client_ids = [client_id_1, client_id_2]
    hunt_obj.args.standard.flow_name = timeline.TimelineFlow.__name__
    hunt_obj.hunt_state = rdf_hunt_objects.Hunt.HuntState.PAUSED

    data_store.REL_DB.WriteHuntObject(hunt_obj)

    entry_1 = rdf_timeline.TimelineEntry()
    entry_1.path = "/bar/baz/quux".encode("utf-8")
    entry_1.ino = 5926273453
    entry_1.size = 13373
    entry_1.atime_ns = 111 * 10**9
    entry_1.mtime_ns = 222 * 10**9
    entry_1.ctime_ns = 333 * 10**9
    entry_1.mode = 0o664

    entry_2 = rdf_timeline.TimelineEntry()
    entry_2.path = "/bar/baz/quuz".encode("utf-8")
    entry_2.ino = 6037384564
    entry_2.size = 13374
    entry_2.atime_ns = 777 * 10**9
    entry_2.mtime_ns = 888 * 10**9
    entry_2.ctime_ns = 999 * 10**9
    entry_2.mode = 0o777

    _WriteTimeline(client_id_1, [entry_1], hunt_id=hunt_id)
    _WriteTimeline(client_id_2, [entry_2], hunt_id=hunt_id)

    args = api_timeline.ApiGetCollectedHuntTimelinesArgs()
    args.hunt_id = hunt_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.BODY

    content = b"".join(self.handler.Handle(args).GenerateContent())
    buffer = io.BytesIO(content)

    with zipfile.ZipFile(buffer, mode="r") as archive:
      client_filename_1 = f"{client_id_1}_bar.quux.com.body"
      with archive.open(client_filename_1, mode="r") as file:
        content_file = file.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(content_file), delimiter="|"))
        self.assertLen(rows, 1)
        self.assertEqual(rows[0][1], "/bar/baz/quux")
        self.assertEqual(rows[0][2], "5926273453")
        self.assertEqual(rows[0][3], stat.filemode(0o664))
        self.assertEqual(rows[0][6], "13373")
        self.assertEqual(rows[0][7], "111")
        self.assertEqual(rows[0][8], "222")
        self.assertEqual(rows[0][9], "333")

      client_filename_2 = f"{client_id_2}_bar.quuz.com.body"
      with archive.open(client_filename_2, mode="r") as file:
        content_file = file.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(content_file), delimiter="|"))
        self.assertLen(rows, 1)
        self.assertEqual(rows[0][1], "/bar/baz/quuz")
        self.assertEqual(rows[0][2], "6037384564")
        self.assertEqual(rows[0][3], stat.filemode(0o777))
        self.assertEqual(rows[0][6], "13374")
        self.assertEqual(rows[0][7], "777")
        self.assertEqual(rows[0][8], "888")
        self.assertEqual(rows[0][9], "999")

  def testRawGzchunkedMultipleClients(self):
    client_id_1 = db_test_utils.InitializeClient(data_store.REL_DB)
    client_id_2 = db_test_utils.InitializeClient(data_store.REL_DB)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id_1
    snapshot.knowledge_base.fqdn = "foo.quux.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id_2
    snapshot.knowledge_base.fqdn = "foo.norf.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    hunt_id = "A0B1D2C3E4"

    hunt_obj = rdf_hunt_objects.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.client_ids = [client_id_1, client_id_2]
    hunt_obj.args.standard.flow_name = timeline.TimelineFlow.__name__
    hunt_obj.hunt_state = rdf_hunt_objects.Hunt.HuntState.PAUSED

    data_store.REL_DB.WriteHuntObject(hunt_obj)

    entry_1 = rdf_timeline.TimelineEntry()
    entry_1.path = "foo_1".encode("utf-8")
    entry_1.ino = 5432154321
    entry_1.size = 13371
    entry_1.atime_ns = 122 * 10**9
    entry_1.mtime_ns = 233 * 10**9
    entry_1.ctime_ns = 344 * 10**9
    entry_1.mode = 0o663

    entry_2 = rdf_timeline.TimelineEntry()
    entry_2.path = "foo_2".encode("utf-8")
    entry_1.ino = 7654376543
    entry_2.size = 13372
    entry_1.atime_ns = 788 * 10**9
    entry_1.mtime_ns = 899 * 10**9
    entry_1.ctime_ns = 900 * 10**9
    entry_1.mode = 0o763

    _WriteTimeline(client_id_1, [entry_1], hunt_id=hunt_id)
    _WriteTimeline(client_id_2, [entry_2], hunt_id=hunt_id)

    args = api_timeline.ApiGetCollectedHuntTimelinesArgs()
    args.hunt_id = hunt_id
    args.format = api_timeline.ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED

    content = b"".join(self.handler.Handle(args).GenerateContent())
    buffer = io.BytesIO(content)

    with zipfile.ZipFile(buffer, mode="r") as archive:
      client_filename_1 = f"{client_id_1}_foo.quux.com.gzchunked"
      with archive.open(client_filename_1, mode="r") as file:
        chunks = chunked.ReadAll(file)
        entries = list(rdf_timeline.TimelineEntry.DeserializeStream(chunks))
        self.assertEqual(entries, [entry_1])

      client_filename_2 = f"{client_id_2}_foo.norf.com.gzchunked"
      with archive.open(client_filename_2, mode="r") as file:
        chunks = chunked.ReadAll(file)
        entries = list(rdf_timeline.TimelineEntry.DeserializeStream(chunks))
        self.assertEqual(entries, [entry_2])


def _WriteTimeline(
    client_id: Text,
    entries: Sequence[rdf_timeline.TimelineEntry],
    hunt_id: Optional[Text] = None,
) -> Text:
  """Writes a timeline to the database (as fake flow result).

  Args:
    client_id: An identifier of the client for which the flow ran.
    entries: A sequence of timeline entries produced by the flow run.
    hunt_id: An (optional) identifier of a hunt the flows belong to.

  Returns:
    An identifier of the flow.
  """
  flow_id = "".join(random.choice("ABCDEF") for _ in range(8))

  flow_obj = rdf_flow_objects.Flow()
  flow_obj.flow_id = flow_id
  flow_obj.client_id = client_id
  flow_obj.flow_class_name = timeline.TimelineFlow.__name__
  flow_obj.create_time = rdfvalue.RDFDatetime.Now()
  flow_obj.parent_hunt_id = hunt_id
  data_store.REL_DB.WriteFlowObject(flow_obj)

  blobs = list(rdf_timeline.TimelineEntry.SerializeStream(iter(entries)))
  blob_ids = data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)

  result = rdf_timeline.TimelineResult()
  result.entry_batch_blob_ids = [blob_id.AsBytes() for blob_id in blob_ids]

  flow_result = rdf_flow_objects.FlowResult()
  flow_result.client_id = client_id
  flow_result.flow_id = flow_id
  flow_result.payload = result

  data_store.REL_DB.WriteFlowResults([flow_result])

  return flow_id


if __name__ == "__main__":
  absltest.main()
