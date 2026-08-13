"""
Unit tests for TargetInspector and pre-invocation target grounding (NE-012.1 Experiment A).
"""

import os
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.tools.base import ToolRequest
from lisa.tools.registry import ToolRegistry
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.filesystem.standard import ReadFileTool, ListDirectoryTool
from lisa.tools.filesystem.target_grounding import TargetInspector, TargetType


class TestTargetGrounding(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = self.temp_dir.name

        # Create a file and a directory in temp project root
        self.file_name = "test_file.txt"
        self.file_path = os.path.join(self.project_path, self.file_name)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("sample content")

        self.dir_name = "test_dir"
        self.dir_path = os.path.join(self.project_path, self.dir_name)
        os.makedirs(self.dir_path, exist_ok=True)

        self.registry = ToolRegistry()
        self.registry.register(ReadFileTool())
        self.registry.register(ListDirectoryTool())
        self.executor = ToolExecutor(self.registry)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inspect_file(self):
        inspection = TargetInspector.inspect(self.file_name, project_path=self.project_path)
        self.assertEqual(inspection.target_type, TargetType.FILE)
        self.assertEqual(inspection.resolved_path, self.file_path)

    def test_inspect_directory(self):
        inspection = TargetInspector.inspect(self.dir_name, project_path=self.project_path)
        self.assertEqual(inspection.target_type, TargetType.DIRECTORY)
        self.assertEqual(inspection.resolved_path, self.dir_path)

    def test_inspect_missing(self):
        inspection = TargetInspector.inspect("non_existent.txt", project_path=self.project_path)
        self.assertEqual(inspection.target_type, TargetType.MISSING)

    def test_validate_operations(self):
        file_insp = TargetInspector.inspect(self.file_name, project_path=self.project_path)
        dir_insp = TargetInspector.inspect(self.dir_name, project_path=self.project_path)
        missing_insp = TargetInspector.inspect("missing.txt", project_path=self.project_path)

        # Valid operations
        v, err = TargetInspector.validate_tool_operation("read_file", file_insp)
        self.assertTrue(v)
        self.assertIsNone(err)

        v, err = TargetInspector.validate_tool_operation("list_directory", dir_insp)
        self.assertTrue(v)
        self.assertIsNone(err)

        # Invalid operations
        v, err = TargetInspector.validate_tool_operation("list_directory", file_insp)
        self.assertFalse(v)
        self.assertIn("Cannot execute list_directory on FILE target", err)

        v, err = TargetInspector.validate_tool_operation("read_file", dir_insp)
        self.assertFalse(v)
        self.assertIn("Cannot execute read_file on DIRECTORY target", err)

        v, err = TargetInspector.validate_tool_operation("read_file", missing_insp)
        self.assertTrue(v)
        self.assertIsNone(err)

    async def test_dispatcher_pre_invocation_rejection(self):
        # Dispatch list_directory on FILE -> must be rejected before tool execution
        req = ToolRequest(tool_name="list_directory", arguments={"path": self.file_name})
        res = await self.executor.execute_request(req, project_path=self.project_path)

        self.assertFalse(res.success)
        self.assertIn("Pre-invocation Grounding Guard Rejected Tool", res.error)
        self.assertTrue(res.metadata.get("rejected_before_execution"))
        self.assertEqual(res.metadata.get("target_type"), "FILE")

    async def test_dispatcher_valid_execution(self):
        # Dispatch read_file on FILE -> must succeed
        req = ToolRequest(tool_name="read_file", arguments={"path": self.file_name})
        res = await self.executor.execute_request(req, project_path=self.project_path)

        self.assertTrue(res.success)
        self.assertEqual(res.output, "sample content")

    async def test_dispatcher_preserve_absolute_path(self):
        abs_file_path = os.path.abspath(self.file_path)
        req = ToolRequest(tool_name="read_file", arguments={"path": abs_file_path})
        res = await self.executor.execute_request(req, project_path=self.project_path)

        self.assertTrue(res.success)
        self.assertEqual(res.metadata.get("resolved_path"), abs_file_path)


if __name__ == "__main__":
    unittest.main()
