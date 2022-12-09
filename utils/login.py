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
        self.questionsRoom = {}
        self.commands = commands().commands

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
        if len(msgSplited) >= 4:
            if msgSplited[1] == "pm":
                rank = msgSplited[2][0]
                sender = name_to_id(msgSplited[2])
                content = msgSplited[4]
                if content[0] == prefix:
                    command = content.split(" ")[0].strip()[1:]
                    commandParams = content.replace(f"{prefix}{command}", "").strip().split(",")
                    if command in self.commands:
                        if self.commands[command]['perm'] == 'host':
                            if sender not in self.questions:
                                question: commands = commands(self.websocket, file, cursor, sender)
                                self.questions[sender] = question
                            self.questions[sender].splitAll(command, commandParams, sender)
                            if self.questions[sender].room and self.questions[sender].room not in self.questions:
                                self.questionsRoom[self.questions[sender].room] = self.questions[sender]
                        
                        elif self.commands[command]['perm'] == 'user':
                            room = name_to_id(commandParams[-1])
                            if room in self.questionsRoom:
                                self.questionsRoom[room].splitAll(command, commandParams, sender)
                        
                        elif self.commands[command]['perm'] == 'adm':
                            room = name_to_id(commandParams[-1])

                            if room not in rooms:
                                return await self.websocket.send(f"|/pm {self.sender}, O bot não está nessa room.")
                            
                            await self.websocket.send(f"|/query roominfo {room}")
                            response = str(await self.websocket.recv()).split("|")[3]['users']

                            users = ' ,'.join(response)
                            userRank = users.find(sender) - 1

                            if userRank in ranksAdm:
                                commandIns = commands(self.websocket, file, cursor)
                                commandIns.splitAll(command, commandParams, sender)

        for owner in self.questions.copy():
            question = self.questions[owner]
            if question.questionFinished:
                self.questions.pop(owner)
        
        for room in self.questionsRoom.copy():
            question = self.questionsRoom[room]
            if question.questionFinished:
                self.questionsRoom.pop(room)