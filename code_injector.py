import os
import subprocess
import shutil
from tempfile import TemporaryDirectory


class CodeInjector:
    DIRECTORY: str = "hook_lib"
    LIB_NAME: str = "hook.so"
    REPLACEMENT_MAP = {
        "MALLOC_MIN_SIZE": "0",
        "MALLOC_MAX_SIZE": "4096",
    }
    
    @staticmethod
    def get_replacement_map() -> dict[str, str]:
        return CodeInjector.REPLACEMENT_MAP

    @staticmethod
    def inject(replacement_map: dict[str, str] = REPLACEMENT_MAP):
        # Get the paths and files
        project_path: str = os.path.dirname(os.path.abspath(__file__))
        lib_path: str = os.path.join(project_path, CodeInjector.DIRECTORY)
        files: list[str] = CodeInjector.get_files(lib_path)

        with TemporaryDirectory() as temp_path:
            for file in files:
                file_name = os.path.basename(file)
                temp_file = os.path.join(temp_path, file_name)

                # Copy each file to the temporary folder and replace
                with open(file, 'r') as src, open(temp_file, 'w') as dst:
                    content: str = src.read()

                    for key, val in replacement_map.items():
                        content = content.replace(key, val)

                    dst.write(content)
            
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

