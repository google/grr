#!/usr/bin/env python
"""Devenv subcommands."""

# This module contains only CLI subcommands, documented via the cli.subcommand()
# decorator. This makes function docstrings superflous.
#
# pylint: disable=missing-function-docstring

import argparse
import shutil
import subprocess
from typing import List
import uuid

from . import cli
from . import config
from . import resdefs
from . import reslib
from . import util
from .util import term


class SubcommandError(Exception):
  """Catch-all exception for anything subcommand-related."""


@cli.subcommand(
    help=(
        "Check if the dependencies needed by the GRR devenv are set up on"
        " your system."
    )
)
def check_deps(args: argparse.Namespace) -> None:
  del args  # not used

  util.say("Checking if podman is available ...")
  podman = shutil.which("podman")
  if not podman:
    raise SubcommandError("podman not found")

  util.say("Checking if podman can run a rootless container ...")
  proc = subprocess.run(
      [
          "podman",
          "container",
          "run",
          "--rm",
          "alpine:latest",
          "sh",
          "-c",
          "echo -n foo",
      ],
      check=False,
      capture_output=True,
  )
  if proc.returncode != 0 or proc.stdout.decode("utf-8") != "foo":
    raise SubcommandError("""
    Error executing podman container.

    Hint: make sure subuids are set up for your user. E.g.:

    $ sudo usermod --add-subuids 500000-565535 --add-subgids 500000-565535 $USER
    """)

  util.say("Done. Everything looks OK.")


@cli.subcommand(help="Remove all local side-effects of running the GRR devenv.")
def clean_all(args: argparse.Namespace) -> None:
  del args  # not used

  util.say("Cleaning up ...")
  resdefs.DEVENV.deep_clean()


@cli.subcommand(
    help=(
        "Rebuild all GRR components. Usually needed after sizeable source"
        " changes."
    )
)
def rebuild_grr(args: argparse.Namespace) -> None:
  del args  # not used

  grr_components: List[str] = [
      "grr/proto",
      "grr/core",
      "grr/client",
      "grr/client_builder",
      "api_client/python",
      "grr/server",
  ]
  builder_ctr = reslib.Container(
      name="grr-builder",
      image=resdefs.GRR_IMG,
      volumes=[resdefs.GRR_SRC_VOL, resdefs.GRR_PERSIST_VOL],
      daemonize=False,
      command=" ".join([
          f". {resdefs.GRR_PERSIST_VOL.mountpoint}/venv/bin/activate",
          f"&& cd {resdefs.GRR_SRC_VOL.mountpoint}",
          *[f"&& pip install -e {comp}" for comp in grr_components],
      ]),
  )
  if builder_ctr.is_up():
    raise SubcommandError("A build is already in progress.")
  with reslib.cleaner([builder_ctr]):
    builder_ctr.create()


# pylint: disable=use-dict-literal
@cli.subcommand(
    help="Restart one of the GRR components.",
    args={
        "-a": dict(
            help="Attach to the container TTY after restart.",
            default=False,
            action="store_true",
        ),
        "container": dict(
            choices=[ctr.name for ctr in resdefs.DEVENV.containers()],
            action="store",
        ),
    },
)
def restart(args: argparse.Namespace) -> None:
  ctr = resdefs.DEVENV.container_by_name(args.container)
  if ctr is None:
    raise SubcommandError(f"Container not found: {args.container}")
  util.say(f"Restarting Container.{args.container}")
  if args.a:
    detach_keys = config.get("cli.container_detach_keys")
    util.say(f"Use {detach_keys} to detach from container tty.")
  ctr.restart(attach=args.a)


@cli.subcommand(
    help="Open a shell in a GRR container.",
    args={
        "-c": dict(
            help=(
                "Open the shell inside this running container."
                " If this option is not specified, the shell will be opened in"
                " a new container, prepared to run any GRR component."
            ),
            choices=[ctr.name for ctr in resdefs.DEVENV.containers()],
            action="store",
        )
    },
)
def shell(args: argparse.Namespace) -> None:
  if args.c:
    ctr = resdefs.DEVENV.container_by_name(args.c)
    if ctr is None:
      raise SubcommandError(f"Container not found: {args.c}")
    if not ctr.is_up():
      raise SubcommandError(f"Container {args.c} is not running")
    util.say(f"Opening shell inside Container.{args.c} ...")
    subprocess.run(
        ["podman", "container", "exec", "-it", args.c, "bash"], check=True
    )
  else:
    ctr_name = f"grr-shell-{str(uuid.uuid4())[:8]}"
    ctr = reslib.Container(
        name=ctr_name,
        image=resdefs.GRR_IMG,
        volumes=[resdefs.GRR_SRC_VOL, resdefs.GRR_PERSIST_VOL],
        pod=resdefs.GRR_POD,
        command="bash",
        daemonize=False,
    )
    ctr.ensure()


@cli.subcommand(help="Start the GRR dev environment.")
def start(args: argparse.Namespace) -> None:
  del args  # not used

  util.say("Starting devenv ...")
  resdefs.DEVENV.ensure()
  util.say(f"""
    Devenv is now running inside podman pod {term.attn(resdefs.GRR_POD.name)}.

    Admin UI is available at http://localhost:{config.get("net.admin_ui_port")}
    user: {config.get("ui.admin_user")}
    password: {config.get("ui.admin_password")}

    MySQL raw access is available at localhost:{config.get("net.mysql_port")}.
    user: grr
    password: grr
    """)


@cli.subcommand(help="Show status of all devenv resources.")
def status(args: argparse.Namespace) -> None:
  del args  # not used

  memo: dict[str, bool] = {}

  def res_key(res: reslib.Resource) -> str:
    return f"{res.__class__.__name__}.{res.name}"

  def walk(res: reslib.Resource, indent: str) -> None:
    key = res_key(res)
    deco = term.meh
    if key not in memo:
      memo[key] = res.is_up()
      deco = term.ok if memo[key] else term.fail
    tag = "o" if memo[key] else "x"
    print(deco(f"{indent}{tag} {res_key(res)}"))
    for dep in res.deps:
      walk(dep, indent + "  ")

  walk(resdefs.DEVENV, "")


@cli.subcommand(help="Stop the GRR dev environment.")
def stop(args: argparse.Namespace) -> None:
  del args  # not used

  util.say("Stopping devenv ...")
  resdefs.DEVENV.destroy()
