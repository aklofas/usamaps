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
    return "".join(['<path data-name="{name}" d="{d}" />'.format(name=part['name'], d=part['d']) for part in regions if part['type'] == 'path'])

def gensvgcircles(regions):
    return "".join(['<circle data-name="{name}" cx="{cx}" cy="{cy}" r="{r}" />'.format(name=part['name'], cx=part['cx'], cy=part['cy'], r=part['r']) for part in regions if part['type'] == 'circle'])

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
        return '<image x="{x}" y="{y}" width="{width}" height="{height}" xlink:href="data:image/png;base64,{data}" />'.format(x=viewbox['x'], y=viewbox['y'], width=int(viewbox['width']), height=int(viewbox['height']), data=blob.base64())

    else:
        return ""

def gensvg(data):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {width} {height}">'
            '<g fill="#000" stroke="#fff" stroke-width="1">{svgparts_paths}{svgparts_circles}</g>{svgparts_points}'
        '</svg>'
    ).format(x=data['viewbox']['x'], y=data['viewbox']['y'], width=data['viewbox']['width'], height=data['viewbox']['height'], svgparts_paths=gensvgpaths(data['regions']), svgparts_circles=gensvgcircles(data['regions']), svgparts_points=gensvgpoints(data['regions'], data['viewbox']))



def writesvg(filename, data):
    with open(filename, 'w') as fp:
        fp.write(data)


# Make prefix directory if needed
if not isdir(DIR_PREFIX):
	makedirs(DIR_PREFIX)

for data in mapdata:
	writesvg(f"{join(DIR_PREFIX, data['name'])}.svg", gensvg(data))
