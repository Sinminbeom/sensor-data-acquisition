from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class void(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Sensor(_message.Message):
    __slots__ = ("name", "ability")
    class HealthCheck(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ENABLE: _ClassVar[Sensor.HealthCheck]
        UNABLE: _ClassVar[Sensor.HealthCheck]
    ENABLE: Sensor.HealthCheck
    UNABLE: Sensor.HealthCheck
    NAME_FIELD_NUMBER: _ClassVar[int]
    ABILITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    ability: Sensor.HealthCheck
    def __init__(self, name: _Optional[str] = ..., ability: _Optional[_Union[Sensor.HealthCheck, str]] = ...) -> None: ...

class Sensors(_message.Message):
    __slots__ = ("list", "reason")
    LIST_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    def __init__(self, list: _Optional[_Iterable[str]] = ..., reason: _Optional[str] = ...) -> None: ...

class Connection(_message.Message):
    __slots__ = ("name", "state")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Connection.State]
        CONNECTED: _ClassVar[Connection.State]
        DISCONNECTED: _ClassVar[Connection.State]
    UNKNOWN: Connection.State
    CONNECTED: Connection.State
    DISCONNECTED: Connection.State
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    name: str
    state: Connection.State
    def __init__(self, name: _Optional[str] = ..., state: _Optional[_Union[Connection.State, str]] = ...) -> None: ...

class Health(_message.Message):
    __slots__ = ("name", "status", "reason")
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Health.Status]
        GOOD: _ClassVar[Health.Status]
        WARN: _ClassVar[Health.Status]
        BAAD: _ClassVar[Health.Status]
    UNKNOWN: Health.Status
    GOOD: Health.Status
    WARN: Health.Status
    BAAD: Health.Status
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    name: str
    status: Health.Status
    reason: str
    def __init__(self, name: _Optional[str] = ..., status: _Optional[_Union[Health.Status, str]] = ..., reason: _Optional[str] = ...) -> None: ...

class SensorSnapshot(_message.Message):
    __slots__ = ("name", "content_type", "data")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    content_type: str
    data: bytes
    def __init__(self, name: _Optional[str] = ..., content_type: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class SensorSnapshots(_message.Message):
    __slots__ = ("list",)
    LIST_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedCompositeFieldContainer[SensorSnapshot]
    def __init__(self, list: _Optional[_Iterable[_Union[SensorSnapshot, _Mapping]]] = ...) -> None: ...

class Acquisition(_message.Message):
    __slots__ = ("name", "state", "reason")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Acquisition.State]
        ACQUIRING: _ClassVar[Acquisition.State]
        NOT_ACQUIRING: _ClassVar[Acquisition.State]
    UNKNOWN: Acquisition.State
    ACQUIRING: Acquisition.State
    NOT_ACQUIRING: Acquisition.State
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    name: str
    state: Acquisition.State
    reason: str
    def __init__(self, name: _Optional[str] = ..., state: _Optional[_Union[Acquisition.State, str]] = ..., reason: _Optional[str] = ...) -> None: ...
