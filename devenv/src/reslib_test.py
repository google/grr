#!/usr/bin/env python
"""Resource tests."""

import pathlib
import tempfile
import uuid

from . import reslib


def _temp_name(prefix: str = "") -> str:
  return f"{prefix}-{uuid.uuid4()}"


class TestRes:

  def test_volume(self) -> None:
    vol = reslib.Volume(_temp_name("test-volume"), mountpoint="/foo")
    with reslib.cleaner((vol,)):
      assert not vol.is_up()
      vol.create()
      assert vol.is_up()
      assert vol.host_path.is_dir()
    assert not vol.is_up()

  def test_local_image(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
      temp_dir = pathlib.Path(temp_dir_str)
      img = reslib.LocalImage(
          name=_temp_name("test-image"),
          context_dir=temp_dir,
      )
      with open(
          temp_dir.joinpath("Containerfile"), "w", encoding="utf-8"
      ) as ctrf:
        ctrf.write("\n".join(["FROM alpine:latest", "RUN echo bar > /foo"]))
      ctr = reslib.Container(
          name=_temp_name("test-container"),
          image=img,
          daemonize=False,
          command="[ $(cat /foo) = bar ]",
      )
      with reslib.cleaner([ctr, img]):
        ctr.ensure()

  def test_container(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      vol = reslib.HostPathVolume(str(temp_dir), mountpoint="/data")
      img = reslib.Image(name="alpine:latest")
      ctr = reslib.Container(
          name=_temp_name("test-container"),
          image=img,
          volumes=[vol],
          command="echo -n bar > /data/foo",
          daemonize=False,
      )
      with reslib.cleaner((ctr, vol, img)):
        ctr.ensure()
      with open(
          pathlib.Path(temp_dir).joinpath("foo"), mode="r", encoding="utf-8"
      ) as foof:
        assert foof.read() == "bar"
