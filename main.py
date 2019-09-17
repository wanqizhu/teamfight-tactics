import time
import threading
import asyncio
import datetime
import json


# TODO: enum types for e.g. team, traits


class ChampionStats:
    def __init__(self, stats):
        self.damage = stats["offense"]["damage"]
        self.attackSpeed = stats["offense"]["attackSpeed"]
        self.dps = stats["offense"]["dps"]
        self.range = stats["offense"]["range"]

        self.health = stats["defense"]["health"]
        self.armor = stats["defense"]["armor"]
        self.magicResist = stats["defense"]["health"]

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)


def load_champion_stats_table():
    '''
    https://solomid-resources.s3.amazonaws.com/blitz/tft/data/champions.json

    https://solomid-resources.s3.amazonaws.com/blitz/tft/data/classes.json

    https://solomid-resources.s3.amazonaws.com/blitz/tft/data/items.json

    https://solomid-resources.s3.amazonaws.com/blitz/tft/data/origins.json

    https://solomid-resources.s3.amazonaws.com/blitz/tft/data/tierlist.json
    '''
    with open('championStats.json') as f:
        data = json.load(f)

    assert 'Ahri' in data

    # only inherit the data we want
    for champion in data:
        traits = data[champion]["origin"] + data[champion]["class"]
        data[champion] = { k : data[champion][k] for k in
                           ["name", "cost", "ability", "stats"]}
        data[champion]['items'] = []
        data[champion]['stats'] = ChampionStats(data[champion]['stats'])
        data[champion]['traits'] = traits

    print(data['Akali'])
    return data



class Unit:
    star_multiplier = [0.5, 1, 1.8, 3.6]
    MANA_PER_ATK = 10
    MAX_MANA_FROM_DMG = 50
    MANA_PER_DMG = 0.1
    stats_table = load_champion_stats_table()

    def __init__(self, name='', 
                 stats=None,
                 star = 1,
                 position=(-1, -1),
                 logfile=None,
                 **kwargs):
        self.name = name
        self.stats = stats
        self._ap = 0
        self.target = None
        self.position = position
        self.star = 1
        self._id = None
        self.board = None
        self.start_time = time.perf_counter()
        self.logfile = logfile
        self.traits = set()
        self.status = []
        # CR-soon: write self to logfile

        for key, value in kwargs.items():
            setattr(self, key, value)
            print(key, value)

        self._mana = self.ability['manaStart']
        self._max_mana = self.ability['manaCost']
        self._hp = self.max_hp
        self.targetable = True


    @classmethod
    def fromName(cls, name, **kwargs):
        if name not in cls.stats_table:
            raise NameError(f'{name} not found')

        attributes = cls.stats_table[name]
        # merge the two dictionaries, allow kwargs overwrite
        return cls(**{**attributes, **kwargs})


    @property
    def ad(self):
        return (self.stats.damage
               * self.star_multiplier[self.star])
    
    @property
    def atspd(self):
        return self.stats.attackSpeed
    
    @property
    def armor(self):
        return self.stats.armor
    
    @property
    def mr(self):
        return self.stats.magicResist

    @property
    def max_hp(self):
        return (self.stats.health
                * self.star_multiplier[self.star])

    @property
    def range(self):
        return self.stats.range
    
    @property
    def hp(self):
        return self._hp
    
    @property
    def ap(self):
        return self._ap

    @property
    def mana(self):
        return self._mana
    
    @property
    def max_mana(self):
        return self._max_mana

    @property
    def mana_per_atk(self):
        mana = self.MANA_PER_ATK 
        if self.star <= 1:
           mana *= 0.8
        if 'Elementalist' in self.traits or 'Sorcerer' in self.traits:
            mana *= 2
        return mana

    @property
    def is_ranged(self):
        return self.range > 1
    

    def __repr__(self):
        return (f"[{self.name} @{self.position}] HP:{self.hp}/{self.max_hp},"
                f"MP:{self.mana}/{self.max_mana}")

    def __str__(self):
        return "[%s (%s)]" % (self.name, self._id)


    def acquire_target(self):
        if self.target is not None:
            return self.target

        if not self.board:
            return None

        self.target = self.board.closest_unit(self, filter_func='enemy')
        return self.target

    def autoattack(self):
        if not self.target:
            self.acquire_target()
            return

        res = self.target.receive_damage(self.ad, self, 'physical', is_autoattack=True)
        self._mana += self.mana_per_atk
        return res


    async def cast_spell(self):
        self.log(f"casting {self.ability['description']}...")
        return

    def receive_damage(self, dmg, source, dmg_type, is_autoattack=False):
        mana_gained = min(self.MAX_MANA_FROM_DMG, int(dmg * self.MANA_PER_DMG))
        self._mana += mana_gained

        if dmg_type == 'physical':
            dmg *= (1 - self.armor / (100 + self.armor))
        if dmg_type == 'magical':
            dmg *= (1 - self.mr / (100 + self.mr))

        return self.on_damage(dmg, source, dmg_type, is_autoattack)


    def on_damage(self, dmg, source, dmg_type, is_autoattack=False):
        dmg = int(dmg)
        self._hp -= dmg
        self.log('%d dmg [%s] from [%s]' % (dmg, dmg_type, source))
        return (True, dmg)

    def log(self, msg):
        logstr = '(%f)[%s %s] %s' % (time.perf_counter() - self.start_time, 
                                  self.name, self._id, msg)

        if self.logfile:
            self.logfile.write(logstr + '\n')
        else:
            print(logstr)



    def death(self):
        self.log('died')
        self.board.remove_unit(self)



    async def loop(self):
        while True:
            if self.hp < 0:
                self.death()
                return

            ## TODO: deal w/ status e.g. stunned
            # can we make this a closed set? e.g. burn effects, is_stunned, etc

            if self.mana >= self.max_mana:
                self._mana = 0
                await self.cast_spell()
                continue

            if self.target is None:
                self.log('acquiring target...')
                self.acquire_target()
            
            if self.target:
                if not self.target.targetable:
                    self.target = None
                    self.acquire_target()

                # check range
                dist = self.board.distance(self.position, 
                                           self.target.position)
                while dist > self.range:
                    self.board.search_path(self, self.target)
                    await asyncio.sleep(1)
                    dist = self.board.distance(self.position, 
                           self.target.position)

                self.autoattack()

            await asyncio.sleep(1 / self.atspd)
            # print(repr(self), end='\r')


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
        ''' hexagonal distance 

        0,0  2,0  4,0, ...
          1,1  3,1  5,1, ...
        0,2  2,2  4,2, ...

        '''
        x1, y1 = pos1
        x2, y2 = pos2
        return (abs(x1-x2) + abs(y1-y2))//2

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
        for x_delta, y_delta in [(-2, 0), (-1, 1), (1, 1), (2, 0), (1, -1), (-1, -1)]:
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
        while True:
            print(' '*80, end='\r')
            print(' | '.join(
                repr(unit) for unit in self.units), end='\r')
            await asyncio.sleep(1)


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