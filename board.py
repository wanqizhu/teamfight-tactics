import asyncio
import json
import math
import sys, pygame, math
from copy import copy, deepcopy

from champions import Unit
from hex_utils import (doublewidth_distance, 
                       doublewidth_rotation,
                       Position)

from projectile import Projectile

BLACK = 0, 0, 0
WHITE = 255, 255, 255
GREEN = 0, 128, 0
RED = 128, 0, 0
BLUE = 0, 0, 128
DARKBLUE = 0, 0, 255
pygame.init()
font = pygame.font.SysFont("comicsans", 24)



class Board:
    WIDTH = 13
    HEIGHT = 5
    MARGIN = 60
    HEX_LENGTH = 100  # Euclidean length for display
    _neighbors = [(-2, 0), (-1, 1), (1, 1), 
                  (2, 0), (1, -1), (-1, -1)]

    def __init__(self, p1, p2, speed=1):
        self.players = (p1, p2)
        self.teams = (set(), set())
        self.units = set()
        self._id = 0
        self.speed = speed
        self.spaces = sum([[Position(x, y) for x in range(y%2, self.WIDTH, 2)] for y in range(self.HEIGHT)], [])

        _x, _y = self.get_hex_center_euc((self.WIDTH+1, self.HEIGHT))
        self.screen_size = (int(_x) + self.MARGIN, int(_y) + self.MARGIN)
        self.screen = pygame.display.set_mode(self.screen_size)
        self.projectiles = set()
        self.isGameActive = False
        self.resolvingGameTask = None

        for unit in p1.champions:
            x, y = unit.position
            if y >= 0:
                self.add_unit(unit, 0, Position(x, y))


        ## TODO: class actives

        for unit in p2.champions:
            x, y = unit.position
            if y >= 0:
                self.add_unit(unit, 1, 
                              (self.WIDTH - x, self.HEIGHT - y))

    async def sleep(self, time):
        await asyncio.sleep(time / self.speed)

    ''' list attr getters. TODO: add locks to avoid sync issues '''
    def get_projectiles(self):
        return copy(self.projectiles)




    ''' grid helper funcs '''
    def is_on_board(self, pos):
        x, y = pos
        if x < 0 or x > self.WIDTH:
            return False
        if y < 0 or y > self.HEIGHT:
            return False
        return (x+y)%2 == 0


    def search_path(self, source_unit, target_unit):
        '''
        champion path-finding

        only makes a single step
        '''
        start_pos = source_unit.position
        target_pos = target_unit.position
        atk_range = source_unit.range

        curr_dist = doublewidth_distance(start_pos, target_pos)
        if curr_dist <= atk_range:
            return start_pos

        for neighbor in self._neighbors:
            tentative_pos = start_pos + neighbor
            if (self.get_unit_at_pos(tentative_pos) is not None
                    or tentative_pos[0] < 0
                    or tentative_pos[0] > self.WIDTH
                    or tentative_pos[1] < 0
                    or tentative_pos[1] > self.HEIGHT):
                continue

            if doublewidth_distance(tentative_pos, target_pos) < curr_dist:
                # take a step closer

                # TODO: update board pos
                self.move_unit(source_unit, tentative_pos)
                source_unit.log(f'moving to {tentative_pos}')

                return tentative_pos

        return start_pos


    def line_trace(self, start, target, width=1, length=-1):
        '''
        https://math.stackexchange.com/a/190373 - find point in rectangle

        width is euclidean width from line extending to both directions
        so total width of rectangle is 2*`width`

        length == -1 to indicate segment from start to target,
        else it traces a line of Euclidean length `length`
        adjacent hexes have Euclidean dist 2
        y-coords need to be scaled by sqrt(3) to go from hex -> euc
        '''
        if isinstance(start, Unit):
            start = start.position
        if isinstance(target, Unit):
            target = target.position

        print('line tracing:', start, target, width, length)

        x0, y0 = start  # center of start of rectangle/line
        x1, y1 = target  # center of end of rectangle/line
        y0 *= math.sqrt(3)
        y1 *= math.sqrt(3)
        euc_dist = math.sqrt((y1-y0)**2 + (x1-x0)**2)

        # direction of line, unit vector
        line_vec_x = (x1-x0)/euc_dist
        line_vec_y = (y1-y0)/euc_dist

        rect_width_vec = (2 * width * line_vec_y,
                      -2 * width * line_vec_x)

        if length == -1:
            length = euc_dist

        rect_length_vec = (length * line_vec_x,
                           length * line_vec_y)

        rect_base_pt = (x0 - width * line_vec_y,
                       y0 + width * line_vec_x)

        hits = []

        for unit in self.units:
            # directly check if pt in rectangle

            pos_euc = unit.position * (1, math.sqrt(3))

            pt_vec = pos_euc - rect_base_pt

            width_dot = pt_vec[0]*rect_width_vec[0] + pt_vec[1]*rect_width_vec[1]
            length_dot = pt_vec[0]*rect_length_vec[0] + pt_vec[1]*rect_length_vec[1]
            
            if (width_dot > -0.01 and width_dot < 4*width*width+0.01
                and length_dot > -0.01 and length_dot < length*length+0.01):
                    hits.append(unit)

        print(hits)
        return hits


    def circle_range(self, center, radius=1):
        hits = []
        for unit in self.units:
            if doublewidth_distance(unit.position, center) <= radius:
                hits.append(unit)

        print(f'circle range: center {center} radius {radius}, hitting: {hits}')
        return hits


    def cone_range(self, center, left_edge, span=1, length=2):
        '''
        @span: number of cone degrees as multiple of 60
        @length: side length of cone, in hexes
        
        Method: for each span, find 3 corners of cone, check if each unit's position's distance
            to each corner is less than the side length
        '''
        
        left_dist = doublewidth_distance(center, left_edge)
        left_corner = center + math.ceil(length / left_dist) * (left_edge - center)
        
        # precompute all the pivot corners of this "cone"
        # really, its [span] number of 60-deg cones stitched together
        corners = [left_corner]
        next_corner = left_corner
        for _ in range(span):
            next_corner = doublewidth_rotation(next_corner, center)
            corners.append(next_corner)


        hits = []
        for unit in self.units:
            if doublewidth_distance(unit.position, center) > length:
                continue

            # each unit needs to be within [length] of the center AND two consecutive corners
            prev_in_range = False
            for c in corners:
                if doublewidth_distance(unit.position, c) <= length:
                    if prev_in_range:
                        hits.append(unit)
                        break
                    prev_in_range = True
                else:
                    prev_in_range = False

        print(f'cone range: center {center} corners {corners}, hitting: {hits}')
        return hits


    ''' unit placement logic '''
    def get_unit_at_pos(self, pos):
        for unit in self.units:
            if unit.position == pos:
                return unit
        return None


    def add_unit(self, unit, team_id, position):
        ## TODO: create new copy from name

        unit.team_id = team_id
        unit._id = self._id
        self._id += 1
        unit.position = position
        unit.board = self
        try:
            unit.img = pygame.image.load("imgs/%s.png" % unit.name)
            unit.img = pygame.transform.scale(unit.img, (128, 128))
        except:
            unit.img = None

        ## TODO: reset stats like hp

        self.units.add(unit)
        self.teams[team_id].add(unit)

    def move_unit(self, unit, target_position):
        assert self.get_unit_at_pos(target_position) is None
        unit.position = target_position

    def remove_unit(self, unit):
        team_id = unit.team_id
        position = unit.position
        self.units.remove(unit)
        self.teams[team_id].remove(unit)

        if len(self.teams[team_id]) == 0:
            self.isGameActive = False


    def closest_unit(self, unit, filter_func='enemy', getFarthest=False):
        '''
        @filter_func: function or one of 'enemy', 'ally', 'all'
        @getFarthest: if True, then get farthest unit instead
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

        dist_multiplier = 1 if not getFarthest else -1
        return min(possible_units, 
                   key=lambda other: dist_multiplier * 
                        doublewidth_distance(unit.position, other.position))

    def get_closest_empty_hex(self, position):
        empty_spaces = set(self.spaces) - set(tuple(u.position) for u in self.units)
        return min(empty_spaces,
                   key=lambda other: doublewidth_distance(position, other))


    def get_hex_center_euc(self, pos):
        ''' output euclidean coordinates '''
        c, r = pos
        x = self.MARGIN + (c+1) * self.HEX_LENGTH * math.sqrt(3) / 2
        y = self.MARGIN + self.HEX_LENGTH * (1 + r * 3 / 2)
        return (x, y)

    def get_hex_corners_euc(self, pos):
        x, y = self.get_hex_center_euc(pos)
        corners = [(x, y - self.HEX_LENGTH),
                   (x + self.HEX_LENGTH * math.sqrt(3) / 2, y - self.HEX_LENGTH / 2),
                   (x + self.HEX_LENGTH * math.sqrt(3) / 2, y + self.HEX_LENGTH / 2),
                   (x, y + self.HEX_LENGTH),
                   (x - self.HEX_LENGTH * math.sqrt(3) / 2, y + self.HEX_LENGTH / 2),
                   (x - self.HEX_LENGTH * math.sqrt(3) / 2, y - self.HEX_LENGTH / 2)]

        return corners



    def draw_background(self):
        self.screen.fill(BLACK)

        for (c, r) in self.spaces:
            pygame.draw.lines(self.screen, (255, 0, 0), True,
                              self.get_hex_corners_euc((c, r)))


    async def battle(self):
        self.isGameActive = True
        self.tasks = [asyncio.ensure_future(unit.loop())
                      for unit in self.units] #+ [
                      #asyncio.ensure_future(self.print_board())]

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: sys.exit()

            self.draw_background()

            # draw raw img first
            for unit in self.units:
                if not unit.img:
                    continue

                x, y = self.get_hex_center_euc(unit.position)
                rect = unit.img.get_rect()
                rect.center = x, y
                unit.img_rect = rect
                
                # align the Surface img to the hex center
                self.screen.blit(unit.img, rect)


            # draw hp & mana bars on top
            for unit in self.units:
                if not unit.img:
                    continue

                x, y = self.get_hex_center_euc(unit.position)
                width = unit.img.get_width()
                topleftx = x - width/2
                toplefty = y - unit.img.get_height()/2

                # draw hp bar, with shield
                pygame.draw.rect(self.screen, WHITE, 
                                 (topleftx, toplefty - 50, width, 20))
                pygame.draw.rect(self.screen, RED, 
                                 (topleftx, toplefty - 50, 
                                  (unit.max_hp / (unit.max_hp + unit.total_shield)) * width, 20))
                pygame.draw.rect(self.screen, GREEN, 
                                 (topleftx, toplefty - 50, 
                                  (unit.hp / (unit.max_hp + unit.total_shield)) * width, 20))
                hptext = font.render("HP: %d/%d+%d" % (unit.hp, unit.max_hp, unit.total_shield), 1, BLACK)
                self.screen.blit(hptext, (topleftx, toplefty - 50))

                # draw mana bar
                pygame.draw.rect(self.screen, DARKBLUE, 
                                 (topleftx, toplefty - 30, width, 20))
                pygame.draw.rect(self.screen, BLUE, 
                                 (topleftx, toplefty - 30, 
                                 ((unit.mana / unit.max_mana)
                                  if unit.max_mana > 0 else 0) * width, 20))
                manatext = font.render("MP: %d/%d" % (unit.mana, unit.max_mana), 1, BLACK)
                self.screen.blit(manatext, (topleftx, toplefty - 30))


            for p in self.get_projectiles():
                p.update()
                self.screen.blit(p.surf, p.rect)
                if p.atDestination:
                    self.projectiles.remove(p)


            if not self.isGameActive: 
                if self.resolvingGameTask is None: # only run once
                    self.resolvingGameTask = asyncio.create_task(self.resolve_game())
                    

                endGameText = font.render("Round over", 1, WHITE)
                self.screen.blit(endGameText, (300, 300))
                

            pygame.display.flip()
            await self.sleep(0.25)



    async def start_game(self, timeout=45):
        self.gameLoopTask = asyncio.create_task(self.battle())
        try:
            await asyncio.wait_for(self.gameLoopTask, timeout=timeout / self.speed)
        except asyncio.TimeoutError:
            print('timeout!')
            if self.resolvingGameTask is None:
                self.resolvingGameTask = asyncio.create_task(self.resolve_game())

            await self.resolvingGameTask

        except asyncio.CancelledError:
            print('normal end')
            pass
            


    async def print_board(self):
        while len(self.units):
            print(' '*80, end='\r')
            print(' | '.join(
                repr(unit) for unit in self.units), end='\r')
            await self.sleep(0.5)


    async def resolve_game(self):
        for task in self.tasks:
            task.cancel()

        self.tasks = []
        await self.sleep(5)
        self.gameLoopTask.cancel()


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

