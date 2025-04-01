import os
import subprocess
import shutil
from tempfile import TemporaryDirectory
from dataclasses import dataclass
from enum import Enum
from cli import *


class Placeholder(str, Enum):
    MALLOC_FILTER_RANGE = "<<<MALLOC_FILTER_RANGE>>>"
    MALLOC_FILTER = "<<<MALLOC_FILTER>>>"
    FREE_CONSTRUCTOR = "<<<FREE_CONSTRUCTOR>>>"
    MALLOC_CONSTRUCTOR = "<<<MALLOC_CONSTRUCTOR>>>"


@dataclass
class CodeEntry:
    placeholder: Placeholder
    snippet: str

    def inject(self, content: str) -> str:
        """Inject the snippet at placeholder in content"""
        return content.replace(self.placeholder, self.snippet)


class CodeEntryFactory:
    @staticmethod
    def malloc_filter_range(bounds: list[tuple[int, int]]) -> CodeEntry:
        placeholder = Placeholder.MALLOC_FILTER_RANGE

        bound_snippet = "(size < {} || {} < size) && {}"
        tail_snippet = "true"
        snippet = "if ({})\nreturn ptr;\n"

        for min, max in bounds:
            snippet = snippet.format(bound_snippet)
            snippet = snippet.format(min, max, "{}")
        snippet = snippet.format(tail_snippet)

        return CodeEntry(placeholder, snippet)

    @staticmethod
    def malloc_filter(values: list[int]) -> CodeEntry:
        placeholder = Placeholder.MALLOC_FILTER

        value_snippet = "(size != {}) && {}"
        tail_snippet = "true"
        snippet = "if ({})\nreturn ptr;\n"

        for value in values:
            snippet = snippet.format(value_snippet)
            snippet = snippet.format(value, "{}")
        snippet = snippet.format(tail_snippet)

        return CodeEntry(placeholder, snippet)

    @staticmethod
    def malloc_constructor(type: str, size: int, last: bool) -> CodeEntry:
        placeholder = Placeholder.MALLOC_CONSTRUCTOR

        snippet = 'malloc_buffer("/mem_hook_alloc", 8, {}, 8 + {}),'

        if type == "w":
            snippet = snippet.format("sizeof(Allocation) * " + str(size), {})
            snippet = snippet.format("sizeof(Allocation) * " + str(size), {})

        elif type == "b":
            snippet = snippet.format(str(size), {})
            snippet = snippet.format(str(size), {})

        # Make sure all entries must be parsed correctly
        else:
            raise Exception(f"Unable to parse buffer type for size: {size}, type: {type}")

        if last:
            snippet = snippet[:-1]
        return CodeEntry(placeholder, snippet)

    @staticmethod
    def free_constructor(type: str, size: int, last: bool) -> CodeEntry:
        placeholder = Placeholder.FREE_CONSTRUCTOR

        placeholder = Placeholder.MALLOC_CONSTRUCTOR

        snippet = 'free_buffer("/mem_hook_free", 8, {}, 8 + {}),'

        if type == "w":
            snippet = snippet.format("sizeof(Free) * " + str(size), {})
            snippet = snippet.format("sizeof(Free) * " + str(size), {})

        elif type == "b":
            snippet = snippet.format(str(size), {})
            snippet = snippet.format(str(size), {})

        # Make sure all entries must be parsed correctly
        else:
            raise Exception(f"Unable to parse buffer type for size: {size}, type: {type}")

        if last:
            snippet = snippet[:-1]
        return CodeEntry(placeholder, snippet)

    @staticmethod
    def buffer_sizes(buffer: BufferSize) -> CodeEntry:
        type = buffer.type
        for i, (function, size) in enumerate(buffer.buffer_sizes):

            # Since classes are instantiated with initializer list 
            # they are comma seperated. Last comma must however be removed
            last = False
            if i == len(buffer.buffer_sizes) - 1:
                last = True

            if function == "free":
                return CodeEntryFactory.free_constructor(type, size, last)
            elif function == "malloc":
                return CodeEntryFactory.malloc_constructor(type, size, last)

            # Make sure all entries must be parsed correctly
            else:
                raise Exception(f"Unable to parse buffer size for function: {function}")

class CodeInjector:
    DIRECTORY: str = "hook_lib"
    LIB_NAME: str = "hook.so"

    @staticmethod
    def inject(code_entries: list[CodeEntry]):
        # Get the paths and files
        project_path: str = os.path.dirname(
            os.path.abspath(__file__)
        )  # Running directory
        lib_path: str = os.path.join(
            project_path, CodeInjector.DIRECTORY
        )  # C++ library directory
        files: list[str] = CodeInjector.get_files(lib_path)  # C++ files to be compiled

        # Copy each C++ file to a temporary directory
        # Insert the snippets, compile, and move the library file to the running directory
        with TemporaryDirectory() as temp_path:
            for file in files:
                file_name = os.path.basename(file)
                temp_file = os.path.join(temp_path, file_name)
                CodeInjector.copy_and_inject(file, temp_file, code_entries)

            # Build the library in the temporary directory
            try:
                subprocess.run(["make", "-C", temp_path], check=True)
            except Exception as e:
                print(f"Could not build library: {e}")
                exit(1)

            # Move the compiled library into the project directory
            lib_src: str = os.path.join(temp_path, CodeInjector.LIB_NAME)
            lib_dst: str = os.path.join(project_path, CodeInjector.LIB_NAME)
            shutil.move(lib_src, lib_dst)

    @staticmethod
    def get_files(dir: str) -> list[str]:
        """Get all files in a directory"""
        files: list[str] = []

        for file in os.listdir(dir):
            file_path = os.path.join(dir, file)
            if os.path.isfile(file_path):
                files.append(file_path)

        return files

    @staticmethod
    def copy_and_inject(
        src_file: str, dst_file: str, code_entries: list[CodeEntry]
    ) -> None:
        # Copy each file to the temporary folder and replace
        with open(src_file, "r") as src, open(dst_file, "w") as dst:
            content: str = src.read()

            # Inject the snippets
            for code_entry in code_entries:
                content = code_entry.inject(content)

            # Clean up all placeholders
            for _, member in Placeholder.__members__.items():
                content = content.replace(member, "")

            dst.write(content)
