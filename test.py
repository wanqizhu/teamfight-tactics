import sys, pygame, math
pygame.init()


WIDTH = 13
HEIGHT = 5
HEX_LENGTH = 50

def get_hex_center_2d(pos):
    c, r = pos
    x = (c+1) * HEX_LENGTH * math.sqrt(3) / 2
    y = HEX_LENGTH * (1 + r * 3 / 2)
    return (x, y)


def get_hex_corners_2d(pos):
    x, y = get_hex_center_2d(pos)
    corners = [(x, y - HEX_LENGTH),
               (x + HEX_LENGTH * math.sqrt(3) / 2, y - HEX_LENGTH / 2),
               (x + HEX_LENGTH * math.sqrt(3) / 2, y + HEX_LENGTH / 2),
               (x, y + HEX_LENGTH),
               (x - HEX_LENGTH * math.sqrt(3) / 2, y + HEX_LENGTH / 2),
               (x - HEX_LENGTH * math.sqrt(3) / 2, y - HEX_LENGTH / 2)]

    return corners


size = width, height = list(map(int, get_hex_center_2d((WIDTH+1, HEIGHT))))
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)

ball = pygame.image.load("imgs/Ahri.png")
ballrect = ball.get_rect()

while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

    ballrect = ballrect.move(speed)
    if ballrect.left < 0 or ballrect.right > width:
        speed[0] = -speed[0]
    if ballrect.top < 0 or ballrect.bottom > height:
        speed[1] = -speed[1]

    screen.fill(black)

    for r in range(HEIGHT):
        for c in range(r % 2, WIDTH, 2):
            pygame.draw.lines(screen, (255, 0, 0), True,
                              get_hex_corners_2d((c, r)))
                      

    screen.blit(ball, ballrect)
    pygame.display.flip()
    break