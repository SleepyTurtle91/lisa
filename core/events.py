from typing import Any, Callable, Dict, List
from dataclasses import dataclass

@dataclass
class Event:
    name: str
    payload: Dict[str, Any]

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def publish(self, event: Event) -> None:
        if event.name in self._listeners:
            for callback in self._listeners[event.name]:
                callback(event)
