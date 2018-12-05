#!/usr/bin/env python
"""A module with database migration flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import data_migration
from grr_response_server import flow


class ClientVfsMigrationFlow(flow.GRRFlow):

  category = "/Administrative/"

  def Start(self):
    super(ClientVfsMigrationFlow, self).Start()

    migrator = data_migration.ClientVfsMigrator()
    migrator.MigrateClient(client_urn=self.client_urn)
