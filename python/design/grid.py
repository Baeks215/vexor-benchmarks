N = 50

import math

import drawsvg as draw

TOTAL_SHAPES = N * N

d = draw.Drawing(1000, 1000, viewBox="0 0 1000 1000")

spacing = 1000.0 / (N + 1)

# Single flat pass over every cell index in [1..N*N]; row/col are recovered
# arithmetically, so one loop replaces the nested r/c loops.
for i in range(1, TOTAL_SHAPES + 1):
    r = (i - 1) // N + 1
    c = (i - 1) % N + 1

    # Calculate coordinate offsets using overlapping wave math
    x = c * spacing
    y = r * spacing + (math.sin(c * 0.5) * 10.0)

    # Dynamic math-driven scaling and coloring
    radius = max(1.0, (math.cos(r * 0.3) + 1.5) * 3.0)

    red = int((x / 1000.0) * 255)
    green = int((y / 1000.0) * 255)
    blue = int(((r * c) / TOTAL_SHAPES) * 255)
    fill = f"#{red:02x}{green:02x}{blue:02x}"

    d.append(
        draw.Circle(x, y, radius, fill=fill, stroke="#111111", stroke_width=0.2)
    )

with open("grid.svg", "w") as f:
    f.write(d.as_svg())

print(f"Saved grid.svg with {TOTAL_SHAPES} elements.")
