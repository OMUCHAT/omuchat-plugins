from chatprovider import client


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()
