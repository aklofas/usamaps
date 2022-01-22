from libmap import Map, Lambert, Circle, Polygons, Transform

parallels = [20, 60]
imgb_state = (530, 600)

def map_generate(regions, nation, layers):
    states = dict(map(lambda s: (s['name'], s), regions['regions']))

    out = []
    for state in nation['states']:
        #if state['name'] not in states: continue
        proj = Lambert(state['center'], parallels)

        state_map = Map(state['abbrev'], extra={
            #'name': state['name']
        })
        state_map.add(Polygons(proj(state['border']['hq'])))
        out.append(state_map.tojson(maxbounds=imgb_state))

        county_map = Map(f"{state['abbrev']}-county")
        for county in state['counties']:
            county_map.add(Polygons(proj(county['border']['hq'])))
        out.append(county_map.tojson(maxbounds=imgb_state))

        congressional_map = Map(f"{state['abbrev']}-congressional")
        for congressional in state['congressional']:
            congressional_map.add(Polygons(proj(congressional['border']['hq'])))
        out.append(congressional_map.tojson(maxbounds=imgb_state))

    return out