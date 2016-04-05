# This directory is reserved for external artifacts

The Makefile removes ``*.yaml`` from this directory when syncing the external
repo located [here] (https://github.com/ForensicArtifacts/artifacts).

## Where artifacts go

- Private artifacts should go in ``artifacts/local``
- Public artifacts that are non GRR specific should be submitted to the external
repo.
- Public artifacts that call GRR functions with ``LIST_FILES``,
  ``GRR_CLIENT_ACTION``, ``GREP`` etc. should live in
  ``artifacts/flow_templates``
