import json
import requests
import logging
import sqlite3

from config import *
from utils.commands import *
from utils.redirecting import *


logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        )

db = sqlite3.connect("database.db", check_same_thread=False)
cursor = db.cursor()


class user():
    def __init__(self, websocket):
        self.loginDone = False
        self.msg = None
        self.websocket = websocket
        self.questions = {}
        self.questionsRoom = {}
        self.commands = allCommands
        self.aliases = allAliases

    async def login(self):
        while True:
            self.msg = str(await self.websocket.recv())
            if self.msg[0:10] == '|challstr|':
                challstr = self.msg[10:]
                postlogin = requests.post('https://play.pokemonshowdown.com/~~showdown/action.php', data={'act':'login','name':username,'pass':password,'challstr':challstr})
                assertion = json.loads(postlogin.text[1:])["assertion"]
                await self.websocket.send(f'|/trn {username},0,{assertion}')
                await self.websocket.send(f'|/avatar {avatar}')
                for room in rooms:
                    await self.websocket.send(f'|/join {room}')
                self.loginDone = True
            if self.loginDone:
                await self.on_login()

    async def on_login(self):
        msgSplited = self.msg.split("|")

        self.questions, self.questionsRoom = \
            await redirectingFunction(websocket=self.websocket, db=db, cursor=cursor,
        msgSplited=msgSplited, aliases=self.aliases, commands=self.commands,
        questions=self.questions, questionsRoom=self.questionsRoom) \
            .verify_command_type()

        for owner in self.questions.copy():
            question = self.questions[owner]
            if question.questionFinished:
                del self.questions[owner]

        for user in self.questionsRoom.copy():
            question = self.questionsRoom[user]
            if question.questionFinished:
                del self.questionsRoom[user]