import asyncio
import websockets

from config import uri
from utils.login import user

async def run():
    """Connect the script to Pokémon Showdown
    """ 
    async with websockets.connect(uri) as websocket:
        bot: user = user(websocket)
        await bot.login()

if __name__ == "__main__":
    asyncio.run(run())