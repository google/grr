#!/usr/bin/env python
"""Dev environment resource lib."""

import abc
import contextlib
import pathlib
import subprocess
import sys
import traceback
from typing import Any, Dict, Iterable, Iterator, List, Optional

from . import config
from . import util


class ResourceError(Exception):
  """Catch-all exception for all resource-related errors."""


class Resource(abc.ABC):
  """An abstract resource.

  Concrete resources extend this class by implementing the creation,
  destruction, and check member functions.
  """

  def __init__(self, name: str, deps: Optional[List["Resource"]] = None):
    self.name: str = name
    self.deps: List["Resource"] = deps or []

  @abc.abstractmethod
  def create(self) -> None:
    pass

  @abc.abstractmethod
  def destroy(self) -> None:
    pass

  @abc.abstractmethod
  def is_up(self) -> bool:
    pass

  def ensure(self) -> None:
    if self.is_up():
      return
    for dep in self.deps:
      dep.ensure()
    util.say(f"Creating {self.__class__.__name__}.{self.name} ...")
    self.create()

  def clean(self) -> None:
    if self.is_up():
      self.destroy()

  def deep_clean(self) -> None:
    self.clean()
    for dep in self.deps:
      dep.deep_clean()


@contextlib.contextmanager
def cleaner(resources: Iterable[Resource]) -> Iterator[None]:
  try:
    yield None
  finally:
    for res in resources:
      try:
        res.clean()
      except Exception:  # pylint: disable=broad-exception-caught
        util.say_fail(f"Error cleaning up {res.__class__.__name__}.{res.name}")
        traceback.print_exc(file=sys.stderr)


