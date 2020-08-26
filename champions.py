import time
import asyncio
import json
import numpy as np
from enum import Enum

from hex_utils import doublewidth_distance, doublewidth_round
from projectile import Projectile

# TODO: enum types for e.g. team, traits

class ChampionStats:
    def __init__(self, stats):
        self.damage = stats["offense"]["damage"]
        self.attackSpeed = stats["offense"]["attackSpeed"]
        self.range = stats["offense"]["range"]

        self.health = stats["defense"]["health"]
        self.armor = stats["defense"]["armor"]
        self.magicResist = stats["defense"]["magicResist"]

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)


def load_champion_stats_table(set_name="set3"):
    '''
    up-to-date
    https://blitz-cdn-plain.blitz.gg/blitz/tft/data-sets/champions.json
    '''
    with open('championStats.json') as f:
        data = json.load(f)

    assert 'Ahri' in data

    # only inherit the data we want
    filtered_data = {}
    for champion in data:
        if set_name not in data[champion]:
            continue

        d = data[champion][set_name]
        if not d:
            continue

        d["name"] = data[champion]["name"]
        traits = d["origin"] + d["class"]
        d = { k : d[k] for k in
                           ["cost", "ability", "stats"]}
        d['items'] = []
        d['stats'] = ChampionStats(d['stats'])
        d['traits'] = traits

        # parse ability stats
        s = {}
        for line in d['ability']['stats']:
            values = line['value'].split("/")  # 200 / 400 / 600, possibly w/ %
            s[line['type']] = list(map(lambda x: float(x.strip(" %")), values))

        d['ability']['stats'] = s

        filtered_data[champion] = d

    print('champion data loaded')
    return filtered_data


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
        self._position = np.array(position)
        self.star = int(star)
        self._id = None
        self.board = None
        self.start_time = time.perf_counter()
        self.logfile = logfile
        self.traits = set()
        self.status = []
        self.team_id = None
        self.shields = []
        # CR-soon: write self to logfile

        for key, value in kwargs.items():
            setattr(self, key, value)
            print(key, value)

        self.mana = self.ability['manaStart']
        self._max_mana = self.ability['manaCost']
        self._hp = self.max_hp
        self.is_targetable = True
        self.custom_init()

    def custom_init(self):
        pass


    @classmethod
    def from_name(cls, name, **kwargs):
        if name not in cls.stats_table:
            raise NameError(f'{name} not found')

        attributes = cls.stats_table[name]
        attributes["name"] = name

        # get unique champion class if exists, for defining abilities
        champion_cls = globals().get(name, cls)
        print(f'loaded {name} as {champion_cls}')
        # merge the two dictionaries, allow kwargs overwrite
        return champion_cls(**{**attributes, **kwargs})


    @property
    def SPELL_DMG(self):
        return self.ability["stats"].get("Damage", [0, 0, 0])[self.star - 1]
    
    @property
    def SPELL_ATTACK_DMG(self):
        return self.ability["stats"].get("Attack Damage", [0, 0, 0])[self.star - 1]
    
    @property
    def SPELL_SHIELD(self):
        return self.ability["stats"].get("Shield", [0, 0, 0])[self.star - 1]
    

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

    @mana.setter
    def mana(self, mana):
        # TODO: check mana_lock
        self._mana = mana
    
    @property
    def max_mana(self):
        return self._max_mana

    @property
    def mana_per_atk(self):
        mana = self.MANA_PER_ATK
        return mana

    @property
    def total_shield(self):
        return sum([s[1] for s in self.shields])
    
    @property
    def is_ranged(self):
        return self.range > 1
    
    @property
    def position(self):
        return self._position
    
    @position.setter
    def position(self, position):
        self._position = np.array(position)

    def __repr__(self):
        return (f"[{self.name} @{self.position}] HP:{self.hp}/{self.max_hp},"
                f"MP:{self.mana}/{self.max_mana}")

    def __str__(self):
        return "[%s (%s)]" % (self.name, self._id)


    @property
    def speed(self):
        return self.board.speed
    

    async def sleep(self, time):
        if self.board:
            await self.board.sleep(time)
        else:
            await asyncio.sleep(time)

    def acquire_target(self):
        if self.target is not None and self.target.is_targetable:
            return self.target

        if not self.board:
            return None

        # tries to acquire target
        self.target = self.board.closest_unit(self, filter_func='enemy')
        return self.target

    def launch_autoattack(self, target):
        res = self.deal_damage(self.target, self.ad, 'physical', is_autoattack=True)
        self._mana += self.mana_per_atk
        return res
        

    async def autoattack(self):
        await self.sleep(0.5 / self.atspd)
        while not self.target:
            self.acquire_target()
            await self.sleep(0.1)

        # walk until in range
        dist = doublewidth_distance(self.position, 
                                   self.target.position)
        while dist > self.range:
            self.board.search_path(self, self.target)
            await self.sleep(1)
            dist = doublewidth_distance(self.position, 
                   self.target.position)

        self.log(f'atk -> {self.target}')
        res = self.launch_autoattack(self.target)
        await self.sleep(0.5 / self.atspd)
        return res

    def deal_damage(self, target, dmg, dmg_type, is_autoattack=False):
        # TODO: more fine-grained dmg source
        if dmg <= 0:
            return
        if target.is_targetable:
            target.receive_damage(dmg, self, dmg_type, is_autoattack)


    async def cast_spell(self):
        if self.max_mana == 0:
            return
        self.log(f"casting {self.ability['description']}...")
        await self.spell_effect()

    async def spell_effect(self):
        print(f'{self} ultimate not implemented')
        pass


    def shield(self, amount, duration=-1):
        if duration == -1:
            duration = 100

        _id = time.perf_counter()
        self.shields.append([time.perf_counter() + duration, amount, _id])
        self.shields.sort(key=lambda x: x[0])
        
        # remove shields after expiration
        def remove_shield():
            for s in self.shields:
                if s[2] == _id:
                    self.shields.remove(s)
                    return

        loop = asyncio.get_event_loop()
        loop.call_later(duration / self.speed, remove_shield)


    def launch_projectile(self, target, speed, start=None,
                          dmg=0, dmg_type='magical', 
                          special_collision_func=None,
                          ending_func=None):
        if start is None:
            start = self.position

        start_euc = self.board.get_hex_center_euc(start)
        end_euc = self.board.get_hex_center_euc(target)

        def collision_func(unit):
            print("projectile colliding on ",
                  unit.name, 
                  "from ", self.name)
            if unit.team_id != self.team_id:
                self.deal_damage(unit, dmg, dmg_type)
            if special_collision_func:
                special_collision_func(unit)

        self.board.projectiles.add(
            Projectile(self, start_euc, end_euc, speed, 
                       img='imgs/%s_ability.png' % self.name,
                       collision_func=collision_func,
                       ending_func=ending_func))


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
        self.log('%d dmg [%s] from [%s]' % (dmg, dmg_type, source))

        for i, s in enumerate(self.shields):
            amount = s[1]
            if amount > dmg:
                self.shields[i][1] -= dmg
                self.shields = self.shields[i:]  # remove previously broken shields
                return (True, dmg)

            # cut through current shield and continue
            dmg -= amount

        self.shields = []
        self._hp -= dmg
        
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
        self.is_targetable = False
        # TODO: clear all tasks and effects
        self.board.remove_unit(self)



    async def loop(self):
        # make a list of tasks, including status and queued effects
        # check for things like am i stunned? did i just cast (and thus can't gain mana)?
        auto_task = asyncio.ensure_future(self.autoattack())
        spell_task = None

        while True:
            if self.hp < 0:
                auto_task.cancel()
                if spell_task:
                    spell_task.cancel()
                self.death()
                return

            ## TODO: deal w/ status e.g. stunned
            # can we make this a closed set? e.g. burn effects, is_stunned, etc

            if self.mana >= self.max_mana:
                self.mana = 0
                spell_task = asyncio.ensure_future(self.cast_spell())
                # non-blocking for now

            self.acquire_target()
        
            if auto_task.done():
                auto_task = asyncio.ensure_future(self.autoattack())
            await self.sleep(0.03)






