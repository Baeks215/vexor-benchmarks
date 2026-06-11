D = 8
# recursion depth; bump to scale complexity (~3^D triangles)

import drawsvg as draw

TOTAL = 3**D

# Three corners of the gasket inside the 1000x1000 canvas.
TOP = (500.0, 60.0)
LEFT = (60.0, 940.0)
RIGHT = (940.0, 940.0)


def clamp8(v):
    """Clamp a channel to a valid 0-255 byte."""
    return max(0, min(255, int(v)))


def midpoint(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def subdivide(p1, p2, p3, depth, elements):
    """Recursively split a triangle into 3 corner sub-triangles (dropping the

    middle) until depth 0, where a single filled triangle is emitted.
    """
    if depth == 0:
        cx = (p1[0] + p2[0] + p3[0]) / 3.0
        cy = (p1[1] + p2[1] + p3[1]) / 3.0
        i = len(elements)

        # Coordinate-based RGB gradient driven by the centroid and emit order.
        red = clamp8(cx / 1000.0 * 255)
        green = clamp8(cy / 1000.0 * 255)
        blue = clamp8(i / max(1, TOTAL) * 255)
        fill = f"#{red:02x}{green:02x}{blue:02x}"

        elements.append(
            draw.Lines(
                p1[0],
                p1[1],
                p2[0],
                p2[1],
                p3[0],
                p3[1],
                close=True,
                fill=fill,
                stroke="#111111",
                stroke_width=0.3,
            )
        )
        return

    m12 = midpoint(p1, p2)
    m23 = midpoint(p2, p3)
    m31 = midpoint(p3, p1)

    subdivide(p1, m12, m31, depth - 1, elements)
    subdivide(m12, p2, m23, depth - 1, elements)
    subdivide(m31, m23, p3, depth - 1, elements)


def generate(depth):
    """Deterministic Sierpinski gasket recursed to the given depth."""
    elements = []
    subdivide(TOP, LEFT, RIGHT, depth, elements)
    return elements


# Initialize the drawing window with an explicit viewBox coordinate field
d = draw.Drawing(1000, 1000, viewBox="0 0 1000 1000")
d.extend(generate(D))

with open("fractal.svg", "w") as f:
    f.write(d.as_svg())

print(f"Saved fractal.svg (depth {D}, {TOTAL} triangles)")
