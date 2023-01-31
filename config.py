import json

with open('config.json') as json_file:
    jsondata = json.load(json_file)
    uri = jsondata['uri']
    username = jsondata['username']
    password = jsondata['password']
    avatar = jsondata['avatar']
    rooms = jsondata['rooms']
    prefix = jsondata['prefix']
    trusted = jsondata['trusted']
    ranksAdm = jsondata['ranksAdm']