class Ahri(Unit):
    async def spell_effect(self):
        if self.target is None or not self.target.is_targetable:
            self.acquire_target()

        start_pos = self.position
        if self.target and (self.target.position != start_pos).any():
            proj_dir = self.target.position - start_pos
            proj_dir = proj_dir / np.linalg.norm(proj_dir)
        else:
            proj_dir = np.array((0.5, 0.5))

        proj_speed = 90
        proj_length = 6

        # draw line through proj_dir 
        end_pos = doublewidth_round(start_pos + proj_dir * proj_length)

        def returning_projectile(outgoing_proj):
            returning_loc = outgoing_proj.owner.position
            self.launch_projectile(returning_loc, speed=proj_speed,
                                   start=end_pos,
                                   dmg=self.SPELL_DMG,
                                   dmg_type='true')


        self.launch_projectile(end_pos, speed=proj_speed, 
                               dmg=self.SPELL_DMG,
                               dmg_type='magical',
                               ending_func=returning_projectile)


class Poppy(Unit):
    async def spell_effect(self):
        # find farthest target
        target = self.board.closest_unit(self, 'enemy', getFarthest=True)

        self.deal_damage(target, self.SPELL_DMG, 'magical')
        
        await self.sleep(0.25)
        
        self.shield(self.SPELL_SHIELD)


