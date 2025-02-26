#!/usr/bin/env python
"""Dev environment resource lib."""

import abc
from collections.abc import Iterable, Iterator
import contextlib
import os
import pathlib
import pty
import select
import shutil
import socket
import subprocess
import sys
import time
import traceback
from typing import Any, Optional, Union

from . import config
from . import util


class ResourceError(Exception):
  """Catch-all exception for all resource-related errors."""


class Resource(abc.ABC):
  """An abstract resource.

  Concrete resources extend this class by implementing the creation,
  destruction, and check member functions.
  """

  def __init__(self, name: str, deps: Optional[list["Resource"]] = None):
    self.name: str = name
    self.deps: list["Resource"] = deps or []

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
      self, name: str, mountpoint: str, deps: Optional[list[Resource]] = None
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
    return self.host_path.exists()

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
      volumes: Optional[list[Volume]] = None,
      deps: Optional[list[Resource]] = None,
  ) -> None:
    volumes = volumes or []
    build_args = build_args or {}
    deps = deps or []
    deps.extend(volumes)
    super().__init__(name, deps)

    self.context_dir: pathlib.Path = context_dir
    self.build_args: dict[str, str] = build_args
    self.volumes: list[Volume] = volumes

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
      ports: Optional[dict[int, int]] = None,
      deps: Optional[list[Resource]] = None,
  ):
    super().__init__(name, deps)
    self.ports: dict[int, int] = ports or {}

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
      volumes: Optional[list[Volume]] = None,
      command: Optional[str] = None,
      env: Optional[dict[str, str]] = None,
      pod: Optional[Pod] = None,
      daemonize: bool = True,
      deps: Optional[list[Resource]] = None,
  ):
    volumes = volumes or []
    deps = deps or []
    deps.append(image)
    deps.extend(volumes)
    if pod:
      deps.append(pod)
    super().__init__(name, deps)

    self.image: Image = image
    self.volumes: list[Volume] = volumes
    self.env = env or {}
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
    for key, val in self.env.items():
      cmdln.extend(["--env", f"{key}={val}"])
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


