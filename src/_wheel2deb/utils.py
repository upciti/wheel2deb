import subprocess
from pathlib import Path
from typing import List, Tuple


def shell(args: List[str], cwd: Path | None = None) -> Tuple[str, int]:
    result = subprocess.run(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return result.stdout.decode("utf-8"), result.returncode
