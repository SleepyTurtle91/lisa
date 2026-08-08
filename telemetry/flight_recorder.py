import os
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from datetime import datetime

class FlightRecorder:
    """Experimental Flight Recorder (EXP-FR-001): Streams lossless raw event traces to JSONL."""

    DEFAULT_LOG_DIR = Path.home() / ".lisa" / "flight_recorder"

    def __init__(self, session_id: str, log_dir: Optional[Path] = None):
        self.session_id = session_id
        self.log_dir = log_dir or self.DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{self.session_id}.jsonl"
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers = [fn for fn in self._subscribers if fn is not callback]

    def record_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_record = {
            "timestamp": datetime.now().isoformat(),
            "time_epoch_ms": round(time.time() * 1000.0, 2),
            "session_id": self.session_id,
            "event_type": event_type,
            "payload": payload
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_record) + "\n")
        except Exception:
            pass

        for callback in list(self._subscribers):
            try:
                callback(event_record)
            except Exception:
                pass
            
        return event_record

    def get_events(self) -> list:
        events = []
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            pass
        return events
