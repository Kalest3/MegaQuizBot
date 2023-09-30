import json

from config  import *
from utils.commands import *
from playing.game import *
from playing.other import *

from showdown.utils import name_to_id

class redirectingFunction():
    def __init__(self, **kwargs) -> None:
        self.websocket = kwargs['websocket']
        self.db = kwargs['db']
        self.cursor = kwargs['cursor']

        self.msgSplited = kwargs['msgSplited']
        self.aliases = kwargs['aliases']
        self.commands = kwargs['commands']

        self.questions = kwargs['questions']
        self.questionsRoom = kwargs['questionsRoom']

    async def verify_command_type(self):
        if len(self.msgSplited) >= 4:
            if self.msgSplited[1] == "pm":
                senderID = name_to_id(self.msgSplited[2])
                content = self.msgSplited[4]
                msgType = 'pm'
            elif self.msgSplited[1] == "c:":
                senderID = name_to_id(self.msgSplited[3])
                content = self.msgSplited[4]
                msgType = 'room'
            else:
                return self.return_question()
        else:
            return self.return_question()

        if msgType == 'room':
            room = self.msgSplited[0]
            if not room:
                room = 'lobby'
            else:
                room = room[1:]

        if content[0] == prefix:
            command = content.split(" ")[0].strip()[1:]
            commandParams = content.replace(f"{prefix}{command}", "").strip().split(",")
            if command in self.aliases:
                command = self.aliases[command]
            if command in self.commands:
                if msgType == 'pm':
                    room = name_to_id(commandParams[-1])
                if self.commands[command]['type'] == 'pm' and msgType == 'room':
                    await self.websocket.send(f"|/pm {senderID}, Este comando deve ser executado somente por PM.")
                    return self.return_question()
                
                if self.commands[command]['perm'] == 'owner':
                    if senderID != owner:
                        await self.websocket.send(f"|/pm {senderID}, Você não tem permissão para executar esse comando.")
                        return self.return_question()

                    commandIns = otherCommands(self.msgSplited, self.websocket, self.db, self.cursor)
                    commandIns.splitAll(command, commandParams, senderID, msgType)

                if self.commands[command]['perm'] == 'host':
                    if await self.verify_perm(room, senderID) and senderID not in self.questions:
                        question: gameCommands = gameCommands(self.msgSplited, self.websocket, self.db, self.cursor, senderID)
                        self.questions[senderID] = question
                    if senderID not in self.questions:
                        await self.websocket.send(f"|/pm {senderID}, Você não tem permissão para executar este comando.")
                        return self.return_question()

                    self.questions[senderID].splitAll(command, commandParams, senderID, msgType)

                elif self.commands[command]['perm'] == 'user':
                    hoster = name_to_id(commandParams[-1])
                    if hoster in self.questions:
                        self.questions[hoster].splitAll(command, commandParams, senderID, msgType)

                elif self.commands[command]['perm'] == 'adm':
                    if room not in rooms:
                        await self.websocket.send(f"|/pm {senderID}, O bot não está nessa room.")
                    else:                    
                        if await self.verify_perm(room, senderID):
                            commandIns = otherCommands(self.msgSplited, self.websocket, self.db, self.cursor)
                            commandIns.splitAll(command, commandParams, senderID, msgType)
                        else:
                            await self.websocket.send(f"|/pm {senderID}, Você não tem permissão para usar este comando.")

                elif self.commands[command]['perm'] == 'general':
                    if msgType == 'pm':
                        room = name_to_id(commandParams[-1])
                        if room in rooms:
                            commandIns = otherCommands(self.msgSplited, self.websocket, self.db, self.cursor)
                            commandIns.splitAll(command, commandParams, senderID, msgType)
                        else:
                            await self.websocket.send(f"|/pm {senderID}, O bot não está nessa room.")
                    else:
                        if await self.verify_perm(room, senderID):
                            commandIns = otherCommands(self.msgSplited, self.websocket, self.db, self.cursor)
                            commandIns.splitAll(command, commandParams, senderID, msgType)
                        else:
                            await self.websocket.send(f"|/pm {senderID}, Você não tem permissão para usar este comando.")

        return self.return_question()

    async def verify_perm(self, room, senderID):
        if room in rooms:
            await self.websocket.send(f"|/query roominfo {room}")
            response = list((json.loads(str(await self.websocket.recv()).split("|")[3])['auth'].values()))

            substringSender = [f'{senderID}']

            if substringSender not in response:
                return
            else:
                return True
        return

    def return_question(self):
        return self.questions, self.questionsRoom