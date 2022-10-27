import json

with open('config.json') as json_file:
    jsondata = json.load(json_file)
    username = jsondata['username']
    username = str(username)
    password = jsondata['password']
    room = jsondata['room']
    prefix = jsondata['prefix']