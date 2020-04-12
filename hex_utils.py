import math

# helpers for hex coordinate conversion
def doublewidth_to_cube(pos):
    x = (pos[0] - pos[1]) // 2
    z = pos[1]
    y = -x-z
    return x, y, z

def cube_to_doublewidth(cube):
    col = 2 * cube[0] + cube[2]
    row = cube[2]
    return col, row


def doublewidth_rotation(point, center, degrees=1):
    '''
    @degrees: number of multiples of 60 degrees clockwise
    '''

    degrees = -degrees  # convert to counterclockwise calculation
    cube_p = doublewidth_to_cube(point)
    cube_c = doublewidth_to_cube(center)
    cube_diff = [cube_p[0] - cube_c[0],
                 cube_p[1] - cube_c[1],
                 cube_p[2] - cube_c[2]]

    cube_rotated = cube_diff[degrees % 3 :] + cube_diff[: degrees % 3]
    if degrees % 2:
        cube_rotated = [-c for c in cube_rotated]

    cube_target = [cube_rotated[0] + cube_c[0],
                   cube_rotated[1] + cube_c[1],
                   cube_rotated[2] + cube_c[2]]

    doublewidth_target = cube_to_doublewidth(cube_target)
    return doublewidth_target


def doublewidth_distance(pos1, pos2):
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
    return dy + max(0, (dx - dy)//2)


def euc_dist(coord1, coord2):
    a, b = coord1
    c, d = coord2
    return math.sqrt((a-c)**2 + (b-d)**2)