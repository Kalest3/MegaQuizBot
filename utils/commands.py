from showdown.utils import name_to_id

class commands():
    def __init__(self, room, command, content, websocket, sender, db, cursor):
        self.room = room
        self.command = command
        self.websocket = websocket
        self.content = content
        self.user = sender
        self.db = db
        self.cursor = cursor
        self.timer
        self.currentQuestion = False
        self.alternativesNumber = 0
        self.alternatives = {}
        self.answer = {}
        self.html = ''

        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.room} (
            user TEXT PRIMARY KEY,
            points INTEGER)""")


        self.commands = {
            'mq': self.makequestion, 'makequestion': self.makequestion, 'makeq': self.makequestion,
        }

    def makequestion(self):
        self.html += f'<div class="infobox"><center><font size="4">{self.content}</font><br><br><table width="100%" frame="box" rules="all" cellpadding="10"><tbody>'
        return self.html

    def addalternative(self):
        if self.alternativesNumber % 2 == 0:
            self.html += f'<tr><td style="width: 50.00%"><center><button name="send" value="/w Repu, {self.content}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{self.content}</b></font></button></center>'
        else:
            self.html += f'<td style="width: 50.00%"><center><button name="send" value="/w Repu, {self.content}" style=background-color:transparent;border:none;><font color="#cc0000" size="3"><b>{self.content}</b></font></button></center></tr>'
        self.alternativesNumber += 1
        self.alternatives[self.alternativesNumber] = self.content

    def defanswer(self):
        if self.content in self.alternatives:
            self.answer[self.content] = self.alternatives[self.content]

    def send(self):
        self.html += "</div>"
        self.websocket.send(f"{self.room}|/adduhtml question, {self.html}")
        self.currentQuestion = True 
    
    def checkUserAnswer(self):
        contents = self.content.split(",")
        answer, room = name_to_id(contents[0]), name_to_id(contents[1])
        if answer == name_to_id(self.answer) and room == self.room:
            self.addpoints(1)

    def leaderboard(self):
        lb = self.cursor.execute("SELECT * FROM (?)", (self.room,))

    def addpoints(self, newPoints):
        self.cursor.execute("""
        SELECT user FROM (?) WHERE user = (?);
        """, (self.room, self.user))

        user = self.cursor.fetchall()

        if user:
            points = self.cursor.execute("SELECT points FROM (?) WHERE user = (?)", (self.room, self.user))
            self.cursor.execute("""UPDATE portugus SET points = 3 WHERE user = (?)""", (self.user, newPoints + points))
        else:
            self.cursor.execute("""INSERT INTO portugus (user, points) VALUES (?,?)""", (self.user, newPoints))

        self.db.commit()

    def clearpoints(self):
        self.cursor.execute("DELETE * FROM (?)", (self.room,))

    def defTimer(self, time):
        self.timer = time