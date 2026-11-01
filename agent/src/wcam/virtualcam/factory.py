import sys
from typing import Literal

from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.pyvirtualcam_sink import PyvirtualcamSink
from wcam.virtualcam.sink import VirtualCameraSink

type SinkChoice = Literal["auto", "obs", "fake"]


def create_sink(choice: SinkChoice) -> VirtualCameraSink:
    backend = ("obs" if sys.platform == "win32" else "fake") if choice == "auto" else choice
    return PyvirtualcamSink() if backend == "obs" else FakeSink()
