import logging
import threading
from typing import Tuple

# noinspection PyUnresolvedReferences,PyPackageRequirements
import gi

gi.require_version('Gst', '1.0')
# noinspection PyUnresolvedReferences,PyPackageRequirements
from gi.repository import Gst, GLib


# gst-launch-1.0 nvv4l2camerasrc device=/dev/video0 \
# ! 'video/x-raw(memory:NVMM),format=UYVY,width=1920,height=1080,framerate=30/1' \
# ! tee name=t \
# ! queue \
# ! nvvidconv \
# ! 'video/x-raw(memory:NVMM),width=1920,height=1080' \
# ! nvv4l2h264enc idrinterval=30 \
# ! video/x-h264, stream-format=byte-stream \
# ! h264parse config-interval=1 \
# ! mpegtsmux \
# ! udpsink host=192.168.10.104 port=5000 \
# t. \
# ! queue \
# ! nvvidconv \
# ! 'video/x-raw,format=RGBA,width=320,height=180' \
# ! pngenc \
# ! multifilesink location=./jpg/640_%03d.png

# noinspection PyUnusedLocal
class GstPipe(threading.Thread):
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

    def create_pipepline_common(self) -> Gst.Element:
        # Create GStreamer elements
        src = Gst.ElementFactory.make("nvv4l2camerasrc")
        src.set_property("device", f"/dev/video{self.dev_num}")

        caps = Gst.ElementFactory.make("capsfilter")
        caps.set_property("caps", Gst.Caps.from_string(
            "video/x-raw(memory:NVMM),format=UYVY,width=1920,height=1080,framerate=30/1"))

        tee = Gst.ElementFactory.make("tee")

        # Build the pipeline
        for elem in [src, caps, tee]:
            self.pipeline.add(elem)

        # Link the elements
        src.link(caps)
        caps.link(tee)

        return tee

    def create_pipepline_h264(self, tee: Gst.Element):
        # Create GStreamer elements
        queue = Gst.ElementFactory.make("queue")

        conv = Gst.ElementFactory.make("nvvidconv")

        caps_conv = Gst.ElementFactory.make("capsfilter")
        caps_conv.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),width=1920,height=1080"))

        encoder = Gst.ElementFactory.make("nvv4l2h264enc")
        encoder.set_property("idrinterval", 30)

        caps_enc = Gst.ElementFactory.make("capsfilter")
        caps_enc.set_property("caps", Gst.Caps.from_string("video/x-h264, stream-format=byte-stream"))

        parser = Gst.ElementFactory.make("h264parse")
        parser.set_property("config-interval", 1)

        muxer = Gst.ElementFactory.make("mpegtsmux")

        sink_name = "udpsink" if self.protocol == 'udp' else "tcpclientsink"
        sink = Gst.ElementFactory.make(sink_name)
        sink.set_property("host", self.dst_ip)
        sink.set_property("port", self.dst_port)

        # Build the pipeline
        for elem in [queue, conv, caps_conv, encoder, caps_enc, parser, muxer, sink]:
            self.pipeline.add(elem)

        # Link the elements
        tee.link(queue)
        queue.link(conv)
        conv.link(caps_conv)
        caps_conv.link(encoder)
        encoder.link(caps_enc)
        caps_enc.link(parser)
        parser.link(muxer)
        muxer.link(sink)

    def create_pipepline_png(self, tee: Gst.Element):
        self.content_type = 'image/png'

        # Create GStreamer elements
        queue = Gst.ElementFactory.make("queue")

        conv = Gst.ElementFactory.make("nvvidconv")

        caps = Gst.ElementFactory.make("capsfilter")
        flt_str = f"video/x-raw,format=RGBA,width={self.thumbnail_width},height={self.thumbnail_height}"
        caps.set_property("caps", Gst.Caps.from_string(flt_str))

        pngenc = Gst.ElementFactory.make("pngenc")
        pngenc.set_property("compression-level", 0)

        sink = Gst.ElementFactory.make("appsink")
        sink.set_property("emit-signals", True)
        sink.set_property("drop", True)
        sink.set_property("sync", False)
        sink.connect("new-sample", self.on_buffer, sink)

        # Build the pipeline
        for elem in [queue, conv, caps, pngenc, sink]:
            self.pipeline.add(elem)

        tee.link(queue)
        queue.link(conv)
        conv.link(caps)
        caps.link(pngenc)
        pngenc.link(sink)

    def create_pipepline_jpg(self, tee):
        self.content_type = 'image/jpeg'

        # Create GStreamer elements
        queue = Gst.ElementFactory.make("queue")

        conv = Gst.ElementFactory.make("nvvidconv")

        caps = Gst.ElementFactory.make("capsfilter")
        flt_str = f"video/x-raw,format=I420,width={self.thumbnail_width},height={self.thumbnail_height}"
        caps.set_property("caps", Gst.Caps.from_string(flt_str))

        jpgenc = Gst.ElementFactory.make("jpegenc")

        sink = Gst.ElementFactory.make("appsink")
        sink.set_property("emit-signals", True)
        sink.set_property("drop", True)
        sink.set_property("sync", False)
        sink.connect("new-sample", self.on_buffer, sink)

        # Build the pipeline
        for elem in [queue, conv, caps, jpgenc, sink]:
            self.pipeline.add(elem)

        tee.link(queue)
        queue.link(conv)
        conv.link(caps)
        caps.link(jpgenc)
        jpgenc.link(sink)

    def on_buffer(self, sink, data):
        sample = sink.emit("pull-sample")
        with self.lock:
            self.buffer = sample.get_buffer()
        return Gst.FlowReturn.OK

    def snapshot(self) -> Tuple[str, bytes]:
        with self.lock:
            return self.content_type, self.buffer.extract_dup(0, self.buffer.get_size())
