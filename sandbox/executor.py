import subprocess
import sys
import tempfile
import os

def run_python_code(code: str, working_dir: str, timeout: int = 30) -> dict:
    """
    Executes Python code in a subprocess with a timeout.
    working_dir should contain the dataset and is where outputs (charts) get saved.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=working_dir, delete=False
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Execution timed out."}
    finally:
        os.remove(script_path)