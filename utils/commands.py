import asyncio
import threading

from showdown.utils import name_to_id
from config import username, prefix

class commands():
    def __init__(self, sender, websocket, db, cursor):
        self.websocket = websocket
        self.sender = sender
        self.db = db
        self.cursor = cursor
        self.currentQuestion = False
        self.questionFinished = False
        self.alternativesNumber = 0
        self.timer = 15
        self.alternatives = []
        self.commandParams = []
        self.room = ''
        self.answer = ''
        self.html = ''
        self.content = ''


        self.commands = {
            'mq': self.makequestion, 'makequestion': self.makequestion, 'makeq': self.makequestion,
            'add': self.addalternative, 'danswer': self.defanswer, 'send': lambda : asyncio.gather(self.send()),
            'respond': self.checkUserAnswer, 'deftimer': self.defTimer, 'lb': lambda : asyncio.gather(self.leaderboard())
        }
    
    def splitAll(self, content):
        self.content = content
        self.command = self.content.split(" ")[0].strip()
        self.commandParams = self.content.replace(self.command, "").strip().split(",")
        if self.command in self.commands:
            self.commands[self.command]()

    async def makequestion(self):
        self.room = self.commandParams[-1].strip()
        question = self.commandParams[0]
        self.html += f'<div class="infobox"><center><font size="4">{question}</font><br><br><table width="100%" frame="box" rules="all" cellpadding="10"><tbody>'

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.room} (
            user TEXT PRIMARY KEY,
            points INTEGER)""")
        
        await self.websocket.send(f"|/pm {self.sender}, Questão feita! Agora, para adicionar alternativas, digite {prefix}add (alternativa).")

    async def addalternative(self):
        alternative = self.commandParams[0]
        if self.alternativesNumber % 2 == 0:
            self.html += f'<tr><td style="width: 50.00%"><center><button name="send" value="/w {username},respond {alternative}, {self.room}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{alternative}</b></font></button></center>'
        else:
            self.html += f'<td style="width: 50.00%"><center><button name="send" value="/w {username},respond {alternative}, {self.room}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{alternative}</b></font></button></center></tr>'
        self.alternativesNumber += 1
        self.alternatives.append(alternative)

        await self.websocket.send(f"|/pm {self.sender}, Alternativa feita! Se quiser colocar alguma alternativa como a correta, digite {prefix}danswer (alternativa).")

    async def defanswer(self):
        alternative = self.commandParams[0]
        if alternative in self.alternatives:
            self.answer = alternative
        
        await self.websocket.send(f"|/pm {self.sender}, A alternativa {alternative} foi configurada como a correta.")

    async def send(self):
        self.html += "</tbody></table></center></div>"
        await self.websocket.send(f"{self.room}|/addhtmlbox {self.html}")
        self.currentQuestion = True
        timer = threading.Timer(self.timer, self.timeLimit)
        timer.start()

    def checkUserAnswer(self):
        if self.currentQuestion:
            answer, room = name_to_id(self.commandParams[0]), name_to_id(self.commandParams[1])
            if answer == name_to_id(self.answer) and room == self.room:
                self.addpoints(1)

    async def leaderboard(self):
        self.cursor.execute(f"SELECT * FROM {self.room}")
        lb = ''
        for data in self.cursor.fetchall():
            user = data[0]
            points = data[1]
            lb += f"{user}: {points}\n"
        await self.websocket.send(f"{self.room}|!code {lb}")

    def addpoints(self, newPoints):
        self.cursor.execute(f"""
        SELECT user FROM {self.room} WHERE user = "{self.sender}";
        """)

        user = self.cursor.fetchall()

        if user:
            points = self.cursor.execute("SELECT points FROM (?) WHERE user = (?)", (self.room, user))
            self.cursor.execute("""UPDATE (?) SET points = (?) WHERE user = (?)""", (self.room, newPoints + points, self.user,))
        else:
            self.cursor.execute(f"""INSERT INTO {self.room} (user, points) VALUES (?,?)""", (self.sender, newPoints))

        self.db.commit()

    def clearpoints(self):
        self.cursor.execute("DELETE * FROM (?)", (self.room,))
    
    async def postRound(self):
        

    def timeLimit(self):
        self.currentQuestion = False
        self.questionFinished = True

    def defTimer(self):
        time = self.commandParams[0]
        self.timer = time