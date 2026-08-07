import unittest
import ast
import os
from pathlib import Path
from dataclasses import is_dataclass

class TestArchitectureRules(unittest.TestCase):
    PROJECT_ROOT = Path("/home/user/development/projects/lisa")

    def _get_python_files(self, relative_dir: str):
        target_dir = self.PROJECT_ROOT / relative_dir
        if not target_dir.exists():
            return []
        return list(target_dir.rglob("*.py"))

    # Rule 1: Runtime Layer must never import concrete providers
    def test_rule_1_runtime_no_concrete_providers(self):
        core_files = self._get_python_files("core") + self._get_python_files("runtime") + self._get_python_files("engine")
        forbidden_imports = ["lisa.providers.ollama", "lisa.providers.openai", "lisa.providers.gemini", "lisa.providers.claude"]

        for file_path in core_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                for forbidden in forbidden_imports:
                    self.assertNotIn(
                        forbidden,
                        content,
                        f"Architecture Violation: Runtime/Engine file '{file_path}' imports concrete provider '{forbidden}'."
                    )

    # Rule 2: Providers Layer must never import Runtime Kernel
    def test_rule_2_providers_no_runtime_kernel(self):
        provider_files = self._get_python_files("providers")
        forbidden_imports = ["lisa.core.kernel", "lisa.runtime.session"]

        for file_path in provider_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                for forbidden in forbidden_imports:
                    self.assertNotIn(
                        forbidden,
                        content,
                        f"Architecture Violation: Provider file '{file_path}' imports Runtime file '{forbidden}'."
                    )

    # Rule 3: ProviderManifest & ToolManifest must remain pure dataclasses with zero behavioral methods
    def test_rule_3_manifests_are_pure_dataclasses(self):
        from lisa.providers.manifest import ProviderManifest
        from lisa.tools.manifest import ToolManifest, ToolContext
        
        for cls in [ProviderManifest, ToolManifest, ToolContext]:
            self.assertTrue(is_dataclass(cls), f"{cls.__name__} must be a dataclass.")
            custom_methods = [
                m for m in dir(cls)
                if not m.startswith("__") and callable(getattr(cls, m))
            ]
            self.assertEqual(
                custom_methods,
                [],
                f"Architecture Violation: {cls.__name__} has behavioral methods: {custom_methods}."
            )

    # Rule 4: ProviderContext must remain a pure dataclass
    def test_rule_4_context_is_pure_dataclass(self):
        from lisa.providers.context import ProviderContext
        self.assertTrue(is_dataclass(ProviderContext), "ProviderContext must be a dataclass.")
        
        custom_methods = [
            m for m in dir(ProviderContext)
            if not m.startswith("__") and callable(getattr(ProviderContext, m))
        ]
        self.assertEqual(
            custom_methods,
            [],
            f"Architecture Violation: ProviderContext has behavioral methods: {custom_methods}."
        )

    # Rule 5: Subsystem Protocol Contracts must remain pure dataclasses
    def test_rule_5_protocol_dataclasses(self):
        from lisa.engine.models import InferenceRequest, InferenceResponse, InferenceResult
        from lisa.tools.base import ToolRequest, ToolResult
        
        for cls in [InferenceRequest, InferenceResponse, InferenceResult, ToolRequest, ToolResult]:
            self.assertTrue(is_dataclass(cls), f"{cls.__name__} must be a dataclass.")
            custom_methods = [
                m for m in dir(cls)
                if not m.startswith("__") and callable(getattr(cls, m))
            ]
            self.assertEqual(
                custom_methods,
                [],
                f"Architecture Violation: {cls.__name__} has behavioral methods: {custom_methods}."
            )

    # Rule 6: Tool execution in Runtime/Session must exclusively pass through ToolExecutor.execute_request
    def test_rule_6_tool_execution_via_executor_only(self):
        session_file = self.PROJECT_ROOT / "runtime" / "session.py"
        with open(session_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("self._executor.execute_request", content, "Session must execute tools via ToolExecutor.execute_request.")
        self.assertNotIn("tool.execute(", content, "Session must not call tool.execute directly.")

if __name__ == "__main__":
    unittest.main()
