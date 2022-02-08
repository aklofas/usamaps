from libmap import Map, Lambert, Circle, Polygons, Transform

parallels = [20, 60]
imgb_nation = (120, 100)

def map_generate(regions, nation, layers):
    cut_alaska = [49.579265, -126.239892]
    split_alaska = lambda p: p[0] > cut_alaska[0]

    cut_hawaii = [36.826914, -131.243901]
    split_hawaii = lambda p: p[1] < cut_hawaii[1]

    cut_territories = [19.828075, -68.975487]
    split_territories = lambda p: p[1] > cut_territories[1] and p[0] < cut_territories[0]

    polys_nation = Polygons(nation['border']['lq'])
    polys_nation.split(split_alaska, returnsplit=False)
    polys_nation.split(split_hawaii, returnsplit=False)
    polys_nation.split(split_territories, returnsplit=False)

    proj = Lambert(nation['center'], parallels)
    proj(polys_nation)

    m = Map("nation-logo")
    m.add([polys_nation])

    return [
        m.tojson(m.maxbounds(*imgb_nation))
    ]
