import re
from typing import List

import iwashi
from omu import Address, OmuClient
from omu.client import Client, ClientListener
from omu.extension import Extension, define_extension_type
from omu.extension.table import TableExtensionType
from omuchat import App
from omuchat.chat.chat_extension import (
    AuthorsTableKey,
    ChannelsTableKey,
    MessagesTableKey,
    ProviderTableKey,
    RoomTableKey,
)
from omuchat.model.channel import Channel, ChannelJson

app = App(
    name="chat-service",
    group="omu.chat",
    description="",
    version="0.1.0",
    authors=["omu"],
    license="MIT",
    repository_url="https://github.com/OMUCHAT",
)
address = Address("127.0.0.1", 26423)
client = OmuClient(app, address=address)


class ChatServiceExt(Extension, ClientListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.add_listener(self)
        tables = client.extensions.get(TableExtensionType)
        self.messages = tables.register(MessagesTableKey)
        self.authors = tables.register(AuthorsTableKey)
        self.channels = tables.register(ChannelsTableKey)
        self.providers = tables.register(ProviderTableKey)
        self.rooms = tables.register(RoomTableKey)


ChatServiceExtType = define_extension_type(
    "chat-service",
    lambda client: ChatServiceExt(client),
    lambda: [],
)

chat = client.extensions.register(ChatServiceExtType)


@client.endpoints.listen(name="create_channel_tree", app="chat")
async def create_channel_tree(url: str) -> List[ChannelJson]:
    results = await iwashi.visit(url)
    if results is None:
        return []
    channels: List[Channel] = []
    providers = await chat.providers.fetch()
    for result in results.to_list():
        for provider in providers.values():
            if provider.id == "misskey":
                continue
            if re.search(provider.regex, result.url) is None:
                continue
            channels.append(
                Channel(
                    provider_id=provider.key(),
                    id=result.url,
                    url=result.url,
                    name=result.title or result.site_name or result.url,
                    description=result.description or "",
                    active=True,
                    icon_url=result.profile_picture or "",
                )
            )
    return [channel.to_json() for channel in channels]


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()
