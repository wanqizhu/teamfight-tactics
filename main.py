import time
import threading
import asyncio


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


class Unit:
    def __init__(self, name='', MAX_HP=500, AD=45,
                 ATSPD=0.8, ARMOR=30, MR=20,
                 MAX_MANA=100,
                 position=(0, 0)
                 ):
        self.name = name
        self._max_hp = MAX_HP
        self._hp = MAX_HP
        self._ad = AD
        self._ap = 0
        self._atspd = ATSPD
        self._armor = ARMOR
        self._mr = MR
        self._max_mana = MAX_MANA
        self._mana = 0
        self._mana_per_atk = 10
        self.target = None
        self.position = position
        self.traits = set()
        self.star = 1
        self._id = None
        self.board = None
        self.start_time = time.perf_counter()

    @property
    def ad(self):
        return self._ad

    @property
    def ap(self):
        return self._ap
    
    @property
    def atspd(self):
        return self._atspd
    
    @property
    def armor(self):
        return self._armor
    
    @property
    def mr(self):
        return self._mr
    
    @property
    def hp(self):
        return self._hp
    
    @property
    def max_hp(self):
        return self._max_hp
    
    @property
    def mana(self):
        return self._mana
    
    @property
    def max_mana(self):
        return self._max_mana

    @property
    def mana_per_atk(self):
        return self._mana_per_atk

    def __repr__(self):
        return "[%s (%s)] hp: %d/%d, mana: %d/%d" % (self.name, self._id,
                                        self.hp, self.max_hp,
                                        self.mana, self.max_mana)

    def __str__(self):
        return "[%s (%s)]" % (self.name, self._id)

    def add_to_board(self, board):
        board.add_unit(self)
        self.board = board

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
        print('(%f)[%s %s] %s' % (time.perf_counter() - self.start_time, 
                                  self.name, self._id, msg))



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
            self.log(repr(self))


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
            print('async cancel')
            pass


    async def battle(self):
        self.tasks = [asyncio.ensure_future(unit.loop())
                      for unit in self.units]
        await asyncio.gather(*self.tasks)


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



def setup(board):
    c1 = Unit(name='c1')
    c2 = Unit(name='c2', position=(1, 1), 
              AD=40, ATSPD=1.2)
    board.add_unit(c1, team_id=0)
    board.add_unit(c2, team_id=1)
    print(board.units)
    print([u.__dict__ for u in board.units])
    return


setup(GAME_BOARD)

GAME_BOARD.start_game()
