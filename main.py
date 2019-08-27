import time
import threading
import asyncio
import datetime

import json

class BackgroundTimer(threading.Thread):
    def __init__(self, delay, func):
        self.delay = delay
        self.func = func
        super().__init__()

    def run(self):
        while True:
            time.sleep(self.delay)
            self.func()

# t = BackgroundTimer(0.6, lambda: print('hello'))
# t.start()

# while True:
#     time.sleep(1)
#     print('wow')



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
        data[champion] = { k : data[champion][k] for k in
                           ["name", "origin", "class",
                            "cost", "ability", "stats"]}
        data[champion]['items'] = []
        data[champion]['stats'] = ChampionStats(data[champion]['stats'])

    print(data['Akali'])
    return data



class Unit:
    star_multiplier = [0.5, 1, 1.8, 3.6]
    stats_table = load_champion_stats_table()

    def __init__(self, name='', 
                 stats=None,
                 star = 1,
                 position=(0, 0),
                 logfile=None,
                 **kwargs):
        self.name = name
        self.stats = stats
        self._ap = 0
        self._mana_per_atk = 10
        self.target = None
        self.position = position
        self.star = 1
        self._id = None
        self.board = None
        self.start_time = time.perf_counter()
        self.logfile = logfile
        # CR-soon: write self to logfile

        for key, value in kwargs.items():
            setattr(self, key, value)
            print(key, value)

        self._mana = self.ability['manaStart']
        self._max_mana = self.ability['manaCost']
        self._hp = self.max_hp


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
        return self._mana_per_atk

    @property
    def is_ranged(self):
        return self.range > 1
    

    def __repr__(self):
        return f"[{self.name} ({self._id})] HP: {self.hp}/{self.max_hp}"

    def __str__(self):
        return "[%s (%s)]" % (self.name, self._id)


    def add_to_board(self, board):
        board.add_unit(self)
        self.board = board
        self._hp = self.max_hp  # ensure up to date
        ## todo: reset everything else

    def acquire_target(self):
        if self.target is not None:
            return 1

        if not self.board:
            return 0

        self.target = self.board.closest_unit(self, filter_func='enemy')
        if not self.target:
            return 0
        return 2

    def autoattack(self):
        if not self.target:
            self.acquire_target()
            return

        res = self.target.receive_damage(self.ad, self, 'physical', is_autoattack=True)
        self._mana += self.mana_per_atk
        return res


    async def cast_spell(self):
        self.log('casting...')
        return

    def receive_damage(self, dmg, source, dmg_type, is_autoattack=False):
        if source == 'physical':
            dmg *= (1 - self.armor / (100 + self.armor))
        if source == 'magical':
            dmg *= (1 - self.mr / (100 + self.mr))

        return self.on_damage(dmg, source, dmg_type, is_autoattack)


    def on_damage(self, dmg, source, dmg_type, is_autoattack=False):
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
        self.board.remove_unit(self, death=True)



    async def loop(self):
        while True:
            if self.hp < 0:
                self.death()
                return

            if self.mana == self.max_mana:
                self._mana = 0
                await self.cast_spell()
                continue

            if not self.target:
                self.log('acquiring target...')
                self.acquire_target()
            
            if self.target:
                # should have target now
                self.autoattack()

            await asyncio.sleep(1 / self.atspd)
            # print(repr(self), end='\r')


class Player:
    # hp, gold, win streak, exp, champion roster
    # should each player get a single board? with half playable
    # space and reflect over for battle
    # each spot points to a champion
    pass


class Board:
    def __init__(self):
        self.units = set()  # maybe dict from position/id -> unit?
        self._id = 0
        # CR-soon: combaine team stats to a namedtuple?
        self.teams = [set(), set()]
        self.team_hp = [100, 100]
        pass

    def distance(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2
        return (x1-x2)**2 + (y1-y2)**2

    def add_unit(self, unit, team_id=0):
        self.units.add(unit)
        unit._id = self._id
        unit.team_id = team_id
        unit.board = self
        self.teams[team_id].add(unit)
        self._id += 1

    def remove_unit(self, unit, death=True):
        team_id = unit.team_id
        self.units.remove(unit)
        self.teams[team_id].remove(unit)
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
                      asyncio.ensure_future(self.print_units_hp())]
        await asyncio.gather(*self.tasks)


    async def print_units_hp(self):
        while True:
            await asyncio.sleep(1)
            print(' | '.join(
                repr(unit) for unit in self.units), end='\r')


    def resolve_game(self):
        for task in self.tasks:
            task.cancel()

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

        print(won, dmg)
        for team_id in range(len(self.teams)):
            self.team_hp[team_id] -= dmg[team_id]

        print('remaining hps', self.team_hp)


GAME_BOARD = Board()

logfile = open('combat_log_%s' % datetime.datetime.now().strftime('%Y_%m_%d'), 'a')
logfile.write(str(datetime.datetime.now()))
logfile.write('\n\n')



def setup(board, logfile=None):
    c1 = Unit.fromName('Ahri', logfile=logfile)
    c2 = Unit.fromName('Aatrox', position=(1, 1), 
                       logfile=logfile)
    board.add_unit(c1, team_id=0)
    board.add_unit(c2, team_id=1)
    print(board.units)
    print([u.__dict__ for u in board.units])
    print('\n')


setup(GAME_BOARD, logfile)

GAME_BOARD.start_game()

logfile.close()