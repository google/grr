#!/usr/bin/env python
"""One-off functions for migrating data from AFF4 to REL_DB."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from absl import app
from typing import Text

from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import server_startup
from grr_response_server.databases import db


def _MigrateArtifact(artifact):
  """Migrate one Artifact from AFF4 to REL_DB."""
  name = Text(artifact.name)

  try:
    logging.info("Migating %s", name)
    data_store.REL_DB.WriteArtifact(artifact)
    logging.info("  Wrote %s", name)
  except db.DuplicatedArtifactError:
    logging.info("  Skipped %s, because artifact already exists.", name)


def _IsCustom(artifact):
  return artifact.loaded_from.startswith("datastore:")


def MigrateArtifacts():
  """Migrates Artifacts from AFF4 to REL_DB."""

  # First, delete all existing artifacts in REL_DB.
  artifacts = data_store.REL_DB.ReadAllArtifacts()
  if artifacts:
    logging.info("Deleting %d artifacts from REL_DB.", len(artifacts))
    for artifact in data_store.REL_DB.ReadAllArtifacts():
      data_store.REL_DB.DeleteArtifact(Text(artifact.name))
  else:
    logging.info("No artifacts found in REL_DB.")

  artifacts = artifact_registry.REGISTRY.GetArtifacts(
      reload_datastore_artifacts=True)

  logging.info("Found %d artifacts in AFF4.", len(artifacts))

  # Only migrate user-created artifacts.
  artifacts = list(filter(_IsCustom, artifacts))

  logging.info("Migrating %d user-created artifacts.", len(artifacts))

  for artifact in artifacts:
    _MigrateArtifact(artifact)


def main(argv):
  del argv  # Unused.
  server_startup.Init()
  MigrateArtifacts()


if __name__ == "__main__":
  app.run(main)
