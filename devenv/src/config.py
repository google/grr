#!/usr/bin/env python
"""Config vars."""

import pathlib
from typing import Any, Dict


CONFIG: Dict[str, Any] = {}
CONFIG["path.src_dir"] = pathlib.Path(__file__).parent.parent.parent.resolve()
CONFIG["path.containers_dir"] = (
    CONFIG["path.src_dir"]
    .joinpath("devenv")
    .joinpath("src")
    .joinpath("containers")
)
CONFIG["net.admin_ui_port"] = 4280
CONFIG["net.mysql_port"] = 4236
CONFIG["ui.admin_user"] = "admin"
CONFIG["ui.admin_password"] = "admin"
CONFIG["build.nodejs_version"] = "16.13.0"
CONFIG["cli.container_detach_keys"] = "ctrl-p,ctrl-q"


def get(key: str) -> Any:
  return CONFIG[key]
