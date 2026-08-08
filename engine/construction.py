import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

@dataclass(frozen=True)
class ScaffoldedEnvironment:
    model_id: str
    tier: str
    instruction_style: str
    workflow_steps: List[str]
    active_rules: List[str]
    scaffolded_system_prompt: str

class ModelConstructionEngine:
    """Model Construction Engine: Builds cognitive scaffolding & environment rules tailored to model tier."""

    PROFILES_DIR = Path(__file__).resolve().parent.parent / "models" / "profiles"

    @classmethod
    def get_profile(cls, model_name: str, intent: Optional[str] = None) -> ScaffoldedEnvironment:
        model_name_clean = model_name.lower().replace(":", "_").replace("-", "_")
        
        profile_path = cls.PROFILES_DIR / f"{model_name_clean}.yaml"
        
        if intent == "engineering_evidence":
            profile_path = cls.PROFILES_DIR / "engineering_evidence.yaml"
        elif intent == "architecture":
            profile_path = cls.PROFILES_DIR / "architecture_evidence.yaml"
        elif not profile_path.exists():
            if "1.7b" in model_name_clean or "1b" in model_name_clean:
                profile_path = cls.PROFILES_DIR / "qwen3_1.7b.yaml"
            elif "4b" in model_name_clean or "3b" in model_name_clean or "7b" in model_name_clean:
                profile_path = cls.PROFILES_DIR / "qwen3_4b.yaml"
            else:
                profile_path = cls.PROFILES_DIR / "default.yaml"

        tier = "standard"
        instruction_style = "guided"
        steps = ["analyze_context", "execute_task", "verify_result"]
        rules = ["preserve_existing_architecture", "verify_after_edits"]

        # Simple YAML/Fallback loader
        if profile_path.exists():
            try:
                content = profile_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("tier:"):
                        tier = line.split(":", 1)[1].strip().strip('"\'')
                    elif line.startswith("instruction_style:"):
                        instruction_style = line.split(":", 1)[1].strip().strip('"\'')
            except Exception:
                pass

        if intent == "engineering_evidence":
            tier = "heavy"
            instruction_style = "strict_evidence_gate"
            steps = ["identify_relevant_project_files", "inspect_files_using_read_file_tool", "establish_observed_facts_file_fact_tool_fact", "separate_observed_facts_from_assumptions", "produce_evidence_grounded_plan", "request_confirmation_before_file_modification"]
            rules = ["must_read_file_before_proposing_code", "never_substitute_generic_patterns_for_missing_evidence", "label_facts_vs_inferences_vs_unknowns", "distinguish_declared_procedure_from_executed_evidence", "do_not_modify_files_without_permission"]
        elif intent == "architecture":
            tier = "heavy"
            instruction_style = "evidence_disciplined"
            steps = ["observe_project_instructions", "inspect_relevant_source_files", "distinguish_fact_from_inference", "analyze_observed_evidence", "stop_if_evidence_missing", "recommend_safest_change"]
            rules = ["label_facts_vs_inferences_vs_unknowns", "never_invent_uninspected_files", "verify_file_existence_before_recommending", "distinguish_observed_fact_from_expectation", "if_evidence_missing_stop_and_request_inspection"]
        elif tier == "small":
            steps = ["understand_request", "inspect_relevant_files", "identify_evidence", "perform_one_action", "verify_result"]
            rules = ["do_not_guess", "inspect_before_editing", "use_tools_for_facts", "change_only_requested_files", "verify_after_modification"]

        # Build Scaffolded System Prompt
        sys_lines = [
            f"🤖 L.I.S.A. Engineering OS — Scaffolded Runtime Environment ({tier.upper()} TIER)",
            "==========================================================================================",
            f"OPERATING WORKFLOW FOR {model_name.upper()} (INTENT: {intent or 'GENERAL'}):",
            "\n".join([f"  {idx + 1}. {step.replace('_', ' ').title()}" for idx, step in enumerate(steps)]),
            "\nSTRICT GOVERNANCE & EVIDENCE RULES:",
            "\n".join([f"  • {rule.replace('_', ' ').capitalize()}" for rule in rules]),
            "=========================================================================================="
        ]
        scaffolded_prompt = "\n".join(sys_lines)

        return ScaffoldedEnvironment(
            model_id=model_name,
            tier=tier,
            instruction_style=instruction_style,
            workflow_steps=steps,
            active_rules=rules,
            scaffolded_system_prompt=scaffolded_prompt
        )
