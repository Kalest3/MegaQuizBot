import asyncio

from showdown.utils import name_to_id
from config import prefix, rooms

class otherCommands():
    def __init__(self, 
                msgSplited=None,
                websocket=None, 
                db=None, 
                cursor=None,
                msgType=''):

        self.msgSplited = msgSplited
        self.websocket = websocket
        self.db = db
        self.cursor = cursor
        self.msgType = msgType
        self.commandParams = []
        self.aliases = {
            "addp": "addpoints",
            "rpoint": "rpoints",
            "removepoints": "rpoints",
            "clear": "clearpoints",
            "dtimer": "deftimer",
        }
        self.room = ''
        self.roomLB = ''
        self.sender = ''

        self.lb, self.addpoint, self.rempoint, self.clearpoint, self.deftimer = \
            lambda : self.call_command(self.leaderboard()), lambda : self.call_command(self.addpoints()), \
            lambda: self.call_command(self.rempoints()), lambda : self.call_command(self.clearpoints()), \
            lambda : self.call_command(self.defTimer())


        self.commands = {
            'deftimer': {'func': self.deftimer, 'perm': 'adm', 'type': 'both'}, 'lb': {'func': self.lb, 'perm': 'general', 'type': 'both'}, 
            'addpoints': {'func': self.addpoint, 'perm': 'adm', 'type': 'both'}, 'rpoints': {'func': self.rempoint, 'perm': 'adm', 'type': 'both'}, 
            'clearpoints': {'func': self.clearpoint, 'perm': 'adm', 'type': 'both'},
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
        self.checkRoom()
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

    async def defTimer(self):
        time = self.commandParams[0]
        if time.isdigit():
            self.timer = float(time)
            self.cursor.execute(f"""
            SELECT roomID FROM rooms WHERE roomID = "{self.room}"
            """)

            room = self.cursor.fetchall()

            if room:
                self.cursor.execute(f"""UPDATE rooms SET timer = "{self.timer}" WHERE roomID = "{self.room}"
                """)
            else:
                self.cursor.execute(f"""INSERT INTO rooms (roomID, timer) VALUES (?,?)""", (self.room, self.timer))

            self.db.commit()

            self.respond(f"O tempo foi alterado para {time} segundos!", self.sender)
        else:
            self.respond("Digite um tempo válido!", self.sender)
    
    async def addpoints(self, newPoints=1):
        if self.command == "addpoints":
            if len(self.commandParams) < 2:
                return self.respond(f"Uso do comando: {prefix}.addpoints [usuario], [pontos], [sala]", self.sender)
            user = name_to_id(self.commandParams[0])
            newPoints = self.commandParams[1]
            try:
                newPoints = float(newPoints)
            except:
                return self.respond(f"Uso do comando: {prefix}addpoints [usuario], [pontos], [sala]", self.sender)
        else:
            user = self.sender

        self.cursor.execute(f"""
        SELECT user FROM "{self.roomLB}" WHERE user = "{user}"
        """)

        userinDB = self.cursor.fetchall()

        if userinDB:
            user = userinDB[0][0]
            self.cursor.execute(f"""SELECT points FROM "{self.roomLB}" WHERE user = "{user}"
            """)
            points = self.cursor.fetchall()[0][0] + newPoints
            self.cursor.execute(f"""UPDATE "{self.roomLB}" SET points = {points} WHERE user = "{user}"
            """)
        else:
            self.cursor.execute(f"""INSERT INTO "{self.roomLB}" (user, points) VALUES (?,?)""", (user, newPoints))

        if self.command == "addpoints":
            self.respond("Pontos adicionados!", self.sender)

        self.db.commit()

    async def rempoints(self, newPoints=1):
        if len(self.commandParams) < 2:
            return self.respond(f"Uso do comando: {prefix}.rpoints [usuario], [pontos], [sala]", self.sender)
        user = name_to_id(self.commandParams[0])
        newPoints = self.commandParams[1]
        try:
            newPoints = float(newPoints)
        except:
            return self.respond(f"Uso do comando: {prefix}rpoints [usuario], [pontos], [sala]", self.sender)

        self.cursor.execute(f"""
        SELECT user FROM "{self.roomLB}" WHERE user = "{user}"
        """)

        user = self.cursor.fetchall()

        if user:
            user = user[0][0]
            self.cursor.execute(f"""SELECT points FROM "{self.roomLB}" WHERE user = "{user}"
            """)
            points = self.cursor.fetchall()[0][0] - newPoints
            self.cursor.execute(f"""UPDATE "{self.roomLB}" SET points = {points} WHERE user = "{user}"
            """)
            if points <= 0:
                self.cursor.execute(f"""
                DELETE FROM "{self.roomLB}" WHERE user = "{user}"
                """)
        else:
            return self.respond("O usuário não tem pontos para serem removidos.", self.sender)

        if self.command == "rpoints":
            self.respond("Pontos removidos!", self.sender)

        self.db.commit()

    async def clearpoints(self):
        self.cursor.execute(f"""DELETE FROM {self.roomLB}""")
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
        self.respond(f"!code Leaderboard:\n{lb}", self.sender)
    
    def checkRoom(self):
        if self.msgType == 'room':
            self.room = self.msgSplited[0]
            if not self.room:
                self.room = 'lobby'
            else:
                self.room = self.room[1:]
            self.roomLB = f"{self.room}lb"
        else:
            self.room = name_to_id(self.commandParams[-1])
            if self.room not in rooms:
                self.respondPM(self.sender, "Sala não presente dentre as que o bot está.")
                return
            self.roomLB = f"{self.room}lb"