#!/usr/bin/env python
"""The GRR relational database abstraction.

This defines the Database abstraction, which defines the methods used by GRR on
a logical relational database model.
"""

import abc
import collections
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence, Set
import dataclasses
import enum
import re
from typing import Literal, NamedTuple, Optional, Protocol, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import precondition
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_proto import user_pb2
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


CLIENT_STATS_RETENTION = rdfvalue.Duration.From(31, rdfvalue.DAYS)

# Use 254 as max length for usernames to allow email addresses.
MAX_USERNAME_LENGTH = 254

# Use 128 as max length for command IDs.
MAX_SIGNED_COMMAND_ID_LENGTH = 128

ED25519_SIGNATURE_LENGTH = 64

MAX_LABEL_LENGTH = 100

MAX_ARTIFACT_NAME_LENGTH = 100

MAX_CRON_JOB_ID_LENGTH = 100

MAX_MESSAGE_HANDLER_NAME_LENGTH = 128

_MAX_CLIENT_PLATFORM_LENGTH = 100

# Using sys.maxsize may not work with real database implementations. We need
# to have a reasonably large number that can be used to read all the records
# using a particular DB API call.
MAX_COUNT = 1024**3

CLIENT_IDS_BATCH_SIZE = 500000

_EMAIL_REGEX = re.compile(r"[^@]+@([^@]+)$")
MAX_EMAIL_LENGTH = 255


UNCHANGED = "__unchanged__"


class Error(Exception):
  """Base exception class for DB exceptions."""

  # Python exception constructors should be able to handle arbitrary amount
  # of arguments if they want to stay pickleable.
  # See:
  # https://stackoverflow.com/questions/41808912/cannot-unpickle-exception-subclass
  #
  # Database exceptions have to be pickleable in order to make self-contained
  # E2E testing with SharedMemoryDB possible (as SharedMemoryDB server has to
  # pass serialized exception objects back to SharedMemoryDB clients running
  # as separate processes - see test/grr_response_test/run_self_contained.py for
  # more details). Consequently, __init__ passes all the positional arguments
  # through and accepts "cause" as a keyword argument.
  #
  # Exceptions inherited from Error are expected to call Error's constructor
  # with all positional arguments they've received and set self.message to
  # a custom message (in case they need one).
  def __init__(self, *args, **kwargs):
    super().__init__(*args)

    self.cause = kwargs.get("cause")
    self.message = None

  def __str__(self):
    message = self.message or super().__str__()

    if self.cause is not None:
      return "%s: %s" % (message, self.cause)

    return message


class NotFoundError(Error):
  pass


class UnknownArtifactError(NotFoundError):
  """An exception class for errors about unknown artifacts.

  Attributes:
    name: A name of the non-existing artifact that was referenced.
    cause: An (optional) exception instance that triggered this error.
  """

  def __init__(self, name: str, cause: Optional[Exception] = None):
    super().__init__(name, cause=cause)

    self.name = name
    self.message = "Artifact with name '%s' does not exist" % self.name


class DuplicatedArtifactError(Error):
  """An exception class for errors about duplicated artifacts being written.

  Attributes:
    name: A name of the artifact that was referenced.
    cause: An (optional) exception instance that triggered this error.
  """

  def __init__(self, name: str, cause: Optional[Exception] = None):
    super().__init__(name, cause=cause)

    self.name = name
    self.message = "Artifact with name '%s' already exists" % self.name


class UnknownClientError(NotFoundError):
  """An exception class representing errors about uninitialized client.

  Attributes:
    client_id: An id of the non-existing client that was referenced.
    cause: An (optional) exception instance that triggered the unknown client
      error.
  """

  def __init__(self, client_id, cause=None):
    super().__init__(client_id, cause=cause)

    self.client_id = client_id
    self.message = "Client with id '%s' does not exist" % self.client_id


class AtLeastOneUnknownClientError(UnknownClientError):

  def __init__(self, client_ids, cause=None):
    super().__init__(client_ids, cause=cause)

    self.client_ids = client_ids
    self.message = "At least one client in '%s' does not exist" % ",".join(
        client_ids
    )


class UnknownPathError(NotFoundError):
  """An exception class representing errors about unknown paths.

  Attributes:
    client_id: An id of the client for which the path does not exist.
    path_type: A type of the path.
    path_id: An id of the path.
  """

  def __init__(self, client_id, path_type, components, cause=None):
    super().__init__(client_id, path_type, components, cause=cause)

    self.client_id = client_id
    self.path_type = path_type
    self.components = components

    self.message = "Path '%s' of type '%s' on client '%s' does not exist"
    self.message %= ("/".join(self.components), self.path_type, self.client_id)


class AtLeastOneUnknownPathError(NotFoundError):
  """An exception class raised when one of a set of paths is unknown."""

  def __init__(self, client_path_ids, cause=None):
    super().__init__(client_path_ids, cause=cause)

    self.client_path_ids = client_path_ids

    self.message = "At least one of client path ids does not exist: "
    self.message += ", ".join(str(cpid) for cpid in self.client_path_ids)


class NotDirectoryPathError(NotFoundError):
  """An exception class raised when a path corresponds to a non-directory."""

  def __init__(self, client_id, path_type, components, cause=None):
    super().__init__(client_id, path_type, components, cause=cause)

    self.client_id = client_id
    self.path_type = path_type
    self.components = components

    self.message = (
        "Listing descendants of path '%s' of type '%s' on client "
        "'%s' that is not a directory"
    ) % ("/".join(self.components), self.path_type, self.client_id)


class UnknownRuleError(NotFoundError):
  pass


class UnknownGRRUserError(NotFoundError):
  """An error thrown when no user is found for a given username."""

  def __init__(self, username, cause=None):
    super().__init__(username, cause=cause)
    self.username = username

    self.message = "Cannot find user with username %r" % self.username


class UnknownApprovalRequestError(NotFoundError):
  pass


class UnknownCronJobError(NotFoundError):
  pass


class UnknownCronJobRunError(NotFoundError):
  pass


class UnknownSignedBinaryError(NotFoundError):
  """Exception raised when a signed binary isn't found in the DB."""

  def __init__(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      cause: Optional[Exception] = None,
  ):
    """Initializes UnknownSignedBinaryError.

    Args:
      binary_id: objects_pb2.SignedBinaryID for the signed binary.
      cause: A lower-level Exception raised by the database driver, which might
        have more details about the error.
    """
    super().__init__(binary_id, cause=cause)

    self.binary_id = binary_id
    self.message = "Signed binary of type %s and path %s was not found" % (
        self.binary_id.binary_type,
        self.binary_id.path,
    )


class UnknownSignedCommandError(NotFoundError):
  """Exception raised when a signed command cannot be found in the database."""

  def __init__(
      self,
      command_id: str,
      operating_system: "signed_commands_pb2.SignedCommand.OS",
  ) -> None:
    super().__init__()

    self.command_id = command_id
    self.operating_system = operating_system

    self.message = (
        f"Signed command {command_id!r} for {operating_system!r} does not exist"
    )


class NoMatchingSignedCommandError(NotFoundError):
  """Exception raised when a matching signed command cannot be found."""

  def __init__(
      self,
      operating_system: signed_commands_pb2.SignedCommand.OS,
      path: str,
      args: Sequence[str],
  ) -> None:
    super().__init__()

    self.operating_system = operating_system
    self.path = path
    self.args = list(args)

    self.message = (
        f"Signed command for path {path!r} and arguments {args!r} not found"
    )


class UnknownFlowError(NotFoundError):

  def __init__(self, client_id, flow_id, cause=None):
    super().__init__(client_id, flow_id, cause=cause)

    self.client_id = client_id
    self.flow_id = flow_id

    self.message = (
        "Flow with client id '%s' and flow id '%s' does not exist"
        % (self.client_id, self.flow_id)
    )


class UnknownScheduledFlowError(NotFoundError):
  """Raised when a nonexistent ScheduledFlow is accessed."""

  def __init__(self, client_id, creator, scheduled_flow_id, cause=None):
    super().__init__(client_id, creator, scheduled_flow_id, cause=cause)

    self.client_id = client_id
    self.creator = creator
    self.scheduled_flow_id = scheduled_flow_id

    self.message = "ScheduledFlow {}/{}/{} does not exist.".format(
        self.client_id, self.creator, self.scheduled_flow_id
    )


class UnknownHuntError(NotFoundError):

  def __init__(self, hunt_id, cause=None):
    super().__init__(hunt_id, cause=cause)
    self.hunt_id = hunt_id

    self.message = "Hunt with hunt id '%s' does not exist" % self.hunt_id


class DuplicatedHuntError(Error):

  def __init__(self, hunt_id, cause=None):
    message = "Hunt with hunt id '{}' already exists".format(hunt_id)
    super().__init__(message, cause=cause)

    self.hunt_id = hunt_id


class UnknownHuntOutputPluginStateError(NotFoundError):

  def __init__(self, hunt_id, state_index):
    super().__init__(hunt_id, state_index)

    self.hunt_id = hunt_id
    self.state_index = state_index

    self.message = (
        "Hunt output plugin state for hunt '%s' with index %d does not exist"
        % (self.hunt_id, self.state_index)
    )


class AtLeastOneUnknownFlowError(NotFoundError):

  def __init__(self, flow_keys, cause=None):
    super().__init__(flow_keys, cause=cause)

    self.flow_keys = flow_keys

    self.message = (
        "At least one flow with client id/flow_id in '%s' does not exist"
        % (self.flow_keys)
    )


class UnknownFlowRequestError(NotFoundError):
  """Raised when a flow request is not found."""

  def __init__(self, client_id, flow_id, request_id, cause=None):
    super().__init__(client_id, flow_id, request_id, cause=cause)

    self.client_id = client_id
    self.flow_id = flow_id
    self.request_id = request_id

    self.message = (
        "Flow request %d for flow with client id '%s' and flow id '%s' "
        "does not exist" % (self.request_id, self.client_id, self.flow_id)
    )


class AtLeastOneUnknownRequestError(NotFoundError):

  def __init__(self, request_keys, cause=None):
    super().__init__(request_keys, cause=cause)

    self.request_keys = request_keys

    self.message = (
        "At least one request with client id/flow_id/request_id in "
        "'%s' does not exist" % (self.request_keys)
    )


class ParentHuntIsNotRunningError(Error):
  """Exception indicating that a hunt-induced flow is not processable."""

  def __init__(self, client_id, flow_id, hunt_id, hunt_state):
    super().__init__(client_id, flow_id, hunt_id, hunt_state)

    self.client_id = client_id
    self.flow_id = flow_id
    self.hunt_id = hunt_id
    self.hunt_state = hunt_state

    self.message = (
        "Parent hunt %s of the flow with client id '%s' and "
        "flow id '%s' is not running: %s"
        % (self.hunt_id, self.client_id, self.flow_id, self.hunt_state)
    )


class HuntOutputPluginsStatesAreNotInitializedError(Error):
  """Exception indicating that hunt output plugin states weren't initialized."""

  def __init__(self, hunt_obj):
    super().__init__(hunt_obj)

    self.hunt_obj = hunt_obj

    self.message = (
        "Hunt %r has output plugins but no output plugins states. "
        "Make sure it was created with hunt.CreateHunt and not "
        "simply written to the database."
        % self.hunt_obj
    )


class ConflictingUpdateFlowArgumentsError(Error):
  """Raised when UpdateFlow is called with conflicting parameter."""

  def __init__(self, client_id, flow_id, param_name):
    super().__init__(client_id, flow_id, param_name)
    self.client_id = client_id
    self.flow_id = flow_id
    self.param_name = param_name

    self.message = (
        "Conflicting parameter when updating flow "
        "%s (client %s). Can't call UpdateFlow with "
        "flow_obj and %s passed together." % (flow_id, client_id, param_name)
    )


class FlowExistsError(Error):
  """Raised when an insertion fails because the Flow already exists."""

  def __init__(self, client_id, flow_id):
    super().__init__("Flow {}/{} already exists.".format(client_id, flow_id))
    self.client_id = client_id
    self.flow_id = flow_id


class AtLeastOneDuplicatedSignedCommandError(Error):
  """Raised when an insertion fails because the command already exists."""

  def __init__(self, commands):
    printable_commands = ", ".join(
        [f"({c.id}, {c.operating_system})" for c in commands]
    )
    super().__init__(
        f"At least one duplicate signed command in [{printable_commands}]."
    )


class StringTooLongError(ValueError):
  """Validation error raised if a string is too long."""


class HuntFlowsCondition(enum.Enum):
  """Constants to be used with ReadHuntFlows/CountHuntFlows methods."""

  UNSET = enum.auto()
  FAILED_FLOWS_ONLY = enum.auto()
  SUCCEEDED_FLOWS_ONLY = enum.auto()
  COMPLETED_FLOWS_ONLY = enum.auto()
  FLOWS_IN_PROGRESS_ONLY = enum.auto()
  CRASHED_FLOWS_ONLY = enum.auto()


HuntCounters = collections.namedtuple(
    "HuntCounters",
    [
        "num_clients",
        "num_successful_clients",
        "num_failed_clients",
        "num_clients_with_results",
        "num_crashed_clients",
        "num_running_clients",
        "num_results",
        "total_cpu_seconds",
        "total_network_bytes_sent",
    ],
)

FlowStateAndTimestamps = collections.namedtuple(
    "FlowStateAndTimestamps",
    [
        "flow_state",
        "create_time",
        "last_update_time",
    ],
)


@dataclasses.dataclass
class FlowErrorInfo:
  """Information about what caused flow to error-out."""

  message: str
  time: rdfvalue.RDFDatetime
  backtrace: Optional[str] = None


class SearchClientsResult(NamedTuple):
  """The result of a structured search."""

  clients: Sequence[str]
  """Sequence of clients."""

  continuation_token: bytes
  """The continuation token for the search."""

  num_remaining_results: int
  """Estimated number of remaining results."""


class ClientPath(object):
  """An immutable class representing certain path on a given client.

  Attributes:
    client_id: A client to which the path belongs to.
    path_type: A type of the path.
    components: A tuple of path components.
    basename: A basename of the path.
    path_id: A path id of the path (corresponding to the path components).
  """

  def __init__(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
  ):
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    _ValidatePathComponents(components)
    self._repr = (
        client_id,
        path_type,
        tuple(components),
    )

  @classmethod
  def OS(cls, client_id, components):
    path_type = objects_pb2.PathInfo.PathType.OS
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def TSK(cls, client_id, components):
    path_type = objects_pb2.PathInfo.PathType.TSK
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def NTFS(cls, client_id, components):
    path_type = objects_pb2.PathInfo.PathType.NTFS
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def Registry(cls, client_id, components):
    path_type = objects_pb2.PathInfo.PathType.REGISTRY
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def Temp(cls, client_id, components):
    path_type = objects_pb2.PathInfo.PathType.TEMP
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def FromPathSpec(
      cls, client_id: str, path_spec: rdf_paths.PathSpec
  ) -> "ClientPath":
    path_info = mig_objects.ToProtoPathInfo(
        rdf_objects.PathInfo.FromPathSpec(path_spec)
    )
    return cls.FromPathInfo(client_id, path_info)

  @classmethod
  def FromPathInfo(
      cls, client_id: str, path_info: objects_pb2.PathInfo
  ) -> "ClientPath":
    return cls(
        client_id=client_id,
        path_type=path_info.path_type,
        components=tuple(path_info.components),
    )

  @property
  def client_id(self):
    return self._repr[0]

  @property
  def path_type(self):
    return self._repr[1]

  @property
  def components(self):
    return self._repr[2]

  @property
  def path_id(self) -> rdf_objects.PathID:
    return rdf_objects.PathID.FromComponents(self.components)

  @property
  def vfs_path(self):
    return rdf_objects.ToCategorizedPath(self.path_type, self.components)

  @property
  def basename(self):
    return self.components[-1]

  def __eq__(self, other):
    if not isinstance(other, ClientPath):
      return NotImplemented

    return self._repr == other._repr  # pylint: disable=protected-access

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return hash(self._repr)

  def Path(self):
    return "/".join(self.components)

  def __repr__(self):
    return "<%s client_id=%r path_type=%r components=%r>" % (
        self.__class__.__name__,
        self.client_id,
        self.path_type,
        self.components,
    )


