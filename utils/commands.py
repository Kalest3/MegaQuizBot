from playing import game, other

cmdGame = set(game.gameCommands().commands.keys())
cmdOther = set(other.otherCommands().commands.keys())

aliasesGame = set(game.gameCommands().aliases.keys())
aliasesOther = set(game.gameCommands().aliases.keys())

allCommands = set()
allAliases = set()

allCommands = allCommands.union(cmdGame, cmdOther)
allAliases = allAliases.union(aliasesGame, aliasesOther)