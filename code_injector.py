import os
import subprocess
import shutil
from tempfile import TemporaryDirectory


class CodeInjector:
    DIRECTORY: str = "hook_lib"
    LIB_NAME: str = "hook.so"

    @staticmethod
    def inject():
        # Get the paths and files
        project_path: str = os.path.dirname(os.path.abspath(__file__))
        lib_path: str = os.path.join(project_path, CodeInjector.DIRECTORY)
        files: list[str] = CodeInjector.get_files(lib_path)

        with TemporaryDirectory() as temp_path:
            for file in files:
                file_name = os.path.basename(file)
                temp_file = os.path.join(temp_path, file_name)
                with open(file, 'r') as src, open(temp_file, 'w') as dst:
                    dst.write(src.read())
            
            # Build the library in the temporary directory
            subprocess.run(["make", "-C", temp_path], check=True)

            # Move the compiled library into the project directory
            lib_src: str = os.path.join(temp_path, CodeInjector.LIB_NAME)
            lib_dst: str = os.path.join(project_path, CodeInjector.LIB_NAME)
            shutil.move(lib_src, lib_dst)

    @staticmethod
    def get_lib_abs_path() -> str:
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, CodeInjector.DIRECTORY)
        return path

    @staticmethod
    def get_files(dir: str) -> list[str]:
        """Get all files in a directory"""
        files: list[str] = []

        for file in os.listdir(dir):
            file_path = os.path.join(dir, file)
            # TODO: Remove the check for object files
            if os.path.isfile(file_path) and not file_path[-1] == 'o':
                files.append(file_path)

        return files

