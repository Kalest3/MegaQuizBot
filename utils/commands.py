import asyncio
import threading

from showdown.utils import name_to_id
from config import username, prefix, rooms, trusted

class commands():
    def __init__(self, websocket=None, db=None, cursor=None, owner='', msgType=''):
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
        self.usersAnswered = []
        self.usersPointers = {}
        self.aliases = {
            'mq': 'makequestion'
        }
        self.room = ''
        self.roomLB = ''
        self.sender = ''
        self.answer = ''
        self.html = ''

        self.mq, self.cancelQ, self.add, self.defans, self.sendHTML, self.userAnswer, self.lb, self.addpoint, self.clearpoint, self.deftimer = \
            lambda : asyncio.create_task(self.makequestion()), lambda : asyncio.create_task(self.cancel()), \
            lambda : asyncio.create_task(self.addalternative()), lambda : asyncio.create_task(self.defanswer()), \
            lambda : asyncio.create_task(self.send()), lambda: asyncio.create_task(self.checkUserAnswer()), \
            lambda : asyncio.create_task(self.leaderboard()), lambda : asyncio.create_task(self.addpoints()), \
            lambda : asyncio.create_task(self.clearpoints()), lambda : asyncio.create_task(self.defTimer())


        self.commands = {
            'mq': {'func': self.mq, 'perm': 'host', 'type': 'pm'}, 'cancel': {'func': self.cancelQ, 'perm': 'host', 'type': 'pm'},
            'add': {'func': self.add, 'perm': 'host', 'type': 'pm'}, 
            'danswer': {'func': self.defans, 'perm': 'host', 'type': 'pm'}, 'send': {'func': self.sendHTML, 'perm': 'host', 'type': 'both'},
            'respond': {'func': self.userAnswer, 'perm': 'user', 'type': 'pm'}, 'deftimer': {'func': self.deftimer, 'perm': 'adm', 'type': 'both'}, 
            'lb': {'func': self.lb, 'perm': 'general', 'type': 'both'}, 'addpoints': {'func': self.addpoint, 'perm': 'adm', 'type': 'both'}, 
            'clearpoints': {'func': self.clearpoint, 'perm': 'adm', 'type': 'pm'},
        }

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
        question = self.commandParams[0]

        self.html += f'<div class="infobox"><center><font size="4">{question}</font><br><br><table width="100%" frame="box" rules="all" cellpadding="10"><tbody>'

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS rooms (
            roomID TEXT PRIMARY KEY,
            timer FLOAT)""")

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.roomLB} (
            user TEXT PRIMARY KEY,
            points INTEGER)""")
        
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

        alternative = self.commandParams[0]
        if self.alternativesNumber % 2 == 0:
            self.html += f'<tr><td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.room}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{alternative}</b></font></button></center>'
        else:
            self.html += f'<td style="width: 50.00%"><center><button name="send" value="/w {username},{prefix}respond {alternative}, {self.room}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{alternative}</b></font></button></center></tr>'
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

    async def send(self):
        if not self.html:
            return self.respond("Nenhuma questão foi definida.", self.sender)

        self.html += "</tbody></table></center></div>"
        self.respondRoom(f"/addhtmlbox {self.html}")
        self.currentQuestion = True
        timer = threading.Timer(self.timer, lambda: asyncio.run(self.timeLimit()))
        timer.start()

    async def checkUserAnswer(self):
        if self.currentQuestion:
            if len(self.commandParams) >= 2:
                self.usersAnswered.append(self.sender)
                answer = name_to_id(self.commandParams[0])
                if answer == name_to_id(self.answer):
                    await self.addpoints(1)
                    if self.sender not in self.usersPointers:
                        self.usersPointers[self.sender] = 1
                    else:
                        self.usersPointers[self.sender] += 1

    async def timeLimit(self):
        self.currentQuestion = False
        self.questionFinished = True
        self.timeToFinish.cancel()
        self.respondRoom(f"/wall ACABOU O TEMPO!")
        await self.postQuestion()
        self.questionFinished = True

    async def postQuestion(self):
        threads = []
        threads.append(threading.Timer(5, self.respondRoom, args=["E a resposta era..."]))
        threads.append(threading.Timer(10, self.respondRoom, args=[f"/wall {self.answer}!"]))
        threads.append(threading.Timer(20, self.respondRoom, args=[f"Pontuadores: {self.usersPointers}"]))
        threads.append(threading.Timer(30, lambda: asyncio.run(self.leaderboard())))
        for thread in threads:
            thread.start()

    async def defTimer(self):
        time = self.commandParams[0]
        roomID = name_to_id(self.commandParams[-1])
        if time.isdigit():
            self.timer = float(time)
            self.cursor.execute(f"""
            SELECT roomID FROM rooms WHERE roomID = "{roomID}"
            """)

            room = self.cursor.fetchall()

            if room:
                self.cursor.execute(f"""UPDATE rooms SET timer = "{self.timer}" WHERE roomID = "{roomID, self.timer}"
                """)
            else:
                self.cursor.execute(f"""INSERT INTO rooms (roomID, timer) VALUES (?,?)""", (roomID, self.timer))

            self.db.commit()

            self.respond(f"O tempo foi alterado para {time} segundos!", self.sender)
        else:
            self.respond("Digite um tempo válido!", self.sender)
    
    async def addpoints(self, newPoints):
        
        self.cursor.execute(f"""
        SELECT user FROM {self.roomLB} WHERE user = "{self.sender}"
        """)

        user = self.cursor.fetchall()

        if user:
            self.cursor.execute(f"""SELECT points FROM {self.roomLB} WHERE user = "{user[0][0]}"
            """)
            points = self.cursor.fetchall()[0][0] + newPoints
            self.cursor.execute(f"""UPDATE {self.roomLB} SET points = "{points}" WHERE user = {user}""")
        else:
            self.cursor.execute(f"""INSERT INTO {self.roomLB} (user, points) VALUES (?,?)""", (self.sender, newPoints))

        self.db.commit()

    async def clearpoints(self):
        room = name_to_id(self.commandParams[0])
        if room not in rooms:
            self.respondPM(self.sender, "Sala não presente dentre as que o bot está.")
        roomLB = f"{room}lb"
        self.cursor.execute(f"""DELETE FROM {roomLB}""")
        self.db.commit()
        self.respondPM(self.sender, "Pontos da sala limpos!")
    
    async def leaderboard(self):
        if not self.room:
            self.room = name_to_id(self.commandParams[-1])
            self.roomLB = f"{self.room}lb"
        self.cursor.execute(f"""SELECT * FROM "{self.roomLB}"
        """)
        lb = ''
        for data in self.cursor.fetchall():
            user = data[0]
            points = data[1]
            lb += f"{user}: {points}\n"
        self.respondRoom(f"!code Leaderboard:\n{lb}")
    
    def finishQuestion(self):
        self.questionFinished = True
        self.respondPM(self.owner, "Acabou o prazo para formalizar a questão.")