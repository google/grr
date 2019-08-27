#!/usr/bin/env python
"""These are low-level related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer


class DumpFlashImageArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DumpFlashImageArgs


class DumpFlashImage(flow_base.FlowBase):
  """Dump Flash image (BIOS)."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  args_type = DumpFlashImageArgs

  def Start(self):
    """Start by collecting general hardware information."""
    self.CallFlow(
        collectors.ArtifactCollectorFlow.__name__,
        artifact_list=["LinuxHardwareInfo"],
        next_state=compatibility.GetName(self.DumpImage))

  def DumpImage(self, responses):
    """Store hardware information and initiate dumping of the flash image."""
    self.state.hardware_info = responses.First()
    self.CallClient(
        server_stubs.DumpFlashImage,
        log_level=self.args.log_level,
        chunk_size=self.args.chunk_size,
        notify_syslog=self.args.notify_syslog,
        next_state=compatibility.GetName(self.CollectImage))

  def CollectImage(self, responses):
    """Collect the image and store it into the database."""
    # If we have any log, forward them.
    for response in responses:
      if hasattr(response, "logs"):
        for log in response.logs:
          self.Log(log)

    if not responses.success:
      raise flow_base.FlowError("Failed to dump the flash image: {0}".format(
          responses.status))
    elif not responses.First().path:
      self.Log("No path returned. Skipping host.")
      return
    else:
      image_path = responses.First().path
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=[image_path],
          request_data={"image_path": image_path},
          next_state=compatibility.GetName(self.DeleteTemporaryImage))

  def DeleteTemporaryImage(self, responses):
    """Remove the temporary image from the client."""
    if not responses.success:
      raise flow_base.FlowError("Unable to collect the flash image: {0}".format(
          responses.status))

    response = responses.First()
    self.SendReply(response)

    # Clean up the temporary image from the client.
    self.CallClient(
        server_stubs.DeleteGRRTempFiles,
        responses.request_data["image_path"],
        next_state=compatibility.GetName(self.TemporaryImageRemoved))

  def TemporaryImageRemoved(self, responses):
    """Verify that the temporary image has been removed successfully."""
    if not responses.success:
      raise flow_base.FlowError("Unable to delete the temporary flash image: "
                                "{0}".format(responses.status))

  def End(self, responses):
    del responses
    if hasattr(self.state, "image_path"):
      self.Log("Successfully wrote Flash image.")


class DumpACPITableArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DumpACPITableArgs

  def Validate(self):
    if not self.table_signature_list:
      raise ValueError("No ACPI table to dump.")


class DumpACPITable(flow_base.FlowBase):
  """Flow to retrieve ACPI tables."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  args_type = DumpACPITableArgs

  def Start(self):
    """Start collecting tables with listed signature."""
    for table_signature in self.args.table_signature_list:
      self.CallClient(
          server_stubs.DumpACPITable,
          logging=self.args.logging,
          table_signature=table_signature,
          request_data={"table_signature": table_signature},
          next_state=compatibility.GetName(self.TableReceived))

  def TableReceived(self, responses):
    """Store received ACPI tables from client in AFF4."""
    for response in responses:
      for log in response.logs:
        self.Log(log)

    table_signature = responses.request_data["table_signature"]

    if not responses.success:
      self.Log("Error retrieving ACPI table with signature %s" %
               table_signature)
      return

    response = responses.First()

    if not response.acpi_tables:
      return

    self.Log("Retrieved ACPI table(s) with signature %s" % table_signature)

    for acpi_table_response in response.acpi_tables:
      acpi_table_response.table_signature = table_signature
      self.SendReply(acpi_table_response)
