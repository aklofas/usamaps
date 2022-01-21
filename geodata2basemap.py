from json import load, dumps
from argparse import ArgumentParser, FileType
from sys import argv, stdout

M2_PER_MI2 = 2589988.11 # square meters per square mile


parser = ArgumentParser(description="Generate basemap JSON file from geodata census files")
parser.add_argument('-d', '--data', metavar='DATA_DIR', action='store', default='geodata', help="Folder holding geodata census files (cartographic boundaries and gazetteer files)")
parser.add_argument('-r', '--regions', metavar='REGION_FILE', action='store', default='regions.json', type=FileType('r'), help="Geodata regions file")
parser.add_argument('-y', '--year', action='store', default=2020, type=int, help="Year data geodata to parse")
parser.add_argument('-o', '--out', metavar='OUT_FILE', type=FileType('w'), action='store', required=True, help="Write basemap to file specified")
args = parser.parse_args()


DIR_GEODATA = args.data
FILE_REGIONS = args.regions
YEAR = args.year
FILE_OUT = args.out

GAZ_PREFIX = f"{DIR_GEODATA}/gaz/gaz_"
CB_PREFIX = f"{DIR_GEODATA}/cb/cb_"
PATH_GAZFILES = f"{GAZ_PREFIX}{YEAR}/files.json"
PATH_CBFILES = f"{CB_PREFIX}{YEAR}/files.json"


def json_open(path, encoding):
    with open(path, encoding=encoding) as fp:
        return load(fp)

regions = load(FILE_REGIONS)
gaz_files = json_open(PATH_GAZFILES, 'utf-8')
cb_files = json_open(PATH_CBFILES, 'utf-8')


gaz_counties = dict()
with open(f"{GAZ_PREFIX}{YEAR}/{gaz_files['counties']['filename']}", encoding=gaz_files['counties']['encoding']) as gaz_counties_fp:
    next(gaz_counties_fp)
    for line in gaz_counties_fp:
        e = line.split("\t")
        gaz_counties[e[1].strip()] = {
            'name': e[3].strip(),
            'center': [float(e[8].strip()), float(e[9].strip())]
        }

gaz_congressional = dict()
with open(f"{GAZ_PREFIX}{YEAR}/{gaz_files['congressional']['filename']}", encoding=gaz_files['congressional']['encoding']) as gaz_congressional_fp:
    next(gaz_congressional_fp)
    for line in gaz_congressional_fp:
        e = line.split("\t")
        gaz_congressional[e[1].strip()] = {
            'center': [float(e[6].strip()), float(e[7].strip())]
        }

gaz_places = list()
with open(f"{GAZ_PREFIX}{YEAR}/{gaz_files['places']['filename']}", encoding=gaz_files['places']['encoding']) as gaz_places_fp:
    next(gaz_places_fp)
    for line in gaz_places_fp:
        e = line.split("\t")
        gaz_places.append({
            'state': e[0].strip(),
            'name': e[3].strip().rsplit(' ', 1)[0],
            'land': float(e[8].strip()),
            'center': [float(e[10].strip()), float(e[11].strip())]
        })


def geo_open(path, encoding):
    geo = json_open(path, encoding)
    if geo['type'] != "FeatureCollection":
        raise RuntimeError(f"Bad {path} json format")
    return geo

geo_nation = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['national']['filename']}", cb_files['national']['encoding'])
geo_states = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['states']['filename']}", cb_files['states']['encoding'])
geo_counties_lq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['counties_lq']['filename']}", cb_files['counties_lq']['encoding'])
geo_counties_hq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['counties_hq']['filename']}", cb_files['counties_hq']['encoding'])
geo_congressionals_lq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['congressional_lq']['filename']}", cb_files['congressional_lq']['encoding'])
geo_congressionals_hq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['congressional_hq']['filename']}", cb_files['congressional_hq']['encoding'])
geo_urbans = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['urbanareas']['filename']}", cb_files['urbanareas']['encoding'])



def region_center(name):
    for r in regions['regions']:
        if r['name'] == name: return r['center']
    raise RuntimeError(f"Region center {name} not found")

def ll_swap(ll):
    return [[[o2[1], o2[0]] for o2 in o1] for o1 in ll]