class Volume(Resource):
  """Container volume."""

  def __init__(
      self, name: str, mountpoint: str, deps: Optional[List[Resource]] = None
  ) -> None:
    super().__init__(name, deps)
    self.mountpoint = mountpoint

  def is_up(self) -> bool:
    proc = subprocess.run(
        f"podman volume exists {self.name}",
        shell=True,
        check=False,
        capture_output=True,
    )
    return proc.returncode == 0

  def create(self) -> None:
    subprocess.run(
        f"podman volume create {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )

  def destroy(self) -> None:
    subprocess.run(
        f"podman volume rm {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )

  @property
  def host_path(self) -> pathlib.Path:
    proc = subprocess.run(
        f'podman volume inspect --format "{{{{.Mountpoint}}}}" {self.name}',
        shell=True,
        check=True,
        capture_output=True,
    )
    return pathlib.Path(proc.stdout.decode("utf-8").strip())


class HostPathVolume(Volume):
  """Container volume backed by a host directory."""

  def is_up(self) -> bool:
    return self.host_path.is_dir()

  def create(self) -> None:
    raise ResourceError("Attempted to use HostPathVolume without a host path.")

  def destroy(self) -> None:
    pass

  @property
  def host_path(self) -> pathlib.Path:
    return pathlib.Path(self.name)


class Image(Resource):
  """A container image."""

  def __init__(self, *args: Any, **kwargs: Any):
    super().__init__(*args, **kwargs)
    self._pulled: bool = False

  def is_up(self) -> bool:
    proc = subprocess.run(
        f"podman image exists {self.name}",
        shell=True,
        check=False,
        capture_output=True,
    )
    return proc.returncode == 0

  def create(self) -> None:
    subprocess.run(
        f"podman image pull {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )
    self._pulled = True

  def destroy(self) -> None:
    if self._pulled:
      subprocess.run(
          f"podman image rm -f {self.name}",
          shell=True,
          check=True,
          capture_output=True,
      )


class LocalImage(Image):
  """A locally-created container image."""

  # pylint: disable=too-many-arguments
  def __init__(
      self,
      name: str,
      context_dir: pathlib.Path,
      build_args: Optional[dict[str, str]] = None,
      volumes: Optional[List[Volume]] = None,
      deps: Optional[List[Resource]] = None,
  ) -> None:
    volumes = volumes or []
    build_args = build_args or {}
    deps = deps or []
    deps.extend(volumes)
    super().__init__(name, deps)

    self.context_dir: pathlib.Path = context_dir
    self.build_args: dict[str, str] = build_args
    self.volumes: List[Volume] = volumes

  def create(self) -> None:
    cmdln = ["podman", "image", "build", "--no-cache", "-t", self.name]
    for key, val in self.build_args.items():
      cmdln.extend(["--build-arg", f"{key}={val}"])
    for vol in self.volumes:
      cmdln.extend(["--volume", f"{vol.host_path}:{vol.mountpoint}"])
    cmdln.append(str(self.context_dir))
    subprocess.run(cmdln, check=True, capture_output=True)

  def destroy(self) -> None:
    subprocess.run(
        f"podman image rm -f {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )


class Pod(Resource):
  """A podman pod."""

  def __init__(
      self,
      name: str,
      ports: Optional[Dict[int, int]] = None,
      deps: Optional[List[Resource]] = None,
  ):
    super().__init__(name, deps)
    self.ports: Dict[int, int] = ports or {}

  def is_up(self) -> bool:
    proc = subprocess.run(
        f"podman pod exists {self.name}",
        shell=True,
        check=False,
        capture_output=True,
    )
    return proc.returncode == 0

  def create(self) -> None:
    port_args = " ".join([f"-p {hp}:{cp}" for hp, cp in self.ports.items()])
    subprocess.run(
        f"podman pod create {port_args} --name {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )

  def destroy(self) -> None:
    subprocess.run(
        f"podman pod rm -f {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )


class Container(Resource):
  """A (podman) container."""

  # pylint: disable=too-many-arguments
  def __init__(
      self,
      name: str,
      image: Image,
      volumes: Optional[List[Volume]] = None,
      command: Optional[str] = None,
      pod: Optional[Pod] = None,
      daemonize: bool = True,
      deps: Optional[List[Resource]] = None,
  ):
    volumes = volumes or []
    deps = deps or []
    deps.append(image)
    deps.extend(volumes)
    if pod:
      deps.append(pod)
    super().__init__(name, deps)

    self.image: Image = image
    self.volumes: List[Volume] = volumes
    self.pod: Optional[Pod] = pod
    self.command: Optional[str] = command
    self.daemonize = daemonize

  def is_up(self) -> bool:
    proc = subprocess.run(
        f"podman container inspect --format {{{{.State.Status}}}} {self.name}",
        shell=True,
        check=False,
        capture_output=True,
    )
    status = proc.stdout.decode("utf-8").strip()
    return proc.returncode == 0 and status == "running"

  def create(self) -> None:
    subprocess.run(
        f"podman container rm -f {self.name}",
        shell=True,
        check=False,
        capture_output=True,
    )

    cmdln = ["podman", "container", "run", "--rm", "-i", "--name", self.name]
    if self.pod:
      cmdln.extend(["--pod", self.pod.name])
    if self.daemonize:
      cmdln.extend(["--detach", "-t", "--init", "--restart=on-failure"])
    elif sys.stdout.isatty():
      cmdln.extend([
          "-t",
          f"""--detach-keys={config.get("cli.container_detach_keys")}""",
      ])
    for vol in self.volumes:
      cmdln.extend(["--volume", f"{vol.name}:{vol.mountpoint}"])
    cmdln.append(self.image.name)
    if self.command:
      cmdln.extend(["sh", "-c", self.command])
    subprocess.run(cmdln, check=True, capture_output=self.daemonize)

  def destroy(self) -> None:
    subprocess.run(
        f"podman container rm -f {self.name}",
        shell=True,
        check=True,
        capture_output=True,
    )

  def restart(self, attach: bool = False) -> None:
    if self.is_up():
      self.destroy()
    self.daemonize = not attach
    self.ensure()


class AdminUser(Resource):
  """GRR admin user. Used to login to AdminUI."""

  # pylint: disable=too-many-arguments
  def __init__(
      self,
      name: str,
      password: str,
      grr_pod: Pod,
      grr_img: LocalImage,
      grr_persist_vol: Volume,
      grr_src_vol: Volume,
      mysql_ctr: Container,
  ) -> None:
    deps = [grr_img, grr_persist_vol, mysql_ctr, grr_pod]
    super().__init__(name, deps)
    self.password: str = password

    self.grr_pod: Pod = grr_pod
    self.grr_img: LocalImage = grr_img
    self.grr_persist_vol: Volume = grr_persist_vol
    self.grr_src_vol: Volume = grr_src_vol
    self.mysql_ctr: Container = mysql_ctr

  def is_up(self) -> bool:
    if not self.mysql_ctr.is_up():
      return False
    query = f'SELECT COUNT(*) FROM grr.grr_users WHERE username="{self.name}"'
    proc = subprocess.run(
        ["podman", "exec", self.mysql_ctr.name, "mysql", "-N", "-e", query],
        check=False,
        capture_output=True,
    )
    count = proc.stdout.decode("utf-8").strip()
    return proc.returncode == 0 and count != "0"

  def create(self) -> None:
    subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{self.grr_persist_vol.name}:{self.grr_persist_vol.mountpoint}",
            "-v",
            f"{self.grr_src_vol.name}:{self.grr_src_vol.mountpoint}",
            "--pod",
            self.grr_pod.name,
            self.grr_img.name,
            f"{self.grr_persist_vol.mountpoint}/venv/bin/grr_config_updater",
            "--config",
            f"{self.grr_src_vol.mountpoint}/devenv/config/grr-server.yaml",
            "add_user",
            self.name,
            "--password",
            self.password,
            "--admin",
            "true",
        ],
        check=True,
    )

  def destroy(self) -> None:
    pass
