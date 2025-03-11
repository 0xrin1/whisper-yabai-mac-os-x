#!/usr/bin/env python3
"""
Documentation extractor for whisper-yabai-mac-os-x.
Extracts docblocks from Python files and generates markdown files for mdBook.
"""

import os
import re
import sys
import glob
import argparse
from typing import List, Dict, Any, Optional, Tuple


class DocExtractor:
    """Extracts documentation from Python files."""

    def __init__(self, base_dir: str, output_dir: str):
        """
        Initialize the documentation extractor.

        Args:
            base_dir: Base directory containing the code
            output_dir: Output directory for the markdown files
        """
        self.base_dir = os.path.abspath(base_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.module_structure = {}
        self.toc = []

    def find_python_files(self) -> List[str]:
        """
        Find all Python files in the project.

        Returns:
            List of paths to Python files
        """
        python_files = []

        for root, _, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith(".py"):
                    # Skip test files and init files
                    if "test_" in file or file == "__init__.py":
                        continue

                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.base_dir)
                    python_files.append(rel_path)

        # Sort files to ensure consistent output
        python_files.sort()
        return python_files

    def extract_docstring(self, content: str) -> Optional[str]:
        """
        Extract the module docstring from a Python file.

        Args:
            content: Content of the Python file

        Returns:
            Extracted docstring or None if not found
        """
        module_docstring_pattern = r'"""([\s\S]*?)"""'
        match = re.search(module_docstring_pattern, content)

        if match:
            docstring = match.group(1).strip()
            return docstring

        return None

    def extract_class_docstrings(self, content: str) -> List[Dict[str, str]]:
        """
        Extract class docstrings from a Python file.

        Args:
            content: Content of the Python file

        Returns:
            List of dictionaries containing class names and docstrings
        """
        class_pattern = r'class\s+(\w+)(?:\(.*?\))?:\s*(?:"""([\s\S]*?)""")?'
        classes = []

        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            docstring = match.group(2)

            if docstring:
                docstring = docstring.strip()
                classes.append({"name": class_name, "docstring": docstring})

        return classes

    def extract_function_docstrings(self, content: str) -> List[Dict[str, str]]:
        """
        Extract function docstrings from a Python file.

        Args:
            content: Content of the Python file

        Returns:
            List of dictionaries containing function names and docstrings
        """
        # Function pattern with support for decorators and type annotations
        function_pattern = r'(?:@\w+(?:\(.*?\))?\s*)*def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*\w+)?:\s*(?:"""([\s\S]*?)""")?'
        functions = []

        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            parameters = match.group(2)
            docstring = match.group(3)

            # Skip special methods like __init__ unless they have docstrings
            if func_name.startswith("__") and (
                not docstring or func_name != "__init__"
            ):
                continue

            if docstring:
                docstring = docstring.strip()
                functions.append(
                    {
                        "name": func_name,
                        "parameters": parameters,
                        "docstring": docstring,
                    }
                )

        return functions

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a Python file and extract all docstrings.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary containing all extracted documentation
        """
        full_path = os.path.join(self.base_dir, file_path)

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        module_docstring = self.extract_docstring(content)
        class_docstrings = self.extract_class_docstrings(content)
        function_docstrings = self.extract_function_docstrings(content)

        return {
            "path": file_path,
            "module_docstring": module_docstring,
            "classes": class_docstrings,
            "functions": function_docstrings,
        }

    def generate_module_structure(self):
        """Generate the module structure from Python files."""
        python_files = self.find_python_files()
        self.module_structure = {}

        for file_path in python_files:
            # Split the path into directories
            parts = file_path.split(os.sep)
            current = self.module_structure

            # Create nested dictionaries for directory structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Store the file
            filename = parts[-1]
            current[filename] = self.process_file(file_path)

    def write_markdown_file(self, output_path: str, content: str):
        """
        Write content to a markdown file.

        Args:
            output_path: Path to write the file
            content: Content to write
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def docstring_to_markdown(self, docstring: str) -> str:
        """
        Convert a docstring to markdown.

        Args:
            docstring: Python docstring

        Returns:
            Markdown content
        """
        if not docstring:
            return ""

        # Process section headers in docstrings (e.g., Args:, Returns:)
        lines = docstring.split("\n")
        markdown_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for section headers
            if re.match(
                r"^(Args|Arguments|Parameters|Returns|Raises|Yields|Examples|Notes):",
                line,
            ):
                section_header = line.strip(":")
                markdown_lines.append(f"\n### {section_header}\n")
                i += 1

                # Process items in the section
                while i < len(lines) and (
                    not lines[i].strip() or lines[i].startswith(" ")
                ):
                    stripped = lines[i].strip()

                    # Handle parameter descriptions
                    param_match = re.match(r"(\w+):\s*(.*)", stripped)
                    if param_match:
                        param_name = param_match.group(1)
                        param_desc = param_match.group(2)
                        markdown_lines.append(f"- **{param_name}**: {param_desc}")
                    else:
                        markdown_lines.append(stripped)

                    i += 1
            else:
                markdown_lines.append(line)
                i += 1

        return "\n".join(markdown_lines)

    def generate_markdown_for_module(
        self, module_data: Dict[str, Any], module_path: str
    ) -> str:
        """
        Generate markdown for a module.

        Args:
            module_data: Module documentation data
            module_path: Path to the module

        Returns:
            Markdown content
        """
        filename = os.path.basename(module_path)
        module_name = os.path.splitext(filename)[0]

        markdown = f"# {module_name}\n\n"

        # Add module docstring
        if module_data.get("module_docstring"):
            markdown += (
                f"{self.docstring_to_markdown(module_data['module_docstring'])}\n\n"
            )

        # Add source code link
        markdown += f"Source: `{module_path}`\n\n"

        # Add classes
        for class_data in module_data.get("classes", []):
            markdown += f"## Class: {class_data['name']}\n\n"
            markdown += f"{self.docstring_to_markdown(class_data['docstring'])}\n\n"

        # Add functions
        for func_data in module_data.get("functions", []):
            markdown += (
                f"## Function: `{func_data['name']}({func_data['parameters']})`\n\n"
            )
            markdown += f"{self.docstring_to_markdown(func_data['docstring'])}\n\n"

        return markdown

    def generate_markdown_files(self):
        """Generate markdown files from the module structure."""
        # Generate SUMMARY.md for mdBook's table of contents
        summary = "# Summary\n\n"
        summary += "- [Introduction](README.md)\n"

        # Process files and directories
        def process_directory(directory, path_prefix="", indent=""):
            nonlocal summary

            # Process Python files in the current directory
            for item_name, item_data in sorted(directory.items()):
                if isinstance(item_data, dict) and "path" not in item_data:
                    # This is a subdirectory
                    dir_name = item_name.capitalize()
                    summary += f"{indent}- [{dir_name}]()\n"

                    # Create a section file for the directory
                    process_directory(
                        item_data, f"{path_prefix}{item_name}/", f"{indent}  "
                    )
                else:
                    # This is a file
                    module_name = os.path.splitext(item_name)[0]
                    file_path = item_data["path"]

                    # Generate markdown
                    markdown = self.generate_markdown_for_module(item_data, file_path)

                    # Determine the output path
                    rel_path = os.path.dirname(file_path)
                    output_rel_path = (
                        f"{rel_path}/{module_name}.md"
                        if rel_path
                        else f"{module_name}.md"
                    )
                    output_path = os.path.join(self.output_dir, output_rel_path)

                    # Write the markdown file
                    self.write_markdown_file(output_path, markdown)

                    # Add to the summary
                    summary += f"{indent}- [{module_name}]({output_rel_path})\n"

        # Start processing from the root
        process_directory(self.module_structure)

        # Write the summary file
        summary_path = os.path.join(self.output_dir, "SUMMARY.md")
        self.write_markdown_file(summary_path, summary)

        # Generate README.md with project overview
        self.generate_readme()

    def generate_readme(self):
        """Generate the main README.md for the documentation."""
        # Get content from the project's README.md
        project_readme_path = os.path.join(self.base_dir, "README.md")

        if os.path.exists(project_readme_path):
            with open(project_readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
        else:
            readme_content = "# Whisper Voice Control for macOS\n\nA voice command daemon that uses OpenAI's Whisper model locally to control your Mac."

        # Add documentation information
        docs_info = """
## Documentation

This is the auto-generated API documentation for the Whisper Voice Control system.
The documentation is extracted from docstrings in the source code.

### Key Components

- **Core**: Core infrastructure components
- **Audio**: Audio recording and processing components
- **Utils**: Utility functions and command processing
- **UI**: User interface components
- **Config**: Configuration management
        """

        # Combine the content
        full_content = f"{readme_content}\n\n{docs_info}"

        # Write the README.md
        readme_path = os.path.join(self.output_dir, "README.md")
        self.write_markdown_file(readme_path, full_content)

    def extract_and_generate(self):
        """Extract documentation and generate markdown files."""
        print(f"Extracting documentation from {self.base_dir}...")
        self.generate_module_structure()

        print(f"Generating markdown files in {self.output_dir}...")
        self.generate_markdown_files()

        print("Documentation generation complete!")


def main():
    """Main function to extract documentation and generate markdown files."""
    parser = argparse.ArgumentParser(
        description="Extract documentation from Python files and generate markdown for mdBook"
    )
    parser.add_argument(
        "--base-dir", default="src", help="Base directory containing the code"
    )
    parser.add_argument(
        "--output-dir",
        default="docs-src/src",
        help="Output directory for the markdown files",
    )

    args = parser.parse_args()

    extractor = DocExtractor(args.base_dir, args.output_dir)
    extractor.extract_and_generate()


if __name__ == "__main__":
    main()