class Jayce(Unit):
    async def spell_effect(self):
        if self.target:
            dist = doublewidth_distance(self.position, self.target.position)
            aim_center = self.position  # default in case weird stuff happens

            # the hex in the direction of our target should have less distance
            for neighbor in self.board._neighbors:
                pos = self.position + neighbor
                if doublewidth_distance(pos, self.target.position) < dist:
                    aim_center = pos
                    break

            assert doublewidth_distance(aim_center, self.position) > 0
        else:
            aim_center = self.position + (1, 1)

        await self.sleep(0.25)
        for target in self.board.circle_range(aim_center, radius=1):
            if target.team_id != self.team_id:
                self.deal_damage(target, self.SPELL_DMG, 'magical')


class Annie(Unit):
    async def spell_effect(self):
        if self.target:
            dist = doublewidth_distance(self.position, self.target.position)
            left_cone_edge = self.position  # default in case weird stuff happens

            # the hex in the direction of our target should have less distance
            for neighbor in self.board._neighbors:
                pos = self.position + neighbor
                if doublewidth_distance(pos, self.target.position) < dist:
                    left_cone_edge = pos
                    break

            assert doublewidth_distance(left_cone_edge, self.position) > 0
        else:
            left_cone_edge = self.position + (1, 1)

        await self.sleep(0.25)
        for target in self.board.cone_range(self.position, left_cone_edge, span=1, length=3):
            if target.team_id != self.team_id:
                self.deal_damage(target, self.SPELL_DMG, 'magical')

        self.shield(self.SPELL_SHIELD)



class Blitzcrank(Unit):
    def custom_init(self):
        # robot trait
        self.mana = self.max_mana

    async def spell_effect(self):
        # find farthest unit
        farthest_unit = self.board.closest_unit(self, getFarthest=True)
        start_location = self.position
        proj_speed = 600

        def pull(proj):
            self.deal_damage(farthest_unit, self.SPELL_DMG, 'magical')
            # displace
            # TODO: ensure no async issues
            empty = self.board.get_closest_empty_hex(start_location)
            self.board.move_unit(farthest_unit, empty)
            # TODO: stun target, aggro allies

        self.launch_projectile(farthest_unit.position, speed=proj_speed, 
                               dmg=0,
                               ending_func=pull)


class Jhin(Unit):
    # TODO: convert atspd to atk
    # todo: show bullet on mana bar
    def custom_init(self):
        self.bullet_count = 4
        self.MANA_PER_ATK = 0
        self.MANA_PER_DMG = 0

    def launch_autoattack(self, target):
        self.bullet_count -= 1
        if self.bullet_count == 0:
            # fourth shot
            res = self.deal_damage(self.target, self.ad * (1 + self.SPELL_ATTACK_DMG / 100),
                                  'physical', is_autoattack=True)
            self.bullet_count = 4
        else:
            res = self.deal_damage(self.target, self.ad, 'physical', is_autoattack=True)
        return res

