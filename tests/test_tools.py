import os
import unittest
from lisa.tools.filesystem.read_file import ReadFileTool

class TestReadFileTool(unittest.TestCase):
    def test_read_file_schema(self):
        tool = ReadFileTool()
        self.assertEqual(tool.name, "read_file")
        self.assertIn("path", tool.parameters_schema["properties"])

if __name__ == "__main__":
    unittest.main()
