import os
import signal
import subprocess
from contextlib import contextmanager
import time
from warnings import warn
from pathlib import Path
import atexit
from threading import Thread

HERE = Path(__file__).parent
WWW = HERE / "www"
MAX_SPACE_NPM = 256
APP_NAME = "src.api"  # Changed to run the new API

os.environ["NODE_OPTIONS"] = f"--max_old_space_size={MAX_SPACE_NPM}"


# Function to clean up background processes
def cleanup(pro: subprocess.Popen):
    print("Cleaning up background processes...")
    pro.terminate()  # Attempt graceful termination
    try:
        pro.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
    except subprocess.TimeoutExpired:
        pro.kill()  # Force kill if not terminated after timeout


# Context manager to handle process start and cleanup
@contextmanager  # type: ignore
def run_background_process() -> subprocess.Popen:  # type: ignore
    pro: subprocess.Popen | None = None
    try:
        # Switch to using the script's current directory:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Start background processes
        pro = subprocess.Popen(
            [
                "uvicorn",
                "--host",
                "0.0.0.0",
                "--port",
                "80",
                "--workers",
                "8",
                "--forwarded-allow-ips=*",
                f"{APP_NAME}:app",  # TODO: programmatically pull this name
            ]
        )
        # Trap SIGINT (Ctrl-C) to call the cleanup function
        signal.signal(signal.SIGINT, lambda signum, frame: lambda: cleanup(pro))
        yield pro
    finally:
        if pro:
            cleanup(pro)


def perform_npm_build() -> None:
    # install first
    print("Building front end with npm...")
    cmd_list: list[str] = [
        "cd",
        str(WWW.absolute()),
        "&&",
        "npm",
        "install",
    ]
    cmd_str = subprocess.list2cmdline(cmd_list)
    return_code = os.system(cmd_str)
    if return_code != 0:
        warn(f"npm install returned {return_code}")
        return
    # Then build to www/dist
    cmd_list: list[str] = [
        "cd",
        str(WWW.absolute()),
        "&&",
        "npm",
        "run",
        "build",
    ]
    cmd_str = subprocess.list2cmdline(cmd_list)
    print(f"Running: {cmd_str}, in {WWW.absolute()}...")
    return_code = os.system(cmd_str)
    if return_code != 0:
        warn(f"npm run build returned {return_code}, you will not have a file server")
        return
    print("Front end built.")


def main() -> None:
    # run npm build first
    # install first
    perform_npm_build()

    # Use the context manager to run and manage the background process
    process: subprocess.Popen
    with run_background_process() as process:
        # Wait for the background process to finish
        assert process is not None
        try:
            rtn = process.wait()
            if rtn != 0:
                warn(f"Background process returned {rtn}")
        except KeyboardInterrupt:
            # Handle Ctrl-C
            pass


# Main function
if __name__ == "__main__":
    main()
