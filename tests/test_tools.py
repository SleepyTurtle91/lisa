import asyncio
import os
import unittest
import tempfile
from pathlib import Path
from lisa.tools.base import ToolRequest
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.registry import ToolRegistry

class TestReadFileTool(unittest.TestCase):
    def test_read_file_schema(self):
        tool = ReadFileTool()
        self.assertEqual(tool.name, "read_file")
        self.assertIn("path", tool.parameters_schema["properties"])

    def test_tool_executor_resolves_project_relative_paths(self):
        registry = ToolRegistry()
        registry.register(ReadFileTool())

        executor = ToolExecutor(registry)
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = "Portable project instructions"
            (Path(temp_dir) / "AGENTS.md").write_text(expected, encoding="utf-8")
            req = ToolRequest(tool_name="read_file", arguments={"path": "AGENTS.md"})

            result = asyncio.run(executor.execute_request(req, project_path=temp_dir))

            self.assertTrue(result.success)
            self.assertIn(expected, result.output)

if __name__ == "__main__":
    unittest.main()