class BackgroundProcess(Resource):
  """A user-specified background process.

  Creating this resource will spawn a background process attached to a pseudo
  TTY. Access to this PTY is managed via a control process, itself accessed via
  a Unix socket. That is, the user can attach to the PTY and this way interact
  with the background process. The resource is considered up/active as long as
  the PTY is kept open by the background process.

  This is (very) roughly equivalent to running a process in a screen or tmux
  session.

  The control process can be inspected via three files that it will create in
  the devenv state dir (see CONFIG["path.state_dir"]):
  - the Unix socket it will listen to for commands / attaches;
  - the PID file to which it will write its PID;
  - the log file, to which the control stdout/stderr are sent, together with all
    output from the background/target process; this should make it easier to
    debug unexpected issues with both the resource definition and the code in
    this class.
  """

  def __init__(
      self,
      name: str,
      command: list[str],
      deps: Optional[list[Resource]] = None,
  ):
    super().__init__(name, deps)
    if command[0].startswith("/"):
      path = command[0]
    else:
      maybe_path = shutil.which(command[0])
      if not maybe_path:
        raise ResourceError(f"Bad BackgroundProcess command: {command}")
      path = maybe_path
    self._target_path: str = path
    self._target_args: list[str] = command[1:]
    self._ctl_sock_path = config.get("path.state_dir").joinpath(
        f"{self.name}.sock"
    )
    self._ctl_pid_path = config.get("path.state_dir").joinpath(
        f"{self.name}.pid"
    )
    self._ctl_log_path = config.get("path.state_dir").joinpath(
        f"{self.name}.log"
    )

  def is_up(self) -> bool:
    return self._ctl_sock_path.exists()

  def create(self) -> None:
    """Create the background process, managed by a daemonized control loop."""

    # Fork the management / control process
    mgr_pid = os.fork()
    if not mgr_pid:
      # This is the management process. Fork again, this time with a pseudo TTY
      # allocation for the child process.
      pid, pty_fd = pty.fork()
      if not pid:
        # This is the child process which will be used to exec into the actual
        # target process that this resource is intended to run in the
        # background. Note that `os.exec*` never returns, but replaces the
        # current process entirely.
        os.execv(self._target_path, [self._target_path] + self._target_args)
      else:
        # On the management/control side, we daemonize and call into the main
        # control loop.
        os.setsid()
        self._manage(pid, pty_fd)
        sys.exit(0)

    # This is only reached by the main process that called `create()`.
    # Having created the (background) control process, return now to other
    # devenv duties.

  def destroy(self) -> None:
    """Kill the background process."""

    try:
      with open(self._ctl_pid_path, "r") as pid_file:
        mgr_pid: int = int(pid_file.read(32))
      sock = self._connect()
      sock.send(b"EXIT\n")
      sock.close()
      time.sleep(1)
    finally:
      if self._ctl_sock_path.exists():
        util.kill_process(mgr_pid)
        self._ctl_sock_path.unlink()
        self._ctl_pid_path.unlink()

  def restart(self) -> None:
    """Restart the background process."""

    if self.is_up():
      self.destroy()
    self.create()

  def attach(self) -> None:
    """Attach to a previously created background process' pseudo TTY."""

    util.say(f"Attaching to {self.__class__.__name__}.{self.name} ...")
    sock = self._connect()
    sock.send(b"ATTACH\n")
    expect: bytes = b"OK\n"
    if sock.recv(len(expect)) != expect:
      raise ResourceError(f"Error attaching to background process {self.name}")
    util.say("Attached. Detach with <ctrl-p>,<ctrl-d>.")

    subprocess.run(["stty", "-echo", "cbreak"], check=True)
    try:
      while True:
        try:
          ready_list, _, _ = select.select([sock, sys.stdin], [], [], 10)
          if sock in ready_list:
            buf = sock.recv(4096)
            if not buf:
              util.say_warn("Background process connection reset")
              break
            os.write(sys.stdout.fileno(), buf)
          if sys.stdin in ready_list:
            buf = os.read(sys.stdin.fileno(), 1)
            if buf == b"\x10":
              # Received ctrl-p (ASCII 0x10). This is the first keystroke in
              # the detach sequence. Wait for the next one for 1 second, and
              # detach if it completes the sequence.
              ready, _, _ = select.select([sys.stdin], [], [], 1)
              if sys.stdin in ready:
                buf2 = os.read(sys.stdin.fileno(), 1)
                if buf2 == b"\x04":
                  # Got ctrl-d (ASCII 0x04), so the detach sequence is complete.
                  print("")
                  util.say("Detached")
                  break
                else:
                  # Not the detach sequence we were looking for. Send everything
                  # to the attached PTY.
                  buf += buf2
            sock.send(buf)
        except KeyboardInterrupt:
          # Send ctrl-c to the background process
          sock.send(b"\x03")
    finally:
      subprocess.run(["stty", "echo", "-cbreak"], check=True)

  def _connect(self) -> socket.socket:
    """Connect to the background process control socket."""

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(str(self._ctl_sock_path))
    return sock

  def _manage(self, target_pid: int, pty_fd: int) -> None:
    """Background process control loop."""

    # This is executed only in the context of the daemonized control process. It
    # listens on a Unix socket for commands, most important of which is ATTACH.
    # This forwards the connected Unix socket to the pseudo TTY of the target
    # background process, giving the user terminal access to it.

    # Set up logging for stdout/stderr
    if not self._ctl_log_path.parent.exists():
      self._ctl_log_path.parent.mkdir(parents=True)
    with open(self._ctl_log_path, "w") as log_file:
      os.dup2(log_file.fileno(), 1)
      os.dup2(log_file.fileno(), 2)
    now: str = time.strftime("%Y-%m-%d %H:%M:%S")
    sys.stdout.write(
        f"\n{now} {self.__class__.__name__}.{self.name} starting ...\n"
    )

    # Write PID file
    if not self._ctl_pid_path.parent.exists():
      self._ctl_pid_path.parent.mkdir(parents=True)
    with open(self._ctl_pid_path, "w") as pid_file:
      pid_file.write(f"{os.getpid()}")

    # Open the control socket
    ctl_sock: socket.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    if not self._ctl_sock_path.parent.exists():
      self._ctl_sock_path.parent.mkdir(parents=True)
    ctl_sock.bind(str(self._ctl_sock_path))
    ctl_sock.listen(1)

    client_sock: Optional[socket.socket] = None
    term_buf: util.RollingLineBuffer = util.RollingLineBuffer(50)

    # Main control loop
    while True:
      rlist: list[Union[socket.socket, int]] = (
          [client_sock] if client_sock else [ctl_sock]
      )
      rlist.append(pty_fd)
      ready_list, _, _ = select.select(rlist, [], [], 10)

      # Check for new clients
      if ctl_sock in ready_list:
        client_sock, _ = ctl_sock.accept()
        cmd = client_sock.recv(32)
        if cmd == b"EXIT\n":
          break
        elif cmd == b"CHECK\n":
          client_sock.send(b"OK\n")
        elif cmd == b"ATTACH\n":
          client_sock.send(b"OK\n")
          client_sock.send(term_buf.get().encode("utf-8"))
        else:
          client_sock.close()
          client_sock = None

      # Check for incoming client data
      if client_sock and client_sock in ready_list:
        buf = client_sock.recv(4096)
        if not buf:
          client_sock = None
          continue
        try:
          os.write(pty_fd, buf)
        except OSError:
          client_sock.close()
          break

      # Check for target process pty output
      if pty_fd in ready_list:
        try:
          buf = os.read(pty_fd, 4096)
        except OSError:
          if client_sock:
            client_sock.close()
          break
        # Send target output to rolling buffer
        term_buf.add(buf.decode("utf-8"))
        # Send target output to log
        sys.stdout.write(util.term.strip_control_chars(buf.decode("utf-8")))
        sys.stdout.flush()
        # Send target output to client, if any is connected
        if client_sock:
          client_sock.send(buf)

    util.kill_process(target_pid)
    ctl_sock.close()
    self._ctl_sock_path.unlink()
    self._ctl_pid_path.unlink()


class ForegroundProcess(Resource):
  """Foreground process can be used to run short-lived commands in the devenv environment."""

  def __init__(
      self,
      name: str,
      command: list[str],
      deps: Optional[list[Resource]] = None,
  ):
    super().__init__(name, deps)
    if command[0].startswith("/"):
      path = command[0]
    else:
      path = shutil.which(command[0])
      if path is None:
        raise ResourceError(f"Bad ForegroundProcess command: {command}")

    self._target_path: str = path
    self._target_args: list[str] = command[1:]
    self._ctl_log_path = config.get("path.state_dir").joinpath(
        f"{self.name}.log"
    )

  def is_up(self) -> bool:
    return False

  def create(self) -> None:
    """Create the foreground process, managed by a daemonized control loop."""
    os.system(" ".join([self._target_path] + self._target_args))

  def destroy(self) -> None:
    pass

  def restart(self) -> None:
    pass

  def attach(self) -> None:
    pass
