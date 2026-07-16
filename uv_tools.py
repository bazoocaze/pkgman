import subprocess


class UvTool:
    @staticmethod
    def install(source):
        result = subprocess.run(["uv", "tool", "install", source], capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, ["uv", "tool", "install", source],
                output=result.stdout, stderr=result.stderr
            )

    @staticmethod
    def remove(name):
        result = subprocess.run(["uv", "tool", "uninstall", name], capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, ["uv", "tool", "uninstall", name],
                output=result.stdout, stderr=result.stderr
            )

    @staticmethod
    def _build_cmd(action, target):
        if action == "install":
            return ["uv", "tool", "install", target]
        elif action == "remove":
            return ["uv", "tool", "uninstall", target]
        else:
            raise RuntimeError(f"Unknown uv action: {action}")