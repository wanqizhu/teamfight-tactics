import math

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise ValueError
        if key < 0 or key > 2:
            raise ValueError
        return (self.x, self.y)[key]

    def __eq__(self, other):
        # compare against Position or tuples
        return (self.x == other[0] and
                self.y == other[1])

    def __hash__(self):
        return (self.x, self.y).__hash__()

    def __add__(self, other):
        if isinstance(other, tuple):
            return Position(self.x + other[0],
                            self.y + other[1])
        elif isinstance(other, int):
            return Position(self.x + other,
                            self.y + other)
        elif isinstance(other, Position):
            return Position(self.x + other.x,
                            self.y + other.y)
        else:
            raise ValueError

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, tuple):
            return Position(self.x - other[0],
                            self.y - other[1])
        elif isinstance(other, int):
            return Position(self.x - other,
                            self.y - other)
        elif isinstance(other, Position):
            return Position(self.x - other.x,
                            self.y - other.y)
        else:
            raise ValueError

    # def __rsub__(self, other):
    #     return __sub__(other)

    def __mul__(self, other):
        if isinstance(other, tuple):
            return Position(self.x * other[0],
                            self.y * other[1])
        elif isinstance(other, int):
            return Position(self.x * other,
                            self.y * other)
        elif isinstance(other, Position):
            return Position(self.x * other.x,
                            self.y * other.y)
        else:
            raise ValueError

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, tuple):
            return Position(self.x / other[0],
                            self.y / other[1])
        elif isinstance(other, int) or isinstance(other, float):
            return Position(self.x / other,
                            self.y / other)
        elif isinstance(other, Position):
            return Position(self.x / other.x,
                            self.y / other.y)
        else:
            raise ValueError

    def norm(self):
        return math.sqrt(self.x**2 + self.y**2)




# helpers for hex coordinate conversion
def doublewidth_to_cube(pos):
    x = (pos[0] - pos[1]) // 2
    z = pos[1]
    y = -x-z
    return x, y, z

def cube_to_doublewidth(cube):
    col = 2 * cube[0] + cube[2]
    row = cube[2]
    return Position(col, row)


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


def doublewidth_round(pos):
    x, y = pos
    rx = int(round(x))
    ry = int(round(y))
    if (rx + ry) % 2 == 1:
        # correct to a valid hex center
        # this isn't exactly correctly, but for simplicity
        # we'll just round in x direction
        x_off = x - rx
        if x_off > 0:
            rx += 1
        else:
            rx -= 1

    return Position(rx, ry)




def doublewidth_distance(pos1, pos2):
    ''' hexagonal grid using Doubled Width Coord

    https://www.redblobgames.com/grids/hexagons

    0,0  2,0  4,0, ...
      1,1  3,1  5,1, ...
    0,2  2,2  4,2, ...

    '''

    # x1, y1 = pos1
    # x2, y2 = pos2
    # dx = abs(x1-x2)
    # dy = abs(y1-y2)
    dx, dy = map(abs, pos1 - pos2)
    return dy + max(0, (dx - dy)//2)
    


def euc_dist(coord1, coord2):
    a, b = coord1
    c, d = coord2
    return math.sqrt((a-c)**2 + (b-d)**2)
    # return (coord1 - coord2).norm()