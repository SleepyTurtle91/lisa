import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

@dataclass
class RawEvidence:
    experiment_id: str
    timestamp: str
    brain_model: str
    hardware_context: str
    task_id: str
    prompt: str
    scaffolding_applied: str
    available_tools: List[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    tool_calls_count: int
    tool_calls_successful: bool
    hallucination_detected: bool
    response_excerpt: str

@dataclass
class DerivedMeasurements:
    success_rate_pct: float
    tool_adherence_pct: float
    hallucination_rate_pct: float
    tok_sec: float
    latency_delta_pct: float = 0.0
    token_savings_pct: float = 0.0

@dataclass
class ResearchInterpretation:
    observation: str
    hypothesis_evaluated: str
    evidence_class: str  # "Pilot Observation", "Repeated Trial", "Matrix Surface", "Adaptive Flight"
    confidence_level: str  # "Low", "Moderate", "High"
    limitations: str
    next_question: str

@dataclass
class ExperimentEntry:
    raw: RawEvidence
    derived: DerivedMeasurements
    interpretation: ResearchInterpretation

class ExperimentRegistry:
    """BANDURA Immutable Experiment Registry & Notebook."""

    REGISTRY_DIR = Path(__file__).resolve().parent

    @classmethod
    def save_experiment(
        cls,
        raw: RawEvidence,
        derived: DerivedMeasurements,
        interpretation: ResearchInterpretation
    ) -> Path:
        entry = ExperimentEntry(raw=raw, derived=derived, interpretation=interpretation)
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{raw.experiment_id.lower()}_registry_{timestamp_str}.json"
        target_path = cls.REGISTRY_DIR / filename
        
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(asdict(entry), f, indent=2)
            
        return target_path

    @classmethod
    def list_experiments(cls) -> List[Dict[str, Any]]:
        entries = []
        for p in sorted(cls.REGISTRY_DIR.glob("*_registry_*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    entries.append(json.load(f))
            except Exception:
                pass
        return entries
