import time
import threading
import asyncio
import datetime
import json

from champions import Unit


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


## board during gameplay
class Board:
    WIDTH = 12
    HEIGHT = 5
    _neighbors = [(-2, 0), (-1, 1), (1, 1), (2, 0), (1, -1), (-1, -1)]

    def __init__(self, p1, p2):
        self.players = (p1, p2)
        self.teams = (set(), set())
        self.units = set()
        self.pos_to_unit = dict()
        self._id = 0

        for unit in p1.champions:
            x, y = unit.position
            if y >= 0:
                self.add_unit(unit, 0, (x, y))


        ## TODO: class actives

        for unit in p2.champions:
            x, y = unit.position
            if y >= 0:
                self.add_unit(unit, 1, 
                              (self.WIDTH - x, self.HEIGHT - y))


    def add_unit(self, unit, team_id, position):
        ## TODO: create new copy from name

        unit.team_id = team_id
        unit._id = self._id
        self._id += 1
        unit.position = position
        unit.board = self

        ## TODO: reset stats like hp

        self.units.add(unit)
        self.teams[team_id].add(unit)
        self.pos_to_unit[(position)] = unit

    def move_unit(self, unit, target_position):
        assert target_position not in self.pos_to_unit
        self.pos_to_unit.pop(unit.position)
        self.pos_to_unit[target_position] = unit
        unit.position = target_position


    ## TODO: dist for unit,unit and raw (pos,pos)
    def distance(self, pos1, pos2):
        ''' hexagonal grid using Doubled Width Coord

        https://www.redblobgames.com/grids/hexagons

        0,0  2,0  4,0, ...
          1,1  3,1  5,1, ...
        0,2  2,2  4,2, ...

        '''
        x1, y1 = pos1
        x2, y2 = pos2
        dx = abs(x1-x2)
        dy = abs(y1-y2)
        return dx + max(0, (dx - dy)//2)

    def search_path(self, source_unit, target_unit):
        '''
        champion path-finding

        only makes a single step
        '''
        start_pos = source_unit.position
        target_pos = target_unit.position
        atk_range = source_unit.range

        curr_dist = self.distance(start_pos, target_pos)
        if curr_dist <= atk_range:
            return start_pos

        x, y = start_pos
        for x_delta, y_delta in self._neighbors:
            tentative_pos = (x+x_delta, y+y_delta)
            if (tentative_pos in self.pos_to_unit
                    or tentative_pos[0] < 0
                    or tentative_pos[0] > self.WIDTH
                    or tentative_pos[1] < 0
                    or tentative_pos[1] > self.HEIGHT):
                continue

            if self.distance(tentative_pos, target_pos) < curr_dist:
                # take a step closer

                # TODO: update board pos
                self.move_unit(source_unit, tentative_pos)
                source_unit.log(f'moving to {tentative_pos}')

                return tentative_pos

        return start_pos



    def remove_unit(self, unit):
        team_id = unit.team_id
        position = unit.position
        self.units.remove(unit)
        self.teams[team_id].remove(unit)
        self.pos_to_unit.pop(position)

        if len(self.teams[team_id]) == 0:
            self.resolve_game()


    def closest_unit(self, unit, filter_func='enemy'):
        '''
        filter_func: function or one of 'enemy', 'ally', 'all'
        '''
        if filter_func == 'enemy':
            filter_func = lambda u: u.team_id != unit.team_id
        elif filter_func == 'ally':
            filter_func = lambda u: u.team_id == unit.team_id
        elif filter_func == 'all':
            filter_func = lambda u: True

        possible_units = set(filter(filter_func, self.units - set([unit])))
        if len(possible_units) == 0:
            return None

        return min(possible_units, 
                   key=lambda other: self.distance(unit.position,
                                                   other.position))

    def start_game(self, timeout=25):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.battle())

        loop.call_later(timeout, self.resolve_game)

        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            print('round over')
            pass


    async def battle(self):
        self.tasks = [asyncio.ensure_future(unit.loop())
                      for unit in self.units] + [
                      asyncio.ensure_future(self.print_board())]
        await asyncio.gather(*self.tasks)


    async def print_board(self):
        while len(self.units):
            print(' '*80, end='\r')
            print(' | '.join(
                repr(unit) for unit in self.units), end='\r')
            await asyncio.sleep(0.5)


    def resolve_game(self):
        for task in self.tasks:
            task.cancel()

        print('\n\n')

        won = [False, False]
        dmg = [0, 0]
        for team_id in range(len(self.teams)):
            team = self.teams[team_id]
            other_team = 1 - team_id
            if len(team) == 0:
                won[other_team] = True
                dmg[team_id] += 2
            else:
                for unit in team:
                    dmg[other_team] += unit.star

        for team_id in range(len(self.teams)):
            self.players[team_id].take_damage(dmg[team_id])



logfile = open('combat_log_%s' % datetime.datetime.now().strftime('%Y_%m_%d'), 'a')
logfile.write(str(datetime.datetime.now()))
logfile.write('\n\n')



def setup(logfile=None):
    p1 = Player()
    p2 = Player()

    c1 = Unit.fromName('Ahri', position=(0, 0), 
                       logfile=logfile)
    c2 = Unit.fromName('Aatrox', position=(1, 1), 
                       logfile=logfile)
    p1.champions.add(c1)
    p2.champions.add(c2)

    board = Board(p1, p2)

    print(board.units)
    print([u.__dict__ for u in board.units])
    print('\n')

    return board


GAME_BOARD = setup(logfile)

GAME_BOARD.start_game()

logfile.close()