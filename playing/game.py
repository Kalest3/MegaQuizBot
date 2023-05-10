import asyncio
import threading
import random

from showdown.utils import name_to_id

from config import username, prefix, rooms, trusted
from playing.other import *

class gameCommands():
    def __init__(self,
                msgSplited = None,
                websocket=None, 
                db=None, 
                cursor=None,
                owner='', 
                msgType=''):
        
        self.msgSplited = msgSplited
        self.websocket = websocket
        self.db = db
        self.cursor = cursor
        self.owner = owner
        self.msgType = msgType
        self.currentQuestion = False
        self.questionFinished = False
        self.alternativesNumber = 0
        self.timer = 15
        self.alternatives = []
        self.commandParams = []
        self.fontColors = ["#008000", "#0000e6", "#cc0000", "#e0ae1b"]
        self.usersAnswered = []
        self.usersPointers = {}
        self.aliases = {
            "makequestion": "mq",
            "cancelquestion": "cancel",
            "answer": "danswer",
            "question": "showquestion",
            "leaderboard": "lb",
        }
        self.room = ''
        self.roomLB = ''
        self.sender = ''
        self.answer = ''
        self.html = ''
        self.question = ''

        self.otherCommands = otherCommands(self.msgSplited, websocket, db, cursor, 'room')

        self.mq, self.cancelQ, self.add, self.defans, self.showQuestion, self.sendHTML, self.userAnswer = \
            lambda : self.call_command(self.makequestion()), lambda : self.call_command(self.cancel()), \
            lambda : self.call_command(self.addalternative()), lambda : self.call_command(self.defanswer()), \
            lambda : self.call_command(self.questionShow()), lambda : self.call_command(self.send()), \
            lambda: self.call_command(self.checkUserAnswer()), \

        self.commands = {
            'mq': {'func': self.mq, 'perm': 'host', 'type': 'pm'}, 'cancel': {'func': self.cancelQ, 'perm': 'host', 'type': 'pm'},
            'add': {'func': self.add, 'perm': 'host', 'type': 'pm'}, 'danswer': {'func': self.defans, 'perm': 'host', 'type': 'pm'},
            'showquestion': {'func': self.showQuestion, 'perm': 'host', 'type': 'pm'},
            'send': {'func': self.sendHTML, 'perm': 'host', 'type': 'both'}, 'respond': {'func': self.userAnswer, 'perm': 'user', 'type': 'pm'},
        }

    def call_command(self, command):
        try:
            loop = asyncio.get_event_loop().is_running()
        except RuntimeError:
            return asyncio.run(command)
        return asyncio.gather(command)

    def splitAll(self, command, commandParams, sender):
        self.sender = sender
        self.command = command
        self.commandParams = commandParams
        self.commands[self.command]['func']()

    def respondRoom(self, message):
        try:
            loop = asyncio.get_event_loop().is_running()
        except RuntimeError:
            return asyncio.run(self.websocket.send(f"{self.room}|{message}"))
        return asyncio.gather(self.websocket.send(f"{self.room}|{message}"))

    def respondPM(self, user, message):
        try:
            loop = asyncio.get_event_loop().is_running()
        except RuntimeError:
            return asyncio.run(self.websocket.send(f"|/pm {user}, {message}"))
        return asyncio.gather(self.websocket.send(f"|/pm {user}, {message}"))
    
    def respond(self, msg, user=None):
        if self.msgType == 'pm':
            self.respondPM(user, msg)
        elif self.msgType == 'room':
            self.respondRoom(msg)

    async def makequestion(self):
        if self.sender not in trusted:
            self.questionFinished = True
            return self.respondPM(self.sender, "Você não tem permissão para executar este comando.")
        if len(self.commandParams) < 2:
            self.questionFinished = True
            return self.respondPM(self.sender, "Comando: .mq [pergunta], [room]")

        self.room = name_to_id(self.commandParams[-1])

        if self.room not in rooms:
            self.questionFinished = True
            return self.respondPM(self.sender, "Room não presente dentre as que o bot está.")
        
        if self.html:
            return self.respondPM(self.sender, f"Cancele a questão com o comando {prefix}cancel para fazer outra.")

        self.roomLB = f"{self.room}lb"
        self.question = self.commandParams[0]

        self.html += f'<div class="infobox"><center><font size="4">{self.question}</font><br><br><table width="100%" frame="box" rules="all" cellpadding="10"><tbody>'

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS rooms (
            roomID TEXT PRIMARY KEY,
            timer FLOAT)""")

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.roomLB} (
            user TEXT PRIMARY KEY,
            points FLOAT)""")
        
        self.cursor.execute(f"""SELECT timer FROM rooms WHERE roomID = "{self.room}"
        """)

        timer = self.cursor.fetchall()

        if timer:
            self.timer = timer[0][0]

        self.respondPM(self.sender, f"Questão feita! Agora, para adicionar alternativas, digite {prefix}add (alternativa).")

        self.timeToFinish = threading.Timer(10 * 60, self.finishQuestion)
        self.timeToFinish.start()
    
    async def cancel(self):
        self.questionFinished = True
        return self.respondPM(self.sender, "Questão cancelada.")

    async def addalternative(self):
        if not self.html:
            self.questionFinished = True
            return self.respondPM(self.sender, "Nenhuma questão foi definida.")
        if self.alternativesNumber == 4:
            return self.respondPM(self.sender, "Limite de alternativas atingido!")

        alternative = self.commandParams[0]
        color = random.choice(self.fontColors)
        if self.alternativesNumber % 2 == 0:
            self.html += f'<tr><td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.owner}" style=background-color:transparent;border:none;><font color="{color}" size="3"><b>{alternative}</b></font></button></center>'
        else:
            self.html += f'<td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.owner}" style=background-color:transparent;border:none;><font color="{color}" size="3"><b>{alternative}</b></font></button></center></tr>'
        self.fontColors.remove(color)
        self.alternativesNumber += 1
        self.alternatives.append(alternative)

        self.respondPM(self.sender, f"Alternativa feita! Se quiser colocar alguma alternativa como a correta, digite {prefix}danswer (alternativa).")

    async def defanswer(self):
        alternative = self.commandParams[0]
        if alternative in self.alternatives:
            self.answer = alternative
            self.respondPM(self.sender, f"A alternativa {alternative} foi configurada como a correta.")

        elif not self.html:
            return self.respondPM(self.sender, "Nenhuma questão foi definida.")

        elif alternative not in self.alternatives:
            return self.respondPM(self.sender, "A alternativa indicada não foi definida.")

    async def questionShow(self):
        if not self.html:
            self.questionFinished = True
            return self.respondPM(self.sender, "Nenhuma questão foi definida.")

        code = f"A questão está assim:\nQuestão: {self.question}\nAlternativas: {', '.join(self.alternatives)}\nAlternativa correta: {self.answer}"

        self.respondPM(self.sender, f"!code {code}")

    async def send(self):
        if not self.html:
            return self.respond("Nenhuma questão foi definida.", self.sender)
        self.html += "</tbody></table></center></div>"
        self.respondRoom(f"/addhtmlbox {self.html}")
        self.currentQuestion = True
        timer = threading.Timer(self.timer, lambda: asyncio.run(self.timeLimit()))
        timer.start()

    async def checkUserAnswer(self):
        points = 0
        if self.currentQuestion:
            if len(self.commandParams) >= 2:
                self.usersAnswered.append(self.sender)
                answer = name_to_id(self.commandParams[0])
                if answer == name_to_id(self.answer):
                    points += 1
                    self.otherCommands.command = ''
                    self.otherCommands.sender = self.sender
                    self.otherCommands.commandParams = [self.sender,points,self.room]
                    await self.otherCommands.addpoints()
                    if self.sender not in self.usersPointers:
                        self.usersPointers[self.sender] = points
                    else:
                        self.usersPointers[self.sender] += points

    async def timeLimit(self):
        self.currentQuestion = False
        self.questionFinished = True
        self.timeToFinish.cancel()
        self.respondRoom(f"/wall ACABOU O TEMPO!")
        await self.postQuestion()
        self.questionFinished = True

    async def postQuestion(self):
        self.msgType = 'room'
        threads = []
        threads.append(threading.Timer(5, self.respondRoom, args=["E a resposta era..."]))
        threads.append(threading.Timer(10, self.respondRoom, args=[f"/wall {self.answer}!"]))
        threads.append(threading.Timer(20, self.respondRoom, args=[f"Pontuadores: {', '.join(self.usersPointers)}"]))
        threads.append(threading.Timer(30, self.otherCommands.splitAll, args=["lb", "", ""]))
        for thread in threads:
            thread.start()

    def finishQuestion(self):
        self.questionFinished = True
        self.respondPM(self.owner, "Acabou o prazo para formalizar a questão.")