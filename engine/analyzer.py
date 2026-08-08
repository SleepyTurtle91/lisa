from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from lisa.core.context import Capability

@dataclass(frozen=True)
class TaskProfile:
    complexity_score: float  # 0.0 (simple chat) to 1.0 (complex multi-turn reasoning/code refactor)
    context_tokens_estimate: int
    required_capabilities: List[Capability] = field(default_factory=list)
    suggested_model_tier: str = "fast"  # "fast", "standard", "heavy"
    detected_intent: str = "general_chat"  # "general_chat", "code_edit", "architecture", "engineering_evidence"
    requires_evidence_gate: bool = False

class TaskAnalyzer:
    """Analyzes incoming prompt text and context to determine task requirements."""
    
    @staticmethod
    def analyze(prompt: str, available_tools: Optional[List[str]] = None) -> TaskProfile:
        prompt_lower = prompt.lower()
        complexity = 0.2
        intent = "general_chat"
        capabilities = [Capability.CHAT]
        suggested_tier = "fast"
        requires_evidence = False
        
        # Analyze Engineering Verbs requiring evidence gate
        eng_verbs = ["implement", "modify", "fix", "refactor", "architect", "inspect", "debug", "add", "remove", "change"]
        if any(verb in prompt_lower for verb in eng_verbs):
            requires_evidence = True

        # Analyze Intent & Complexity
        code_keywords = ["fix", "bug", "refactor", "write", "create", "implement", "edit", "code", "file", "function"]
        arch_keywords = ["architecture", "design", "structure", "system", "benchmark", "doctor"]
        
        if any(kw in prompt_lower for kw in arch_keywords):
            complexity = 0.8
            intent = "engineering_evidence" if requires_evidence else "architecture"
            suggested_tier = "heavy"
            capabilities.append(Capability.LONG_CONTEXT)
        elif any(kw in prompt_lower for kw in code_keywords) or requires_evidence:
            complexity = 0.6
            intent = "engineering_evidence" if requires_evidence else "code_edit"
            suggested_tier = "standard"
            capabilities.append(Capability.TOOLS)
            
        if "read" in prompt_lower or "list" in prompt_lower or "file" in prompt_lower or "search" in prompt_lower:
            if Capability.TOOLS not in capabilities:
                capabilities.append(Capability.TOOLS)
                
        # Estimate context length (approx 4 chars per token)
        est_tokens = max(50, len(prompt) // 4)
        
        return TaskProfile(
            complexity_score=complexity,
            context_tokens_estimate=est_tokens,
            required_capabilities=capabilities,
            suggested_model_tier=suggested_tier,
            detected_intent=intent,
            requires_evidence_gate=requires_evidence
        )
