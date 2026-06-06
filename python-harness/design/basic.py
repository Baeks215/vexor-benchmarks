import drawsvg as draw

d = draw.Drawing(100, 100, origin="center")
d.append(draw.Circle(0, 0, 30, fill="skyblue", stroke="black", stroke_width=1))

d.save_svg("circle.svg")
print("Saved circle.svg")
