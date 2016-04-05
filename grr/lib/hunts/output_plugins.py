#!/usr/bin/env python
"""The various output plugins for GenericHunts."""



# TODO(user): remove this file as soon as it's ok to break hunts with
# pickled OutputPlugin objects (OutputPlugin was renamed to
# OutputPluginDescriptor).

from grr.lib import output_plugin


# pylint: disable=invalid-name
OutputPlugin = output_plugin.OutputPluginDescriptor
