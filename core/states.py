from enum import Enum, auto

class RuntimeState(Enum):
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    BUSY = auto()
    RECOVERING = auto()
    SHUTTING_DOWN = auto()
    FAILED = auto()

class SessionState(Enum):
    CREATED = auto()
    BOOTING = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()
    FAILED = auto()
    CLOSED = auto()

class BootstrapState(Enum):
    DISCOVER_PROJECT = auto()
    READ_BOOT = auto()
    LOAD_PLUGINS = auto()
    REGISTER_TOOLS = auto()
    INITIALIZE_PROVIDER = auto()
    CREATE_SESSION = auto()
    READY = auto()
