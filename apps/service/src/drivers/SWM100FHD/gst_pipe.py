import logging
import threading
from abc import ABC, abstractmethod
from typing import Tuple

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


class IGstPipe(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        pass

    @abstractmethod
    def snapshot(self) -> Tuple[str, bytes]:
        pass


class abGstPipe(threading.Thread, IGstPipe):
    lock = threading.Lock()
    buffer: Gst.Buffer = None

    def __init__(self, name: str, dev_num: int, protocol: str, dst_ip: str, dst_port: int,
                 thumbnail_size: Tuple[int, int]):
        super().__init__()

        Gst.init(None)

        self.dev_num = dev_num
        self.protocol = protocol
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.thumbnail_width, self.thumbnail_height = thumbnail_size

        self.content_type = 'unknown'

        self.pipeline = Gst.Pipeline.new(name)
        self.loop: GLib.MainLoop = None

    def run(self):
        tee: Gst.Element = self.create_pipepline_common()
        self.create_pipepline_h264(tee)
        # self.create_pipepline_png(tee)
        self.create_pipepline_jpg(tee)

        self.loop = GLib.MainLoop()

        # Set up the pipeline bus to accept signals
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_callback, self.loop)

        # start play back and listen to events
        self.pipeline.set_state(Gst.State.PLAYING)

        self.loop.run()

        # cleanup
        self.pipeline.set_state(Gst.State.NULL)
        Gst.deinit()

    def bus_callback(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.stop()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.error(f"Error: {err}, {debug}")
            self.stop()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logging.warning(f"Warning: {err}, {debug}")
        return True

    def stop(self):
        self.loop.quit()
        self.join()

    def on_buffer(self, sink, data):
        sample = sink.emit("pull-sample")
        with self.lock:
            self.buffer = sample.get_buffer()
        return Gst.FlowReturn.OK

    def snapshot(self) -> Tuple[str, bytes]:
        with self.lock:
            return self.content_type, self.buffer.extract_dup(0, self.buffer.get_size())

    @abstractmethod
    def create_pipepline_common(self) -> Gst.Element:
        pass

    @abstractmethod
    def create_pipepline_h264(self, tee: Gst.Element):
        pass

    @abstractmethod
    def create_pipepline_jpg(self, tee: Gst.Element):
        pass

    @abstractmethod
    def create_pipepline_png(self, tee: Gst.Element):
        pass
