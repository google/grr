#!/usr/bin/env python
"""Entry points for the grr-response-client-builder pip package."""

# pylint: disable=g-import-not-at-top


def ClientBuild():
  from grr_response_client_builder import client_build
  client_build.Run()
