import unittest
from dataclasses import is_dataclass
from pathlib import Path


class TestArchitectureRules(unittest.TestCase):
    # Resolve the repository from this file so the checks work in local clones
    # and in CI runners regardless of the checkout directory.
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    def _get_python_files(self, relative_dir: str):
        target_dir = self.PROJECT_ROOT / relative_dir
        if not target_dir.exists():
            return []
        return list(target_dir.rglob("*.py"))

    def test_project_root_is_the_repository_root(self):
        self.assertTrue((self.PROJECT_ROOT / "AGENTS.md").is_file())
        self.assertTrue((self.PROJECT_ROOT / "ARCHITECTURE.md").is_file())

    def test_architecture_directories_are_present(self):
        for directory in ("core", "runtime", "engine", "providers"):
            with self.subTest(directory=directory):
                self.assertTrue(
                    (self.PROJECT_ROOT / directory).is_dir(),
                    f"Expected architecture directory '{directory}' under {self.PROJECT_ROOT}",
                )
                self.assertTrue(
                    self._get_python_files(directory),
                    f"No Python files discovered under '{directory}'",
                )

    # Rule 1: Runtime Layer must never import concrete providers.
    def test_rule_1_runtime_no_concrete_providers(self):
        core_files = (
            self._get_python_files("core")
            + self._get_python_files("runtime")
            + self._get_python_files("engine")
        )
        forbidden_imports = (
            "lisa.providers.ollama",
            "lisa.providers.openai",
            "lisa.providers.gemini",
            "lisa.providers.claude",
        )

        for file_path in core_files:
            content = file_path.read_text(encoding="utf-8")
            for forbidden in forbidden_imports:
                self.assertNotIn(
                    forbidden,
                    content,
                    f"Architecture Violation: Runtime/Engine file '{file_path}' imports concrete provider '{forbidden}'.",
                )

    # Rule 2: Providers Layer must never import Runtime Kernel.
    def test_rule_2_providers_no_runtime_kernel(self):
        provider_files = self._get_python_files("providers")
        forbidden_imports = ("lisa.core.kernel", "lisa.runtime.session")

        for file_path in provider_files:
            content = file_path.read_text(encoding="utf-8")
            for forbidden in forbidden_imports:
                self.assertNotIn(
                    forbidden,
                    content,
                    f"Architecture Violation: Provider file '{file_path}' imports Runtime file '{forbidden}'.",
                )

    # Rule 3: ProviderManifest & ToolManifest must remain pure dataclasses.
    def test_rule_3_manifests_are_pure_dataclasses(self):
        from lisa.providers.manifest import ProviderManifest
        from lisa.tools.manifest import ToolManifest, ToolContext

        for cls in (ProviderManifest, ToolManifest, ToolContext):
            self.assertTrue(is_dataclass(cls), f"{cls.__name__} must be a dataclass.")
            custom_methods = [
                method
                for method in dir(cls)
                if not method.startswith("__") and callable(getattr(cls, method))
            ]
            self.assertEqual(
                custom_methods,
                [],
                f"Architecture Violation: {cls.__name__} has behavioral methods: {custom_methods}.",
            )

    # Rule 4: ProviderContext must remain a pure dataclass.
    def test_rule_4_context_is_pure_dataclass(self):
        from lisa.providers.context import ProviderContext

        self.assertTrue(is_dataclass(ProviderContext), "ProviderContext must be a dataclass.")
        custom_methods = [
            method
            for method in dir(ProviderContext)
            if not method.startswith("__") and callable(getattr(ProviderContext, method))
        ]
        self.assertEqual(
            custom_methods,
            [],
            f"Architecture Violation: ProviderContext has behavioral methods: {custom_methods}.",
        )

    # Rule 5: Subsystem Protocol Contracts must remain pure dataclasses.
    def test_rule_5_protocol_dataclasses(self):
        from lisa.engine.models import InferenceRequest, InferenceResponse, InferenceResult
        from lisa.tools.base import ToolRequest, ToolResult

        for cls in (
            InferenceRequest,
            InferenceResponse,
            InferenceResult,
            ToolRequest,
            ToolResult,
        ):
            self.assertTrue(is_dataclass(cls), f"{cls.__name__} must be a dataclass.")
            custom_methods = [
                method
                for method in dir(cls)
                if not method.startswith("__") and callable(getattr(cls, method))
            ]
            self.assertEqual(
                custom_methods,
                [],
                f"Architecture Violation: {cls.__name__} has behavioral methods: {custom_methods}.",
            )

    # Rule 6: Session tool execution must exclusively pass through ToolExecutor.
    def test_rule_6_tool_execution_via_executor_only(self):
        session_file = self.PROJECT_ROOT / "runtime" / "session.py"
        content = session_file.read_text(encoding="utf-8")

        self.assertIn(
            "self._executor.execute_request",
            content,
            "Session must execute tools via ToolExecutor.execute_request.",
        )
        self.assertNotIn(
            "tool.execute(",
            content,
            "Session must not call tool.execute directly.",
        )


if __name__ == "__main__":
    unittest.main()
