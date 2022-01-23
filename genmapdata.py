from json import load, dumps
from argparse import ArgumentParser, FileType
from importlib.util import spec_from_file_location, module_from_spec
from sys import path

parser = ArgumentParser(description="Generate mapdata file from input JSON files")
parser.add_argument('-r', '--regions', action='store', default='regions.json', type=FileType('r'), help="Geodata regions file")
#parser.add_argument('-s', '--scriptdir', action='store', default='maps', help="Directory with the map scripts")
parser.add_argument('-m', '--mapscript', metavar='MAP_SCRIPT', action='store', required=True, help="Mapfile script to execute")
parser.add_argument('-b', '--base', metavar='BASE_FILE', type=FileType('r'), action='store', required=True, help="Base map JSON file")
parser.add_argument('-l', '--layer', metavar='LAYER_FILE', nargs='+', type=FileType('r'), action='store', help="List of layer JSON files to parse and add to map")
parser.add_argument('-o', '--out', metavar='OUT_FILE', type=FileType('w'), action='store', required=True, help="Write map data output to file specified")
args = parser.parse_args()

FILE_REGIONS = args.regions
#PATH_SCRIPTDIR = args.scriptdir
FILE_MAPSCRIPT = args.mapscript
FILE_BASE = args.base
FILE_LAYERS = args.layer
FILE_OUT = args.out

regions = load(FILE_REGIONS)
basemap = load(FILE_BASE)
layers = []

path.extend(['lib'])
spec = spec_from_file_location("mapscript", FILE_MAPSCRIPT)
mapscript = module_from_spec(spec)

spec.loader.exec_module(mapscript)
mapdata = mapscript.map_generate(regions, basemap, layers)

FILE_OUT.write(dumps(mapdata, sort_keys=True, separators=(',', ':')))