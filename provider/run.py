import asyncio

from chatprovider import client


async def main():
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
