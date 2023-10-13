import asyncio
import threading
import random

from showdown.utils import name_to_id

from config import username, prefix, rooms
from utils.responding import *
from playing.other import *

class gameCommands():
    def __init__(self,
                msgSplited = None,
                websocket=None, 
                db=None, 
                cursor=None,
                owner=''
                ):
        
        self.msgSplited = msgSplited
        self.websocket = websocket
        self.db = db
        self.cursor = cursor
        self.owner = owner
        self.currentQuestion = False
        self.questionFinished = False
        self.alternativesNumber = 0
        self.timer = 15
        self.alternatives = []
        self.commandParams = []
        self.fontColors = ["#008000", "#0000e6", "#cc0000", "#e0ae1b"]
        self.rooms = []
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
        self.senderID = ''
        self.answer = ''
        self.html = ''
        self.question = ''

        self.otherCommands = otherCommands(self.msgSplited, websocket, db, cursor)

        self.mq, self.cancelQ, self.add, self.defans, self.showQuestion, self.sendHTML, self.userAnswer = \
            lambda : call_command(self.makequestion()), lambda : call_command(self.cancel()), \
            lambda : call_command(self.addalternative()), lambda : call_command(self.defanswer()), \
            lambda : call_command(self.questionShow()), lambda : call_command(self.send()), \
            lambda: call_command(self.checkUserAnswer()), \

        self.commands = {
            'mq': {'func': self.mq, 'perm': 'host', 'type': 'pm'}, 'cancel': {'func': self.cancelQ, 'perm': 'host', 'type': 'pm'},
            'add': {'func': self.add, 'perm': 'host', 'type': 'pm'}, 'danswer': {'func': self.defans, 'perm': 'host', 'type': 'pm'},
            'showquestion': {'func': self.showQuestion, 'perm': 'host', 'type': 'pm'}, 'send': {'func': self.sendHTML, 'perm': 'host', 'type': 'both'}, 
            'respond': {'func': self.userAnswer, 'perm': 'user', 'type': 'pm'},
        }

    def splitAll(self, command, commandParams, sender, msgType):
        self.sender = sender
        self.senderID = name_to_id(self.sender)
        self.command = command
        self.commandParams = commandParams
        self.msgType = msgType
        self.commands[self.command]['func']()

    async def makequestion(self):
        if len(self.commandParams) < 2:
            self.questionFinished = True
            return respondPM(self.senderID, "Comando: .mq [pergunta], [sala]", self.websocket)

        self.room = name_to_id(self.commandParams[-1])
        
        if self.html:
            return respondPM(self.senderID, f"Cancele a questão com o comando {prefix}cancel para fazer outra.", self.websocket)

        self.roomLB = f"{self.room}lb"
        self.question = self.commandParams[0]

        self.html += f'<div class="infobox"><center><font size="4">{self.question}</font><br><br><table width="100%" frame="box" rules="all" cellpadding="10"><tbody>'

        self.cursor.execute(f"""SELECT timer FROM room WHERE roomNAME = "{self.room}"
        """)

        timer = self.cursor.fetchall()

        if timer:
            self.timer = timer[0][0]

        respondPM(self.senderID, f"Questão feita! Agora, para adicionar alternativas, digite {prefix}add (alternativa).", self.websocket)

        self.timeToFinish = threading.Timer(10 * 60, self.finishQuestion)
        self.timeToFinish.start()
    
    async def cancel(self):
        if not self.html:
            self.questionFinished = True
            return respondPM(self.senderID, "Nenhuma questão foi definida.", self.websocket)
        self.questionFinished = True
        return respondPM(self.senderID, "Questão cancelada.", self.websocket)

    async def addalternative(self):
        if len(self.commandParams) < 2:
            return respondPM(self.senderID, "Comando: .add [alternativa], [sala]", self.websocket)
        if not self.html:
            self.questionFinished = True
            return respondPM(self.senderID, "Nenhuma questão foi definida.", self.websocket)
        if self.alternativesNumber == 4:
            return respondPM(self.senderID, "Limite de alternativas atingido!", self.websocket)

        alternative = self.commandParams[0]
        color = random.choice(self.fontColors)
        if self.alternativesNumber % 2 == 0:
            self.html += f'<tr><td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.owner}" style=background-color:transparent;border:none;><font color="{color}" size="3"><b>{alternative}</b></font></button></center>'
        else:
            self.html += f'<td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.owner}" style=background-color:transparent;border:none;><font color="{color}" size="3"><b>{alternative}</b></font></button></center></tr>'
        self.fontColors.remove(color)
        self.alternativesNumber += 1
        self.alternatives.append(alternative)

        respondPM(self.senderID, f"Alternativa feita! Se quiser colocar alguma alternativa como a correta, digite {prefix}danswer (alternativa).", self.websocket)

    async def defanswer(self):
        if len(self.commandParams) < 2:
            return respondPM(self.senderID, "Comando: .danswer [alternativa], [sala]", self.websocket)
        alternative = self.commandParams[0]
        if alternative in self.alternatives:
            self.answer = alternative
            respondPM(self.senderID, f"A alternativa {alternative} foi configurada como a correta.", self.websocket)

        elif not self.html:
            return respondPM(self.senderID, "Nenhuma questão foi definida.", self.websocket)

        elif alternative not in self.alternatives:
            return respondPM(self.senderID, "A alternativa indicada não foi definida.", self.websocket)

    async def questionShow(self):
        if len(self.commandParams) < 1:
            return respondPM(self.senderID, "Comando: .question [sala]", self.websocket)
        if not self.html:
            self.questionFinished = True
            return respondPM(self.senderID, "Nenhuma questão foi definida.", self.websocket)

        code = f"A questão está assim:\nQuestão: {self.question}\nAlternativas: {', '.join(self.alternatives)}\nAlternativa correta: {self.answer}"

        respondPM(self.senderID, f"!code {code}", self.websocket)

    async def send(self):
        if len(self.commandParams) < 1 and self.msgType == 'pm':
            return respondPM(self.senderID, "Comando: .send [sala]", self.websocket)
        if not self.html:
            return respond(self.msgType, "Nenhuma questão foi definida.", self.websocket, self.senderID, self.room)
        self.html += "</tbody></table></center></div>"
        respondRoom(f"/addhtmlbox {self.html}", self.websocket, self.room)
        self.currentQuestion = True
        timer = threading.Timer(self.timer, lambda: asyncio.run(self.timeLimit()))
        timer.start()

    async def checkUserAnswer(self):
        points = 0
        if self.currentQuestion:
            if len(self.commandParams) >= 2:
                self.usersAnswered.append(self.senderID)
                answer = name_to_id(self.commandParams[0])
                if answer == name_to_id(self.answer):
                    points += 1
                    self.otherCommands.room = self.room
                    self.otherCommands.command = ''
                    self.otherCommands.sender = self.sender
                    self.otherCommands.senderID = self.senderID
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
        respondRoom(f"/wall ACABOU O TEMPO!", self.websocket, self.room)
        await self.postQuestion()

    async def postQuestion(self):
        self.msgType = 'room'
        threads = []
        threads.append(threading.Timer(5, respondRoom, args=["E a resposta era...", self.websocket, self.room]))
        threads.append(threading.Timer(10, respondRoom, args=[f"/wall {self.answer}!", self.websocket, self.room]))
        threads.append(threading.Timer(20, respondRoom, args=[f"Pontuadores: {', '.join(self.usersPointers)}", self.websocket, self.room]))
        threads.append(threading.Timer(30, self.otherCommands.splitAll, args=["lb", "", "", "room"]))
        for thread in threads:
            thread.start()

    def finishQuestion(self):
        self.questionFinished = True
        respondPM(self.owner, "Acabou o prazo para formalizar a questão.", self.websocket)