from json import load
import PythonMagick as PM
from argparse import ArgumentParser, FileType
from os import makedirs
from os.path import isdir, join
from sys import argv, stderr, stdout, exit

parser = ArgumentParser(description="Generate map image files from input mapdata files")
parser.add_argument('-d', '--directory', metavar='OUT_DIR', action='store', default='build', help="Directory prefix to store image files")
parser.add_argument('-f', '--mapdatafile', metavar='MAPDATA_FILE', type=FileType('r'), action='store', required=True, help="Base map JSON file")
args = parser.parse_args()

DIR_PREFIX = args.directory
FILE_MAPDATA = args.mapdatafile

mapdata = load(FILE_MAPDATA)


def gensvgpaths(regions):
    #return "".join([f'<path data-name="{part["name"]}" d="{part["d"]}" />' for part in regions if part['type'] == 'path'])
    return "".join([f'<path d="{part["d"]}" />' for part in regions if part['type'] == 'path'])

def gensvgcircles(regions):
    return "".join([f'<circle data-name="{part["name"]}" cx="{part["cx"]}" cy="{part["cy"]}" r="{part["r"]}" />' for part in regions if part['type'] == 'circle'])

def gensvgpoints(regions, viewbox):
    geo = None
    img = None
    hasimg = False
    for part in regions:
        if part['type'] == 'points':
            if not hasimg:
                geo = PM.Geometry(int(viewbox['width']), int(viewbox['height']))
                img = PM.Image(geo, PM.Color("none"))
                img.fillColor(PM.Color("red"))
                hasimg = True

            for point in part['points']:
                x1, y1 = (int(point['0']-viewbox['x']), int(point['1']-viewbox['y']))
                x2, y2 = (x1, y1+0.75)
                if x1 < geo.width() and y1 < geo.height():
                    img.draw(PM.DrawableCircle(x1, y1, x2, y2))

    if hasimg:
        blob = PM.Blob()
        #img.quality(100)
        img.magick("png")
        img.write(blob)
        return f'<image x="{viewbox["x"]}" y="{viewbox["y"]}" width="{int(viewbox["width"])}" height="{int(viewbox["height"])}" xlink:href="data:image/png;base64,{blob.base64()}" />'

    else:
        return ""

def gensvg(data):
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{data["viewbox"]["x"]} {data["viewbox"]["y"]} {data["viewbox"]["width"]} {data["viewbox"]["height"]}">'
            f'<g fill="#000" stroke="#fff" stroke-width="1">{gensvgpaths(data["regions"])}{gensvgcircles(data["regions"])}</g>{gensvgpoints(data["regions"], data["viewbox"])}'
        f'</svg>'
    )


# Make prefix directory if needed
if not isdir(DIR_PREFIX):
	makedirs(DIR_PREFIX)

for data in mapdata:
	with open(f"{join(DIR_PREFIX, data['name'])}.svg", 'w') as fp:
		fp.write(gensvg(data))
