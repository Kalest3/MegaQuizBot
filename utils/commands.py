from playing import game, other

cmdGame = game.gameCommands().commands
cmdOther = other.otherCommands().commands

aliasesGame = game.gameCommands().aliases
aliasesOther = other.otherCommands().aliases

allCommands = cmdGame | cmdOther
allAliases = aliasesGame | aliasesOther