#!/usr/bin/env python
"""This file defines valid configuration contexts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib

# Different client platforms.
PLATFORM_DARWIN = config_lib.DEFINE_context("Platform:Darwin")
PLATFORM_LINUX = config_lib.DEFINE_context("Platform:Linux")
PLATFORM_WINDOWS = config_lib.DEFINE_context("Platform:Windows")

# Client architectures.
ARCH_AMD64 = config_lib.DEFINE_context("Arch:amd64")
ARCH_I386 = config_lib.DEFINE_context("Arch:i386")
ARCH_PPC64LE = config_lib.DEFINE_context("Arch:ppc64le")
ARCH_AARCH64 = config_lib.DEFINE_context("Arch:aarch64")

# Global system install context - set when GRR is installed globally on the
# system.
GLOBAL_INSTALL_CONTEXT = config_lib.DEFINE_context("Global Install Context")

# Different components.
ADMIN_UI_CONTEXT = config_lib.DEFINE_context("AdminUI Context")
CLIENT_CONTEXT = config_lib.DEFINE_context("Client Context")
CONFIG_UPDATER_CONTEXT = config_lib.DEFINE_context("ConfigUpdater Context")
CONSOLE_CONTEXT = config_lib.DEFINE_context("Console Context")
DEMO_CONTEXT = config_lib.DEFINE_context("Demo Context")
ENTRY_POINT_CONTEXT = config_lib.DEFINE_context("EntryPoint Context")
EXPORT_TOOL_CONTEXT = config_lib.DEFINE_context("ExportTool Context")
HTTP_SERVER_CONTEXT = config_lib.DEFINE_context("HTTPServer Context")
POOL_CLIENT_CONTEXT = config_lib.DEFINE_context("PoolClient Context")
WORKER_CONTEXT = config_lib.DEFINE_context("Worker Context")
FS_FRONTEND_CONTEXT = config_lib.DEFINE_context("FleetspeakFrontend Context")
BENCHMARK_CONTEXT = config_lib.DEFINE_context("Benchmark Context")

# Client building contexts.
CLIENT_BUILD_CONTEXT = config_lib.DEFINE_context("ClientBuilder Context")
DEBUG_CLIENT_BUILD_CONTEXT = config_lib.DEFINE_context(
    "DebugClientBuild Context")
TARGET_DARWIN = config_lib.DEFINE_context("Target:Darwin")
TARGET_LINUX = config_lib.DEFINE_context("Target:Linux")
TARGET_LINUX_DEB = config_lib.DEFINE_context("Target:LinuxDeb")
TARGET_LINUX_RPM = config_lib.DEFINE_context("Target:LinuxRpm")
TARGET_WINDOWS = config_lib.DEFINE_context("Target:Windows")

# Running from the command line.
COMMAND_LINE_CONTEXT = config_lib.DEFINE_context("Commandline Context")

# For debugging.
DEBUG_CONTEXT = config_lib.DEFINE_context("Debug Context")
TEST_CONTEXT = config_lib.DEFINE_context("Test Context")

# Datastores.
MYSQL_DATA_STORE = config_lib.DEFINE_context("MySQLDataStore")

# Client installer context.
INSTALLER_CONTEXT = config_lib.DEFINE_context("Installer Context")
