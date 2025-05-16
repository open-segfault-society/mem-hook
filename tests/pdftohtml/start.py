import os
import subprocess
import shutil

OUT_DIR = "html_output/"
OUT_FILE = "out"
IN_PDF = "input.pdf"
LIB = "timer.so"


if __name__ == "__main__":
    os.mkdir("html_output")
    env = os.environ.copy()
    env["LD_PRELOAD"] = f"./{LIB}"
    proc = subprocess.Popen(["pdftohtml", "-s", IN_PDF, OUT_DIR + OUT_FILE], env=env)
    print(f"Started process with PID: {proc.pid}")
    proc.wait()
    shutil.rmtree(OUT_DIR)
