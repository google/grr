#!/usr/bin/env python
"""GRR export tool plugins tests."""


# These need to register plugins so, pylint: disable=unused-import
from grr.tools.export_plugins import collection_files_plugin_test
from grr.tools.export_plugins import collection_plugin_test
from grr.tools.export_plugins import file_plugin_test
from grr.tools.export_plugins import hash_file_store_plugin_test
# pylint: enable=unused-import
