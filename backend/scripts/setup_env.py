import os
import sys
import subprocess

def resolve_juliapkg():
    """
    Resolves Julia dependencies.
    Replaces: PYTHON_JULIAPKG_OFFLINE='no' python -c 'import os, sys, juliapkg; ...'
    """
    print("Resolving Julia packages...", flush=True)

    env = os.environ.copy()
    env["PYTHON_JULIAPKG_OFFLINE"] = "no"
    env["JULIA_PYTHONCALL_EXE"] = sys.executable
    # Force unbuffered output in the subprocess as well
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable,
        "-u",  # unbuffered stdout/stderr
        "-c",
        "import juliapkg; juliapkg.resolve()"
    ]

    subprocess.check_call(cmd, env=env)

def main():
    print("Starting environment setup...", flush=True)
    resolve_juliapkg()
    print("Environment setup complete.", flush=True)

if __name__ == "__main__":
    main()
