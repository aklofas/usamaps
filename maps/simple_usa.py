from libmap import Map, Lambert, Mercator, Circle, Polygons, Transform
from unicodedata import normalize

parallels = [20, 60]

imgb_nation = (800, 500)
imgb_state = (530, 600)
imgb_county = (530, 600)



def map_generate(regions, nation, layers):
    states = list(map(lambda s: s['name'], filter(lambda s: s['type'] in ["state", "district"], regions['regions'])))
    proj = Lambert(nation['center'], parallels)
    #proj = Mercator(nation['center'][1])
    
    cut_alaska1 = proj([52.827620, -169.447600])
    cut_alaska2 = proj([51.939180, -128.990621])
    cut_hawaii = proj([28.325120, -138.578629])
    cut_puertorico = proj([19.828075, -68.975487])
    split_alaska1 = lambda p: p[0] < cut_alaska1[0]
    split_puertorico = lambda p: p[0] > cut_puertorico[0] and p[1] > cut_puertorico[1]

    center_alaska = None
    center_hawaii = None

    xform_alaska = None
    xform_hawaii = None


    m2 = Map('nation')
    m2_overlays = []
    for state in nation['states']:
        if state['name'] not in states: continue
        extra = {
            'name': state['name'],
            'abbrev': state['abbrev'],
            'fips': state['fips']
        }

        if state['name'] == "District of Columbia":
            m2_overlays.append(Circle(proj(state['center']), 0.004, extra))

        else:
            obj = Polygons(proj(state['border']), extra=extra)

            if state['name'] == "Alaska":
                obj.split(split_alaska1, returnsplit=False)
                center_alaska = proj(state['center'])
                xform_alaska = (
                    Transform.move(center_alaska, proj([27.945609, -115.466288])) *
                    Transform(scale=(0.37, 0.37), rotate=-27.5, center=proj(state['center']))
                )
                xform_alaska(obj)

            elif state['name'] == "Hawaii":
                center_hawaii = proj(state['center'])
                xform_hawaii = (
                    Transform.move(center_hawaii, proj([26.872555, -104.949767])) *
                    Transform(rotate=-35, center=proj(state['center']))
                )
                xform_hawaii(obj)

            m2.add(obj)
    m2.add(m2_overlays)
    return [m2.tojson(m2.maxbounds(*imgb_nation), sortf=lambda r: r['name'])]

