from dataclasses import dataclass
from typing import Optional, List, Tuple
from lisa.engine.analyzer import TaskAnalyzer, TaskProfile
from lisa.engine.planner import ExecutionPlan, ExecutionPlanner
from lisa.providers.selector import ProviderSelector
from lisa.providers.base import BaseProvider

@dataclass(frozen=True)
class AutoSelectionResult:
    provider: BaseProvider
    model_name: str
    task_profile: TaskProfile
    plan: ExecutionPlan

class AutoSelector:
    """Intelligent Provider & Model Selector based on Task Analysis."""
    
    def __init__(self, provider_selector: ProviderSelector):
        self._provider_selector = provider_selector

    async def plan_execution(
        self,
        prompt: str,
        available_tools: Optional[List[str]] = None,
        preferred_provider_id: Optional[str] = None
    ) -> ExecutionPlan:
        profile = TaskAnalyzer.analyze(prompt)
        tools = available_tools or ["read_file", "write_file", "list_directory"]
        
        try:
            provider = self._provider_selector.select(
                required_capabilities=profile.required_capabilities,
                preferred_id=preferred_provider_id
            )
        except Exception:
            # Fallback to core CHAT capability if strict advanced capabilities (e.g. LONG_CONTEXT) are not registered
            from lisa.core.context import Capability
            provider = self._provider_selector.select(
                required_capabilities=[Capability.CHAT],
                preferred_id=preferred_provider_id
            )
        
        manifest = await provider.handshake()
        model_name = manifest.supported_models[0] if manifest.supported_models else "default"
        
        if profile.suggested_model_tier == "heavy" and len(manifest.supported_models) > 1:
            for m in manifest.supported_models:
                if "large" in m or "70b" in m or "pro" in m or "32b" in m:
                    model_name = m
                    break
        elif profile.suggested_model_tier == "fast" and len(manifest.supported_models) > 1:
            for m in manifest.supported_models:
                if "1.7b" in m or "3b" in m or "mini" in m or "flash" in m:
                    model_name = m
                    break

        plan = ExecutionPlanner.create_plan(
            profile=profile,
            provider_id=provider.id,
            model_name=model_name,
            available_tools=tools
        )
        return plan

    async def select_for_prompt(self, prompt: str, preferred_provider_id: Optional[str] = None) -> AutoSelectionResult:
        plan = await self.plan_execution(prompt, preferred_provider_id=preferred_provider_id)
        try:
            provider = self._provider_selector.select(
                required_capabilities=plan.capabilities_required,
                preferred_id=plan.provider_id
            )
        except Exception:
            from lisa.core.context import Capability
            provider = self._provider_selector.select(
                required_capabilities=[Capability.CHAT],
                preferred_id=plan.provider_id
            )
        profile = TaskAnalyzer.analyze(prompt)
        return AutoSelectionResult(
            provider=provider,
            model_name=plan.model_name,
            task_profile=profile,
            plan=plan
        )
