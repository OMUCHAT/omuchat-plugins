import json
import subprocess
from pathlib import Path
from typing import Any, List, TypedDict

import psutil

from omu import Address, App, OmuClient

APP = App(
    name="obs-sync",
    group="omu.plugins",
    version="0.1.0",
)
client = OmuClient(APP, address=Address("127.0.0.1", 26423))


def get_launch_command():
    import os
    import sys

    return {
        "cwd": os.getcwd(),
        "args": [sys.executable, "-m", "omuserver", *sys.argv[1:]],
    }


def get_scene_folder():
    import os
    import sys

    if sys.platform == "win32":
        APP_DATA = os.getenv("APPDATA")
        if not APP_DATA:
            raise Exception("APPDATA not found")
        return Path(APP_DATA) / "obs-studio" / "basic" / "scenes"
    else:
        return Path("~/.config/obs-studio/basic/scenes").expanduser()


def generate_launcher():
    return f"""\
import subprocess
class g:
    process: subprocess.Popen | None = None

def _launch():
    if g.process:
        _kill()
    g.process = subprocess.Popen(**{get_launch_command()})

def _kill():
    if g.process:
        g.process.kill()

# obs
def script_load(settings):
    _launch()

def script_unload():
    _kill()
"""


class obs:
    launch_command: List[str] | None = None
    cwd: Path | None = None


def kill_obs():
    for proc in psutil.process_iter():
        if proc.name() == "obs":
            obs.launch_command = proc.cmdline()
            obs.cwd = Path(proc.cwd())
            proc.kill()


def launch_obs():
    if obs.launch_command:
        subprocess.Popen(obs.launch_command, cwd=obs.cwd)


class ScriptToolJson(TypedDict):
    path: str
    settings: Any


ModulesJson = TypedDict("modules", {"scripts-tool": List[ScriptToolJson]})


class SceneJson(TypedDict):
    modules: ModulesJson


def inject_all():
    launcher = Path(__file__).parent / "launcher.py"
    launcher.write_text(generate_launcher())
    scene_folder = get_scene_folder()
    for scene in scene_folder.glob("*.json"):
        inject(launcher, scene)


def inject(launcher: Path, scene: Path):
    data: SceneJson = json.loads(scene.read_text(encoding="utf-8"))
    if "modules" not in data:
        data["modules"] = {}
    if "scripts-tool" not in data["modules"]:
        data["modules"]["scripts-tool"] = []
    data["modules"]["scripts-tool"].append({"path": str(launcher), "settings": {}})
    scene.write_text(json.dumps(data), encoding="utf-8")


@client.endpoints.listen(name="inject")
async def on_inject():
    kill_obs()
    inject_all()
    launch_obs()


async def main():
    if __name__ == "__main__":
        raise Exception("This plugin cannot be run directly")
    await client.start()
