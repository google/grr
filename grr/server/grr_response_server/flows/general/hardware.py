#!/usr/bin/env python
"""These are low-level related flows."""

from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import hardware
from grr.server.grr_response_server.flows.general import collectors
from grr.server.grr_response_server.flows.general import transfer


class DumpFlashImageArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DumpFlashImageArgs


class DumpFlashImage(flow.GRRFlow):
  """Dump Flash image (BIOS)."""

  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = DumpFlashImageArgs

  @flow.StateHandler()
  def Start(self):
    """Start by collecting general hardware information."""
    self.CallFlow(
        collectors.ArtifactCollectorFlow.__name__,
        artifact_list=["LinuxHardwareInfo"],
        next_state="DumpImage")

  @flow.StateHandler()
  def DumpImage(self, responses):
    """Store hardware information and initiate dumping of the flash image."""
    self.state.hardware_info = responses.First()
    self.CallClient(
        server_stubs.DumpFlashImage,
        log_level=self.args.log_level,
        chunk_size=self.args.chunk_size,
        notify_syslog=self.args.notify_syslog,
        next_state="CollectImage")

  @flow.StateHandler()
  def CollectImage(self, responses):
    """Collect the image and store it into the database."""
    # If we have any log, forward them.
    for response in responses:
      if hasattr(response, "logs"):
        for log in response.logs:
          self.Log(log)

    if not responses.success:
      raise flow.FlowError("Failed to dump the flash image: {0}".format(
          responses.status))
    elif not responses.First().path:
      self.Log("No path returned. Skipping host.")
      self.CallState(next_state="End")
    else:
      image_path = responses.First().path
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=[image_path],
          request_data={"image_path": image_path},
          next_state="DeleteTemporaryImage")

  @flow.StateHandler()
  def DeleteTemporaryImage(self, responses):
    """Remove the temporary image from the client."""
    if not responses.success:
      raise flow.FlowError("Unable to collect the flash image: {0}".format(
          responses.status))

    response = responses.First()
    self.SendReply(response)

    # Update the symbolic link to the new instance.
    with aff4.FACTORY.Create(
        self.client_id.Add("spiflash"), aff4.AFF4Symlink,
        token=self.token) as symlink:
      symlink.Set(symlink.Schema.SYMLINK_TARGET,
                  response.AFF4Path(self.client_id))

    # Clean up the temporary image from the client.
    self.CallClient(
        server_stubs.DeleteGRRTempFiles,
        responses.request_data["image_path"],
        next_state="TemporaryImageRemoved")

  @flow.StateHandler()
  def TemporaryImageRemoved(self, responses):
    """Verify that the temporary image has been removed successfully."""
    if not responses.success:
      raise flow.FlowError("Unable to delete the temporary flash image: "
                           "{0}".format(responses.status))

  @flow.StateHandler()
  def End(self):
    if hasattr(self.state, "image_path"):
      self.Log("Successfully wrote Flash image.")


class DumpACPITableArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DumpACPITableArgs

  def Validate(self):
    if not self.table_signature_list:
      raise ValueError("No ACPI table to dump.")


class DumpACPITable(flow.GRRFlow):
  """Flow to retrieve ACPI tables."""

  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = DumpACPITableArgs

  @flow.StateHandler()
  def Start(self):
    """Start collecting tables with listed signature."""
    for table_signature in self.args.table_signature_list:
      self.CallClient(
          server_stubs.DumpACPITable,
          logging=self.args.logging,
          table_signature=table_signature,
          next_state="TableReceived")

  @flow.StateHandler()
  def TableReceived(self, responses):
    """Store received ACPI tables from client in AFF4."""
    for response in responses:
      for log in response.logs:
        self.Log(log)

    table_signature = responses.request.request.payload.table_signature

    if not responses.success:
      self.Log(
          "Error retrieving ACPI table with signature %s" % table_signature)
      return

    response = responses.First()

    if response.acpi_tables:
      self.Log("Retrieved ACPI table(s) with signature %s" % table_signature)
      with data_store.DB.GetMutationPool() as mutation_pool:

        # TODO(amoser): Make this work in the UI!?
        collection_urn = self.client_id.Add(
            "devices/chipsec/acpi/tables/%s" % table_signature)
        for acpi_table_response in response.acpi_tables:
          hardware.ACPITableDataCollection.StaticAdd(
              collection_urn, acpi_table_response, mutation_pool=mutation_pool)
          self.SendReply(acpi_table_response)
