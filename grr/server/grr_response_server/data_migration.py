#!/usr/bin/env python
"""Helper class to migrate data."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from multiprocessing import pool
import sys
import threading
import traceback


from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import objects as rdf_objects

_CLIENT_BATCH_SIZE = 200
_BLOB_BATCH_SIZE = 1000
_CLIENT_VERSION_THRESHOLD = rdfvalue.Duration("24h")
_PROGRESS_INTERVAL = rdfvalue.Duration("1s")


def _MapWithPool(func, iterable, thread_count):
  tp = pool.ThreadPool(processes=thread_count)
  tp.map(func, iterable)
  tp.terminate()
  tp.join()


class UsersMigrator(object):
  """Migrates users objects from AFF4 to REL_DB."""

  def __init__(self):
    self._lock = threading.Lock()

    self._total_count = 0
    self._migrated_count = 0
    self._start_time = None
    self._last_progress_time = None

  def _GetUsers(self):
    urns = aff4.FACTORY.ListChildren("aff4:/users")
    return sorted(
        aff4.FACTORY.MultiOpen(urns, aff4_type=aff4_users.GRRUser),
        key=lambda u: u.urn.Basename())

  def Execute(self):
    """Runs the migration procedure."""
    if not data_store.RelationalDBWriteEnabled():
      raise ValueError("No relational database available.")

    sys.stdout.write("Collecting clients...\n")
    users = self._GetUsers()

    sys.stdout.write("Users to migrate: {}\n".format(len(users)))
    for u in users:
      self._MigrateUser(u)

  def _MigrateUser(self, u):
    """Migrates individual AFF4 user object to REL_DB."""

    sys.stdout.write("Migrating user {}\n".format(u.urn.Basename()))

    password = u.Get(u.Schema.PASSWORD, None)
    gui_settings = u.Get(u.Schema.GUI_SETTINGS)
    if "admin" in u.GetLabelsNames():
      user_type = rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN
    else:
      user_type = rdf_objects.GRRUser.UserType.USER_TYPE_STANDARD

    if password:
      sys.stdout.write(
          "Warning: Unable to migrate password for user {}\n".format(
              u.urn.Basename()))

    data_store.REL_DB.WriteGRRUser(
        u.urn.Basename(),
        ui_mode=gui_settings.mode,
        canary_mode=gui_settings.canary_mode,
        user_type=user_type)
    sys.stdout.write("User migration success for the user {}\n".format(
        u.urn.Basename()))


def Migrate(thread_count=300):
  """Migrates clients from the legacy storage to the relational database.

  Args:
    thread_count: A number of threads to execute thr migration with.
  """
  ClientsMigrator().Execute(thread_count)
  UsersMigrator().Execute()


class ClientsMigrator(object):
  """A simple worker class that uses thread pool to drive the migration."""

  def __init__(self):
    self._lock = threading.Lock()

    self._total_count = 0
    self._migrated_count = 0
    self._start_time = None
    self._last_progress_time = None

  def Execute(self, thread_count):
    """Runs the migration procedure.

    Args:
      thread_count: A number of threads to execute the migration with.

    Raises:
      AssertionError: If not all clients have been migrated.
      ValueError: If the relational database backend is not available.
    """
    if not data_store.RelationalDBWriteEnabled():
      raise ValueError("No relational database available.")

    sys.stdout.write("Collecting clients...\n")
    client_urns = _GetClientUrns()

    sys.stdout.write("Clients to migrate: {}\n".format(len(client_urns)))
    sys.stdout.write("Threads to use: {}\n".format(thread_count))

    self._total_count = len(client_urns)
    self._migrated_count = 0
    self._start_time = rdfvalue.RDFDatetime.Now()

    batches = collection.Batch(client_urns, _CLIENT_BATCH_SIZE)

    self._Progress()
    _MapWithPool(self._MigrateBatch, list(batches), thread_count)
    self._Progress()

    if self._migrated_count == self._total_count:
      message = "\nMigration has been finished (migrated {} clients).\n".format(
          self._migrated_count)
      sys.stdout.write(message)
    else:
      message = "Not all clients have been migrated ({}/{})".format(
          self._migrated_count, self._total_count)
      raise AssertionError(message)

  def _MigrateBatch(self, batch):
    for client in aff4.FACTORY.MultiOpen(batch, mode="r", age=aff4.ALL_TIMES):
      _WriteClient(client)

      with self._lock:
        self._migrated_count += 1

        delta = rdfvalue.RDFDatetime.Now() - self._last_progress_time
        if delta >= _PROGRESS_INTERVAL:
          self._Progress()

  def _Progress(self):
    """Prints the migration progress."""
    elapsed = rdfvalue.RDFDatetime.Now() - self._start_time
    if elapsed.seconds > 0:
      cps = self._migrated_count / elapsed.seconds
    else:
      cps = 0.0

    fraction = self._migrated_count / self._total_count
    message = "\rMigrating clients... {:>9}/{} ({:.2%}, cps: {:.2f})".format(
        self._migrated_count, self._total_count, fraction, cps)
    sys.stdout.write(message)
    sys.stdout.flush()

    self._last_progress_time = rdfvalue.RDFDatetime.Now()


def _WriteClient(client):
  """Store the AFF4 client in the relational database."""
  _WriteClientMetadata(client)
  _WriteClientHistory(client)
  _WriteClientLabels(client)


def _WriteClientMetadata(client):
  """Store the AFF4 client metadata in the relational database."""
  client_ip = client.Get(client.Schema.CLIENT_IP)
  if client_ip:
    last_ip = rdf_client_network.NetworkAddress(
        human_readable_address=utils.SmartStr(client_ip))
  else:
    last_ip = None

  data_store.REL_DB.WriteClientMetadata(
      client.urn.Basename(),
      certificate=client.Get(client.Schema.CERT),
      fleetspeak_enabled=client.Get(client.Schema.FLEETSPEAK_ENABLED) or False,
      last_ping=client.Get(client.Schema.PING),
      last_clock=client.Get(client.Schema.CLOCK),
      last_ip=last_ip,
      last_foreman=client.Get(client.Schema.LAST_FOREMAN_TIME),
      first_seen=client.Get(client.Schema.FIRST_SEEN))


def _WriteClientHistory(client):
  """Store versions of the AFF4 client in the relational database."""
  snapshots = list()

  for version in _GetClientVersions(client):
    clone_attrs = {}
    for key, values in iteritems(client.synced_attributes):
      clone_attrs[key] = [value for value in values if value.age <= version.age]

    synced_client = aff4_grr.VFSGRRClient(
        client.urn, clone=clone_attrs, age=(0, version.age))

    client_snapshot = ConvertVFSGRRClient(synced_client)
    client_snapshot.timestamp = version.age
    snapshots.append(client_snapshot)

  data_store.REL_DB.WriteClientSnapshotHistory(snapshots)


def _WriteClientLabels(client):
  labels = dict()
  for label in client.Get(client.Schema.LABELS) or []:
    labels.setdefault(label.owner, []).append(label.name)

  for owner, names in iteritems(labels):
    data_store.REL_DB.AddClientLabels(client.urn.Basename(), owner, names)


def _GetClientUrns():
  """Returns a set of client URNs available in the data store."""
  result = set()

  for urn in aff4.FACTORY.ListChildren("aff4:/"):
    try:
      client_urn = rdf_client.ClientURN(urn)
    except type_info.TypeValueError:
      continue

    result.add(client_urn)

  return result


def _GetClientVersions(client):
  """Obtains a list of versions for the given client."""
  versions = []
  for typ in client.GetValuesForAttribute(client.Schema.TYPE):
    if not versions or versions[-1].age - typ.age > _CLIENT_VERSION_THRESHOLD:
      versions.append(typ)
  return versions


def ConvertVFSGRRClient(client):
  """Converts from `VFSGRRClient` to `rdfvalues.objects.ClientSnapshot`."""
  snapshot = rdf_objects.ClientSnapshot(client_id=client.urn.Basename())

  snapshot.filesystems = client.Get(client.Schema.FILESYSTEM)
  snapshot.hostname = client.Get(client.Schema.HOSTNAME)
  snapshot.fqdn = client.Get(client.Schema.FQDN)
  snapshot.os_release = client.Get(client.Schema.OS_RELEASE)
  snapshot.os_version = utils.SmartStr(client.Get(client.Schema.OS_VERSION))
  snapshot.arch = client.Get(client.Schema.ARCH)
  snapshot.install_time = client.Get(client.Schema.INSTALL_DATE)
  snapshot.knowledge_base = client.Get(client.Schema.KNOWLEDGE_BASE)
  snapshot.startup_info.boot_time = client.Get(client.Schema.LAST_BOOT_TIME)
  snapshot.startup_info.client_info = client.Get(client.Schema.CLIENT_INFO)

  conf = client.Get(client.Schema.GRR_CONFIGURATION) or []
  for key in conf or []:
    snapshot.grr_configuration.Append(key=key, value=utils.SmartStr(conf[key]))

  lib = client.Get(client.Schema.LIBRARY_VERSIONS) or []
  for key in lib or []:
    snapshot.library_versions.Append(key=key, value=utils.SmartStr(lib[key]))

  snapshot.kernel = client.Get(client.Schema.KERNEL)
  snapshot.volumes = client.Get(client.Schema.VOLUMES)
  snapshot.interfaces = client.Get(client.Schema.INTERFACES)
  snapshot.hardware_info = client.Get(client.Schema.HARDWARE_INFO)
  snapshot.memory_size = client.Get(client.Schema.MEMORY_SIZE)
  snapshot.cloud_instance = client.Get(client.Schema.CLOUD_INSTANCE)

  return snapshot


def ListVfs(client_urn):
  """Lists all known paths for a given client.

  Args:
    client_urn: An instance of `ClientURN`.

  Returns:
    A list of `RDFURN` instances corresponding to client's VFS paths.
  """
  return ListVfses([client_urn])


def ListVfses(client_urns):
  """Lists all known paths for a list of clients.

  Args:
    client_urns: A list of `ClientURN` instances.

  Returns:
    A list of `RDFURN` instances corresponding to VFS paths of given clients.
  """
  vfs = set()

  cur = set()
  for client_urn in client_urns:
    cur.update([
        client_urn.Add("fs/os"),
        client_urn.Add("fs/tsk"),
        client_urn.Add("temp"),
        client_urn.Add("registry"),
    ])

  while cur:
    nxt = []
    for _, children in aff4.FACTORY.MultiListChildren(cur):
      nxt.extend(children)

    vfs.update(nxt)
    cur = nxt

  return vfs


class ClientVfsMigrator(object):
  """A class used to migrate VFS to relational database.

  Attributes:
    thread_count: A number of threads to use to perform the migration.
    client_batch_size: A size of a batch into which all client URNs to migrate
      are divided into.
    init_vfs_group_size: An upper bound for a size of a group into which VFS
      URNs of a particular batch are divided into to perform path initialization
      (clearing any old entries and writing latest known information).
    history_vfs_group_size: A size of a group into which VFS URNs of a
      particular batch are divided into to write the history information.
  """

  def __init__(self):
    self.thread_count = 300
    self.client_batch_size = 200
    self.init_vfs_group_size = 30000
    self.history_vfs_group_size = 10000

    self._client_urns_to_migrate = []
    self._client_urns_migrated = []
    self._client_urns_failed = []

    self._start_time = None

  def MigrateAllClients(self, shard_number=None, shard_count=None):
    """Migrates entire VFS of all clients available in the AFF4 data store."""
    if shard_number is not None or shard_count is not None:
      if shard_number is None:
        raise ValueError("Shard number must be specified if shard count is")
      if shard_count is None:
        raise ValueError("Shard count must be specified if shard number is")
    else:
      shard_number = 1
      shard_count = 1

    sys.stdout.write("Collecting clients... ")

    client_urns = []
    for client_urn in _GetClientUrns():
      client_nr = int(client_urn.Basename()[2:], 16)
      if client_nr % shard_count == shard_number - 1:
        client_urns.append(client_urn)

    sys.stdout.write("DONE\n")

    self.MigrateClients(client_urns)

  def MigrateClients(self, client_urns):
    """Migrates entire VFS of given client list to the relational data store."""
    self._start_time = rdfvalue.RDFDatetime.Now()

    self._client_urns_to_migrate = client_urns
    self._client_urns_migrated = []
    self._client_urns_failed = []

    to_migrate_count = len(self._client_urns_to_migrate)
    sys.stdout.write("Clients to migrate: {}\n".format(to_migrate_count))

    batches = collection.Batch(client_urns, self.client_batch_size)

    _MapWithPool(self.MigrateClientBatch, list(batches), self.thread_count)

    migrated_count = len(self._client_urns_migrated)
    sys.stdout.write("Migrated clients: {}\n".format(migrated_count))

    if to_migrate_count == migrated_count:
      sys.stdout.write("All clients migrated successfully!\n")
    else:
      message = "Not all clients have been migrated ({}/{})".format(
          migrated_count, to_migrate_count)
      raise RuntimeError(message)

  def MigrateClient(self, client_urn):
    """Migrate entire VFS of a particular client to the relational database."""
    self.MigrateClientBatch([client_urn])

  def MigrateClientBatch(self, client_urns):
    """Migrates entire VFS of given client batch to the relational database."""
    try:
      now = rdfvalue.RDFDatetime.Now()
      vfs_urns = ListVfses(client_urns)
      list_vfs_duration = rdfvalue.RDFDatetime.Now() - now

      now = rdfvalue.RDFDatetime.Now()
      self._InitVfsUrns(vfs_urns)
      init_vfs_duration = rdfvalue.RDFDatetime.Now() - now

      now = rdfvalue.RDFDatetime.Now()
      self._MigrateVfsUrns(vfs_urns)
      migrate_vfs_duration = rdfvalue.RDFDatetime.Now() - now

      self._client_urns_migrated.extend(client_urns)
    except Exception as error:
      sys.stderr.write("Failed to migrate batch: {}\n".format(client_urns))
      traceback.print_exc(error)
      self._client_urns_failed.extend(client_urns)
      raise error

    if self._start_time is not None:
      elapsed = rdfvalue.RDFDatetime.Now() - self._start_time
    else:
      elapsed = rdfvalue.Duration("0s")

    if elapsed.seconds > 0:
      cps = len(self._client_urns_migrated) / elapsed.seconds
    else:
      cps = 0

    message = [
        "Migrated a batch "
        "(total migrated clients: {migrated_count}, failed: {failed_count})",
        "  total time elapsed: {elapsed} ({cps:.2f} clients per second)",
        "  number of VFS paths in current batch: {vfs_urn_count}",
        "  listing VFS took: {list_vfs_duration}",
        "  path initialization took: {init_vfs_duration}",
        "  writing path history took: {migrate_vfs_duration}",
        "",
    ]
    sys.stdout.write("\n".join(message).format(
        migrated_count=len(self._client_urns_migrated),
        failed_count=len(self._client_urns_failed),
        elapsed=elapsed,
        cps=cps,
        vfs_urn_count=len(vfs_urns),
        list_vfs_duration=list_vfs_duration,
        init_vfs_duration=init_vfs_duration,
        migrate_vfs_duration=migrate_vfs_duration))

  def _InitVfsUrns(self, vfs_urns):
    """Writes initial path information for a list of VFS URNs."""
    client_vfs_urns = dict()
    for vfs_urn in vfs_urns:
      client_id, _ = vfs_urn.Split(2)
      client_vfs_urns.setdefault(client_id, []).append(vfs_urn)

    groups = list()
    groups.append([])
    for urns in itervalues(client_vfs_urns):
      if len(groups[-1]) + len(urns) > self.init_vfs_group_size:
        groups.append([])
      groups[-1].extend(urns)

    for group in groups:
      self._InitVfsUrnGroup(group)

  def _InitVfsUrnGroup(self, vfs_urns):
    """Writes initial path information for a group of VFS URNs."""
    path_infos = dict()
    for vfs_urn in vfs_urns:
      client_id, vfs_path = vfs_urn.Split(2)
      path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

      path_info = rdf_objects.PathInfo(
          path_type=path_type, components=components)
      path_infos.setdefault(client_id, []).append(path_info)

    data_store.REL_DB.MultiInitPathInfos(path_infos)

  def _MigrateVfsUrns(self, vfs_urns):
    """Migrates history of given list of VFS URNs."""
    for group in collection.Batch(vfs_urns, self.history_vfs_group_size):
      self._MigrateVfsUrnGroup(group)

  def _MigrateVfsUrnGroup(self, vfs_urns):
    """Migrates history of given group of VFS URNs."""
    client_path_histories = dict()

    for fd in aff4.FACTORY.MultiOpen(vfs_urns, age=aff4.ALL_TIMES):
      client_id, vfs_path = fd.urn.Split(2)
      path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

      client_path = db.ClientPath(client_id, path_type, components)
      client_path_history = db.ClientPathHistory()

      for stat_entry in fd.GetValuesForAttribute(fd.Schema.STAT):
        client_path_history.AddStatEntry(stat_entry.age, stat_entry)

      for hash_entry in fd.GetValuesForAttribute(fd.Schema.HASH):
        client_path_history.AddHashEntry(hash_entry.age, hash_entry)

      client_path_histories[client_path] = client_path_history

    data_store.REL_DB.MultiWritePathHistory(client_path_histories)


class BlobsMigrator(object):
  """Blob store migrator."""

  def __init__(self):
    self._lock = threading.Lock()

    self._total_count = 0
    self._migrated_count = 0
    self._start_time = None

  def _MigrateBatch(self, batch):
    """Migrates a batch of blobs."""

    blobs = {}
    for stream in aff4.FACTORY.MultiOpen(
        batch, mode="r", aff4_type=aff4.AFF4UnversionedMemoryStream):
      if stream.size > 0:
        content_bytes = stream.Read(stream.size)
        bid = rdf_objects.BlobID.FromBlobData(content_bytes)
        blobs[bid] = content_bytes

    data_store.REL_DB.WriteBlobs(blobs)

    with self._lock:
      self._migrated_count += len(batch)
      self._Progress()

  def _Progress(self):
    """Prints the migration progress."""

    elapsed = rdfvalue.RDFDatetime.Now() - self._start_time
    if elapsed.seconds > 0:
      bps = self._migrated_count / elapsed.seconds
    else:
      bps = 0.0

    fraction = self._migrated_count / self._total_count
    message = "\rMigrating blobs... {:>9}/{} ({:.2%}, bps: {:.2f})".format(
        self._migrated_count, self._total_count, fraction, bps)
    sys.stdout.write(message)
    sys.stdout.flush()

  def Execute(self, thread_count, urns=None):
    """Runs the migration with a given thread count."""

    if urns is None:
      blob_urns = list(aff4.FACTORY.ListChildren("aff4:/blobs"))
    else:
      blob_urns = [rdfvalue.RDFURN(urn) for urn in urns]

    sys.stdout.write("Blobs to migrate: {}\n".format(len(blob_urns)))
    sys.stdout.write("Threads to use: {}\n".format(thread_count))

    self._total_count = len(blob_urns)
    self._migrated_count = 0
    self._start_time = rdfvalue.RDFDatetime.Now()

    batches = collection.Batch(blob_urns, _BLOB_BATCH_SIZE)

    self._Progress()
    _MapWithPool(self._MigrateBatch, list(batches), thread_count)
    self._Progress()

    if self._migrated_count == self._total_count:
      message = "\nMigration has been finished (migrated {} blobs).\n".format(
          self._migrated_count)
      sys.stdout.write(message)
    else:
      message = "Not all blobs have been migrated ({}/{})".format(
          self._migrated_count, self._total_count)
      raise AssertionError(message)
