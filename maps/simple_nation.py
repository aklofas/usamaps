from libmap import Map, Lambert, Circle, Polygons, Transform

parallels = [20, 60]
imgb_nation = (800, 500)

def map_generate(regions, nation, layers):
    states = dict(map(lambda s: (s['name'], s), filter(lambda s: s['type'] in ["state", "district"], regions['regions'])))
    proj = Lambert(nation['center'], parallels)

    center_alaska = proj(states['Alaska']['center'])
    xform_alaska = (
        Transform.move(center_alaska, proj([27.945609, -115.466288])) *
        Transform(scale=(0.37, 0.37), rotate=-27.5, center=center_alaska)
    )
    cut_alaska = proj([52.827620, -169.447600])
    split_alaska = lambda p: p[0] < cut_alaska[0]

    center_hawaii = proj(states['Hawaii']['center'])
    xform_hawaii = (
        Transform.move(center_hawaii, proj([26.872555, -104.949767])) *
        Transform(rotate=-35, center=center_hawaii)
    )
    cut_hawaii = proj([28.325120, -138.578629])

    cut_territories = proj([19.828075, -68.975487])
    split_territories = lambda p: p[0] > cut_territories[0] and p[1] > cut_territories[1]


    # (1) National map
    m1 = Map("national1")
    polys_nation = Polygons(proj(nation['border']['lq']))
    polys_nation.split(split_territories, returnsplit=False)

    obj_hawaii = polys_nation.split(Circle(center_hawaii, cut_hawaii).within)
    xform_hawaii(obj_hawaii)

    polys_nation.split(split_alaska, returnsplit=False)
    obj_alaska = polys_nation.split(Circle(center_alaska, cut_alaska).within)
    xform_alaska(obj_alaska)

    m1.add([polys_nation, obj_alaska, obj_hawaii])


    # (2) National map with state outlines
    m2 = Map("nation2")
    m2_overlays = []
    for state in nation['states']:
        if state['name'] not in states.keys(): continue
        extra = {
            'name': state['name'],
            'abbrev': state['abbrev'],
            #'fips': state['fips']
        }

        if state['name'] == "District of Columbia":
            m2_overlays.append(Circle(proj(state['center']), 0.004, extra))

        else:
            obj = Polygons(proj(state['border']['lq']), extra=extra)

            if state['name'] == "Alaska":
                obj.split(split_alaska, returnsplit=False)
                xform_alaska(obj)

            elif state['name'] == "Hawaii":
                xform_hawaii(obj)

            m2.add(obj)
    m2.add(m2_overlays)

    return [
        m1.tojson(m1.maxbounds(*imgb_nation)),
        m2.tojson(m2.maxbounds(*imgb_nation), sortf=lambda r: r['name'])
    ]
