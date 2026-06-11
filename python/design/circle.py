import drawsvg as draw

# Setup canvas
d = draw.Drawing(200, 200, origin="center")

# Add single circle of radius 100
d.append(draw.Circle(0, 0, 100))

# Export to svg
d.save_svg("circle.svg")
