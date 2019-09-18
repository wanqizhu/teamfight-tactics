import time
import asyncio
import json
from enum import Enum

# TODO: enum types for e.g. team, traits

class ChampionStats:
    def __init__(self, stats):
        self.damage = stats["offense"]["damage"]
        self.attackSpeed = stats["offense"]["attackSpeed"]
        self.dps = stats["offense"]["dps"]
        self.range = stats["offense"]["range"]

        self.health = stats["defense"]["health"]
        self.armor = stats["defense"]["armor"]
        self.magicResist = stats["defense"]["magicResist"]

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

    print('champion data loaded')
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
        self.is_targetable = True


    @classmethod
    def fromName(cls, name, **kwargs):
        if name not in cls.stats_table:
            raise NameError(f'{name} not found')

        attributes = cls.stats_table[name]

        # get unique champion class if exists, for defining abilities
        champion_cls = globals().get(name, cls)
        print(f'loaded {name} as {champion_cls}')
        # merge the two dictionaries, allow kwargs overwrite
        return champion_cls(**{**attributes, **kwargs})

    @property
    def time_alive(self):
        return time.perf_counter() - self.start_time

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

        self.log(f'atk -> {self.target}')
        res = self.deal_damage(self.target, self.ad, 'physical', is_autoattack=True)
        self._mana += self.mana_per_atk
        return res

    def deal_damage(self, target, dmg, dmg_type, is_autoattack=False):
        # TODO: more fine-grained dmg source
        if target.is_targetable:
            target.receive_damage(dmg, self, dmg_type, is_autoattack)

    async def cast_spell(self):
        self.log(f"casting {self.ability['description']}...")
        await self.spell_effect()

    async def spell_effect(self):
        print(f'{self} ultimate not implemented')
        pass


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
        logstr = '(%f)[%s %s] %s' % (self.time_alive, 
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
                if not self.target.is_targetable:
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



class Ahri(Unit):
    SPELL_DMG = [60, 100, 200, 300]
    async def spell_effect(self):
        if self.target is None or not self.target.is_targetable:
            self.acquire_target()

        if self.target:
            self.deal_damage(self.target, self.SPELL_DMG[self.star], 'magical')
            await asyncio.sleep(0.2)
            self.deal_damage(self.target, self.SPELL_DMG[self.star], 'true')