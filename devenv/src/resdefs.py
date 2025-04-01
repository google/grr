#!/usr/bin/env python
"""Resource definitions."""

from typing import Optional

from . import config
from . import reslib


MYSQL_DATA_VOL = reslib.Volume(
    name="grr-mysql-data-vol", mountpoint="/var/lib/mysql"
)

MYSQL_IMG = reslib.LocalImage(
    name="grr-mysql-img",
    context_dir=config.get("path.containers_dir").joinpath("mysql"),
)

FLEETSPEAK_SERVER_IMG = reslib.LocalImage(
    name="grr-fleetspeak-server-img",
    context_dir=config.get("path.containers_dir").joinpath("fleetspeak-server"),
)

GRR_SRC_VOL = reslib.HostPathVolume(
    name=str(config.get("path.src_dir")), mountpoint="/grr/src"
)

GRR_PERSIST_VOL = reslib.Volume(
    name="grr-persist-vol", mountpoint="/grr/persist"
)

GRR_IMG = reslib.LocalImage(
    name="grr-main-img",
    context_dir=config.get("path.containers_dir").joinpath("grr"),
    build_args={"NODEJS_VERSION": config.get("build.nodejs_version")},
    volumes=[GRR_SRC_VOL, GRR_PERSIST_VOL],
)

GRR_POD = reslib.Pod(
    name="grr-pod",
    ports={
        config.get("net.admin_ui_port"): 8000,
        config.get("net.mysql_port"): 3306,
    },
)

MYSQL_CTR = reslib.Container(
    name="grr-mysql",
    image=MYSQL_IMG,
    volumes=[MYSQL_DATA_VOL],
    pod=GRR_POD,
)

FLEETSPEAK_ADMIN_CTR = reslib.Container(
    name="grr-fleetspeak-admin",
    image=FLEETSPEAK_SERVER_IMG,
    pod=GRR_POD,
    command="bash /fleetspeak/run.sh admin",
    deps=[MYSQL_CTR],
)

FLEETSPEAK_FRONTEND_CTR = reslib.Container(
    name="grr-fleetspeak-frontend",
    image=FLEETSPEAK_SERVER_IMG,
    pod=GRR_POD,
    command="bash /fleetspeak/run.sh frontend localhost",
    deps=[MYSQL_CTR],
)

GRR_ADMIN_UI_CTR = reslib.Container(
    name="grr-admin-ui",
    image=GRR_IMG,
    pod=GRR_POD,
    volumes=[GRR_SRC_VOL, GRR_PERSIST_VOL],
    command=(
        f"{GRR_PERSIST_VOL.mountpoint}/venv/bin/python"
        " -m grr_response_server.gui.admin_ui"
        f" --config {GRR_SRC_VOL.mountpoint}/devenv/config/grr-server.yaml"
    ),
    deps=[MYSQL_CTR],
)

GRR_WORKER_CTR = reslib.Container(
    name="grr-worker",
    image=GRR_IMG,
    pod=GRR_POD,
    volumes=[GRR_SRC_VOL, GRR_PERSIST_VOL],
    command=(
        f"{GRR_PERSIST_VOL.mountpoint}/venv/bin/python"
        " -m grr_response_server.bin.worker"
        f" --config {GRR_SRC_VOL.mountpoint}/devenv/config/grr-server.yaml"
    ),
    deps=[MYSQL_CTR],
)

GRR_FRONTEND_CTR = reslib.Container(
    name="grr-frontend",
    image=GRR_IMG,
    pod=GRR_POD,
    volumes=[GRR_SRC_VOL, GRR_PERSIST_VOL],
    command=(
        f"{GRR_PERSIST_VOL.mountpoint}/venv/bin/python"
        " -m grr_response_server.bin.fleetspeak_frontend"
        f" --config {GRR_SRC_VOL.mountpoint}/devenv/config/grr-server.yaml"
    ),
    deps=[MYSQL_CTR],
)

GRR_CLIENT_CTR = reslib.Container(
    name="grr-client",
    image=GRR_IMG,
    pod=GRR_POD,
    volumes=[GRR_SRC_VOL, GRR_PERSIST_VOL],
    command=(
        f"{GRR_PERSIST_VOL.mountpoint}/venv/fleetspeak-client-bin/usr/bin/fleetspeak-client"
        " -config"
        f" {GRR_SRC_VOL.mountpoint}/devenv/config/fleetspeak-client/client.config"
    ),
)

ADMIN_USER = reslib.AdminUser(
    name=config.get("ui.admin_user"),
    password=config.get("ui.admin_password"),
    grr_pod=GRR_POD,
    grr_img=GRR_IMG,
    grr_persist_vol=GRR_PERSIST_VOL,
    grr_src_vol=GRR_SRC_VOL,
    mysql_ctr=MYSQL_CTR,
)


class Devenv(reslib.Resource):
  """Wrapper resource for the entire devenv."""

  components: list[reslib.Resource] = [
      MYSQL_CTR,
      FLEETSPEAK_ADMIN_CTR,
      FLEETSPEAK_FRONTEND_CTR,
      GRR_ADMIN_UI_CTR,
      GRR_WORKER_CTR,
      GRR_FRONTEND_CTR,
      GRR_CLIENT_CTR,
      ADMIN_USER,
  ]

  def __init__(self) -> None:
    super().__init__("grr-devenv", self.components[:])

  def is_up(self) -> bool:
    for comp in self.components:
      if not comp.is_up():
        return False
    return True

  def create(self) -> None:
    pass

  def destroy(self) -> None:
    GRR_POD.clean()

  def containers(self) -> list[reslib.Container]:
    return [ctr for ctr in self.components if isinstance(ctr, reslib.Container)]

  def container_by_name(self, name: str) -> Optional[reslib.Container]:
    for comp in self.components:
      if isinstance(comp, reslib.Container) and comp.name == name:
        return comp
    return None


DEVENV = Devenv()
