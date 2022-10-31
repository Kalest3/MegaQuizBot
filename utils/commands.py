import asyncio
import threading

from showdown.utils import name_to_id
from config import username, prefix, rooms, trusted

class commands():
    def __init__(self, sender, websocket, db, cursor, owner):
        self.websocket = websocket
        self.sender = sender
        self.db = db
        self.cursor = cursor
        self.owner = owner
        self.currentQuestion = False
        self.questionFinished = False
        self.alternativesNumber = 0
        self.timer = 15
        self.alternatives = []
        self.commandParams = []
        self.usersPointers = {}
        self.room = ''
        self.roomLB = ''
        self.answer = ''
        self.html = ''
        self.content = ''

        mq, add, defanswer, send, respond, lb, addpoints, clearpoints, deftimer = lambda : asyncio.create_task(self.makequestion()), \
            lambda : asyncio.create_task(self.addalternative()), lambda : asyncio.create_task(self.defanswer()), \
            lambda : asyncio.create_task(self.send()), lambda: asyncio.create_task(self.checkUserAnswer()), \
            lambda : asyncio.create_task(self.leaderboard()), lambda : asyncio.create_task(self.addpoints()), \
            lambda : asyncio.create_task(self.clearpoints()), lambda : asyncio.create_task(self.defTimer())

        self.commands = {
            'mq': mq, 'makequestion': mq, 'makeq': mq,
            'add': add, 'danswer': defanswer, 'send': send,
            'respond': respond, 'deftimer': deftimer, 'lb': lb,
            'addpoints': addpoints, 'clearpoints': clearpoints,
        }

        timeToFinish = threading.Timer(10 *  60, self.finishQuestion)
        timeToFinish.start()
    
    def splitAll(self, content):
        self.content = content
        self.command = self.content.split(" ")[0].strip()[1:]
        self.commandParams = self.content.replace(f"{prefix}{self.command}", "").strip().split(",")
        if self.command in self.commands:
            self.commands[self.command]()

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

    async def makequestion(self):
        if self.sender not in trusted:
            self.questionFinished = True
            return self.respondPM(self.sender, "Você não tem permissão para executar este comando.")
        self.room = name_to_id(self.commandParams[-1])

        if self.room not in rooms:
            self.questionFinished = True
            return self.respondPM(self.sender, "Room não presente dentre as que o bot está.")

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

    async def addalternative(self):
        if not self.html:
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
        self.html += "</tbody></table></center></div>"
        self.respondRoom(f"/addhtmlbox {self.html}")
        self.currentQuestion = True
        timer = threading.Timer(self.timer, lambda: asyncio.run(self.timeLimit()))
        timer.start()

    async def checkUserAnswer(self):
        if self.currentQuestion:
            if len(self.commandParams) >= 2:
                answer, room = name_to_id(self.commandParams[0]), name_to_id(self.commandParams[1])
                if answer == name_to_id(self.answer) and room == self.room:
                    await self.addpoints(1)
                    if self.sender not in self.usersPointers:
                        self.usersPointers[self.sender] = 1
                    else:
                        self.usersPointers[self.sender] += 1


    async def timeLimit(self):
        self.currentQuestion = False
        self.questionFinished = True
        self.respondRoom(f"/wall ACABOU O TEMPO!")
        await self.postQuestion()

    async def postQuestion(self):
        threads = []
        threads.append(threading.Timer(5, self.respondRoom, args=["E a resposta era..."]))
        threads.append(threading.Timer(10, self.respondRoom, args=[f"{self.answer}!"]))
        threads.append(threading.Timer(20, self.respondRoom, args=[f"Pontuadores: {self.usersPointers}"]))
        threads.append(threading.Timer(30, lambda: asyncio.run(self.leaderboard())))
        for thread in threads:
            thread.start()

    async def defTimer(self):
        time: str = self.commandParams[0]
        if time.isdigit():
            self.timer = time
            self.cursor.execute(f"""
            SELECT roomID FROM rooms WHERE roomID = {self.room};
            """)

            room = self.cursor.fetchall()

            if room:
                self.cursor.execute("""UPDATE rooms SET timer = (?) WHERE roomID = (?)""", (self.timer, self.room,))
            else:
                self.cursor.execute(f"""INSERT INTO rooms (roomID, timer) VALUES (?,?)""", (self.room, self.timer))

            self.db.commit()

            self.respondPM(self.sender, f"O tempo foi alterado para {time} segundos!")
        else:
            self.respondPM(self.sender, "Digite um tempo válido!")
    
    async def addpoints(self, newPoints):
        self.cursor.execute(f"""
        SELECT user FROM {self.roomLB} WHERE user = "{self.sender}";
        """)

        user = self.cursor.fetchall()

        if user:
            points = self.cursor.execute(f"""SELECT points FROM {self.roomLB} WHERE user = "{user}"
            """)
            self.cursor.execute(f"""UPDATE {self.roomLB} SET points = {newPoints + points} WHERE user = {user}""")
        else:
            self.cursor.execute(f"""INSERT INTO {self.roomLB} (user, points) VALUES (?,?)""", (self.sender, newPoints))

        self.db.commit()

    async def clearpoints(self):
        self.room = name_to_id(self.commandParams[0])
        self.cursor.execute("DELETE * FROM (?)", (self.room))
        self.respondPM(self.sender, "Pontos da sala limpos!")
    
    async def leaderboard(self):
        self.cursor.execute(f"SELECT * FROM {self.roomLB}")
        lb = ''
        for data in self.cursor.fetchall():
            user = data[0]
            points = data[1]
            lb += f"{user}: {points}\n"
        self.respondRoom(f"!code Leaderboard:\n{lb}")
    
    def finishQuestion(self):
        self.questionFinished = True
        self.respondPM(self.owner, "Acabou o prazo para formalizar a questão.")