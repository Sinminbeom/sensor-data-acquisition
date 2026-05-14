import service_pb2 as _service_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Device(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class Connections(_message.Message):
    __slots__ = ("list",)
    LIST_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedCompositeFieldContainer[_service_pb2.Connection]
    def __init__(self, list: _Optional[_Iterable[_Union[_service_pb2.Connection, _Mapping]]] = ...) -> None: ...

class Healths(_message.Message):
    __slots__ = ("list",)
    LIST_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedCompositeFieldContainer[_service_pb2.Health]
    def __init__(self, list: _Optional[_Iterable[_Union[_service_pb2.Health, _Mapping]]] = ...) -> None: ...

class Acquisitions(_message.Message):
    __slots__ = ("list",)
    LIST_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedCompositeFieldContainer[_service_pb2.Acquisition]
    def __init__(self, list: _Optional[_Iterable[_Union[_service_pb2.Acquisition, _Mapping]]] = ...) -> None: ...

class VoiceTag(_message.Message):
    __slots__ = ("timestamp", "voice")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    voice: bytes
    def __init__(self, timestamp: _Optional[int] = ..., voice: _Optional[bytes] = ...) -> None: ...
