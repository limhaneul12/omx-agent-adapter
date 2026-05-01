import subprocess


def run_omx_command(arguments: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["omx", *arguments], cwd=cwd, text=True, capture_output=True, check=False)
