import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, TypedDict

from omuchat import App, Client, model

APP = App(
    name="emoji",
    group="omu.chat.plugins",
    version="0.1.0",
)
client = Client(APP)


class Emoji(TypedDict):
    id: str
    name: str
    image_url: str
    regex: str


class registry:
    emojis: Dict[str, Emoji] = {}
    emojis_dir: Path


@client.omu.registry.listen("emojis")
async def on_emojis_update(emojis: Dict[str, Emoji]) -> None:
    registry.emojis = emojis or {}


class Directories(TypedDict):
    data: str
    assets: str
    plugins: str


@client.omu.registry.listen("directories", app="server")
async def on_directories(directories: Directories) -> None:
    registry.emojis_dir = Path(directories["assets"]) / "emojis"
    registry.emojis_dir.mkdir(parents=True, exist_ok=True)


@client.omu.endpoints.listen(name="upload")
async def upload_emoji(files: List[str]) -> None:
    for file in files:
        name = Path(file).stem
        id = name
        i = 1
        while id in registry.emojis:
            id = f"{name}{i}"
            i += 1
        path = registry.emojis_dir / f"{id}.png"
        shutil.copyfile(file, path)
        registry.emojis[id] = {
            "id": id,
            "name": name,
            "image_url": f"http://{client.address}/assets?path=emojis/{id}.png",
            "regex": re.escape(name),
        }
    await client.omu.registry.set("emojis", registry.emojis)


@dataclass
class EmojiMatch:
    emoji: Emoji
    match: re.Match
    start: int
    end: int


def transform(component: model.ContentComponent) -> model.ContentComponent:
    if isinstance(component, model.TextContent):
        parts = transform_text_content(component)
        if len(parts) == 1:
            return parts[0]
        return model.RootContent(parts)
    if component.siblings:
        component.siblings = [transform(sibling) for sibling in component.siblings]
    return component


def transform_text_content(
    component: model.TextContent,
) -> list[model.ContentComponent]:
    text = component.text
    parts = []
    while text:
        match: EmojiMatch | None = None
        for emoji in registry.emojis.values():
            if not emoji["regex"]:
                continue
            result = re.search(emoji["regex"], text)
            if not result:
                continue
            if not match or result.start() < match.start:
                match = EmojiMatch(emoji, result, result.start(), result.end())
        if not match:
            parts.append(model.TextContent(text))
            break
        if match.start > 0:
            parts.append(model.TextContent(text[: match.start]))
        parts.append(
            model.ImageContent(
                match.emoji["image_url"],
                match.emoji["id"],
                match.emoji["name"],
            )
        )
        text = text[match.end :]
    return parts


@client.chat.messages.proxy
async def on_message(message: model.Message):
    if not message.author_id:
        return message
    if not message.content:
        return message
    message.content = transform(message.content)
    return message


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()
