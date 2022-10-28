import json
import requests
import logging
import sqlite3
from config import *
from utils.commands import *
from showdown.utils import name_to_id

logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        )

file = sqlite3.connect("leaderboard.db", check_same_thread=False)
cursor = file.cursor()


class user():
    def __init__(self, websocket):
        self.loginDone = False
        self.msg = None
        self.websocket = websocket
        self.questions = {}

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
                sender = name_to_id(msgSplited[2])
                content = msgSplited[4]
                if content[0] == prefix:
                    if sender not in self.questions:
                        question: commands = commands(sender, self.websocket, file, cursor)
                        self.questions[sender] = question
                        self.questions[sender].owner = sender
                    self.questions[sender].splitAll(content)
        
        for owner in self.questions.copy():
            question = self.questions[owner]
            if question.questionFinished:
                self.questions.pop(owner)