class Database(metaclass=abc.ABCMeta):
  """The GRR relational database abstraction."""

  UNCHANGED_TYPE = Literal["__unchanged__"]
  UNCHANGED: UNCHANGED_TYPE = "__unchanged__"

  @abc.abstractmethod
  def Now(self) -> rdfvalue.RDFDatetime:
    """Retrieves current time as reported by the database."""

  # Different DB engines might make different assumptions about what a valid
  # minimal timestamp is.
  # For example, MySQL doesn't handle sub second fractional timestamps well:
  # Per https://dev.mysql.com/doc/refman/8.0/en/datetime.html:
  # "the range for TIMESTAMP values is '1970-01-01 00:00:01.000000' to
  # '2038-01-19 03:14:07.999999'".
  @abc.abstractmethod
  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    """Returns minimal timestamp allowed by the DB."""

  @abc.abstractmethod
  def WriteArtifact(self, artifact: artifact_pb2.Artifact) -> None:
    """Writes new artifact to the database.

    Args:
      artifact: An artifact instance to write.
    """

  # TODO(hanuszczak): Consider removing this method if it proves to be useless
  # after the artifact registry refactoring.
  @abc.abstractmethod
  def ReadArtifact(self, name: str) -> artifact_pb2.Artifact:
    """Looks up an artifact with given name from the database.

    Args:
      name: A name of the artifact to return.

    Returns:
      An artifact corresponding to the given name.

    Raises:
      UnknownArtifactError: If an artifact with given name does not exist.
    """

  @abc.abstractmethod
  def ReadAllArtifacts(self) -> Sequence[artifact_pb2.Artifact]:
    """Lists all artifacts that are stored in the database.

    Returns:
      A list of artifacts stored in the database.
    """

  @abc.abstractmethod
  def DeleteArtifact(self, name: str) -> None:
    """Deletes an artifact with given name from the database.

    Args:
      name: A name of the artifact to delete.

    Raises:
      UnknownArtifactError: If an artifact with given name does not exist.
    """

  @abc.abstractmethod
  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    """Writes ClientMetadata records for a list of clients.

    Updates one or more client metadata fields for a list of clients. Any of
    the data fields can be left as None, and in this case are not changed.

    Args:
      client_ids: A collection of GRR client id strings, e.g.
        ["C.ea3b2b71840d6fa7", "C.ea3b2b71840d6fa8"]
      first_seen: An rdfvalue.Datetime, indicating the first time the client
        contacted the server.
      last_ping: An rdfvalue.Datetime, indicating the last time the client
        contacted the server.
      last_foreman: An rdfvalue.Datetime, indicating the last time that the
        client sent a foreman message to the server.
      fleetspeak_validation_info: A dict with validation info from Fleetspeak.
    """

  def WriteClientMetadata(
      self,
      client_id: str,
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    """Write metadata about the client.

    Updates one or more client metadata fields for the given client_id. Any of
    the data fields can be left as None, and in this case are not changed.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      first_seen: An rdfvalue.Datetime, indicating the first time the client
        contacted the server.
      last_ping: An rdfvalue.Datetime, indicating the last time the client
        contacted the server.
      last_foreman: An rdfvalue.Datetime, indicating the last time that the
        client sent a foreman message to the server.
      fleetspeak_validation_info: A dict with validation info from Fleetspeak.
    """
    self.MultiWriteClientMetadata(
        client_ids=[client_id],
        first_seen=first_seen,
        last_ping=last_ping,
        last_foreman=last_foreman,
        fleetspeak_validation_info=fleetspeak_validation_info,
    )

  @abc.abstractmethod
  def DeleteClient(
      self,
      client_id: str,
  ) -> None:
    """Deletes a client with all associated metadata.

    This method is a stub. Deletion is not yet supported.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
    """

  @abc.abstractmethod
  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    """Reads ClientMetadata records for a list of clients.

    Note: client ids not found in the database will be omitted from the
    resulting map.

    Args:
      client_ids: A collection of GRR client id strings, e.g.
        ["C.ea3b2b71840d6fa7", "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to corresponding metadata.
    """

  def ReadClientMetadata(
      self,
      client_id: str,
  ) -> objects_pb2.ClientMetadata:
    """Reads the ClientMetadata record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      Metadata corresponding to the client with the given identifier.

    Raises:
      UnknownClientError: if no client with corresponding id was found.
    """
    result = self.MultiReadClientMetadata([client_id])
    try:
      return result[client_id]
    except KeyError:
      raise UnknownClientError(client_id)

  @abc.abstractmethod
  def WriteClientSnapshot(
      self,
      snapshot: objects_pb2.ClientSnapshot,
  ) -> None:
    """Writes new client snapshot.

    Writes a new snapshot of the client to the client history, typically saving
    the results of an interrogate flow.

    Args:
      snapshot: A client snapshot object to store in the database.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientSnapshot]:
    """Reads the latest client snapshots for a list of clients.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to rdfvalues.objects.ClientSnapshot.
    """

  def ReadClientSnapshot(
      self,
      client_id: str,
  ) -> Optional[objects_pb2.ClientSnapshot]:
    """Reads the latest client snapshot for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.objects.ClientSnapshot object.
    """
    return self.MultiReadClientSnapshot([client_id]).get(client_id)

  @abc.abstractmethod
  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    """Reads full client information for a list of clients.

    Note: client ids not found in the database will be omitted from the
    resulting map.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]
      min_last_ping: If not None, only the clients with last ping time bigger
        than min_last_ping will be returned.

    Returns:
      A map from client ids to `ClientFullInfo` instance.
    """

  def ReadClientFullInfo(
      self,
      client_id: str,
  ) -> objects_pb2.ClientFullInfo:
    """Reads full client information for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A `ClientFullInfo` instance for given client.

    Raises:
      UnknownClientError: if no client with such id was found.
    """
    result = self.MultiReadClientFullInfo([client_id])
    try:
      return result[client_id]
    except KeyError:
      raise UnknownClientError(client_id)

  def ReadAllClientIDs(
      self,
      min_last_ping=None,
      batch_size=CLIENT_IDS_BATCH_SIZE,
  ):
    """Yields lists of client ids for all clients in the database.

    Args:
      min_last_ping: If provided, only ids for clients with a last-ping
        timestamp newer than (or equal to) the given value will be returned.
      batch_size: Integer, specifying the number of client ids to be queried at
        a time.

    Yields:
      Lists of client IDs.
    """

    for results in self.ReadClientLastPings(
        min_last_ping=min_last_ping, batch_size=batch_size
    ):
      yield list(results.keys())

  @abc.abstractmethod
  def ReadClientLastPings(
      self,
      min_last_ping=None,
      max_last_ping=None,
      batch_size=CLIENT_IDS_BATCH_SIZE,
  ):
    """Yields dicts of last-ping timestamps for clients in the DB.

    Args:
      min_last_ping: The minimum timestamp to fetch from the DB.
      max_last_ping: The maximum timestamp to fetch from the DB.
      batch_size: Integer, specifying the number of client pings to be queried
        at a time.

    Yields:
      Dicts mapping client ids to their last-ping timestamps.
    """

  @abc.abstractmethod
  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    """Reads the full history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all history
        items are fetched. Note: "from" and "to" are inclusive: i.e. a from <=
        time <= to condition is applied.

    Returns:
      A list of client snapshots, newest snapshot first.
    """

  @abc.abstractmethod
  def ReadClientStartupInfoHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
      exclude_snapshot_collections: bool = False,
  ) -> Sequence[jobs_pb2.StartupInfo]:
    """Reads the full StartupInfo history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all history
        items are fetched. Note: "from" and "to" are inclusive: i.e. a from <=
        time <= to condition is applied.
      exclude_snapshot_collections: If true, startup info that was collected as
        part of the snapshot (based on the snapshot timestamp) will not be
        returned.

    Returns:
      A list of client startup infos, newest startup info first.
    """

  @abc.abstractmethod
  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup_info: jobs_pb2.StartupInfo,
  ) -> None:
    """Writes a new client startup record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      startup_info: A startup record. Will be saved at the "current" timestamp.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
  ) -> None:
    """Writes a new RRG startup entry to the database.

    Args:
      client_id: An identifier of the client that started the agent.
      startup: A startup entry to write.

    Raises:
      UnknownClientError: If the client is not known.
    """

  @abc.abstractmethod
  def ReadClientRRGStartup(
      self,
      client_id: str,
  ) -> Optional[rrg_startup_pb2.Startup]:
    """Reads the latest RRG startup entry for the given client.

    Args:
      client_id: An identifier of the client for which read the startup entry.

    Returns:
      The latest startup entry if available and `None` if there are no such.

    Raises:
      UnknownClientError: If the client is not known.
    """

  @abc.abstractmethod
  def ReadClientStartupInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.StartupInfo]:
    """Reads the latest client startup record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A startup record.
    """

  @abc.abstractmethod
  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash_info: jobs_pb2.ClientCrash,
  ) -> None:
    """Writes a new client crash record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      crash_info: A client crash object. Will be saved at the "current"
        timestamp.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ReadClientCrashInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.ClientCrash]:
    """Reads the latest client crash record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A client crash object.
    """

  @abc.abstractmethod
  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    """Reads the full crash history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A list of client crash objects sorted by timestamp, newest entry first.
    """

  def AddClientKeywords(
      self,
      client_id: str,
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      keywords: An iterable container of keyword strings to write.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """
    try:
      self.MultiAddClientKeywords([client_id], set(keywords))
    except AtLeastOneUnknownClientError as error:
      raise UnknownClientError(client_id) from error

  @abc.abstractmethod
  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the specified clients.

    Args:
      client_ids: A list of client identifiers to associate with the keywords.
      keywords: A list of keywords to associate with the clients.

    Raises:
      AtLeastOneUnknownClientError: At least one of the clients is not known.
    """

  @abc.abstractmethod
  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, Collection[str]]:
    """Lists the clients associated with keywords.

    Args:
      keywords: An iterable container of keyword strings to look for.
      start_time: If set, should be an rdfvalue.RDFDatime and the function will
        only return keywords associated after this time.

    Returns:
      A dict mapping each provided keyword to a potentially empty list of client
        ids.
    """

  @abc.abstractmethod
  def RemoveClientKeyword(
      self,
      client_id: str,
      keyword: str,
  ) -> None:
    """Removes the association of a particular client to a keyword.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      keyword: The keyword to delete.
    """

  def AddClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches a user label to a client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      owner: Username string that owns the created labels.
      labels: The labels to attach as a list of strings.
    """
    try:
      self.MultiAddClientLabels([client_id], owner, labels)
    except AtLeastOneUnknownClientError as error:
      raise UnknownClientError(client_id) from error

  @abc.abstractmethod
  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches user labels to the specified clients.

    Args:
      client_ids: A list a client identifiers to attach the labels to.
      owner: A name of the user that owns the attached labels.
      labels: Labels to attach.
    """

  @abc.abstractmethod
  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Sequence[objects_pb2.ClientLabel]]:
    """Reads the user labels for a list of clients.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to a list of client label messages, sorted by owner
      and label name.
    """

  def ReadClientLabels(
      self,
      client_id: str,
  ) -> Sequence[objects_pb2.ClientLabel]:
    """Reads the user labels for a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A list of client label messages for the given client, sorted by owner and
      label name.
    """
    return self.MultiReadClientLabels([client_id])[client_id]

  @abc.abstractmethod
  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Sequence[str],
  ) -> None:
    """Removes a list of user labels from a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      owner: Username string that owns the labels that should be removed.
      labels: The labels to remove as a list of strings.
    """

  @abc.abstractmethod
  def ReadAllClientLabels(self) -> Collection[str]:
    """Lists all client labels known to the system.

    Returns:
      A collection of labels in the system.
    """

  @abc.abstractmethod
  def WriteForemanRule(self, rule: jobs_pb2.ForemanCondition) -> None:
    """Writes a foreman rule to the database.

    Args:
      rule: A jobs_pb2.ForemanCondition object.
    """

  @abc.abstractmethod
  def RemoveForemanRule(self, hunt_id: str) -> None:
    """Removes a foreman rule from the database.

    Args:
      hunt_id: Hunt id of the rule that should be removed.

    Raises:
      UnknownRuleError: No rule with the given hunt_id exists.
    """

  @abc.abstractmethod
  def ReadAllForemanRules(self) -> Sequence[jobs_pb2.ForemanCondition]:
    """Reads all foreman rules from the database.

    Returns:
      A list of jobs_pb2.ForemanCondition objects.
    """

  @abc.abstractmethod
  def RemoveExpiredForemanRules(self) -> None:
    """Removes all expired foreman rules from the database."""

  @abc.abstractmethod
  def WriteGRRUser(
      self,
      username: str,
      password: Optional[jobs_pb2.Password] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
      canary_mode: Optional[bool] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      email: Optional[str] = None,
  ) -> None:
    """Writes user object for a user with a given name.

    If a user with the given username exists, it is overwritten.

    Args:
      username: Name of a user to insert/update.
      password: If set, should be a string with a new encrypted user password.
      ui_mode: If set, should be a GUISettings.UIMode enum.
      canary_mode: If not None, should be a boolean indicating user's preferred
        canary mode setting.
      user_type: GRRUser.UserType enum describing user type (unset, standard or
        admin).
      email: If set, E-Mail address overriding the default
        <username>@<Logging.domain>.
    """

  @abc.abstractmethod
  def ReadGRRUser(self, username) -> objects_pb2.GRRUser:
    """Reads a user object corresponding to a given name.

    Args:
      username: Name of a user.

    Returns:
      A objects_pb2.GRRUser objects.
    Raises:
      UnknownGRRUserError: if there's no user corresponding to the given name.
    """

  @abc.abstractmethod
  def ReadGRRUsers(self, offset=0, count=None) -> Sequence[objects_pb2.GRRUser]:
    """Reads GRR users with optional pagination, sorted by username.

    Args:
      offset: An integer specifying an offset to be used when reading results.
      count: Maximum number of users to return. If not provided, all users will
        be returned (respecting offset).

    Returns: A List of `objects_pb2.GRRUser` objects.

    Raises:
      ValueError: if offset or count are negative.
    """

  @abc.abstractmethod
  def CountGRRUsers(self):
    """Returns the total count of GRR users."""

  @abc.abstractmethod
  def DeleteGRRUser(self, username):
    """Deletes the user and all related metadata with the given username.

    Args:
      username: Username identifying the user.

    Raises:
      UnknownGRRUserError: if there is no user corresponding to the given name.
    """

  @abc.abstractmethod
  def WriteApprovalRequest(
      self, approval_request: objects_pb2.ApprovalRequest
  ) -> str:
    """Writes an approval request object.

    Args:
      approval_request: objects_pb2.ApprovalRequest object. Note: approval_id
        and timestamps provided inside the argument object will be ignored.
        Values generated by the database will be used instead.

    Returns:
      approval_id: String identifying newly created approval request.
                   Approval id is unique among approval ids for the same
                   username. I.e. there can be no 2 approvals with the same id
                   for the same username.
    """

  @abc.abstractmethod
  def ReadApprovalRequest(
      self, requestor_username: str, approval_id: str
  ) -> objects_pb2.ApprovalRequest:
    """Reads an approval request object with a given id.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_id: String identifying approval request object.

    Returns:
      objects_pb2.ApprovalRequest object.
    Raises:
      UnknownApprovalRequestError: if there's no corresponding approval request
          object.
    """

  @abc.abstractmethod
  def ReadApprovalRequests(
      self,
      requestor_username: str,
      approval_type: "objects_pb2.ApprovalRequest.ApprovalType",
      subject_id: Optional[str] = None,
      include_expired: Optional[bool] = False,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    """Reads approval requests of a given type for a given user.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_type: Type of approvals to list.
      subject_id: String identifying the subject (client id, hunt id or cron job
        id). If not None, only approval requests for this subject will be
        returned.
      include_expired: If True, will also yield already expired approvals.

    Returns:
      A list of objects_pb2.ApprovalRequest objects.
    """

  @abc.abstractmethod
  def GrantApproval(
      self, requestor_username: str, approval_id: str, grantor_username: str
  ) -> None:
    """Grants approval for a given request using given username.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_id: String identifying approval request object.
      grantor_username: String with a username of a user granting the approval.
    """

  @abc.abstractmethod
  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> objects_pb2.PathInfo:
    """Retrieves a path info record for a given path.

    The `timestamp` parameter specifies for what moment in time the path
    information is to be retrieved. For example, if (using abstract time units)
    at time 1 the path was in state A, at time 5 it was observed to be in state
    B and at time 8 it was in state C one wants to retrieve information at time
    6 the result is going to be B.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve path
        information for.
      timestamp: A moment in time for which we want to retrieve the information.
        If none is provided, the latest known path information is returned.

    Returns:
      A PathInfo instance.
    """

  @abc.abstractmethod
  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    """Retrieves path info records for given paths.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components_list: An iterable of tuples of path components corresponding to
        paths to retrieve path information for.

    Returns:
      A dictionary mapping path components to PathInfo instances.
    """

  def ListChildPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to children of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve child path
        information for.
      timestamp: If set, lists only descendants that existed only at that
        timestamp.

    Returns:
      A list of PathInfo instances sorted by path components.
    """
    return self.ListDescendantPathInfos(
        client_id, path_type, components, max_depth=1, timestamp=timestamp
    )

  @abc.abstractmethod
  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to descendants of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve descendent
        path information for.
      timestamp: If set, lists only descendants that existed at that timestamp.
      max_depth: If set, the maximum number of generations to descend, otherwise
        unlimited.

    Returns:
      A list of objects_pb2.PathInfo instances sorted by path components.
    """

  @abc.abstractmethod
  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Iterable[objects_pb2.PathInfo],
  ) -> None:
    """Writes a collection of path_info records for a client.

    If any records are already present in the database, they will be merged -
    see db_path_utils.MergePathInfo.

    Args:
      client_id: The client of interest.
      path_infos: A list of rdfvalue.objects.PathInfo records.
    """

  @abc.abstractmethod
  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Iterable[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    """Reads a collection of hash and stat entries for given paths.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path history information for.
      components_list: An iterable of tuples of path components corresponding to
        paths to retrieve path information for.
      cutoff: An optional timestamp cutoff up to which the history entries are
        collected.

    Returns:
      A dictionary mapping path components to lists of PathInfo
      ordered by timestamp in ascending order.
    """

  def ReadPathInfoHistory(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Reads a collection of hash and stat entry for given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path history for.
      components: A tuple of path components corresponding to path to retrieve
        information for.
      cutoff: An optional timestamp cutoff up to which the history entries are
        collected.

    Returns:
      A list of PathInfo ordered by timestamp in ascending order.
    """
    histories = self.ReadPathInfosHistories(
        client_id=client_id,
        path_type=path_type,
        components_list=[components],
        cutoff=cutoff,
    )

    return histories[components]

  @abc.abstractmethod
  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[ClientPath, Optional[objects_pb2.PathInfo]]:
    """Returns PathInfos that have corresponding HashBlobReferences.

    Args:
      client_paths: ClientPath objects pointing to files.
      max_timestamp: If not specified, then for every path simply the latest
        PathInfo that has a matching HashBlobReference entry will be returned.
        If specified, should be an rdfvalue.RDFDatetime, then the latest
        PathInfo with a timestamp less or equal to max_timestamp will be
        returned for every path.

    Returns:
      A dictionary mapping client paths to PathInfo objects. Every client path
      from the client_paths argument is guaranteed to be a key in the resulting
      dictionary. If a particular path won't have a PathInfo with a
      corresponding HashBlobReference entry, None will be used as a dictionary
      value.
    """

  @abc.abstractmethod
  def WriteUserNotification(
      self, notification: objects_pb2.UserNotification
  ) -> None:
    """Writes a notification for a given user.

    Args:
      notification: objects.UserNotification object to be written.
    """

  @abc.abstractmethod
  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]
      ] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    """Reads notifications scheduled for a user within a given timerange.

    Args:
      username: Username identifying the user.
      state: If set, only return the notifications with a given state attribute.
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all
        notifications are fetched. Note: "from" and "to" are inclusive: i.e. a
        from <= time <= to condition is applied.

    Returns:
      List of objects.UserNotification objects.
    """

  @abc.abstractmethod
  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
  ) -> None:
    """Updates existing user notification objects.

    Args:
      username: Username identifying the user.
      timestamps: List of timestamps of the notifications to be updated.
      state: objects.UserNotification.State enum value to be written into the
        notifications objects.
    """

  @abc.abstractmethod
  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[list[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> list[objects_pb2.APIAuditEntry]:
    """Returns audit entries stored in the database.

    The event log is sorted according to their timestamp (with the oldest
    recorded event being first).

    Args:
      username: username associated with the audit entries
      router_method_names: list of names of router methods
      min_timestamp: minimum rdfvalue.RDFDateTime (inclusive)
      max_timestamp: maximum rdfvalue.RDFDateTime (inclusive)

    Returns:
      List of `APIAuditEntry` instances.
    """

  @abc.abstractmethod
  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, rdfvalue.RDFDatetime], int]:
    """Returns audit entry counts grouped by user and calendar day.

    Examples:
      >>> db.REL_DB.CountAPIAuditEntriesByUserAndDay()
      {("sampleuser", RDFDateTime("2019-02-02 00:00:00")): 5}

    Args:
      min_timestamp: minimum rdfvalue.RDFDateTime (inclusive)
      max_timestamp: maximum rdfvalue.RDFDateTime (inclusive)

    Returns:
      A dictionary mapping tuples of usernames and datetimes to counts.
      - The dictionary has no entry if the count is zero for a day and user.
      - The RDFDateTime only contains date information. The time part is always
        midnight in UTC.
    """

  @abc.abstractmethod
  def WriteAPIAuditEntry(self, entry: objects_pb2.APIAuditEntry) -> None:
    """Writes an audit entry to the database.

    Args:
      entry: An `APIAuditEntry` instance.
    """

  @abc.abstractmethod
  def WriteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Writes a list of message handler requests to the database.

    Args:
      requests: List of MessageHandlerRequest.
    """

  @abc.abstractmethod
  def ReadMessageHandlerRequests(
      self,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    """Reads all message handler requests from the database.

    Returns:
      A list of MessageHandlerRequest, sorted by timestamp,
      newest first.
    """

  @abc.abstractmethod
  def DeleteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Deletes a list of message handler requests from the database.

    Args:
      requests: List of MessageHandlerRequest.
    """

  @abc.abstractmethod
  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Registers a message handler to receive batches of messages.

    Args:
      handler: Method, which will be called repeatedly with lists of leased
        MessageHandlerRequest. Required.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid. Required.
      limit: Limit for the number of leased requests to give one execution of
        handler.
    """

  @abc.abstractmethod
  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered message handler.

    Args:
      timeout: A timeout in seconds for joining the handler thread.
    """

  @abc.abstractmethod
  def WriteCronJob(self, cronjob: flows_pb2.CronJob) -> None:
    """Writes a cronjob to the database.

    Args:
      cronjob: A cronjobs.CronJob object.
    """

  def ReadCronJob(self, cronjob_id: str) -> flows_pb2.CronJob:
    """Reads a cronjob from the database.

    Args:
      cronjob_id: The id of the cron job to read.

    Returns:
      A flows_pb2.CronJob object.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    return self.ReadCronJobs(cronjob_ids=[cronjob_id])[0]

  @abc.abstractmethod
  def ReadCronJobs(
      self, cronjob_ids: Optional[Sequence[str]] = None
  ) -> Sequence[flows_pb2.CronJob]:
    """Reads all cronjobs from the database.

    Args:
      cronjob_ids: A list of cronjob ids to read. If not set, returns all cron
        jobs in the database.

    Returns:
      A list of flows_pb2.CronJob objects.

    Raises:
      UnknownCronJobError: A cron job for at least one of the given ids
                           does not exist.
    """

  @abc.abstractmethod
  def EnableCronJob(self, cronjob_id: str) -> None:
    """Enables a cronjob.

    Args:
      cronjob_id: The id of the cron job to enable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def DisableCronJob(self, cronjob_id: str) -> None:
    """Disables a cronjob.

    Args:
      cronjob_id: The id of the cron job to disable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def DeleteCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def UpdateCronJob(
      self,
      cronjob_id: str,
      last_run_status: Union[
          "flows_pb2.CronJobRun.CronJobRunStatus", Literal[UNCHANGED]
      ] = UNCHANGED,
      last_run_time: Union[
          rdfvalue.RDFDatetime, Literal[UNCHANGED]
      ] = UNCHANGED,
      current_run_id: Union[str, Literal[UNCHANGED]] = UNCHANGED,
      state: Union[jobs_pb2.AttributedDict, Literal[UNCHANGED]] = UNCHANGED,
      forced_run_requested: Union[bool, Literal[UNCHANGED]] = UNCHANGED,
  ) -> None:
    """Updates run information for an existing cron job.

    Args:
      cronjob_id: The id of the cron job to update.
      last_run_status: A CronJobRunStatus object.
      last_run_time: The last time a run was started for this cron job.
      current_run_id: The id of the currently active run.
      state: The state dict for stateful cron jobs.
      forced_run_requested: A boolean indicating if a forced run is pending for
        this job.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def LeaseCronJobs(
      self,
      cronjob_ids: Optional[Sequence[str]] = None,
      lease_time: Optional[rdfvalue.Duration] = None,
  ) -> Sequence[flows_pb2.CronJob]:
    """Leases all available cron jobs.

    Args:
      cronjob_ids: A list of cronjob ids that should be leased. If None, all
        available cronjobs will be leased.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid.

    Returns:
      A list of flows_pb2.CronJob objects that were leased.
    """

  @abc.abstractmethod
  def ReturnLeasedCronJobs(self, jobs: Sequence[flows_pb2.CronJob]) -> None:
    """Makes leased cron jobs available for leasing again.

    Args:
      jobs: A list of leased cronjobs.

    Raises:
      ValueError: If not all of the cronjobs are leased.
    """

  @abc.abstractmethod
  def WriteCronJobRun(self, run_object: flows_pb2.CronJobRun) -> None:
    """Stores a cron job run object in the database.

    Args:
      run_object: A flows_pb2.CronJobRun object to store.
    """

  @abc.abstractmethod
  def ReadCronJobRuns(self, job_id: str) -> Sequence[flows_pb2.CronJobRun]:
    """Reads all cron job runs for a given job id.

    Args:
      job_id: Runs will be returned for the job with the given id.

    Returns:
      A list of flows_pb2.CronJobRun objects.
    """

  @abc.abstractmethod
  def ReadCronJobRun(self, job_id: str, run_id: str) -> flows_pb2.CronJobRun:
    """Reads a single cron job run from the db.

    Args:
      job_id: The job_id of the run to be read.
      run_id: The run_id of the run to be read.

    Returns:
      An flows_pb2.CronJobRun object.
    """

  @abc.abstractmethod
  def DeleteOldCronJobRuns(
      self, cutoff_timestamp: rdfvalue.RDFDatetime
  ) -> None:
    """Deletes cron job runs that are older than cutoff_timestamp.

    Args:
      cutoff_timestamp: This method deletes all runs that were started before
        cutoff_timestamp.

    Returns:
      The number of deleted runs.
    """

  @abc.abstractmethod
  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
  ) -> None:
    """Writes blob references for a given set of hashes.

    Every file known to GRR has a history of PathInfos. Every PathInfo has a
    hash_entry corresponding to a known hash of a file (or a downloaded part
    of the file) at a given moment.

    GRR collects files by collecting individual data blobs from the client.
    Thus, in the end a file contents may be described as a sequence of blobs.
    Using WriteHashBlobReferences we key this sequence of blobs not with the
    file name, but rather with a hash identifying file contents.

    This way for any given PathInfo we can look at the hash and say whether
    we have corresponding contents of the file by using ReadHashBlobReferences.

    Args:
      references_by_hash: A dict where SHA256HashID objects are keys and lists
        of BlobReference objects are values.
    """

  @abc.abstractmethod
  def ReadHashBlobReferences(
      self,
      hashes: Collection[rdf_objects.SHA256HashID],
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    """Reads blob references of a given set of hashes.

    Every file known to GRR has a history of PathInfos. Every PathInfo has a
    hash_entry corresponding to a known hash of a file (or a downloaded part
    of the file) at a given moment.

    GRR collects files by collecting individual data blobs from the client.
    Thus, in the end a file contents may be described as a sequence of blobs.
    We key this sequence of blobs not with the file name, but rather with a
    hash identifying file contents.

    This way for any given PathInfo we can look at the hash and say whether
    we have corresponding contents of the file by using ReadHashBlobReferences.

    Args:
      hashes: An iterable of SHA256HashID objects.

    Returns:
      A dict where SHA256HashID objects are keys and iterables of BlobReference
      objects are values. If no blob references are found for a certain hash,
      None will be used as a value instead of a list.
    """

  # If we send a message unsuccessfully to a client five times, we just give up
  # and remove the message to avoid endless repetition of some broken action.
  CLIENT_MESSAGES_TTL = 5

  @abc.abstractmethod
  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
  ) -> None:
    """Writes a flow object to the database.

    Args:
      flow_obj: A Flow object to write.
      allow_update: If False, raises AlreadyExistsError if the flow already
        exists in the database. If True, the flow will be updated.

    Raises:
      AlreadyExistsError: The flow already exists and allow_update is False.
      UnknownClientError: The client with the flow's client_id does not exist.
    """

  @abc.abstractmethod
  def ReadFlowObject(self, client_id: str, flow_id: str) -> flows_pb2.Flow:
    """Reads a flow object from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read.

    Returns:
      A Flow object.

    Raises:
      UnknownFlowError: The flow cannot be found.
    """

  @abc.abstractmethod
  def ReadAllFlowObjects(
      self,
      client_id: Optional[str] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
  ) -> list[flows_pb2.Flow]:
    """Returns all flow objects.

    Args:
      client_id: The client id.
      parent_flow_id: An (optional) identifier of a parent of listed flows.
      min_create_time: the minimum creation time (inclusive)
      max_create_time: the maximum creation time (inclusive)
      include_child_flows: include child flows in the results. If False, only
        parent flows are returned. Must be `True` if the parent flow is given.
      not_created_by: exclude flows created by any of the users in this list.

    Returns:
      A list of Flow objects.
    """

  def ReadChildFlowObjects(
      self, client_id: str, flow_id: str
  ) -> list[flows_pb2.Flow]:
    """Reads flow objects that were started by a given flow from the database.

    Args:
      client_id: The client id on which the flows are running.
      flow_id: The id of the parent flow.

    Returns:
      A list of rdf_flow_objects.Flow objects.
    """
    return self.ReadAllFlowObjects(
        client_id=client_id, parent_flow_id=flow_id, include_child_flows=True
    )

  @abc.abstractmethod
  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
  ) -> flows_pb2.Flow:
    """Marks a flow as being processed on this worker and returns it.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read.
      processing_time: Duration that the worker has to finish processing before
        the flow is considered stuck.

    Raises:
      ValueError: The flow is already marked as being processed.
      ParentHuntIsNotRunningError: If the flow's parent hunt is stopped or
      completed.

    Returns:
      And Flow object.
    """

  @abc.abstractmethod
  def ReleaseProcessedFlow(self, flow_obj: flows_pb2.Flow) -> bool:
    """Releases a flow that the worker was processing to the database.

    This method will check if there are currently more requests ready for
    processing. If there are, the flow will not be written to the database and
    the method will return false.

    Args:
      flow_obj: The Flow object to return to the database.

    Returns:
      A boolean indicating if it was possible to return the flow to the
      database. If there are currently more requests ready to being processed,
      this method will return false and the flow will not be written.
    """

  @abc.abstractmethod
  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[flows_pb2.Flow, UNCHANGED_TYPE] = UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, UNCHANGED_TYPE
      ] = UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, UNCHANGED_TYPE
      ] = UNCHANGED,
      processing_on: Union[str, UNCHANGED_TYPE] = UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, UNCHANGED_TYPE]
      ] = UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, UNCHANGED_TYPE]
      ] = UNCHANGED,
  ) -> None:
    """Updates flow objects in the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to update.
      flow_obj: An updated rdf_flow_objects.Flow object.
      flow_state: An update rdf_flow_objects.Flow.FlowState value.
      client_crash_info: A rdf_client.ClientCrash object to store with the flow.
      processing_on: Worker this flow is currently processed on.
      processing_since: Timestamp when the worker started processing this flow.
      processing_deadline: Time after which this flow will be considered stuck
        if processing hasn't finished.
    """

  @abc.abstractmethod
  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
  ) -> None:
    """Writes a list of flow requests to the database.

    Args:
      requests: List of FlowRequest objects.
    """

  @abc.abstractmethod
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
  ) -> None:
    """Updates next response ids of given requests.

    Used to update incremental requests (requests with a callback_state
    specified) after each new batch of responses is processed.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The flow id of the flow with requests to update.
      next_response_id_updates: A map from request ids to new "next_response_id"
        values.
    """

  @abc.abstractmethod
  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
  ) -> None:
    """Deletes a list of flow requests from the database.

    Note: This also deletes all corresponding responses.

    Args:
      requests: List of FlowRequest objects.
    """

  @abc.abstractmethod
  def WriteFlowResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> None:
    """Writes Flow responses and updates corresponding requests.

    This method not only stores the list of responses given in the database but
    also updates flow status information at the same time. Specifically, it
    updates all corresponding flow requests, setting the needs_processing flag
    in case all expected responses are available in the database after this call
    and, in case the request the flow is currently waiting on becomes available
    for processing, it also writes a FlowProcessingRequest to notify the worker.

    Args:
      responses: List of FlowResponses, FlowStatuses or FlowIterators values to
        write.
    """

  @abc.abstractmethod
  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> Iterable[
      tuple[
          flows_pb2.FlowRequest,
          dict[
              int,
              Sequence[
                  Union[
                      flows_pb2.FlowResponse,
                      flows_pb2.FlowStatus,
                      flows_pb2.FlowIterator,
                  ],
              ],
          ],
      ]
  ]:
    """Reads all requests and responses for a given flow from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read requests and responses for.

    Returns:
      A list of tuples (request, dict mapping response_id to response) for each
      request in the db.
    """

  @abc.abstractmethod
  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> None:
    """Deletes all requests and responses for a given flow from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to delete requests and responses for.
    """

  @abc.abstractmethod
  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
  ) -> dict[
      int,
      tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    """Reads all requests for a flow.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read requests for.

    Returns:
      A dict mapping flow request id to tuples (request,
      sorted list of responses for the request).
    """

  @abc.abstractmethod
  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Writes a list of flow processing requests to the database.

    Args:
      requests: List of FlowProcessingRequest.
    """

  @abc.abstractmethod
  def ReadFlowProcessingRequests(
      self,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    """Reads all flow processing requests from the database.

    Returns:
      A list of FlowProcessingRequest, sorted by timestamp,
      newest first.
    """

  @abc.abstractmethod
  def AckFlowProcessingRequests(
      self, requests: Iterable[flows_pb2.FlowProcessingRequest]
  ) -> None:
    """Acknowledges and deletes flow processing requests.

    Args:
      requests: List of rdf_flows.FlowProcessingRequest.
    """

  @abc.abstractmethod
  def DeleteAllFlowProcessingRequests(self) -> None:
    """Deletes all flow processing requests from the database."""

  @abc.abstractmethod
  def RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    """Registers a handler to receive flow processing messages.

    Args:
      handler: Method, which will be called repeatedly with lists of
        rdf_flows.FlowProcessingRequest. Required.
    """

  @abc.abstractmethod
  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered flow processing handler.

    Args:
      timeout: A timeout in seconds for joining the handler thread.
    """

  @abc.abstractmethod
  def WriteFlowResults(self, results: Sequence[flows_pb2.FlowResult]) -> None:
    """Writes flow results for a given flow.

    Args:
      results: A sequence of FlowResult protos.
    """

  @abc.abstractmethod
  def ReadFlowResults(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads flow results of a given flow using given query options.

    If both with_tag and with_type and/or with_substring arguments are provided,
    they will be applied using AND boolean operator.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read results for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be returned.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be returned.
      with_proto_type_url: (Optional) When specified, should be a string. Only
        results of a specified proto type url will be returned.
      with_substring: (Optional) When specified, should be a string. Only
        results having the specified string as a substring in their serialized
        form will be returned.

    Returns:
      A list of FlowResult values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountFlowResults(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow results of a given flow using given query options.

    If both with_tag and with_type arguments are provided, they will be applied
    using AND boolean operator.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count results for.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be accounted for.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be accounted for.

    Returns:
      A number of flow results of a given flow matching given query options.
    """

  @abc.abstractmethod
  def CountFlowResultsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by result type.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count results for.

    Returns:
      A dictionary of "type name" => <number of items>.
    """

  @abc.abstractmethod
  def CountFlowResultsByProtoTypeUrl(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by proto result type.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count results for.

    Returns:
      A dictionary of "type name" => <number of items>.
    """

  @abc.abstractmethod
  def CountFlowErrorsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow errors grouped by error type.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count errors for.

    Returns:
      A dictionary of "type name" => <number of items>.
    """

  @abc.abstractmethod
  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    """Writes flow errors for a given flow.

    Args:
      errors: An iterable with FlowError rdfvalues.
    """

  @abc.abstractmethod
  def ReadFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowError]:
    """Reads flow errors of a given flow using given query options.

    If both with_tag and with_type and/or with_substring arguments are provided,
    they will be applied using AND boolean operator.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read errors for.
      offset: An integer specifying an offset to be used when reading errors.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of errors to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      with_tag: (Optional) When specified, should be a string. Only errors
        having specified tag will be returned.
      with_type: (Optional) When specified, should be a string. Only errors of a
        specified type will be returned.

    Returns:
      A list of FlowError values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow errors of a given flow using given query options.

    If both with_tag and with_type arguments are provided, they will be applied
    using AND boolean operator.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count errors for.
      with_tag: (Optional) When specified, should be a string. Only errors
        having specified tag will be accounted for.
      with_type: (Optional) When specified, should be a string. Only errors of a
        specified type will be accounted for.

    Returns:
      A number of flow errors of a given flow matching given query options.
    """

  @abc.abstractmethod
  def WriteFlowLogEntry(self, entry: flows_pb2.FlowLogEntry) -> None:
    """Writes a single flow log entry to the database.

    Args:
      entry: A log entry to write.

    Returns:
      Nothing.
    """

  @abc.abstractmethod
  def ReadFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads flow log entries of a given flow using given query options.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to read log entries for.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_substring filter is applied
        (if specified).
      count: Number of log entries to read. "count" is applied after the
        with_substring filter is applied (if specified).
      with_substring: (Optional) When specified, should be a string. Only log
        entries having the specified string as a message substring will be
        returned.

    Returns:
      A list of FlowLogEntry values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountFlowLogEntries(self, client_id: str, flow_id: str) -> int:
    """Returns number of flow log entries of a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count log entries for.

    Returns:
      Number of flow log entries of a given flow.
    """

  @abc.abstractmethod
  def WriteFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      request_id: int,
      logs: Mapping[int, rrg_pb2.Log],
  ) -> None:
    """Writes new log entries for a particular action request.

    Args:
      client_id: An identifier of the client on which the action that logged the
        message ran on.
      flow_id: An identifier of the flow that issued the action that logged the
        message.
      request_id: An identifier of the flow action request that spawned the
        action that logged the message.
      logs: A mapping from response identifiers to log entries.

    Raises:
      UnknownFlowError: If the specified flow is not known.
    """

  @abc.abstractmethod
  def ReadFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
  ) -> Sequence[rrg_pb2.Log]:
    """Reads log entries logged by actions issued by a particular flow.

    Args:
      client_id: An identifier of the client on which the action that logged the
        message ran on.
      flow_id: An identifier of the flow that issued the action that logged the
        message.
      offset: Number of log entries to skip (in response order).
      count: Number of log entries to read.

    Returns:
      A sequence of log messages (sorted in order in which they were logged).
    """

  @abc.abstractmethod
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: flows_pb2.FlowOutputPluginLogEntry,
  ) -> None:
    """Writes a single output plugin log entry to the database.

    Args:
      entry: An output plugin flow entry to write.
    """

  @abc.abstractmethod
  def WriteMultipleFlowOutputPluginLogEntries(
      self,
      entries: Sequence[flows_pb2.FlowOutputPluginLogEntry],
  ) -> None:
    """Writes multiple output plugin log entries to the database.

    Args:
      entries: A list of output plugin flow entries to write.
    """

  @abc.abstractmethod
  def ReadFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to read log entries for.
      output_plugin_id: The id of an output plugin with logs to be read.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_type filter is applied (if
        specified).
      count: Number of log entries to read. "count" is applied after the
        with_type filter is applied (if specified).
      with_type: (Optional) When specified, should have a
        FlowOutputPluginLogEntry.LogEntryType value. Output will be limited to
        entries with a given type.

    Returns:
      A list of FlowOutputPluginLogEntry values sorted by timestamp in ascending
      order.
    """

  @abc.abstractmethod
  def ReadAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries for all plugins of a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to read log entries for.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_type filter is applied (if
        specified).
      count: Number of log entries to read. "count" is applied after the
        with_type filter is applied (if specified).
      with_type: (Optional) When specified, should have a
        FlowOutputPluginLogEntry.LogEntryType value. Output will be limited to
        entries with a given type.

    Returns:
      A list of FlowOutputPluginLogEntry values sorted by timestamp in ascending
      order.
    """

  @abc.abstractmethod
  def CountFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> int:
    """Returns the number of flow output plugin log entries of a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count output plugin log entries for.
      output_plugin_id: The id of an output plugin with logs to be read. NOTE:
        REL_DB code uses strings for output plugin ids for consistency (as all
        other DB ids are strings). At the moment plugin_id in the database is
        simply a stringified index of the plugin in Flow/Hunt.output_plugins
        list.
      with_type: (Optional) When specified, should have a
        FlowOutputPluginLogEntry.LogEntryType value. Only records of a given
        type will be counted.

    Returns:
      Number of output log entries.
    """

  @abc.abstractmethod
  def CountAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
  ) -> int:
    """Returns the total number of flow output plugin log entries."""

  @abc.abstractmethod
  def ReadHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ):
    """Reads hunt output plugin log entries.

    Args:
      hunt_id: The hunt id of a hunt with the flows to read output plugins log
        entries from.
      output_plugin_id: The id of an output plugin with logs to be read. NOTE:
        REL_DB code uses strings for output plugin ids for consistency (as all
        other DB ids are strings). At the moment plugin_id in the database is
        simply a stringified index of the plugin in Flow/Hunt.output_plugins
        list.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_type filter is applied (if
        specified).
      count: Number of log entries to read. "count" is applied after the
        with_type filter is applied (if specified).
      with_type: (Optional) When specified, should have a
        FlowOutputPluginLogEntry.LogEntryType value. Output will be limited to
        entries with a given type.

    Returns:
      A list of FlowOutputPluginLogEntry values sorted by timestamp in ascending
      order.
    """

  @abc.abstractmethod
  def CountHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ):
    """Returns number of hunt output plugin log entries of a given hunt.

    Args:
      hunt_id: The hunt id of a hunt with output plugins log entries to be
        counted.
      output_plugin_id: The id of an output plugin with logs to be read. NOTE:
        REL_DB code uses strings for output plugin ids for consistency (as all
        other DB ids are strings). At the moment plugin_id in the database is
        simply a stringified index of the plugin in Flow/Hunt.output_plugins
        list.
      with_type: (Optional) When specified, should have a
        FlowOutputPluginLogEntry.LogEntryType value. Only records of a given
        type will be counted.

    Returns:
      Number of output plugin log entries.
    """

  @abc.abstractmethod
  def WriteHuntObject(self, hunt_obj: hunts_pb2.Hunt) -> None:
    """Writes a hunt object to the database.

    Args:
      hunt_obj: A Hunt object to write.
    """

  @abc.abstractmethod
  def UpdateHuntObject(
      self,
      hunt_id: str,
      duration: Optional[rdfvalue.Duration] = None,
      client_rate: Optional[float] = None,
      client_limit: Optional[int] = None,
      hunt_state: Optional[hunts_pb2.Hunt.HuntState.ValueType] = None,
      hunt_state_reason: Optional[
          hunts_pb2.Hunt.HuntStateReason.ValueType
      ] = None,
      hunt_state_comment: Optional[str] = None,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      num_clients_at_start_time: Optional[int] = None,
  ):
    """Updates the hunt object by applying the update function.

    Each keyword argument when set to None, means that that corresponding value
    shouldn't be updated.

    Args:
      hunt_id: Id of the hunt to be updated.
      duration: A maximum allowed running time duration of the flow.
      client_rate: Number corresponding to hunt's client rate.
      client_limit: Number corresponding hunt's client limit.
      hunt_state: New Hunt.HuntState value.
      hunt_state_reason: New Hunt.HuntStateReason value.
      hunt_state_comment: String corresponding to a hunt state comment.
      start_time: RDFDatetime corresponding to a start time of the hunt.
      num_clients_at_start_time: Integer corresponding to a number of clients at
        start time.
    """

  @abc.abstractmethod
  def ReadHuntOutputPluginsStates(
      self, hunt_id: str
  ) -> list[output_plugin_pb2.OutputPluginState]:
    """Reads all hunt output plugins states of a given hunt.

    Args:
      hunt_id: Id of the hunt.

    Returns:
      An iterable of rdf_flow_runner.OutputPluginState objects.

    Raises:
      UnknownHuntError: if a hunt with a given hunt id does not exit.
    """

  @abc.abstractmethod
  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
  ) -> None:
    """Writes hunt output plugin states for a given hunt.

    Args:
      hunt_id: Id of the hunt.
      states: An iterable with rdf_flow_runner.OutputPluginState objects.

    Raises:
      UnknownHuntError: if a hunt with a given hunt id does not exit.
    """
    pass

  @abc.abstractmethod
  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[
          [jobs_pb2.AttributedDict],
          jobs_pb2.AttributedDict,
      ],
  ) -> None:
    """Updates hunt output plugin state for a given output plugin.

    Args:
      hunt_id: Id of the hunt to be updated.
      state_index: Index of a state in ReadHuntOutputPluginsStates-returned
        list.
      update_fn: A function accepting a (descriptor, state) arguments, where
        descriptor is OutputPluginDescriptor and state is an AttributedDict. The
        function is expected to return a modified state (it's ok to modify it
        in-place).

    Raises:
      UnknownHuntError: if a hunt with a given hunt id does not exit.
      UnknownHuntOutputPluginStateError: if a state with a given index does
          not exist.
    """

  @abc.abstractmethod
  def DeleteHuntObject(self, hunt_id: str) -> None:
    """Deletes a hunt object with a given id.

    Args:
      hunt_id: Id of the hunt to be deleted.
    """

  @abc.abstractmethod
  def ReadHuntObject(self, hunt_id: str) -> hunts_pb2.Hunt:
    """Reads a hunt object from the database.

    Args:
      hunt_id: The id of the hunt to read.

    Raises:
      UnknownHuntError: if there's no hunt with the corresponding id.

    Returns:
      An rdf_hunt_objects.Hunt object.
    """

  @abc.abstractmethod
  def ReadHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> list[hunts_pb2.Hunt]:
    """Reads hunt objects from the database.

    Args:
      offset: An integer specifying an offset to be used when reading hunt
        objects.
      count: Number of hunt objects to read.
      with_creator: When specified, should be a string corresponding to a GRR
        username. Only hunts created by the matching user will be returned.
      created_after: When specified, should be a rdfvalue.RDFDatetime. Only
        hunts with create_time after created_after timestamp will be returned.
      with_description_match: When specified, will only return hunts with
        descriptions containing a given substring.
      created_by: When specified, should be a list of strings corresponding to
        GRR usernames. Only metadata for hunts created by the matching users
        will be returned.
      not_created_by: When specified, should be a list of strings corresponding
        to GRR usernames. Only metadata for hunts NOT created by any of the
        matching users will be returned.
      with_states: When specified should be a list of `Hunt.HuntState`s. Only
        metadata for hunts with states on the list will be returned.

    Returns:
      A list of rdf_hunt_objects.Hunt objects sorted by create_time in
      descending order.
    """

  # TODO: Cleanup `with_creator`(single user) in favor of
  # `created_by`(list).
  @abc.abstractmethod
  def ListHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> list[hunts_pb2.HuntMetadata]:
    """Reads metadata for hunt objects from the database.

    Args:
      offset: An integer specifying an offset to be used when reading hunt
        metadata.
      count: Number of hunt metadata objects to read.
      with_creator: When specified, should be a string corresponding to a GRR
        username. Only metadata for hunts created by the matching user will be
        returned.
      created_after: When specified, should be a rdfvalue.RDFDatetime. Only
        metadata for hunts with create_time after created_after timestamp will
        be returned.
      with_description_match: When specified, will only return metadata for
        hunts with descriptions containing a given substring.
      created_by: When specified, should be a list of strings corresponding to
        GRR usernames. Only metadata for hunts created by the matching users
        will be returned.
      not_created_by: When specified, should be a list of strings corresponding
        to GRR usernames. Only metadata for hunts NOT created by any of the
        matching users will be returned.
      with_states: When specified should be a list of `Hunt.HuntState`s. Only
        metadata for hunts with states on the list will be returned.

    Returns:
      A list of rdf_hunt_objects.HuntMetadata objects sorted by create_time in
      descending order.
    """

  @abc.abstractmethod
  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads hunt log entries of a given hunt using given query options.

    Args:
      hunt_id: The id of the hunt to read log entries for.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_substring filter is applied
        (if specified).
      count: Number of log entries to read. "count" is applied after the
        with_substring filter is applied (if specified).
      with_substring: (Optional) When specified, should be a string. Only log
        entries having the specified string as a message substring will be
        returned.

    Returns:
      A list of FlowLogEntry values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountHuntLogEntries(self, hunt_id: str) -> int:
    """Returns number of hunt log entries of a given hunt.

    Args:
      hunt_id: The id of the hunt to count log entries for.

    Returns:
      Number of hunt log entries of a given hunt.
    """

  @abc.abstractmethod
  def ReadHuntResults(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
      with_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options.

    If both with_tag and with_type and/or with_substring arguments are provided,
    they will be applied using AND boolean operator.

    Args:
      hunt_id: The id of the hunt to read results for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be returned.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be returned.
      with_proto_type_url: (Optional) When specified, should be a string. Only
        results of a specified proto type url will be returned.
      with_substring: (Optional) When specified, should be a string. Only
        results having the specified string as a substring in their serialized
        form will be returned.
      with_timestamp: (Optional) When specified should an rdfvalue.RDFDatetime.
        Only results with a given timestamp will be returned.

    Returns:
      A list of FlowResult values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
  ) -> int:
    """Counts hunt results of a given hunt using given query options.

    If both with_tag and with_type arguments are provided, they will be applied
    using AND boolean operator.

    Args:
      hunt_id: The id of the hunt to count results for.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be accounted for.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be accounted for.
      with_proto_type_url: (Optional) When specified, should be a string. Only
        results of a specified proto type will be accounted for.

    Returns:
      A number of hunt results of a given hunt matching given query options.
    """

  @abc.abstractmethod
  def CountHuntResultsByType(self, hunt_id: str) -> Mapping[str, int]:
    """Returns counts of items in hunt results grouped by type.

    Args:
      hunt_id: The id of the hunt to count results for.

    Returns:
      A dictionary of "type name" => <number of items>.
    """

  @abc.abstractmethod
  def CountHuntResultsByProtoTypeUrl(self, hunt_id: str) -> Mapping[str, int]:
    """Returns counts of hunt results grouped by proto result type.

    Args:
      hunt_id: The id of the hunt to count results for.

    Returns:
      A dictionary of "type url" => <number of items>.
    """

  @abc.abstractmethod
  def ReadHuntFlows(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: HuntFlowsCondition = HuntFlowsCondition.UNSET,
  ) -> Sequence[flows_pb2.Flow]:
    """Reads hunt flows matching given conditins.

    If more than one condition is specified, all of them have to be fulfilled
    for a particular flow object to be returned (i.e. they're applied with AND).

    Args:
      hunt_id: The id of the hunt to read log entries for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      filter_condition: One of HuntFlowsCondition constants describing a
        condition to filter ReadHuntFlows results.

    Returns:
      A list of Flow objects.
    """

  @abc.abstractmethod
  def CountHuntFlows(
      self,
      hunt_id: str,
      filter_condition: Optional[HuntFlowsCondition] = HuntFlowsCondition.UNSET,
  ) -> int:
    """Counts hunt flows matching given conditions.

    If more than one condition is specified, all of them have to be fulfilled
    for a particular flow object to be returned (i.e. they're applied with AND).

    Args:
      hunt_id: The id of the hunt to read log entries for.
        with_tag/with_type/with_substring filters are applied.
      filter_condition: One of HuntFlowsCondition constants describing a
        condition to influence CountHuntFlows results.

    Returns:
      A number of flows matching the specified condition.
    """

  def ReadHuntFlowErrors(
      self,
      hunt_id: str,
      offset: int,
      count: int,
  ) -> Mapping[str, FlowErrorInfo]:
    """Returns errors for flows of the given hunt.

    Args:
      hunt_id: Identifier of the hunt for which to retrieve errors.
      offset: Offset from which we start returning errors.
      count: Number of rows

    Returns:
      A mapping from client identifiers to information about errors.
    """
    results = {}

    for flow_obj in self.ReadHuntFlows(
        hunt_id,
        offset=offset,
        count=count,
        filter_condition=HuntFlowsCondition.FAILED_FLOWS_ONLY,
    ):
      flow_obj = mig_flow_objects.ToRDFFlow(flow_obj)
      info = FlowErrorInfo(
          message=flow_obj.error_message,
          time=flow_obj.last_update_time,
      )
      if flow_obj.HasField("backtrace"):
        info.backtrace = flow_obj.backtrace

      results[flow_obj.client_id] = info

    return results

  def ReadHuntCounters(
      self,
      hunt_id: str,
  ) -> HuntCounters:
    """Reads hunt counters.

    Args:
      hunt_id: The id of the hunt to read counters for.

    Returns:
      HuntCounters object.
    """
    return self.ReadHuntsCounters([hunt_id])[hunt_id]

  @abc.abstractmethod
  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
  ) -> Mapping[str, HuntCounters]:
    """Reads hunt counters for several hunt_ids.

    Args:
      hunt_ids: The ids of the hunts to read counters for.

    Returns:
      A mapping from hunt_ids to HuntCounters objects.
    """

  @abc.abstractmethod
  def ReadHuntClientResourcesStats(
      self, hunt_id: str
  ) -> jobs_pb2.ClientResourcesStats:
    """Read hunt client resources stats.

    Args:
      hunt_id: The id of the hunt to read counters for.

    Returns:
      ClientResourcesStats object.
    """

  @abc.abstractmethod
  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
  ) -> Sequence[FlowStateAndTimestamps]:
    """Reads hunt flows states and timestamps.

    Args:
      hunt_id: The id of the hunt to read counters for.

    Returns:
      An iterable of FlowStateAndTimestamps objects (in no particular
      sorting order).
    """

  @abc.abstractmethod
  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
  ) -> None:
    """Writes blob references for a signed binary to the DB.

    Args:
      binary_id: Signed binary id of the binary.
      references: Binary blob references.
    """

  @abc.abstractmethod
  def ReadSignedBinaryReferences(
      self, binary_id: objects_pb2.SignedBinaryID
  ) -> tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    """Reads blob references for the signed binary with the given id.

    Args:
      binary_id: Signed binary id of the binary to read.

    Returns:
      A tuple of the signed binary's rdf_objects.BlobReferences and an
      RDFDatetime representing the time when the references were written to the
      DB.
    """

  @abc.abstractmethod
  def ReadIDsForAllSignedBinaries(self) -> Sequence[objects_pb2.SignedBinaryID]:
    """Returns ids for all signed binaries in the DB."""

  @abc.abstractmethod
  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
  ) -> None:
    """Deletes blob references for the given signed binary from the DB.

    Does nothing if no entry with the given id exists in the DB.

    Args:
      binary_id: An id of the signed binary to delete.
    """

  @abc.abstractmethod
  def WriteYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      username: str,
  ) -> None:
    """Marks the specified blob id as a YARA signature.

    Args:
      blob_id: An identifier of a blob that is to be marked as YARA signature.
      username: An name of the GRR user that uploaded the signature.
    """

  @abc.abstractmethod
  def VerifyYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
  ) -> bool:
    """Verifies whether the specified blob is a YARA signature.

    Args:
      blob_id: An identifier of a blob to verify.

    Returns:
      `True` if the blob identifier refers to a YARA signature.
    """

  @abc.abstractmethod
  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
  ) -> None:
    """Inserts or updates the ScheduledFlow in the database.

    Args:
      scheduled_flow: the ScheduledFlow to insert.

    Raises:
      UnknownClientError: if no client with client_id exists.
      UnknownGRRUserError: if creator does not exist as user.
    """

  @abc.abstractmethod
  def DeleteScheduledFlow(
      self,
      client_id: str,
      creator: str,
      scheduled_flow_id: str,
  ) -> None:
    """Deletes the ScheduledFlow from the database.

    Args:
      client_id: The ID of the client of the ScheduledFlow.
      creator: The username of the user who created the ScheduledFlow.
      scheduled_flow_id: The ID of the ScheduledFlow.

    Raises:
      UnknownScheduledFlowError: if no such ScheduledFlow exists.
    """

  @abc.abstractmethod
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    """Lists all ScheduledFlows for the client and creator."""

  @abc.abstractmethod
  def WriteBlobEncryptionKeys(
      self,
      key_names: dict[models_blobs.BlobID, str],
  ) -> None:
    """Associates the specified blobs with the given encryption keys.

    Args:
      key_names: A mapping from blobs to key names to associate.
    """

  @abc.abstractmethod
  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[models_blobs.BlobID],
  ) -> dict[models_blobs.BlobID, Optional[str]]:
    """Retrieves encryption keys associated with blobs.

    Args:
      blob_ids: A collection of blob identifiers to retrieve the key names for.

    Returns:
      An mapping from blob to a key name associated with it (if available).
    """

  def WriteSignedCommand(
      self,
      signed_command: signed_commands_pb2.SignedCommand,
  ) -> None:
    """Writes a signed command to the database.

    Args:
      signed_command: A signed command to write.

    Raises:
      AtLeastOneDuplicatedSignedCommandError: The command already exists.
    """
    self.WriteSignedCommands([signed_command])

  @abc.abstractmethod
  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
  ) -> None:
    """Writes signed commands to the database.

    Args:
      signed_commands: Signed commands to write.

    Raises:
      AtLeastOneDuplicatedSignedCommandError: At least one of the commands
      already exists.
    """

  @abc.abstractmethod
  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
  ) -> signed_commands_pb2.SignedCommand:
    """Reads a signed command from the database.

    Args:
      id_: The identifier of the command to read.
      operating_system: Operating system of the command to read.

    Returns:
      A signed command for the given name.
    Raises:
      NotFoundError: The command does not exist.
    """

  @abc.abstractmethod
  def ReadSignedCommands(
      self,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    """Reads all signed commands from the database.

    Returns:
      All signed commands.
    """

  def LookupSignedCommand(
      self,
      operating_system: signed_commands_pb2.SignedCommand.OS,
      path: str,
      args: Sequence[str],
  ) -> signed_commands_pb2.SignedCommand:
    """Lookups a signed command matching the given system, path and arguments.

    A command matching the path and arguments is returned only if it has no
    environment variables, stdin specified or unsigned parts.

    Args:
      operating_system: System the signed command is supposed to run on.
      path: Path of the signed command.
      args: Arguments of the signed command.

    Returns:
      Signed command instance that matches the given path and arguments.

    Raises:
      NoMatchingSignedCommandError: If a matching command cannot be found.
    """
    path_raw_bytes = path.encode("utf-8")

    for command in self.ReadSignedCommands():
      rrg_command = rrg_execute_signed_command_pb2.Command()
      rrg_command.ParseFromString(command.command)

      if any(arg.unsigned_allowed for arg in rrg_command.args):
        continue

      args_signed = []
      args_signed.extend(rrg_command.args_signed)
      args_signed.extend(arg.signed for arg in rrg_command.args)

      if (
          command.operating_system == operating_system
          and rrg_command.path.raw_bytes == path_raw_bytes
          and args_signed == args
          and not rrg_command.env_signed
          and not rrg_command.env_unsigned_allowed
          and not rrg_command.signed_stdin
          and not rrg_command.unsigned_stdin_allowed
      ):
        return command

    raise NoMatchingSignedCommandError(
        operating_system=operating_system,
        path=path,
        args=args,
    )

  @abc.abstractmethod
  def DeleteAllSignedCommands(
      self,
  ):
    """Deletes all signed commands from the database."""


class DatabaseValidationWrapper(Database):
  """Database wrapper that validates the arguments."""

  def __init__(self, delegate: Database):
    super().__init__()
    self.delegate = delegate

  def Now(self) -> rdfvalue.RDFDatetime:
    return self.delegate.Now()

  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    return self.delegate.MinTimestamp()

  def WriteArtifact(self, artifact: artifact_pb2.Artifact) -> None:
    precondition.AssertType(artifact, artifact_pb2.Artifact)
    if not artifact.name:
      raise ValueError("Empty artifact name")
    _ValidateStringLength(
        "Artifact names", artifact.name, MAX_ARTIFACT_NAME_LENGTH
    )

    return self.delegate.WriteArtifact(artifact)

  def ReadArtifact(self, name: str) -> artifact_pb2.Artifact:
    precondition.AssertType(name, str)
    return self.delegate.ReadArtifact(name)

  def ReadAllArtifacts(self) -> Sequence[artifact_pb2.Artifact]:
    return self.delegate.ReadAllArtifacts()

  def DeleteArtifact(self, name: str) -> None:
    precondition.AssertType(name, str)
    return self.delegate.DeleteArtifact(name)

  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    _ValidateClientIds(client_ids)
    precondition.AssertOptionalType(first_seen, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(last_ping, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(last_foreman, rdfvalue.RDFDatetime)

    if fleetspeak_validation_info is not None:
      precondition.AssertDictType(fleetspeak_validation_info, str, str)

    return self.delegate.MultiWriteClientMetadata(
        client_ids=client_ids,
        first_seen=first_seen,
        last_ping=last_ping,
        last_foreman=last_foreman,
        fleetspeak_validation_info=fleetspeak_validation_info,
    )

  def DeleteClient(
      self,
      client_id: str,
  ) -> None:
    precondition.ValidateClientId(client_id)
    return self.delegate.DeleteClient(client_id)

  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientMetadata(client_ids)

  def WriteClientSnapshot(
      self,
      snapshot: objects_pb2.ClientSnapshot,
  ) -> None:
    precondition.AssertType(snapshot, objects_pb2.ClientSnapshot)
    _ValidateStringLength(
        "Platform", snapshot.knowledge_base.os, _MAX_CLIENT_PLATFORM_LENGTH
    )
    return self.delegate.WriteClientSnapshot(snapshot)

  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientSnapshot]:
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientSnapshot(client_ids)

  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientFullInfo(
        client_ids, min_last_ping=min_last_ping
    )

  def ReadClientLastPings(
      self,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      batch_size: int = CLIENT_IDS_BATCH_SIZE,
  ) -> Iterator[Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    precondition.AssertOptionalType(min_last_ping, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(max_last_ping, rdfvalue.RDFDatetime)
    precondition.AssertType(batch_size, int)

    if batch_size < 1:
      raise ValueError(
          "batch_size needs to be a positive integer, got {}".format(batch_size)
      )

    return self.delegate.ReadClientLastPings(
        min_last_ping=min_last_ping,
        max_last_ping=max_last_ping,
        batch_size=batch_size,
    )

  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    precondition.ValidateClientId(client_id)
    if timerange is not None:
      self._ValidateTimeRange(timerange)

    return self.delegate.ReadClientSnapshotHistory(
        client_id, timerange=timerange
    )

  def ReadClientStartupInfoHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
      exclude_snapshot_collections: bool = False,
  ) -> Sequence[jobs_pb2.StartupInfo]:
    precondition.ValidateClientId(client_id)
    if timerange is not None:
      self._ValidateTimeRange(timerange)

    return self.delegate.ReadClientStartupInfoHistory(
        client_id,
        timerange=timerange,
        exclude_snapshot_collections=exclude_snapshot_collections,
    )

  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup_info: jobs_pb2.StartupInfo,
  ) -> None:
    precondition.AssertType(startup_info, jobs_pb2.StartupInfo)
    precondition.ValidateClientId(client_id)

    return self.delegate.WriteClientStartupInfo(client_id, startup_info)

  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
  ) -> None:
    return self.delegate.WriteClientRRGStartup(client_id, startup)

  def ReadClientRRGStartup(
      self,
      client_id: str,
  ) -> Optional[rrg_startup_pb2.Startup]:
    return self.delegate.ReadClientRRGStartup(client_id)

  def ReadClientStartupInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.StartupInfo]:
    precondition.ValidateClientId(client_id)

    return self.delegate.ReadClientStartupInfo(client_id)

  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash_info: jobs_pb2.ClientCrash,
  ) -> None:
    precondition.AssertType(crash_info, jobs_pb2.ClientCrash)
    precondition.ValidateClientId(client_id)

    return self.delegate.WriteClientCrashInfo(client_id, crash_info)

  def ReadClientCrashInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.ClientCrash]:
    precondition.ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfo(client_id)

  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    precondition.ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfoHistory(client_id)

  def AddClientKeywords(
      self,
      client_id: str,
      keywords: Collection[str],
  ) -> None:
    precondition.ValidateClientId(client_id)
    precondition.AssertIterableType(keywords, str)

    return self.delegate.AddClientKeywords(client_id, keywords)

  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the specified clients."""
    return self.delegate.MultiAddClientKeywords(client_ids, keywords)

  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, Collection[str]]:
    precondition.AssertIterableType(keywords, str)
    keywords = set(keywords)

    if start_time:
      self._ValidateTimestamp(start_time)

    result = self.delegate.ListClientsForKeywords(
        keywords, start_time=start_time
    )
    precondition.AssertDictType(result, str, Collection)
    for value in result.values():
      precondition.AssertIterableType(value, str)
    return result

  def RemoveClientKeyword(
      self,
      client_id: str,
      keyword: str,
  ) -> None:
    precondition.ValidateClientId(client_id)
    precondition.AssertType(keyword, str)

    return self.delegate.RemoveClientKeyword(client_id, keyword)

  def AddClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Collection[str],
  ) -> None:
    precondition.ValidateClientId(client_id)
    _ValidateUsername(owner)
    for label in labels:
      _ValidateLabel(label)

    return self.delegate.AddClientLabels(client_id, owner, labels)

  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches user labels to the specified clients."""
    return self.delegate.MultiAddClientLabels(client_ids, owner, labels)

  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Sequence[objects_pb2.ClientLabel]]:
    _ValidateClientIds(client_ids)
    result = self.delegate.MultiReadClientLabels(client_ids)
    precondition.AssertDictType(result, str, list)
    for value in result.values():
      precondition.AssertIterableType(value, objects_pb2.ClientLabel)
    return result

  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Sequence[str],
  ) -> None:
    precondition.ValidateClientId(client_id)
    for label in labels:
      _ValidateLabel(label)

    return self.delegate.RemoveClientLabels(client_id, owner, labels)

  def ReadAllClientLabels(self) -> Collection[str]:
    result = self.delegate.ReadAllClientLabels()
    precondition.AssertIterableType(result, str)
    return result

  def WriteForemanRule(self, rule: jobs_pb2.ForemanCondition) -> None:
    precondition.AssertType(rule, jobs_pb2.ForemanCondition)

    if not rule.hunt_id:
      raise ValueError("Foreman rule has no hunt_id: %s" % rule)

    return self.delegate.WriteForemanRule(rule)

  def RemoveForemanRule(self, hunt_id: str) -> None:
    _ValidateHuntId(hunt_id)
    return self.delegate.RemoveForemanRule(hunt_id)

  def ReadAllForemanRules(self) -> Sequence[jobs_pb2.ForemanCondition]:
    return self.delegate.ReadAllForemanRules()

  def RemoveExpiredForemanRules(self) -> None:
    return self.delegate.RemoveExpiredForemanRules()

  def WriteGRRUser(
      self,
      username: str,
      password: Optional[jobs_pb2.Password] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
      canary_mode: Optional[bool] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      email: Optional[str] = None,
  ) -> None:
    _ValidateUsername(username)

    if email is not None:
      _ValidateEmail(email)

    return self.delegate.WriteGRRUser(
        username,
        password=password,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type,
        email=email,
    )

  def ReadGRRUser(self, username) -> objects_pb2.GRRUser:
    _ValidateUsername(username)

    return self.delegate.ReadGRRUser(username)

  def ReadGRRUsers(self, offset=0, count=None) -> Sequence[objects_pb2.GRRUser]:
    if offset < 0:
      raise ValueError("offset has to be non-negative.")

    if count is not None and count < 0:
      raise ValueError("count has to be non-negative or None.")

    return self.delegate.ReadGRRUsers(offset=offset, count=count)

  def CountGRRUsers(self):
    return self.delegate.CountGRRUsers()

  def DeleteGRRUser(self, username):
    _ValidateUsername(username)

    return self.delegate.DeleteGRRUser(username)

  def WriteApprovalRequest(
      self, approval_request: objects_pb2.ApprovalRequest
  ) -> str:
    precondition.AssertType(approval_request, objects_pb2.ApprovalRequest)
    _ValidateUsername(approval_request.requestor_username)
    _ValidateApprovalType(approval_request.approval_type)

    if approval_request.grants:
      message = "Approval request with grants already set: {}"
      raise ValueError(message.format(approval_request))

    return self.delegate.WriteApprovalRequest(approval_request)

  def ReadApprovalRequest(self, requestor_username, approval_id):
    _ValidateUsername(requestor_username)
    _ValidateApprovalId(approval_id)

    return self.delegate.ReadApprovalRequest(requestor_username, approval_id)

  def ReadApprovalRequests(
      self,
      requestor_username,
      approval_type,
      subject_id=None,
      include_expired=False,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    _ValidateUsername(requestor_username)
    _ValidateApprovalType(approval_type)

    if subject_id is not None:
      _ValidateStringId("approval subject id", subject_id)

    return self.delegate.ReadApprovalRequests(
        requestor_username,
        approval_type,
        subject_id=subject_id,
        include_expired=include_expired,
    )

  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    _ValidateUsername(requestor_username)
    _ValidateApprovalId(approval_id)
    _ValidateUsername(grantor_username)

    return self.delegate.GrantApproval(
        requestor_username, approval_id, grantor_username
    )

  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> objects_pb2.PathInfo:
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    _ValidatePathComponents(components)

    if timestamp is not None:
      self._ValidateTimestamp(timestamp)

    return self.delegate.ReadPathInfo(
        client_id, path_type, components, timestamp=timestamp
    )

  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    precondition.AssertType(components_list, list)
    for components in components_list:
      _ValidatePathComponents(components)

    return self.delegate.ReadPathInfos(client_id, path_type, components_list)

  def ListChildPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    _ValidatePathComponents(components)
    precondition.AssertOptionalType(timestamp, rdfvalue.RDFDatetime)

    return self.delegate.ListChildPathInfos(
        client_id, path_type, components, timestamp=timestamp
    )

  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    _ValidatePathComponents(components)
    precondition.AssertOptionalType(timestamp, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(max_depth, int)

    return self.delegate.ListDescendantPathInfos(
        client_id,
        path_type,
        components,
        timestamp=timestamp,
        max_depth=max_depth,
    )

  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Iterable[objects_pb2.PathInfo],
  ) -> None:
    precondition.ValidateClientId(client_id)
    _ValidatePathInfos(path_infos)
    return self.delegate.WritePathInfos(client_id, path_infos)

  def WriteUserNotification(
      self, notification: objects_pb2.UserNotification
  ) -> None:
    precondition.AssertType(notification, objects_pb2.UserNotification)
    _ValidateUsername(notification.username)
    _ValidateNotificationType(notification.notification_type)
    _ValidateNotificationState(notification.state)

    return self.delegate.WriteUserNotification(notification)

  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]
      ] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    _ValidateUsername(username)
    if timerange is not None:
      self._ValidateTimeRange(timerange)
    if state is not None:
      _ValidateNotificationState(state)

    return self.delegate.ReadUserNotifications(
        username, state=state, timerange=timerange
    )

  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Iterable[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    precondition.ValidateClientId(client_id)
    _ValidateProtoEnumType(path_type, objects_pb2.PathInfo.PathType)
    precondition.AssertType(components_list, list)
    for components in components_list:
      _ValidatePathComponents(components)
    precondition.AssertOptionalType(cutoff, rdfvalue.RDFDatetime)

    return self.delegate.ReadPathInfosHistories(
        client_id=client_id,
        path_type=path_type,
        components_list=components_list,
        cutoff=cutoff,
    )

  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[ClientPath, Optional[objects_pb2.PathInfo]]:
    precondition.AssertIterableType(client_paths, ClientPath)
    precondition.AssertOptionalType(max_timestamp, rdfvalue.RDFDatetime)
    return self.delegate.ReadLatestPathInfosWithHashBlobReferences(
        client_paths, max_timestamp=max_timestamp
    )

  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
  ) -> None:
    precondition.AssertIterableType(timestamps, rdfvalue.RDFDatetime)
    _ValidateNotificationState(state)

    return self.delegate.UpdateUserNotifications(
        username, timestamps, state=state
    )

  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[list[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> list[objects_pb2.APIAuditEntry]:
    return self.delegate.ReadAPIAuditEntries(
        username=username,
        router_method_names=router_method_names,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
    )

  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, rdfvalue.RDFDatetime], int]:
    precondition.AssertOptionalType(min_timestamp, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(max_timestamp, rdfvalue.RDFDatetime)
    return self.delegate.CountAPIAuditEntriesByUserAndDay(
        min_timestamp=min_timestamp, max_timestamp=max_timestamp
    )

  def WriteAPIAuditEntry(self, entry: objects_pb2.APIAuditEntry) -> None:
    precondition.AssertType(entry, objects_pb2.APIAuditEntry)
    return self.delegate.WriteAPIAuditEntry(entry)

  def WriteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    precondition.AssertIterableType(requests, objects_pb2.MessageHandlerRequest)
    for request in requests:
      _ValidateMessageHandlerName(request.handler_name)
    return self.delegate.WriteMessageHandlerRequests(requests)

  def DeleteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    return self.delegate.DeleteMessageHandlerRequests(requests)

  def ReadMessageHandlerRequests(
      self,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    return self.delegate.ReadMessageHandlerRequests()

  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    if handler is None:
      raise ValueError("handler must be provided")

    _ValidateDuration(lease_time)
    return self.delegate.RegisterMessageHandler(
        handler, lease_time, limit=limit
    )

  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    return self.delegate.UnregisterMessageHandler(timeout=timeout)

  def WriteCronJob(self, cronjob: flows_pb2.CronJob):
    precondition.AssertType(cronjob, flows_pb2.CronJob)
    _ValidateCronJobId(cronjob.cron_job_id)
    return self.delegate.WriteCronJob(cronjob)

  def ReadCronJob(self, cronjob_id: str) -> flows_pb2.CronJob:
    _ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJob(cronjob_id)

  def ReadCronJobs(
      self, cronjob_ids: Optional[Sequence[str]] = None
  ) -> Sequence[flows_pb2.CronJob]:
    if cronjob_ids is not None:
      for cronjob_id in cronjob_ids:
        _ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJobs(cronjob_ids=cronjob_ids)

  def EnableCronJob(self, cronjob_id: str) -> None:
    _ValidateCronJobId(cronjob_id)
    return self.delegate.EnableCronJob(cronjob_id)

  def DisableCronJob(self, cronjob_id: str) -> None:
    _ValidateCronJobId(cronjob_id)
    return self.delegate.DisableCronJob(cronjob_id)

  def DeleteCronJob(self, cronjob_id: str) -> None:
    _ValidateCronJobId(cronjob_id)
    return self.delegate.DeleteCronJob(cronjob_id)

  def UpdateCronJob(
      self,
      cronjob_id: str,
      last_run_status: Union[
          "flows_pb2.CronJobRun.CronJobRunStatus", Literal[UNCHANGED]
      ] = UNCHANGED,
      last_run_time: Union[
          rdfvalue.RDFDatetime, Literal[UNCHANGED]
      ] = UNCHANGED,
      current_run_id: Union[str, Literal[UNCHANGED]] = UNCHANGED,
      state: Union[jobs_pb2.AttributedDict, Literal[UNCHANGED]] = UNCHANGED,
      forced_run_requested: Union[bool, Literal[UNCHANGED]] = UNCHANGED,
  ) -> None:
    _ValidateCronJobId(cronjob_id)
    if current_run_id is not None and current_run_id != Database.UNCHANGED:
      _ValidateCronJobRunId(current_run_id)
    if last_run_time is not None and last_run_time != Database.UNCHANGED:
      precondition.AssertType(last_run_time, rdfvalue.RDFDatetime)
    if state is not None and state != Database.UNCHANGED:
      precondition.AssertType(state, jobs_pb2.AttributedDict)
    if (
        forced_run_requested is not None
        and forced_run_requested != Database.UNCHANGED
    ):
      precondition.AssertType(forced_run_requested, bool)

    return self.delegate.UpdateCronJob(
        cronjob_id,
        last_run_status=last_run_status,
        last_run_time=last_run_time,
        current_run_id=current_run_id,
        state=state,
        forced_run_requested=forced_run_requested,
    )

  def LeaseCronJobs(
      self,
      cronjob_ids: Optional[Sequence[str]] = None,
      lease_time: Optional[rdfvalue.Duration] = None,
  ) -> Sequence[flows_pb2.CronJob]:
    if cronjob_ids:
      for cronjob_id in cronjob_ids:
        _ValidateCronJobId(cronjob_id)
    _ValidateDuration(lease_time)
    return self.delegate.LeaseCronJobs(
        cronjob_ids=cronjob_ids, lease_time=lease_time
    )

  def ReturnLeasedCronJobs(self, jobs: Sequence[flows_pb2.CronJob]) -> None:
    for job in jobs:
      precondition.AssertType(job, flows_pb2.CronJob)
    return self.delegate.ReturnLeasedCronJobs(jobs)

  def WriteCronJobRun(self, run_object: flows_pb2.CronJobRun) -> None:
    precondition.AssertType(run_object, flows_pb2.CronJobRun)
    return self.delegate.WriteCronJobRun(run_object)

  def ReadCronJobRun(self, job_id: str, run_id: str) -> flows_pb2.CronJobRun:
    _ValidateCronJobId(job_id)
    _ValidateCronJobRunId(run_id)
    return self.delegate.ReadCronJobRun(job_id, run_id)

  def ReadCronJobRuns(self, job_id: str) -> Sequence[flows_pb2.CronJobRun]:
    _ValidateCronJobId(job_id)
    return self.delegate.ReadCronJobRuns(job_id)

  def DeleteOldCronJobRuns(
      self, cutoff_timestamp: rdfvalue.RDFDatetime
  ) -> None:
    self._ValidateTimestamp(cutoff_timestamp)
    return self.delegate.DeleteOldCronJobRuns(cutoff_timestamp)

  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
  ) -> None:
    for h, refs in references_by_hash.items():
      _ValidateSHA256HashID(h)
      precondition.AssertIterableType(refs, objects_pb2.BlobReference)

    self.delegate.WriteHashBlobReferences(references_by_hash)

  def ReadHashBlobReferences(
      self,
      hashes: Collection[rdf_objects.SHA256HashID],
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    precondition.AssertIterableType(hashes, rdf_objects.SHA256HashID)
    return self.delegate.ReadHashBlobReferences(hashes)

  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
  ) -> None:
    precondition.AssertType(flow_obj, flows_pb2.Flow)
    precondition.AssertType(allow_update, bool)

    if flow_obj.HasField("create_time"):
      raise ValueError(f"Create time set on the flow object: {flow_obj}")

    return self.delegate.WriteFlowObject(flow_obj, allow_update=allow_update)

  def ReadFlowObject(self, client_id, flow_id):
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    return self.delegate.ReadFlowObject(client_id, flow_id)

  def ReadAllFlowObjects(
      self,
      client_id: Optional[str] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
  ) -> list[flows_pb2.Flow]:
    if client_id is not None:
      precondition.ValidateClientId(client_id)
    precondition.AssertOptionalType(min_create_time, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(max_create_time, rdfvalue.RDFDatetime)

    if parent_flow_id is not None and not include_child_flows:
      raise ValueError(
          f"Parent flow id specified ('{parent_flow_id}') in the childless mode"
      )

    if not_created_by is not None:
      precondition.AssertIterableType(not_created_by, str)

    return self.delegate.ReadAllFlowObjects(
        client_id=client_id,
        parent_flow_id=parent_flow_id,
        min_create_time=min_create_time,
        max_create_time=max_create_time,
        include_child_flows=include_child_flows,
        not_created_by=not_created_by,
    )

  def ReadChildFlowObjects(
      self,
      client_id: str,
      flow_id: str,
  ) -> list[flows_pb2.Flow]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    return self.delegate.ReadChildFlowObjects(client_id, flow_id)

  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
  ) -> flows_pb2.Flow:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    _ValidateDuration(processing_time)
    return self.delegate.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )

  def ReleaseProcessedFlow(self, flow_obj: flows_pb2.Flow) -> bool:
    precondition.AssertType(flow_obj, flows_pb2.Flow)
    return self.delegate.ReleaseProcessedFlow(flow_obj)

  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[
          flows_pb2.Flow, Database.UNCHANGED_TYPE
      ] = Database.UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, Database.UNCHANGED_TYPE
      ] = Database.UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, Database.UNCHANGED_TYPE
      ] = Database.UNCHANGED,
      processing_on: Union[str, Database.UNCHANGED_TYPE] = Database.UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, Database.UNCHANGED_TYPE]
      ] = Database.UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, Database.UNCHANGED_TYPE]
      ] = Database.UNCHANGED,
  ) -> None:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    if flow_obj != Database.UNCHANGED:
      precondition.AssertType(flow_obj, flows_pb2.Flow)

      if flow_state != Database.UNCHANGED:
        raise ConflictingUpdateFlowArgumentsError(
            client_id, flow_id, "flow_state"
        )
    if flow_state != Database.UNCHANGED:
      _ValidateProtoEnumType(flow_state, flows_pb2.Flow.FlowState)
    if client_crash_info != Database.UNCHANGED:
      precondition.AssertType(client_crash_info, jobs_pb2.ClientCrash)
    if processing_since != Database.UNCHANGED:
      if processing_since is not None:
        self._ValidateTimestamp(processing_since)
    if processing_deadline != Database.UNCHANGED:
      if processing_deadline is not None:
        self._ValidateTimestamp(processing_deadline)
    return self.delegate.UpdateFlow(
        client_id,
        flow_id,
        flow_obj=flow_obj,
        flow_state=flow_state,
        client_crash_info=client_crash_info,
        processing_on=processing_on,
        processing_since=processing_since,
        processing_deadline=processing_deadline,
    )

  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
  ) -> None:
    precondition.AssertIterableType(requests, flows_pb2.FlowRequest)
    return self.delegate.WriteFlowRequests(requests)

  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
  ) -> None:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertDictType(next_response_id_updates, int, int)
    return self.delegate.UpdateIncrementalFlowRequests(
        client_id, flow_id, next_response_id_updates
    )

  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
  ) -> None:
    precondition.AssertIterableType(requests, flows_pb2.FlowRequest)
    return self.delegate.DeleteFlowRequests(requests)

  def WriteFlowResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> None:
    for r in responses:
      precondition.AssertType(r.request_id, int)
      precondition.AssertType(r.response_id, int)
      precondition.AssertType(r.client_id, str)
      precondition.AssertType(r.flow_id, str)

    return self.delegate.WriteFlowResponses(responses)

  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> Iterable[
      tuple[
          flows_pb2.FlowRequest,
          dict[
              int,
              Sequence[
                  Union[
                      flows_pb2.FlowResponse,
                      flows_pb2.FlowStatus,
                      flows_pb2.FlowIterator,
                  ],
              ],
          ],
      ]
  ]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    return self.delegate.ReadAllFlowRequestsAndResponses(client_id, flow_id)

  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> None:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    return self.delegate.DeleteAllFlowRequestsAndResponses(client_id, flow_id)

  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
  ) -> dict[
      int,
      tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    return self.delegate.ReadFlowRequests(client_id, flow_id)

  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
  ) -> None:
    precondition.AssertIterableType(requests, flows_pb2.FlowProcessingRequest)
    return self.delegate.WriteFlowProcessingRequests(requests)

  def ReadFlowProcessingRequests(
      self,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    return self.delegate.ReadFlowProcessingRequests()

  def AckFlowProcessingRequests(
      self, requests: Iterable[flows_pb2.FlowProcessingRequest]
  ) -> None:
    precondition.AssertIterableType(requests, flows_pb2.FlowProcessingRequest)
    return self.delegate.AckFlowProcessingRequests(requests)

  def DeleteAllFlowProcessingRequests(self) -> None:
    return self.delegate.DeleteAllFlowProcessingRequests()

  def RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    if handler is None:
      raise ValueError("handler must be provided")
    return self.delegate.RegisterFlowProcessingHandler(handler)

  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    return self.delegate.UnregisterFlowProcessingHandler(timeout=timeout)

  def WriteFlowResults(self, results):
    for r in results:
      precondition.AssertType(r, flows_pb2.FlowResult)
      precondition.ValidateClientId(r.client_id)
      precondition.ValidateFlowId(r.flow_id)
      if r.HasField("hunt_id") and r.hunt_id:
        _ValidateHuntId(r.hunt_id)

    return self.delegate.WriteFlowResults(results)

  def ReadFlowResults(
      self,
      client_id,
      flow_id,
      offset,
      count,
      with_tag=None,
      with_type=None,
      with_proto_type_url=None,
      with_substring=None,
  ):
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)
    precondition.AssertOptionalType(with_proto_type_url, str)
    if with_type and with_proto_type_url:
      raise ValueError(
          "Only one of `with_type` and `with_proto_type_url` can be set."
      )
    precondition.AssertOptionalType(with_substring, str)

    return self.delegate.ReadFlowResults(
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_proto_type_url=with_proto_type_url,
        with_substring=with_substring,
    )

  def CountFlowResults(
      self,
      client_id,
      flow_id,
      with_tag=None,
      with_type=None,
  ):
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)

    return self.delegate.CountFlowResults(
        client_id, flow_id, with_tag=with_tag, with_type=with_type
    )

  def CountFlowResultsByType(
      self,
      client_id,
      flow_id,
  ):
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.CountFlowResultsByType(client_id, flow_id)

  def CountFlowResultsByProtoTypeUrl(
      self,
      client_id: str,
      flow_id: str,
  ) -> Mapping[str, int]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.CountFlowResultsByProtoTypeUrl(client_id, flow_id)

  def CountFlowErrorsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.CountFlowErrorsByType(client_id, flow_id)

  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    for r in errors:
      precondition.AssertType(r, flows_pb2.FlowError)
      precondition.ValidateClientId(r.client_id)
      precondition.ValidateFlowId(r.flow_id)
      if r.HasField("hunt_id") and r.hunt_id:
        _ValidateHuntId(r.hunt_id)

    return self.delegate.WriteFlowErrors(errors)

  def ReadFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowError]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)

    return self.delegate.ReadFlowErrors(
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
    )

  def CountFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)

    return self.delegate.CountFlowErrors(
        client_id, flow_id, with_tag=with_tag, with_type=with_type
    )

  def WriteFlowLogEntry(self, entry: flows_pb2.FlowLogEntry) -> None:
    precondition.ValidateClientId(entry.client_id)
    precondition.ValidateFlowId(entry.flow_id)
    if entry.HasField("hunt_id") and entry.hunt_id:
      _ValidateHuntId(entry.hunt_id)

    return self.delegate.WriteFlowLogEntry(entry)

  def ReadFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_substring, str)

    return self.delegate.ReadFlowLogEntries(
        client_id, flow_id, offset, count, with_substring=with_substring
    )

  def CountFlowLogEntries(self, client_id: str, flow_id: str) -> int:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.CountFlowLogEntries(client_id, flow_id)

  def WriteFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      request_id: int,
      logs: Mapping[int, rrg_pb2.Log],
  ) -> None:
    """Writes new log entries for a particular action request."""
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs=logs,
    )

  def ReadFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
  ) -> Sequence[rrg_pb2.Log]:
    """Reads log entries logged by actions issued by a particular flow."""
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    return self.delegate.ReadFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        offset=offset,
        count=count,
    )

  def WriteFlowOutputPluginLogEntry(
      self,
      entry: flows_pb2.FlowOutputPluginLogEntry,
  ) -> None:
    """Writes a single output plugin log entry to the database."""
    precondition.AssertType(entry, flows_pb2.FlowOutputPluginLogEntry)
    precondition.ValidateClientId(entry.client_id)
    precondition.ValidateFlowId(entry.flow_id)
    if entry.hunt_id:
      _ValidateHuntId(entry.hunt_id)

    return self.delegate.WriteFlowOutputPluginLogEntry(entry)

  def WriteMultipleFlowOutputPluginLogEntries(
      self,
      entries: Sequence[flows_pb2.FlowOutputPluginLogEntry],
  ) -> None:
    """Writes multiple output plugin log entries to the database."""
    for entry in entries:
      precondition.AssertType(entry, flows_pb2.FlowOutputPluginLogEntry)
      precondition.ValidateClientId(entry.client_id)
      precondition.ValidateFlowId(entry.flow_id)
      if entry.hunt_id:
        _ValidateHuntId(entry.hunt_id)
    return self.delegate.WriteMultipleFlowOutputPluginLogEntries(entries)

  def ReadFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      # See https://github.com/protocolbuffers/protobuf/pull/8182
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    _ValidateOutputPluginId(output_plugin_id)
    if with_type is not None:
      _ValidateProtoEnumType(
          with_type, flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      )

    return self.delegate.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, offset, count, with_type=with_type
    )

  def ReadAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    if with_type is not None:
      _ValidateProtoEnumType(
          with_type, flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      )

    return self.delegate.ReadAllFlowOutputPluginLogEntries(
        client_id, flow_id, offset, count, with_type=with_type
    )

  def CountFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ):
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    _ValidateOutputPluginId(output_plugin_id)

    return self.delegate.CountFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, with_type=with_type
    )

  def CountAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
  ) -> int:
    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)
    if with_type is not None:
      _ValidateProtoEnumType(
          with_type, flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      )
    return self.delegate.CountAllFlowOutputPluginLogEntries(
        client_id, flow_id, with_type=with_type
    )

  def ReadHuntOutputPluginLogEntries(
      self, hunt_id, output_plugin_id, offset, count, with_type=None
  ):
    _ValidateHuntId(hunt_id)
    _ValidateOutputPluginId(output_plugin_id)
    if with_type is not None:
      _ValidateProtoEnumType(
          with_type, flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      )

    return self.delegate.ReadHuntOutputPluginLogEntries(
        hunt_id, output_plugin_id, offset, count, with_type=with_type
    )

  def CountHuntOutputPluginLogEntries(
      self, hunt_id, output_plugin_id, with_type=None
  ):
    _ValidateHuntId(hunt_id)
    _ValidateOutputPluginId(output_plugin_id)
    if with_type is not None:
      _ValidateProtoEnumType(
          with_type, flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      )

    return self.delegate.CountHuntOutputPluginLogEntries(
        hunt_id, output_plugin_id, with_type=with_type
    )

  def WriteHuntObject(self, hunt_obj: hunts_pb2.Hunt) -> None:
    precondition.AssertType(hunt_obj, hunts_pb2.Hunt)

    if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
      raise ValueError("Creation of hunts in non-paused state is not allowed.")

    return self.delegate.WriteHuntObject(hunt_obj)

  def UpdateHuntObject(
      self,
      hunt_id: str,
      duration: Optional[rdfvalue.Duration] = None,
      client_rate: Optional[float] = None,
      client_limit: Optional[int] = None,
      hunt_state: Optional[hunts_pb2.Hunt.HuntState.ValueType] = None,
      hunt_state_reason: Optional[
          hunts_pb2.Hunt.HuntStateReason.ValueType
      ] = None,
      hunt_state_comment: Optional[str] = None,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      num_clients_at_start_time: Optional[int] = None,
  ):
    """Updates the hunt object by applying the update function."""
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(duration, rdfvalue.Duration)
    precondition.AssertOptionalType(client_rate, (float, int))
    precondition.AssertOptionalType(client_limit, int)
    if hunt_state is not None:
      _ValidateProtoEnumType(hunt_state, hunts_pb2.Hunt.HuntState)
    if hunt_state_reason is not None:
      _ValidateProtoEnumType(hunt_state, hunts_pb2.Hunt.HuntStateReason)

    precondition.AssertOptionalType(hunt_state_comment, str)
    precondition.AssertOptionalType(start_time, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(num_clients_at_start_time, int)

    return self.delegate.UpdateHuntObject(
        hunt_id,
        duration=duration,
        client_rate=client_rate,
        client_limit=client_limit,
        hunt_state=hunt_state,
        hunt_state_reason=hunt_state_reason,
        hunt_state_comment=hunt_state_comment,
        start_time=start_time,
        num_clients_at_start_time=num_clients_at_start_time,
    )

  def ReadHuntOutputPluginsStates(
      self,
      hunt_id: str,
  ) -> list[output_plugin_pb2.OutputPluginState]:
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntOutputPluginsStates(hunt_id)

  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
  ) -> None:
    """Writes a list of output plugin states to the database."""
    if not states:
      return

    _ValidateHuntId(hunt_id)
    precondition.AssertIterableType(states, output_plugin_pb2.OutputPluginState)
    self.delegate.WriteHuntOutputPluginsStates(hunt_id, states)

  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[
          [jobs_pb2.AttributedDict],
          jobs_pb2.AttributedDict,
      ],
  ) -> None:
    _ValidateHuntId(hunt_id)
    precondition.AssertType(state_index, int)
    return self.delegate.UpdateHuntOutputPluginState(
        hunt_id, state_index, update_fn
    )

  def DeleteHuntObject(self, hunt_id: str) -> None:
    _ValidateHuntId(hunt_id)
    return self.delegate.DeleteHuntObject(hunt_id)

  def ReadHuntObject(self, hunt_id: str) -> hunts_pb2.Hunt:
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntObject(hunt_id)

  def ReadHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> list[hunts_pb2.Hunt]:
    precondition.AssertOptionalType(offset, int)
    precondition.AssertOptionalType(count, int)
    precondition.AssertOptionalType(with_creator, str)
    precondition.AssertOptionalType(created_after, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(with_description_match, str)
    if created_by is not None:
      precondition.AssertIterableType(created_by, str)
    if not_created_by is not None:
      precondition.AssertIterableType(not_created_by, str)
    if with_states is not None:
      for state in with_states:
        _ValidateProtoEnumType(state, hunts_pb2.Hunt.HuntState)

    return self.delegate.ReadHuntObjects(
        offset,
        count,
        with_creator=with_creator,
        created_after=created_after,
        with_description_match=with_description_match,
        created_by=created_by,
        not_created_by=not_created_by,
        with_states=with_states,
    )

  def ListHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ):
    precondition.AssertOptionalType(offset, int)
    precondition.AssertOptionalType(count, int)
    precondition.AssertOptionalType(with_creator, str)
    precondition.AssertOptionalType(created_after, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(with_description_match, str)
    if created_by is not None:
      precondition.AssertIterableType(created_by, str)
    if not_created_by is not None:
      precondition.AssertIterableType(not_created_by, str)
    if with_states is not None:
      for state in with_states:
        _ValidateProtoEnumType(state, hunts_pb2.Hunt.HuntState)

    return self.delegate.ListHuntObjects(
        offset,
        count,
        with_creator=with_creator,
        created_after=created_after,
        with_description_match=with_description_match,
        created_by=created_by,
        not_created_by=not_created_by,
        with_states=with_states,
    )

  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_substring, str)

    return self.delegate.ReadHuntLogEntries(
        hunt_id, offset, count, with_substring=with_substring
    )

  def CountHuntLogEntries(self, hunt_id: str) -> int:
    _ValidateHuntId(hunt_id)
    return self.delegate.CountHuntLogEntries(hunt_id)

  def ReadHuntResults(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
      with_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options."""
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)
    precondition.AssertOptionalType(with_proto_type_url, str)
    if with_type and with_proto_type_url:
      raise ValueError(
          "Only one of `with_type` and `with_proto_type_url` can be set."
      )
    precondition.AssertOptionalType(with_substring, str)
    precondition.AssertOptionalType(with_timestamp, rdfvalue.RDFDatetime)
    return self.delegate.ReadHuntResults(
        hunt_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_proto_type_url=with_proto_type_url,
        with_substring=with_substring,
        with_timestamp=with_timestamp,
    )

  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
  ):
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_tag, str)
    precondition.AssertOptionalType(with_type, str)
    precondition.AssertOptionalType(with_proto_type_url, str)
    if with_type and with_proto_type_url:
      raise ValueError(
          "Only one of `with_type` and `with_proto_type_url` can be set."
      )
    return self.delegate.CountHuntResults(
        hunt_id,
        with_tag=with_tag,
        with_type=with_type,
        with_proto_type_url=with_proto_type_url,
    )

  def CountHuntResultsByType(self, hunt_id: str) -> Mapping[str, int]:
    _ValidateHuntId(hunt_id)
    return self.delegate.CountHuntResultsByType(hunt_id)

  def CountHuntResultsByProtoTypeUrl(self, hunt_id: str) -> Mapping[str, int]:
    _ValidateHuntId(hunt_id)
    return self.delegate.CountHuntResultsByProtoTypeUrl(hunt_id)

  def ReadHuntFlows(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: HuntFlowsCondition = HuntFlowsCondition.UNSET,
  ) -> Sequence[flows_pb2.Flow]:
    _ValidateHuntId(hunt_id)
    _ValidateHuntFlowCondition(filter_condition)
    return self.delegate.ReadHuntFlows(
        hunt_id, offset, count, filter_condition=filter_condition
    )

  def CountHuntFlows(
      self,
      hunt_id: str,
      filter_condition: Optional[HuntFlowsCondition] = HuntFlowsCondition.UNSET,
  ) -> int:
    _ValidateHuntId(hunt_id)
    _ValidateHuntFlowCondition(filter_condition)
    return self.delegate.CountHuntFlows(
        hunt_id, filter_condition=filter_condition
    )

  def ReadHuntCounters(self, hunt_id: str) -> HuntCounters:
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntCounters(hunt_id)

  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
  ) -> Mapping[str, HuntCounters]:
    for hunt_id in hunt_ids:
      _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntsCounters(hunt_ids)

  def ReadHuntClientResourcesStats(
      self, hunt_id: str
  ) -> jobs_pb2.ClientResourcesStats:
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntClientResourcesStats(hunt_id)

  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
  ) -> Sequence[FlowStateAndTimestamps]:
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntFlowsStatesAndTimestamps(hunt_id)

  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
  ) -> None:
    precondition.AssertType(binary_id, objects_pb2.SignedBinaryID)
    precondition.AssertType(references, objects_pb2.BlobReferences)
    if not references.items:
      raise ValueError("No actual blob references provided.")

    self.delegate.WriteSignedBinaryReferences(binary_id, references)

  def ReadSignedBinaryReferences(
      self, binary_id: objects_pb2.SignedBinaryID
  ) -> tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    precondition.AssertType(binary_id, objects_pb2.SignedBinaryID)
    return self.delegate.ReadSignedBinaryReferences(binary_id)

  def ReadIDsForAllSignedBinaries(self) -> Sequence[objects_pb2.SignedBinaryID]:
    return self.delegate.ReadIDsForAllSignedBinaries()

  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
  ) -> None:
    precondition.AssertType(binary_id, objects_pb2.SignedBinaryID)
    return self.delegate.DeleteSignedBinaryReferences(binary_id)

  def WriteYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      username: str,
  ) -> None:
    _ValidateUsername(username)
    return self.delegate.WriteYaraSignatureReference(blob_id, username)

  def VerifyYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
  ) -> bool:
    return self.delegate.VerifyYaraSignatureReference(blob_id)

  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
  ) -> None:
    _ValidateStringId("scheduled_flow_id", scheduled_flow.scheduled_flow_id)
    _ValidateUsername(scheduled_flow.creator)
    precondition.ValidateClientId(scheduled_flow.client_id)
    return self.delegate.WriteScheduledFlow(scheduled_flow)

  def DeleteScheduledFlow(
      self, client_id: str, creator: str, scheduled_flow_id: str
  ) -> None:
    precondition.ValidateClientId(client_id)
    _ValidateUsername(creator)
    _ValidateStringId("scheduled_flow_id", scheduled_flow_id)
    return self.delegate.DeleteScheduledFlow(
        client_id, creator, scheduled_flow_id
    )

  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    precondition.ValidateClientId(client_id)
    _ValidateUsername(creator)
    return self.delegate.ListScheduledFlows(client_id, creator)

  def WriteBlobEncryptionKeys(
      self,
      key_names: dict[models_blobs.BlobID, str],
  ) -> None:
    for blob_id in key_names.keys():
      _ValidateBlobID(blob_id)

    return self.delegate.WriteBlobEncryptionKeys(key_names)

  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[models_blobs.BlobID],
  ) -> dict[models_blobs.BlobID, Optional[str]]:
    for blob_id in blob_ids:
      _ValidateBlobID(blob_id)

    return self.delegate.ReadBlobEncryptionKeys(blob_ids)

  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
  ) -> None:
    for signed_command in signed_commands:
      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(signed_command.command)

      _ValidateSignedCommandId(signed_command.id)
      _ValidateOperatingSystem(signed_command.operating_system)
      _ValidateEd25519Signature(signed_command.ed25519_signature)
      _ValidateStringLength(
          "signed_command.command.path",
          command.path.raw_bytes,
          max_length=65535,
          min_length=1,
      )

    return self.delegate.WriteSignedCommands(signed_commands)

  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
  ) -> signed_commands_pb2.SignedCommand:
    _ValidateStringId("id", id_)
    _ValidateProtoEnumType(
        operating_system, signed_commands_pb2.SignedCommand.OS
    )
    return self.delegate.ReadSignedCommand(id_, operating_system)

  def ReadSignedCommands(
      self,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    return self.delegate.ReadSignedCommands()

  def DeleteAllSignedCommands(
      self,
  ) -> None:
    return self.delegate.DeleteAllSignedCommands()

  # Minimal allowed timestamp is DB-specific. Thus the validation code for
  # timestamps is DB-specific as well.
  def _ValidateTimeRange(
      self, timerange: tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]
  ):
    """Parses a timerange argument and always returns non-None timerange."""
    if len(timerange) != 2:
      raise ValueError("Timerange should be a sequence with 2 items.")

    (start, end) = timerange
    precondition.AssertOptionalType(start, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(end, rdfvalue.RDFDatetime)
    if start is not None:
      self._ValidateTimestamp(start)
    if end is not None:
      self._ValidateTimestamp(end)

  # Minimal allowed timestamp is DB-specific. Thus the validation code for
  # timestamps is DB-specific as well.
  def _ValidateTimestamp(self, timestamp: rdfvalue.RDFDatetime):
    precondition.AssertType(timestamp, rdfvalue.RDFDatetime)
    if timestamp < self.delegate.MinTimestamp():
      raise ValueError(
          "Timestamp is less than the minimal timestamp allowed by the DB: "
          f"{timestamp} < {self.delegate.MinTimestamp()}."
      )


class ProtoEnumProtocol(Protocol):

  def Name(self, number: int) -> str:
    """Maps enum value to its name. Raises ValueError on invalid input."""


def _ValidateProtoEnumType(value: int, expected_enum_type: ProtoEnumProtocol):
  try:
    expected_enum_type.Name(value)
  except ValueError as e:
    raise TypeError(
        f"Got unexpected value for enum `{expected_enum_type}`: `{value}`"
    ) from e


def _ValidateStringId(typename, value):
  precondition.AssertType(value, str)
  if not value:
    message = "Expected %s `%s` to be non-empty" % (typename, value)
    raise ValueError(message)


def _ValidateClientIds(client_ids):
  precondition.AssertIterableType(client_ids, str)
  for client_id in client_ids:
    precondition.ValidateClientId(client_id)


def _ValidateOutputPluginId(output_plugin_id):
  _ValidateStringId("output_plugin_id", output_plugin_id)


def _ValidateHuntId(hunt_id):
  _ValidateStringId("hunt_id", hunt_id)


def _ValidateCronJobId(cron_job_id):
  _ValidateStringId("cron_job_id", cron_job_id)
  _ValidateStringLength("cron_job_id", cron_job_id, MAX_CRON_JOB_ID_LENGTH)


def _ValidateCronJobRunId(cron_job_run_id):
  _ValidateStringId("cron_job_run_id", cron_job_run_id)
  # Raises TypeError if cron_job_id is not a valid hex number.
  int(cron_job_run_id, 16)
  if len(cron_job_run_id) != 8:
    raise ValueError("Invalid cron job run id: %s" % cron_job_run_id)


def _ValidateApprovalId(approval_id):
  _ValidateStringId("approval_id", approval_id)


def _ValidateSignedCommandId(signed_command_id: str) -> None:
  _ValidateStringId("signed_command_id", signed_command_id)
  _ValidateStringLength(
      "signed_command.id", signed_command_id, MAX_SIGNED_COMMAND_ID_LENGTH
  )


def _ValidateApprovalType(approval_type):
  if (
      approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_NONE
  ):
    raise ValueError("Unexpected approval type: %s" % approval_type)


def _ValidateStringLength(name, string, max_length, min_length=0):
  if len(string) > max_length or len(string) < min_length:
    raise StringTooLongError(
        "{} must have between {} and {} characters, got {}.".format(
            name, min_length, max_length, len(string)
        )
    )


def _ValidateNumBytes(name: str, bytez: bytes, num: int) -> None:
  if len(bytez) != num:
    raise ValueError(f"{name} must have exactly {num} bytes, got {len(bytez)}.")


def _ValidateUsername(username):

  _ValidateStringId("username", username)
  _ValidateStringLength("Usernames", username, MAX_USERNAME_LENGTH)


def _ValidateLabel(label):

  _ValidateStringId("label", label)
  _ValidateStringLength("Labels", label, MAX_LABEL_LENGTH)


def _ValidatePathInfo(path_info: objects_pb2.PathInfo) -> None:
  precondition.AssertType(path_info, objects_pb2.PathInfo)
  if not path_info.path_type:
    raise ValueError(
        "Expected path_type to be set, got: %s" % path_info.path_type
    )


def _ValidatePathInfos(path_infos: Iterable[objects_pb2.PathInfo]) -> None:
  """Validates a sequence of path infos."""
  precondition.AssertIterableType(path_infos, objects_pb2.PathInfo)

  validated = set()
  for path_info in path_infos:
    _ValidatePathInfo(path_info)

    path_key = (
        path_info.path_type,
        rdf_objects.PathID.FromComponents(path_info.components),
    )
    if path_key in validated:
      message = "Conflicting writes for path: '{path}' ({path_type})".format(
          path="/".join(path_info.components), path_type=path_info.path_type
      )
      raise ValueError(message)

    if path_info.HasField("hash_entry"):
      if not path_info.hash_entry.sha256:
        message = "Path with hash entry without SHA256: {}".format(path_info)
        raise ValueError(message)

    validated.add(path_key)


def _ValidatePathComponents(components):
  precondition.AssertIterableType(components, str)


def _ValidateNotificationType(notification_type):
  if notification_type is None:
    raise ValueError("notification_type can't be None")

  if notification_type == objects_pb2.UserNotification.Type.TYPE_UNSET:
    raise ValueError("notification_type can't be TYPE_UNSET")


def _ValidateNotificationState(notification_state):
  if notification_state is None:
    raise ValueError("notification_state can't be None")

  if notification_state == objects_pb2.UserNotification.State.STATE_UNSET:
    raise ValueError("notification_state can't be STATE_UNSET")


def _ValidateDuration(duration):
  precondition.AssertType(duration, rdfvalue.Duration)


def _ValidateBlobID(blob_id):
  precondition.AssertType(blob_id, models_blobs.BlobID)


def _ValidateSHA256HashID(sha256_hash_id):
  precondition.AssertType(sha256_hash_id, rdf_objects.SHA256HashID)


def _ValidateHuntFlowCondition(value):
  precondition.AssertType(value, HuntFlowsCondition)


def _ValidateMessageHandlerName(name):
  _ValidateStringLength(
      "MessageHandler names", name, MAX_MESSAGE_HANDLER_NAME_LENGTH
  )


def _ValidateEmail(email):
  _ValidateStringLength("email", email, MAX_EMAIL_LENGTH)
  if email and not _EMAIL_REGEX.match(email):
    raise ValueError("Invalid E-Mail address: {}".format(email))


def _ValidateOperatingSystem(
    operating_system: "signed_commands_pb2.SignedCommand.OS",
) -> None:
  _ValidateProtoEnumType(operating_system, signed_commands_pb2.SignedCommand.OS)
  if operating_system == signed_commands_pb2.SignedCommand.OS.UNSET:
    raise ValueError("Operating system must be set.")


def _ValidateEd25519Signature(signature: bytes) -> None:
  precondition.AssertType(signature, bytes)
  _ValidateNumBytes(
      "Invalid ed25519 signature", signature, ED25519_SIGNATURE_LENGTH
  )
