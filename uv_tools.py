import subprocess


class UvTool:
    @staticmethod
    def install(source):
        subprocess.run(["uv", "tool", "install", source], check=True)

    @staticmethod
    def remove(name):
        subprocess.run(["uv", "tool", "uninstall", name], check=True)

    @staticmethod
    def _build_cmd(action, target):
        if action == "install":
            return ["uv", "tool", "install", target]
        elif action == "remove":
            return ["uv", "tool", "uninstall", target]
        else:
            raise RuntimeError(f"Unknown uv action: {action}")