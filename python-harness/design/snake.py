import math

import drawsvg as draw

steps = 100
head_size = 80
max_dist = 400
revolutions = 2


def make_circle(max_steps):
    def inner(i):
        frac = i / max_steps

        radius = head_size * frac
        color = f"hsl({frac * 360}, 90%, 50%)"

        angle = 2 * math.pi * revolutions * frac
        x = math.cos(angle) * max_dist * frac
        y = math.sin(angle) * max_dist * frac

        return draw.Circle(x, y, radius, fill=color)

    return inner


def make_snake():
    g = draw.Group()
    for c in map(make_circle(steps), range(1, steps + 1)):
        g.append(c)
    return g


d = draw.Drawing(1000, 1000, origin="center")
d.append(make_snake())
d.save_svg("snake.svg")
print("Saved snake.svg")
