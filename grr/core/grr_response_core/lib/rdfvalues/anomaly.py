#!/usr/bin/env python
"""Implementation of anomaly types.


Anomalies are things discovered during analysis of a system that are outside
expected norms. In the case of incident response or forensics these can
represent any number of things that may be of interest to an investigator.

To give some examples:
 1. Analysis of a disk shows that there is a large unformatted section which
    contains high entropy data. This may indicate a hidden encrypted partition.
 2. A sqlite file supposed to contain chrome history cannot be parsed by a
    standard Chrome history parser. This may indcate modification of the file,
    a broken parser, data corruption in transif, or a corrupt file on the
    system.
 3. A file that has the characteristics of a JPG file has an extension of .dat.
    This may be an indication of someone trying to hide images.
 4. A driver that does not exist on disk is loaded into memory. This may
    indicate it has been loaded and removed or loaded directly from memory which
    is generally an indicator of badness.

Anomalies can be found in multiple stages of analysis, in the collection of
data, during parsing of data, through automated analysis of parsed data, or
manually through manual human analysis of information.

Anomaly Database
~~~~~~~~~~~~~~~~
Anomalies can and should be shared across systems. Take a a generic idea such as
"DLL loaded in memory, but not found on disk".
- This can have multiple explanations, e.g. dll injection malware, rootkit
  detection software using malware techniques, or even a corrupt filesystem
- Multiple tools can find this anomaly, e.g. commercial memory analysis tools,
  windbg modules, AV scanners.
- The explanations may evolve over time. The reasons this anomaly may exist may
  differ on different versions of Windows.

For these reasons, we don't want to hardcode this data when we generate the
anomaly. The bare, system specific information required to investigate the issue
should be stored with the anomaly, but any generic analysis of what it means,
how to further diagnose or how it occurs should be stored outside the system, in
a place that can be easily updated as our understanding of the anomaly evolves.

Based on this, we do not store information such as labels or detailed,
descriptions within the anomaly itself. These will be stored in an external,
editable wiki.

Whitelisting
~~~~~~~~~~~~~
To make anomalies useful in real systems, it is necessary to allow for
whitelisting. In any environment, there are numerous anomalous things, that are
considered normal for that particular environment.

Additionally, some things that seem anomalous are widely known exceptions, e.g.
it may be ok for a virus scanner to alert, if the alert is an Eicar detection.

Intention as of Dec 2013 is that these will be whitelisted by matching the
anomaly and knowledge_base using object filter syntax. E.g.

(kb.os = "Windows" and
 anomaly.generated_by contains "Antivirus" and
 anomaly.description contains "eicar")

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import anomaly_pb2


class Anomaly(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an artifact."""
  protobuf = anomaly_pb2.Anomaly
  rdf_deps = [
      rdf_paths.PathSpec,
  ]
