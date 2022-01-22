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


def region_center(name):
    for r in regions['regions']:
        if r['name'] == name: return r['center']
    raise RuntimeError(f"Region center {name} not found")

def ll_swap(ll):
    return [[[o2[1], o2[0]] for o2 in o1] for o1 in ll]

def ll_format(type, ll):
    if type == "Polygon": return ll_swap(ll)
    elif type == "MultiPolygon": return ll_swap([l[0] for l in ll])


def geo_open(index, key):
    path = f"{CB_PREFIX}{YEAR}/{index[key]['filename']}"
    geo = json_open(path, index[key]['encoding'])
    if geo['type'] != "FeatureCollection":
        raise RuntimeError(f"Bad {path} json format")
    return geo

def geo_features(geo, name, q): return geo[name][q]['features']
def geo_property(feature, name): return feature['properties'][name]
def geo_ll(feature): return ll_format(feature['geometry']['type'], feature['geometry']['coordinates'])

def geo_feature_lookup(geo, name, q, property, value):
    for f in geo_features(geo, name, q):
        if f['properties'][property] == value:
            return f
    raise RuntimeError(f"Feature {name}.{q} with ['{property}'] == '{value}' not found")

geo = {
    'nation': {'lq': geo_open(cb_files, 'national_lq'), 'hq': geo_open(cb_files, 'national_hq')},
    'states': {'lq': geo_open(cb_files, 'states_lq'), 'hq': geo_open(cb_files, 'states_hq')},
    'counties': {'lq': geo_open(cb_files, 'counties_lq'), 'hq': geo_open(cb_files, 'counties_hq')},
    'congressional': {'lq': geo_open(cb_files, 'congressional_lq'), 'hq': geo_open(cb_files, 'congressional_hq')},
    'urbans': {'hq': geo_open(cb_files, 'urbanareas')}
}
#geo_nation = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['national']['filename']}", cb_files['national']['encoding'])
#geo_states = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['states']['filename']}", cb_files['states']['encoding'])
#geo_counties_lq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['counties_lq']['filename']}", cb_files['counties_lq']['encoding'])
#geo_counties_hq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['counties_hq']['filename']}", cb_files['counties_hq']['encoding'])
#geo_congressionals_lq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['congressional_lq']['filename']}", cb_files['congressional_lq']['encoding'])
#geo_congressionals_hq = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['congressional_hq']['filename']}", cb_files['congressional_hq']['encoding'])
#geo_urbans = geo_open(f"{CB_PREFIX}{YEAR}/{cb_files['urbanareas']['filename']}", cb_files['urbanareas']['encoding'])


out = {
    'name': "United States",
    'border': {
        'lq': geo_ll(geo_features(geo, 'nation', 'lq')[0]),
        'hq': geo_ll(geo_features(geo, 'nation', 'hq')[0])
    },
    'center': region_center("United States"),
    'states': [],
    'urbanareas': []
}


# Process states
for geo_state in geo_features(geo, 'states', 'hq'):
    name = geo_property(geo_state, 'NAME')
    statefp = geo_property(geo_state, 'STATEFP')

    # Ignore terratory islands (don't have state data)
    if statefp in ['60', '64', '66', '68', '69', '70', '74', '78']:
        continue

    data = {
        'name': name,
        'center': region_center(name),
        'abbrev': geo_property(geo_state, 'STUSPS'),
        'fips': geo_property(geo_state, 'STATEFP'),
        'land': geo_property(geo_state, 'ALAND') / M2_PER_MI2,
        'water': geo_property(geo_state, 'AWATER') / M2_PER_MI2,
        'border': {
            'lq': geo_ll(geo_feature_lookup(geo, 'states', 'lq', 'NAME', name)),
            'hq': geo_ll(geo_state)
        },
        'counties': [],
        'congressional': [],
        'places': [{
            'name': place['name'],
            'land': place['land'],
            'center': place['center']
        } for place in gaz_places if place['state'] == geo_property(geo_state, 'STUSPS')]
    }
    out['states'].append(data)


# Process counties
for geo_county in geo_features(geo, 'counties', 'hq'):
    geoid = geo_property(geo_county, 'GEOID')
    statefp = geo_property(geo_county, 'STATEFP')

    # Ignore terratory islands (don't have state data)
    if statefp in ['60', '64', '66', '68', '69', '70', '74', '78']:
        continue

    data = {
        'name': gaz_counties[geoid]['name'],
        'center': gaz_counties[geoid]['center'],
        'fips': geo_property(geo_county, 'COUNTYFP'),
        'land': geo_property(geo_county, 'ALAND') / M2_PER_MI2,
        'water': geo_property(geo_county, 'AWATER') / M2_PER_MI2,
        'border': {
            'lq': geo_ll(geo_feature_lookup(geo, 'counties', 'lq', 'GEOID', geoid)),
            'hq': geo_ll(geo_county)
        }
    }

    found = False
    for state in out['states']:
        if state['fips'] == statefp:
            state['counties'].append(data)
            found = True
            break

    if not found:
        raise RuntimeError(f"County not found in states: {data['name']}, {statefp}")


# Process congressional districts
for geo_congressional in geo_features(geo, 'congressional', 'hq'):
    geoid = geo_property(geo_congressional, 'GEOID')
    statefp = geo_property(geo_congressional, 'STATEFP')

    # Ignore terratory islands (don't have state data)
    if statefp in ['60', '64', '66', '68', '69', '70', '74', '78']:
        continue

    if 'NAMELSAD' in geo_congressional['properties']:
        name = geo_congressional['properties']['NAMELSAD']
    else:
        session = geo_congressional['properties']['CDSESSN']
        district = int(geo_congressional['properties'][f"CD{session}FP"], base=10)
        name = f"Congressional District {district}"

    data = {
        'name': name,
        'center': gaz_congressional[geoid]['center'],
        'land': geo_property(geo_congressional, 'ALAND') / M2_PER_MI2,
        'water': geo_property(geo_congressional, 'AWATER') / M2_PER_MI2,
        'border': {
            'lq': geo_ll(geo_feature_lookup(geo, 'congressional', 'lq', 'GEOID', geoid)),
            'hq': geo_ll(geo_congressional)
        }
    }

    found = False
    for state in out['states']:
        if state['fips'] == statefp:
            state['congressional'].append(data)
            found = True
            break

    if not found:
        raise RuntimeError(f"County not found in congressional: {data['name']}, {statefp}")

for geo_urban in geo_features(geo, 'urbans', 'hq'):
    data = {
        'name': geo_property(geo_urban, 'NAME10'),
        'border': {
            'hq': geo_ll(geo_urban)
        }
    }
    out['urbanareas'].append(data)

FILE_OUT.write(dumps(out, sort_keys=True, separators=(',', ':')))