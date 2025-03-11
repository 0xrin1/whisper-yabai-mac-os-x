#!/usr/bin/env python3
"""
Script to add comprehensive docstrings to key project files.
This serves as a tool for automatically enhancing code documentation.
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Tuple, Optional


class DocstringAdder:
    """Utility to add docstrings to Python files."""

    def __init__(self, project_root: str):
        """
        Initialize the docstring adder.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = os.path.abspath(project_root)

    def process_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Process a Python file to add or enhance docstrings.

        Args:
            file_path: Path to the Python file to process

        Returns:
            Tuple of (success, message)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if file already has docstrings
            module_docstring = self._extract_module_docstring(content)
            class_docstrings = self._extract_class_docstrings(content)
            function_docstrings = self._extract_function_docstrings(content)

            # Count existing docstrings
            total_classes = len(re.findall(r"class\s+\w+", content))
            total_functions = len(re.findall(r"def\s+\w+", content))

            existing_count = (
                (1 if module_docstring else 0)
                + len(class_docstrings)
                + len(function_docstrings)
            )
            total_count = 1 + total_classes + total_functions

            # Report on existing docstrings
            if existing_count >= total_count * 0.75:  # 75% coverage threshold
                return (
                    True,
                    f"File already has good docstring coverage ({existing_count}/{total_count})",
                )

            # Create templates for missing docstrings
            new_content = content

            # Add module docstring if missing
            if not module_docstring:
                module_name = os.path.basename(file_path)
                new_module_docstring = self._generate_module_docstring(module_name)
                if "#!/usr/bin/env python3" in new_content:
                    new_content = re.sub(
                        r"(#!/usr/bin/env python3\n)",
                        r'\1"""\n' + new_module_docstring + '\n"""\n\n',
                        new_content,
                    )
                else:
                    new_content = (
                        '"""\n' + new_module_docstring + '\n"""\n\n' + new_content
                    )

            # Add class docstrings
            class_pattern = r'class\s+(\w+)(?:\(.*?\))?:\s*(?:"""[\s\S]*?""")?\s*'
            for match in re.finditer(r"class\s+(\w+)(?:\(.*?\))?:", content):
                class_name = match.group(1)
                if not any(doc["name"] == class_name for doc in class_docstrings):
                    # This class doesn't have a docstring, add one
                    class_pos = match.end()
                    docstring = (
                        f'    """{self._generate_class_docstring(class_name)}"""'
                    )

                    new_content = (
                        new_content[:class_pos]
                        + "\n"
                        + docstring
                        + "\n    "
                        + new_content[class_pos:]
                    )

            # Add function docstrings
            for match in re.finditer(r"def\s+(\w+)\s*\((.*?)\)(?:\s*->.*?)?:", content):
                func_name = match.group(1)
                params = match.group(2)

                # Skip if function already has docstring or is a dunder method
                if any(doc["name"] == func_name for doc in function_docstrings) or (
                    func_name.startswith("__")
                    and func_name.endswith("__")
                    and func_name != "__init__"
                ):
                    continue

                # Generate docstring
                func_pos = match.end()
                indent = "    " if "class" in content[: match.start()] else ""
                docstring = f'{indent}    """{self._generate_function_docstring(func_name, params)}"""'

                new_content = (
                    new_content[:func_pos]
                    + "\n"
                    + docstring
                    + "\n"
                    + indent
                    + "    "
                    + new_content[func_pos:]
                )

            # Write the updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return True, f"Added docstrings to file"

        except Exception as e:
            return False, f"Error processing {file_path}: {str(e)}"

    def _extract_module_docstring(self, content: str) -> Optional[str]:
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

    def _extract_class_docstrings(self, content: str) -> List[Dict[str, str]]:
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

    def _extract_function_docstrings(self, content: str) -> List[Dict[str, str]]:
        """
        Extract function docstrings from a Python file.

        Args:
            content: Content of the Python file

        Returns:
            List of dictionaries containing function names and docstrings
        """
        function_pattern = (
            r'def\s+(\w+)\s*\((.*?)\)(?:\s*->.*?)?:\s*(?:"""([\s\S]*?)""")?'
        )
        functions = []

        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            params = match.group(2)
            docstring = match.group(3)

            if docstring:
                docstring = docstring.strip()
                functions.append(
                    {"name": func_name, "parameters": params, "docstring": docstring}
                )

        return functions

    def _generate_module_docstring(self, module_name: str) -> str:
        """
        Generate a template module docstring.

        Args:
            module_name: Name of the module

        Returns:
            Generated docstring template
        """
        module_name = module_name.replace(".py", "")
        words = re.findall(r"[A-Z][a-z]*|[a-z]+", module_name)
        readable_name = " ".join(word.lower() for word in words)

        return f"{readable_name.capitalize()} module for voice control system.\nProvides functionality for {readable_name}."

    def _generate_class_docstring(self, class_name: str) -> str:
        """
        Generate a template class docstring.

        Args:
            class_name: Name of the class

        Returns:
            Generated docstring template
        """
        words = re.findall(r"[A-Z][a-z]*", class_name)
        readable_name = " ".join(word.lower() for word in words)

        return f"{readable_name.capitalize()} for the voice control system."

    def _generate_function_docstring(self, func_name: str, params: str) -> str:
        """
        Generate a template function docstring with parameters.

        Args:
            func_name: Name of the function
            params: Parameter string from function definition

        Returns:
            Generated docstring template with parameter section
        """
        # Create readable function name
        if func_name.startswith("_"):
            readable_name = func_name[1:]
        else:
            readable_name = func_name

        words = re.findall(r"[a-z]+|[A-Z][a-z]*", readable_name)
        readable_desc = " ".join(words).lower()

        # Parse parameters
        param_list = []
        if params.strip():
            param_parts = params.split(",")
            for part in param_parts:
                part = part.strip()
                if part and part != "self":
                    # Extract parameter name (without type annotations)
                    param_name = part.split(":")[0].strip()
                    param_list.append(param_name)

        docstring = f"{readable_desc.capitalize()}."

        # Add parameter section if we have parameters
        if param_list:
            docstring += "\n        \n        Args:"
            for param in param_list:
                docstring += f"\n            {param}: Description of {param}"

        return docstring


def main():
    """Main function to add docstrings to Python files."""
    parser = argparse.ArgumentParser(description="Add docstrings to Python files")
    parser.add_argument(
        "--project-root", default=".", help="Root directory of the project"
    )
    parser.add_argument("--file", help="Process a specific file")
    parser.add_argument("--dir", help="Process files in a specific directory")

    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    docstring_adder = DocstringAdder(project_root)

    if args.file:
        file_path = os.path.abspath(args.file)
        success, message = docstring_adder.process_file(file_path)
        print(f"{file_path}: {message}")
    elif args.dir:
        dir_path = os.path.abspath(args.dir)
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    success, message = docstring_adder.process_file(file_path)
                    print(f"{file_path}: {message}")
    else:
        print("Please specify --file or --dir")


if __name__ == "__main__":
    main()
