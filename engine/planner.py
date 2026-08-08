from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from lisa.engine.analyzer import TaskProfile
from lisa.core.context import Capability

from lisa.engine.construction import ModelConstructionEngine, ScaffoldedEnvironment

@dataclass(frozen=True)
class ExecutionPlan:
    mode: str  # "AUTO", "MANUAL", "FALLBACK"
    complexity_level: str  # "LOW", "MEDIUM", "HIGH"
    provider_id: str
    model_name: str
    capabilities_required: List[Capability]
    tools_exposed: List[str]
    confidence: float  # 0.0 to 1.0
    reason: str
    estimated_latency_tier: str  # "FAST (<500ms)", "STANDARD (<5s)", "HEAVY (>15s)"
    hardware_score: float  # Score based on GPU/CPU/RAM suitability
    hardware_cost_tier: str = "LOW"  # "LOW", "MEDIUM", "HIGH"
    hardware_load_tier: str = "LOW"  # "LOW", "MODERATE", "HIGH"
    scaffolded_env: Optional[ScaffoldedEnvironment] = None

class ExecutionPlanner:
    """Adaptive Execution Planner: Transforms TaskProfile + Hardware Constraints into an Explainable ExecutionPlan."""

    @staticmethod
    def create_plan(
        profile: TaskProfile,
        provider_id: str,
        model_name: str,
        available_tools: List[str],
        ram_gb: float = 16.0,
        has_gpu: bool = True
    ) -> ExecutionPlan:
        # Determine Complexity Level & Hardware Load
        if profile.complexity_score < 0.4:
            complexity_lvl = "LOW"
            est_latency = "FAST (<500ms)"
            cost_tier = "LOW"
            load_tier = "LOW"
        elif profile.complexity_score < 0.7:
            complexity_lvl = "MEDIUM"
            est_latency = "STANDARD (<5s)"
            cost_tier = "MEDIUM"
            load_tier = "MODERATE"
        else:
            complexity_lvl = "HIGH"
            est_latency = "HEAVY (>15s)"
            cost_tier = "HIGH"
            load_tier = "HIGH"

        # Construct Cognitive Scaffolding for Model Tier & Intent
        scaffold = ModelConstructionEngine.get_profile(model_name, intent=profile.detected_intent)

        # Hardware-aware scoring
        hw_score = 0.95
        if "30b" in model_name.lower() or "70b" in model_name.lower():
            cost_tier = "HIGH"
            load_tier = "HIGH"
            if ram_gb < 32.0 and not has_gpu:
                hw_score = 0.40
            elif ram_gb < 32.0:
                hw_score = 0.65
        elif "1.7b" in model_name.lower() or "3b" in model_name.lower() or "flash" in model_name.lower():
            hw_score = 0.98

        # Build Explainable Reasoning
        reasons = []
        if profile.detected_intent in ("architecture", "engineering_evidence") and profile.complexity_score >= 0.7:
            reasons.append("Task contains system design or architecture keywords requiring high-capacity context.")
        elif profile.detected_intent in ("code_edit", "engineering_evidence"):
            reasons.append(f"Task detected engineering/code modifications across workspace ({len(available_tools)} tools assigned).")
        else:
            reasons.append("Task detected as general query; routed to optimal fast response model.")

        reasons.append(f"Applied {scaffold.tier.upper()} Cognitive Scaffolding ({len(scaffold.workflow_steps)} workflow steps, {len(scaffold.active_rules)} rules).")

        if hw_score > 0.9:
            reasons.append(f"Hardware compatibility: PASS | Hardware load: {load_tier} | Model suitability: HIGH ({ram_gb}GB RAM).")
        else:
            reasons.append(f"Model '{model_name}' may experience higher latency under current hardware constraints.")

        confidence = round(min(0.99, max(0.5, profile.complexity_score * 0.4 + hw_score * 0.6)), 2)

        return ExecutionPlan(
            mode="AUTO",
            complexity_level=complexity_lvl,
            provider_id=provider_id,
            model_name=model_name,
            capabilities_required=profile.required_capabilities,
            tools_exposed=available_tools,
            confidence=confidence,
            reason=" | ".join(reasons),
            estimated_latency_tier=est_latency,
            hardware_score=hw_score,
            hardware_cost_tier=cost_tier,
            hardware_load_tier=load_tier,
            scaffolded_env=scaffold
        )