def ll_format(type, ll):
    if type == "Polygon": return ll_swap(ll)
    elif type == "MultiPolygon": return ll_swap([l[0] for l in ll])

out = {
    'name': "United States",
    'border': ll_format(geo_nation['features'][0]['geometry']['type'], geo_nation['features'][0]['geometry']['coordinates']),
    'center': region_center("United States"),
    'states': [],
    'urbanareas': []
}

for geo_state in geo_states['features']:
    name = geo_state['properties']['NAME']
    data = {
        'name': name,
        'abbrev': geo_state['properties']['STUSPS'],
        'fips': geo_state['properties']['STATEFP'],
        'land': geo_state['properties']['ALAND'] / M2_PER_MI2,
        'water': geo_state['properties']['AWATER'] / M2_PER_MI2,
        'border': ll_format(geo_state['geometry']['type'], geo_state['geometry']['coordinates']),
        'center': region_center(name),
        'counties_lq': [],
        'counties_hq': [],
        'congressional_lq': [],
        'congressional_hq': [],
        'places': [{'name': place['name'], 'land': place['land'], 'center': place['center']} for place in gaz_places if place['state'] == geo_state['properties']['STUSPS']]
    }
    out['states'].append(data)

# Process counties
for geo_counties_q in [(geo_counties_lq, 'counties_lq'), (geo_counties_hq, 'counties_hq')]:
    geo_counties = geo_counties_q[0]
    key_counties = geo_counties_q[1]

    for geo_county in geo_counties['features']:
        # Ignore terratory islands (don't have state data)
        if geo_county['properties']['STATEFP'] in ['60', '64', '66', '68', '69', '70', '74', '78']:
            continue

        data = {
            'name': gaz_counties[geo_county['properties']['GEOID']]['name'],
            'fips': geo_county['properties']['COUNTYFP'],
            'land': geo_county['properties']['ALAND'] / M2_PER_MI2,
            'water': geo_county['properties']['AWATER'] / M2_PER_MI2,
            'border': ll_format(geo_county['geometry']['type'], geo_county['geometry']['coordinates']),
            'center': gaz_counties[geo_county['properties']['GEOID']]['center']
        }

        found = False
        for state in out['states']:
            if state['fips'] == geo_county['properties']['STATEFP']:
                state[key_counties].append(data)
                found = True
                break

        if not found:
            raise RuntimeError(f"County not found in states: {data['name']}, {geo_county['properties']['STATEFP']}")

# Process congressional districts
for geo_congressionals_q in [(geo_congressionals_lq, 'congressional_lq'), (geo_congressionals_hq, 'congressional_hq')]:
    geo_congressionals = geo_congressionals_q[0]
    key_congressionals = geo_congressionals_q[1]

    for geo_congressional in geo_congressionals['features']:
        # Ignore terratory islands (don't have state data)
        if geo_congressional['properties']['STATEFP'] in ['60', '64', '66', '68', '69', '70', '74', '78']:
            continue

        if 'NAMELSAD' in geo_congressional['properties']:
            name = geo_congressional['properties']['NAMELSAD']
        else:
            session = geo_congressional['properties']['CDSESSN']
            district = int(geo_congressional['properties'][f"CD{session}FP"], base=10)
            name = f"Congressional District {district}"

        data = {
            'name': name,
            'land': geo_congressional['properties']['ALAND'] / M2_PER_MI2,
            'water': geo_congressional['properties']['AWATER'] / M2_PER_MI2,
            'border': ll_format(geo_congressional['geometry']['type'], geo_congressional['geometry']['coordinates']),
            'center': gaz_congressional[geo_congressional['properties']['GEOID']]['center']
        }

        found = False
        for state in out['states']:
            if state['fips'] == geo_congressional['properties']['STATEFP']:
                state[key_congressionals].append(data)
                found = True
                break

        if not found:
            raise RuntimeError(f"County not found in congressional: {data['name']}, {geo_congressional['properties']['STATEFP']}")

for geo_urban in geo_urbans['features']:
    data = {
        'name': geo_urban['properties']['NAME10'],
        'border': ll_format(geo_urban['geometry']['type'], geo_urban['geometry']['coordinates'])
    }
    out['urbanareas'].append(data)

FILE_OUT.write(dumps(out, sort_keys=True, separators=(',', ':')))