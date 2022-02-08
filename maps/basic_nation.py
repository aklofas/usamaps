from libmap import Map, Lambert, Circle, Polygons, Transform

parallels = [20, 60]
imgb_nation = (800, 500)

def map_generate(regions, nation, layers):
    states = dict(map(lambda s: (s['name'], s), regions['regions']))


    # (1) National map
    polys_nation = Polygons(nation['border']['lq'])
    proj_nation = Lambert(nation['center'], parallels)


    center_alaska = states['Alaska']['center']
    cut_alaska = [49.149804, -169.447600]
    split_alaska = lambda p: p[1] > 0 or (p[0] > cut_alaska[0] and p[1] < cut_alaska[1])
    
    polys_nation.split(split_alaska, returnsplit=False)
    obj_alaska = polys_nation.split(Circle(center_alaska, cut_alaska).within)

    proj_alaska = Lambert(center_alaska, parallels)
    xform_alaska = (
        Transform.move([0, 0], proj_nation([27.945609, -115.466288])) *
        Transform(scale=(0.37, 0.37), rotate=7.5)
    )

    proj_alaska(obj_alaska)
    xform_alaska(obj_alaska)


    center_hawaii = states['Hawaii']['center']
    cut_hawaii = [28.325120, -138.578629]

    obj_hawaii = polys_nation.split(Circle(center_hawaii, cut_hawaii).within)
    
    proj_hawaii = Lambert(center_hawaii, parallels)
    xform_hawaii = (
        Transform.move([0, 0], proj_nation([26.872555, -104.949767]))
    )

    proj_hawaii(obj_hawaii)
    xform_hawaii(obj_hawaii)


    center_puertorico = states['Puerto Rico']['center']
    cut_puertorico = [22.672492, -70.995562]

    obj_puertorico = polys_nation.split(Circle(center_puertorico, cut_puertorico).within)

    proj_puertorico = Lambert(center_puertorico, parallels)
    xform_puertorico = (
        Transform.move([0, 0], proj_nation([24.028488, -75.910581])) *
        Transform(scale=(1.4, 1.4))
    )

    proj_puertorico(obj_puertorico)
    xform_puertorico(obj_puertorico)


    proj_nation(polys_nation)

    m1 = Map("National1")
    m1.add([polys_nation, obj_alaska, obj_hawaii, obj_puertorico])


    # (2) National map with state outlines
    m2 = Map("Nation2")
    m2_overlays = []
    for state in nation['states']:
        if state['name'] not in states.keys(): continue
        extra = {
            'data-name': state['name'],
            'data-abbrev': state['abbrev']
        }

        if state['name'] == "District of Columbia":
            m2_overlays.append(Circle(state['center'], 0.004, extra=extra))

        else:
            border = state['border']['lq']
            if border is None: continue

            obj = Polygons(border, extra=extra)

            if state['name'] == "Alaska":
                obj.split(split_alaska, returnsplit=False)
                proj_alaska(obj)
                xform_alaska(obj)

            elif state['name'] == "Hawaii":
                proj_hawaii(obj)
                xform_hawaii(obj)

            elif state['name'] == "Puerto Rico":
                proj_puertorico(obj)
                xform_puertorico(obj)

            else:
                proj_nation(obj)

            m2.add(obj)
    m2.add(m2_overlays)

    return [
        m1.tojson(m1.maxbounds(*imgb_nation)),
        m2.tojson(m2.maxbounds(*imgb_nation), sortf=lambda r: r['data-name'])
    ]
