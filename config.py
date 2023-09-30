import json

with open('config.json') as json_file:
    jsondata = json.load(json_file)
    uri = jsondata['uri']
    username = jsondata['username']
    password = jsondata['password']
    owner = jsondata['owner']
    rooms = jsondata['rooms']
    avatar = jsondata['avatar']
    prefix = jsondata['prefix']
    ranksAdm = jsondata['ranksAdm']