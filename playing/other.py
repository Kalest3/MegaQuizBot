from showdown.utils import name_to_id

from config import prefix, rooms
from utils.responding import *

class otherCommands():
    def __init__(self,
                msgSplited='',
                websocket=None, 
                db=None, 
                cursor=None
                ):

        self.msgSplited = msgSplited
        self.websocket = websocket
        self.db = db
        self.cursor = cursor
        self.command = ''
        self.commandParams = []
        self.aliases = {
            "addp": "addpoints",
            "rpoint": "rpoints",
            "removepoints": "rpoints",
            "clear": "clearpoints",
            "settimer": "deftimer",
            "timer": "deftimer",
            "dtimer": "deftimer",
        }

        self.room = ''
        self.sender = ''

        self.lb, self.addpoint, self.rempoint, self.clearpoint, self.deftimer = \
            lambda : call_command(self.leaderboard()), lambda : call_command(self.addpoints()), \
            lambda: call_command(self.rempoints()), lambda : call_command(self.clearpoints()), \
            lambda : call_command(self.defTimer())


        self.commands = {
            'deftimer': {'func': self.deftimer, 'perm': 'adm', 'type': 'both'}, 'lb': {'func': self.lb, 'perm': 'general', 'type': 'both'}, 
            'addpoints': {'func': self.addpoint, 'perm': 'adm', 'type': 'both'}, 'rpoints': {'func': self.rempoint, 'perm': 'adm', 'type': 'both'}, 
            'clearpoints': {'func': self.clearpoint, 'perm': 'adm', 'type': 'both'},
        }
    
    def splitAll(self, command, commandParams, sender, msgType):
        self.sender = sender
        self.command = command
        self.commandParams = commandParams
        self.msgType = msgType

        if not self.checkRoom():
            return
        self.commands[self.command]['func']()

    async def defTimer(self):
        if len(self.commandParams) < 1:
            return respond(self.msgType, f"Uso do comando: {prefix}deftimer [segundos], [sala]", self.websocket, self.sender, self.room)
        time = self.commandParams[0]
        if time.isdigit():
            self.timer = float(time)
            self.cursor.execute(f"""
            SELECT roomNAME FROM room WHERE roomNAME = "{self.room}"
            """)

            room = self.cursor.fetchall()

            if room:
                self.cursor.execute(f"""UPDATE room SET timer = "{self.timer}" WHERE roomNAME = "{self.room}"
                """)
            else:
                respondPM(self.sender, "Sala não presente dentre as que o bot está.", self.websocket)

            self.db.commit()

            respond(self.msgType, f"O tempo foi alterado para {time} segundos!", self.websocket, self.sender, self.room)
        else:
            respond(self.msgType, "Digite um tempo válido!", self.websocket, self.sender, self.room)
    
    async def addpoints(self, newPoints=1):
        if self.command == "addpoints":
            if len(self.commandParams) < 2:
                return respond(self.msgType, f"Uso do comando: {prefix}addpoints [usuario], [pontos], [sala]", self.websocket, self.sender, self.room)
            user = name_to_id(self.commandParams[0])
            newPoints = self.commandParams[1]
            try:
                newPoints = float(newPoints)
            except:
                return respond(self.msgType, f"Uso do comando: {prefix}addpoints [usuario], [pontos], [sala]", self.websocket, self.sender, self.room)
        else:
            user = self.sender

        self.cursor.execute(f"""
        SELECT user FROM roomLB WHERE user = "{user}" and roomNAME = "{self.room}"
        """)

        userinDB = self.cursor.fetchall()

        if userinDB:
            user = userinDB[0][0]
            self.cursor.execute(f"""SELECT points FROM roomLB WHERE user = "{user}" and roomNAME = "{self.room}"
            """)
            points = self.cursor.fetchall()[0][0] + newPoints
            self.cursor.execute(f"""UPDATE roomLB SET points = {points} WHERE user = "{user}" and roomNAME = "{self.room}"
            """)
        else:
            self.cursor.execute(f"""INSERT INTO roomLB (roomNAME, user, points) VALUES (?,?,?)""", (self.room, user, newPoints))

        if self.command == "addpoints":
            respond(self.msgType, "Pontos adicionados!", self.websocket, self.sender, self.room)

        self.db.commit()

    async def rempoints(self, newPoints=1):
        user = name_to_id(self.commandParams[0])
        newPoints = self.commandParams[1]
        try:
            newPoints = float(newPoints)
        except:
            return respond(self.msgType, f"Uso do comando: {prefix}rpoints [usuario], [pontos], [sala]", self.websocket, self.sender, self.room)

        self.cursor.execute(f"""
        SELECT user FROM roomLB WHERE user = "{user}" and roomNAME = "{self.room}"
        """)

        user = self.cursor.fetchall()

        if user:
            user = user[0][0]
            self.cursor.execute(f"""SELECT points FROM roomLB WHERE user = "{user}" and roomNAME = "{self.room}"
            """)
            points = self.cursor.fetchall()[0][0] - newPoints
            self.cursor.execute(f"""UPDATE roomLB SET points = {points} WHERE user = "{user}" and roomNAME = "{self.room}"
            """)
            if points <= 0:
                self.cursor.execute(f"""
                DELETE FROM roomLB WHERE user = "{user}" and roomNAME = "{self.room}"
                """)
        else:
            return respond(self.msgType, "O usuário não tem pontos para serem removidos.", self.websocket, self.sender, self.room)

        if self.command == "rpoints":
            respond(self.msgType, "Pontos removidos!", self.websocket, self.sender, self.room)

        self.db.commit()

    async def clearpoints(self):
        self.cursor.execute(f"""DELETE FROM roomLB WHERE roomNAME = "{self.room}"
        """)
        self.db.commit()
        respond(self.msgType, "Pontos da sala limpos!", self.websocket, self.sender, self.room)
    
    async def leaderboard(self):
        self.cursor.execute(f"""SELECT * FROM roomLB WHERE roomNAME = "{self.room}"
        """)
        lb = ''
        for data in self.cursor.fetchall():
            user = data[1]
            points = data[2]
            if int(points) == points:
                points = int(points)
            lb += f"{user}: {points}\n"
        respond(self.msgType, f"!code Leaderboard:\n{lb}", self.websocket, self.sender, self.room)
    
    def checkRoom(self):
        if self.msgType == 'room':
            self.room = self.msgSplited[0].strip()
            if not self.room:
                self.room = 'lobby'
            else:
                self.room = self.room[1:]
        else:
            self.room = name_to_id(self.commandParams[-1])
            if self.room not in rooms:
                return
        return True