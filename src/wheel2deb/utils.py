import os
import subprocess
from pathlib import Path
from typing import List, Tuple


def shell(args: List[str], cwd: Path | None = None) -> Tuple[str, int]:
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    result = subprocess.run(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )
    return result.stdout.decode("utf-8"), result.returncode
