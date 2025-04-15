import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from tempfile import TemporaryDirectory

import cli


class Placeholder(str, Enum):
    ALLOC_FILTER_RANGE = "<<<ALLOC_FILTER_RANGE>>>"
    ALLOC_FILTER = "<<<ALLOC_FILTER>>>"
    BUFFER = "<<<BUFFER>>>"
    BACKTRACE_FAST = "<<<USE_BACKTRACE_FAST>>>"
    BACKTRACE_GLIBC = "<<<USE_BACKTRACE_GLIBC>>>"


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
        placeholder = Placeholder.ALLOC_FILTER_RANGE

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
        placeholder = Placeholder.ALLOC_FILTER

        value_snippet = "(size != {}) && {}"
        tail_snippet = "true"
        snippet = "if ({})\nreturn ptr;\n"

        for value in values:
            snippet = snippet.format(value_snippet)
            snippet = snippet.format(value, "{}")
        snippet = snippet.format(tail_snippet)

        return CodeEntry(placeholder, snippet)

    @staticmethod
    def buffer_sizes(buffer: cli.BufferSize) -> CodeEntry:
        placeholder = Placeholder.BUFFER
        snippet = ""
        type = buffer.type
        snippet = 'buffer("/mem_hook", 12, {}, 12 + {})'

        if type == "w":
            snippet = snippet.format("sizeof(Trace) * " + str(buffer.size), {})
            snippet = snippet.format("sizeof(Trace) * " + str(buffer.size), {})

        elif type == "b":
            snippet = snippet.format(str(buffer.size), {})
            snippet = snippet.format(str(buffer.size), {})

        return CodeEntry(placeholder, snippet)

    @staticmethod
    def backtrace_fast() -> CodeEntry:
        snippet = (
            "uint32_t backtrace_size = walk_stack_fp<void*, 20>(backtrace_buffer, 1);"
        )
        return CodeEntry(Placeholder.BACKTRACE_FAST, snippet)

    @staticmethod
    def backtrace_glibc() -> CodeEntry:
        snippet = "uint32_t backtrace_size = backtrace(backtrace_buffer.begin(), BUFFER_SIZE);"
        return CodeEntry(Placeholder.BACKTRACE_GLIBC, snippet)


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
