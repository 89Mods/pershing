from __future__ import print_function

import random

from PIL import Image, ImageDraw, ImageFont

from util import blocks

font = ImageFont.load_default()

NORTH = 0
WEST = 1
SOUTH = 2
EAST = 3

def blockid2texture(blockid):
    block_name = blocks.block_names[blockid]
    return lut[block_name]

def pins_to_image(layout_dimensions, pins):
    width = layout_dimensions[2] * 32
    height = layout_dimensions[1] * 32
    img = Image.new("RGBA", size=(width, height), color=(0, 0, 0, 0))

    draw = ImageDraw.Draw(img)
    for name, locations in pins.items():
        for location in locations:
            _, z, x = location
            z *= 32
            x *= 32
            # draw "shadow"
            draw.text((x+1, z+1), name, font=font, fill=(200, 200, 200, 255))
            # draw actual text
            draw.text((x, z), name, font=font, fill=(0, 0, 0, 255))

    del draw

    return img

def layout_to_composite(layout, layers=None, pins=None):
    blocks, data = layout

    # TODO: factor in data
    layout = blocks

    img = None
    
    if layers is None:
        layers = range(layout.shape[0])

    for y in layers:
        new_img = layer_to_img(layout, y)
        # img.save("{}_{}.png".format(filename_base, y))
        # print("Wrote layer {}".format(y))

        if img is None:
            img = new_img
        else:
            img.paste(new_img, mask=new_img)

    if pins is not None:
        pin_img = pins_to_image(layout.shape, pins)
        img.paste(pin_img, mask=pin_img)

    return img

def random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def nets_to_png(layout, routing, filename_base="nets", layers=None):
    img = layout_to_composite(layout, layers)
    draw = ImageDraw.Draw(img)

    for name, net in routing.iteritems():
        color = random_color()
        for segment in net["segments"]:
            u, v = segment["pins"]

            (_, uz, ux), (_, vz, vx) = u, v
            x1 = (ux * 32) + 16
            y1 = (uz * 32) + 16
            x2 = (vx * 32) + 16
            y2 = (vz * 32) + 16
            draw.line((x1, y1, x2, y2), fill=color, width=3)

    full_name = filename_base + ".png"
    img.save(full_name)
    print("Image written to", full_name)

def layout_to_png(layout, filename_base="composite", layers=None):
    img = layout_to_composite(layout, layers)
    full_name = filename_base + ".png"
    img.save(full_name)
    print("Image written to", full_name)

def layer_to_img(layout, y):
    image_width = 32 * layout.shape[2]
    image_height = 32 * layout.shape[1]

    img = Image.new("RGBA", (image_width, image_height))
    for z in range(layout.shape[1]):
        for x in range(layout.shape[2]):
            img_x = x * 32
            img_y = z * 32
            blockid = layout[y, z, x]
            # print(blockid)
            block_name = blocks.block_names[blockid]

            # handle redstone differently
            if block_name in ["redstone_wire"]:
                tile = extract_redstone_texture((y, z, x), layout)
            else:
                tile = lut[block_name]

            img.paste(tile, (img_x, img_y))

    return img

def extract_redstone_texture(coord, layout):
    """
    Generate the image corresponding to the redstone wire at coord, based
    on what's at the adjacent locations that can transmit redstone
    signals.
    """
    connect_directions = [NORTH, WEST, SOUTH, EAST]
    dzdx = [(-1, 0), (0, -1), (1, 0), (0, 1)]

    def conducts(coord, rel_locations):
        y, z, x = coord
        for rl in rel_locations:
            dy, dz, dx = rl
            try:
                if layout[y + dy, z + dz, x + dx] in conductivity_list:
                    return True
            except IndexError:
                pass
        return False

    # follows as north, west, south, east
    connected = [False, False, False, False]

    for i, (dz, dx) in enumerate(dzdx):
        rels = [(-1, dz, dx), (0, dz, dx), (1, dz, dx)]
        connected[i] = connected[i] or conducts(coord, rels)

    key = tuple([direction for yes, direction in zip(connected, connect_directions) if yes])

    return redstone_lut[key]

def create_redstone_textures():
    redstone_cross_alpha = Image.open("./imgs/redstone_dust_cross.png").convert(mode="L")
    redstone_cross = Image.new("RGB", size=(32, 32), color=(127, 0, 0))
    redstone_cross.putalpha(redstone_cross_alpha)

    redstone_line_alpha = Image.open("./imgs/redstone_dust_line.png").convert(mode="L")
    redstone_line = Image.new("RGB", size=(32, 32), color=(127, 0, 0))
    redstone_line.putalpha(redstone_line_alpha)
    redstone_line = redstone_line.rotate(90)

    # Creates a T (with tee down) from the cross
    redstone_t = redstone_cross.copy()
    redstone_t_draw = ImageDraw.Draw(redstone_t)
    redstone_t_draw.rectangle([(0, 0), (31, 8)], fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))
    del redstone_t_draw

    # Create an elbow with east, south directions
    redstone_elbow = redstone_t.copy()
    redstone_elbow_draw = ImageDraw.Draw(redstone_elbow)
    redstone_elbow_draw.rectangle([(0, 0), (8, 31)], fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))
    del redstone_elbow_draw

    redstone_dot = redstone_elbow.copy()
    redstone_dot_draw = ImageDraw.Draw(redstone_dot)
    redstone_dot_draw.rectangle([(24,0), (24, 31)], fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))
    redstone_dot_draw.rectangle([(0,24), (0, 31)], fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))

    redstone_east_west_line = redstone_line.rotate(90)

    textures = {(NORTH, WEST, SOUTH, EAST): redstone_cross,

                (NORTH, SOUTH): redstone_line,
                (WEST, EAST): redstone_east_west_line,

                (WEST, SOUTH, EAST): redstone_t,
                (NORTH, SOUTH, EAST): redstone_t.rotate(90),
                (NORTH, WEST, EAST): redstone_t.rotate(180),
                (NORTH, WEST, SOUTH): redstone_t.rotate(270),

                (SOUTH, EAST): redstone_elbow,
                (NORTH, EAST): redstone_elbow.rotate(90),
                (NORTH, WEST): redstone_elbow.rotate(180),
                (WEST, SOUTH): redstone_elbow.rotate(270),

                (NORTH,): redstone_line,
                (WEST,): redstone_east_west_line,
                (SOUTH,): redstone_line,
                (EAST,): redstone_east_west_line,

                (): redstone_dot
                }

    return textures

blank = Image.new("RGBA", (32, 32))

coords = {"stone": (20, 9),
          "redstone_torch": (19, 3),
          # "redstone_wire": (18, 11),
          "redstone_lamp": (18, 15),
          "unlit_redstone_torch": (19, 2),
          "unpowered_repeater": (19, 5),
          "powered_repeater": (19, 6),
          "unpowered_comparator": (1, 6),
          "powered_comparator": (2, 6),
          "sticky_piston": (15, 15),
          "redstone_block": (18, 10),
          "planks": (16, 4),
          "lever": (10, 13),
          "glass": (10, 13)
         }

lut = {"air": blank}
for name, coord in coords.items():
    lut[name] = Image.open("./imgs/" + name + ".png")

conductivity_list_names = ["redstone_wire", "redstone_torch", "unlit_redstone_torch", "powered_repeater", "unpowered_repeater", "unpowered_comparator", "powered_comparator"]
conductivity_list = [blocks.block_names.index(n) for n in conductivity_list_names]

redstone_lut = create_redstone_textures()
