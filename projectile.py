import pygame
import math
from hex_utils import euc_dist


class Projectile(pygame.sprite.Sprite):
    def __init__(self, board, starting_loc, ending_loc,
                 speed, size=(50, 50), img=None):
        '''
        @starting_loc, ending_loc: Euclidean coords for display
        '''
        super().__init__()

        self.board = board
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



    def update(self):
        # move
        d = math.ceil(euc_dist(self.rect.center, self.ending_loc))

        move_vec = (self.speed*(self.ending_loc[0] - self.rect.x) // d,
                    self.speed*(self.ending_loc[1] - self.rect.y) // d)


        self.rect.move_ip(*move_vec)

        if self.rect.collidepoint(self.ending_loc):
            print(self, "at destination, removing...")
            self.atDestination = True
            return

        # TODO: check for board collisions




class HomingProjectile(Projectile):
    # TODO
    pass