from execution.invoke import run_omx_command


def read_runtime_status() -> str:
    result = run_omx_command(["status"])
    return result.stdout.strip() or result.stderr.strip()
