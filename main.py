import time
import asyncio
import datetime
import json

from champions import Unit
from board import Board


class Player:
    # hp, gold, win streak, exp, champion roster
    # should each player get a single board? with half playable
    # space and reflect over for battle
    # each spot points to a champion
    def __init__(self):
        self.champions = set()
        self.level = 1
        self.exp = 0
        self.gold = 0
        self.win_streak = 0
        self.hp = 100

    def take_damage(self, dmg):
        self.hp -= dmg
        print('dmg', dmg, ', remaining hp', self.hp)
        if self.hp <= 0:
            ## TODO
            print('died')
            pass


logfile = open('combat_log_%s' % datetime.datetime.now().strftime('%Y_%m_%d'), 'a')
logfile.write(str(datetime.datetime.now()))
logfile.write('\n\n')



def setup(logfile=None):
    p1 = Player()
    p2 = Player()

    c0 = Unit.from_name('Ahri', position=(0, 0), 
                       logfile=logfile)
    c1 = Unit.from_name('Ahri', position=(2, 0), 
                       logfile=logfile)

    p1.champions.add(c0)
    p1.champions.add(c1)

    c2 = Unit.from_name('Ahri', position=(1, 1), 
                       logfile=logfile)
    c3 = Unit.from_name('Poppy', position=(9, 1), 
                       logfile=logfile)
    p2.champions.add(c2)
    p2.champions.add(c3)

    board = Board(p1, p2, speed=2)

    print(board.units)
    print([u.__dict__ for u in board.units])
    print('\n\nsetup complete\n')

    return board


GAME_BOARD = setup(logfile)

GAME_BOARD.start_game()

logfile.close()