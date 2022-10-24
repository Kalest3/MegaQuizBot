import json
import requests
import asyncio
import logging
import threading
import sqlite3
from config import *
from showdown.utils import name_to_id

logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        )

file = sqlite3.connect("leaderboard.db")
cursor = file.cursor()


class user():
    def __init__(self, websocket):
        self.loginDone = False
        self.msg = None
        self.websocket = websocket

    async def login(self):
        while True:
            self.msg = str(await self.websocket.recv())
            if self.msg[0:10] == '|challstr|':
                challstr = self.msg[10:]
                postlogin = requests.post('https://play.pokemonshowdown.com/~~showdown/action.php', data={'act':'login','name':username,'pass':password,'challstr':challstr})
                assertion = json.loads(postlogin.text[1:])["assertion"]
                await self.websocket.send(f'|/trn {username},0,{assertion}')
                await self.websocket.send(f"|/j {room}")
                self.loginDone = True
            if self.loginDone:
                await self.on_login()

    async def on_login(self):
        msgSplited = self.msg.split("|")
        if len(msgSplited) >= 4:
            if msgSplited[1] == "pm":
                content = msgSplited[4]
                

    def wait(self):
        asyncio.run(self.timeLimit())
    
    async def timeLimit(self):
        await self.websocket.send(f"{room}|/wall ACABOU O TEMPO")