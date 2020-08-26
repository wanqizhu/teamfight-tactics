import pygame
import math
from hex_utils import euc_dist


class Projectile(pygame.sprite.Sprite):
    def __init__(self, owner, starting_loc, ending_loc,
                 speed, size=(50, 50), img=None, collision_func=None,
                 ending_func=None):
        '''
        @starting_loc, ending_loc: Euclidean coords for display
        '''
        super().__init__()

        self.owner = owner
        self.board = owner.board
        self.ending_loc = ending_loc
        self.speed = speed

        try:
            self.img = pygame.image.load(img)
            self.img = pygame.transform.scale(self.img, size)
        except Exception as e:
            print("Error loading img: ", e)
            self.img = None

        self.surf = pygame.Surface(size)
        self.surf.fill((255, 255, 255))
        self.rect = self.surf.get_rect()
        if self.img:
            self.surf.blit(self.img, self.rect)
        
        self.rect.move_ip(*starting_loc)
        self.atDestination = False
        self.collision_func = collision_func
        self.ending_func = ending_func
        self.collided_targets = set()


    def update(self):
        # move
        d = math.ceil(euc_dist(self.rect.center, self.ending_loc))

        move_vec = (self.speed*(self.ending_loc[0] - self.rect.x) // d,
                    self.speed*(self.ending_loc[1] - self.rect.y) // d)


        self.rect.move_ip(*move_vec)

        # check for board collisions
        if self.collision_func:
            for unit in self.board.units:
                if unit in self.collided_targets:
                    continue

                # try to collide against image
                if unit.img_rect is not None:
                    if self.rect.colliderect(unit.img_rect):
                        self.collision_func(unit)
                        self.collided_targets.add(unit)
                else:
                    p = self.board.get_hex_center_euc(unit.position)
                    if self.rect.collidepoint(p):
                        self.collision_func(unit)
                        self.collided_targets.add(unit)


        if self.rect.collidepoint(self.ending_loc):
            print(self, "at destination, removing...")
            self.atDestination = True
            if self.ending_func:
                self.ending_func(self)
            return

