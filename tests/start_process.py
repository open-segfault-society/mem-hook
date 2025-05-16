import sys
import os
import subprocess

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python start_process.py <process>")
        exit(1)

    p_cmd = sys.argv[1]
    p_args = sys.argv[2:]

    # Add the path of the script if none was found
    if p_cmd.find("/") == -1:
        path = os.path.dirname(os.path.abspath(__file__))
        p_cmd = os.path.join(path, p_cmd)

    print(f"Starting process: {p_cmd}")

    process = subprocess.Popen([p_cmd] + p_args)
    pid = process.pid

    print(f"Started process with PID: {pid}")

    try:
        print("Press Ctrl+C to stop the process.")
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        print(f"Process with PID {pid} terminated.")
