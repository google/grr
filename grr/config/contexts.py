#!/usr/bin/env python
"""This file defines valid configuration contexts."""

# Also import the contexts needed for client building.
# pylint: disable=unused-import
from grr.config import build_contexts
# pylint: enable=unused-import
from grr.lib import config_lib

# Different client platforms.
config_lib.CONFIG.DEFINE_context("Platform:Darwin")
config_lib.CONFIG.DEFINE_context("Platform:Linux")
config_lib.CONFIG.DEFINE_context("Platform:Windows")

# Client architectures.
config_lib.CONFIG.DEFINE_context("Arch:amd64")
config_lib.CONFIG.DEFINE_context("Arch:i386")

# Global system install context - set when GRR is installed globally on the
# system.
config_lib.CONFIG.DEFINE_context("Global Install Context")

# Different components.
config_lib.CONFIG.DEFINE_context("AdminUI Context")
config_lib.CONFIG.DEFINE_context("Client Context")
config_lib.CONFIG.DEFINE_context("ConfigUpdater Context")
config_lib.CONFIG.DEFINE_context("Console Context")
config_lib.CONFIG.DEFINE_context("DataServer Context")
config_lib.CONFIG.DEFINE_context("Demo Context")
config_lib.CONFIG.DEFINE_context("EntryPoint Context")
config_lib.CONFIG.DEFINE_context("ExportTool Context")
config_lib.CONFIG.DEFINE_context("HTTPServer Context")
config_lib.CONFIG.DEFINE_context("PoolClient Context")
config_lib.CONFIG.DEFINE_context("Worker Context")

# Client building contexts.
config_lib.CONFIG.DEFINE_context("ClientBuilder Context")
config_lib.CONFIG.DEFINE_context("DebugClientBuild Context")
config_lib.CONFIG.DEFINE_context("Target:Darwin")
config_lib.CONFIG.DEFINE_context("Target:Linux")
config_lib.CONFIG.DEFINE_context("Target:LinuxDeb")
config_lib.CONFIG.DEFINE_context("Target:LinuxRpm")
config_lib.CONFIG.DEFINE_context("Target:Windows")

# Running from the command line.
config_lib.CONFIG.DEFINE_context("Commandline Context")

# For debugging.
config_lib.CONFIG.DEFINE_context("Debug Context")
config_lib.CONFIG.DEFINE_context("Test Context")

# Datastores.
config_lib.CONFIG.DEFINE_context("MySQLDataStore")

# Client installer context.
config_lib.CONFIG.DEFINE_context("Installer Context")
