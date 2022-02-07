from json import load, dumps
from unicodedata import normalize
from copy import deepcopy
from math import radians, degrees, sin, cos, tan, atan, sinh, asinh, pow, log, sqrt, pi
from numpy import sign, matmul
from shapely.geometry import Point as ShPoint
from shapely.geometry.polygon import Polygon as ShPolygon
from sys import argv, stderr, stdout, exit


numfmt = 2

depth = lambda L: isinstance(L, (tuple, list, dict)) and max(map(depth, L))+1
itertype = lambda L: isinstance(L, (Group, Polygons, Points, Circle))
fmt = lambda n: (("%."+str(numfmt)+"f") % n).rstrip('0').rstrip('.')
#name = lambda n: normalize('NFKD', n).encode("ascii", "ignore")
sec = lambda r: 1.0 / cos(r)
cot = lambda r: cos(r)/sin(r)

class _Projection:
    def wraptype(t, a, b):
        if type(t) is tuple: return (a, b)
        elif type(t) is list: return [a, b]
        elif type(t) is dict:
            r = t.copy()
            r[0] = a
            r[1] = b
            return r

# http://mathworld.wolfram.com/LambertConformalConicProjection.html
# Params: ll = Lat/Lon, cll = Center Lat/Lon, pl = Parallels
class Lambert(_Projection):
    def __init__(self, cll, pl):
        self.cll_r = (radians(cll[0]), radians(cll[1]))
        self.pl_r = (radians(pl[0]), radians(pl[1]))

    def __call__(self, ll):
        if depth(ll) > 1: return [self.__call__(l) for l in ll]
        ll_r = [radians(ll[0]), radians(ll[1])]

        # Handle wrap-around
        while ll_r[1]-self.cll_r[1] > pi: ll_r[1] = ll_r[1] - 2*pi
        while ll_r[1]-self.cll_r[1] < -pi: ll_r[1] = ll_r[1] + 2*pi

        n = log(cos(self.pl_r[0])*sec(self.pl_r[1]))/log(tan(0.25*pi+0.5*self.pl_r[1])*cot(0.25*pi+0.5*self.pl_r[0]))
        F = cos(self.pl_r[0]) * pow(tan(0.25*pi+0.5*self.pl_r[0]), n)/n
        r = F*pow(cot(0.25*pi+0.5*ll_r[0]), n)
        r0 = F*pow(cot(0.25*pi+0.5*self.cll_r[0]), n)

        x = r*sin(n*(ll_r[1]-self.cll_r[1]))
        y = r0-r*cos(n*(ll_r[1]-self.cll_r[1]))

        ll[0] = x
        ll[1] = -y
        #return _Projection.wraptype(ll, x, -y)


    def inv(self, p):
        if depth(p) > 1: return [self.inv(i) for i in p]
        x = p[0]
        y = -p[1]

        n = log(cos(self.pl_r[0])*sec(self.pl_r[1]))/log(tan(0.25*pi+0.5*self.pl_r[1])*cot(0.25*pi+0.5*self.pl_r[0]))
        F = cos(self.pl_r[0]) * pow(tan(0.25*pi+0.5*self.pl_r[0]), n)/n
        r0 = F*pow(cot(0.25*pi+0.5*self.cll_r[0]), n)
        r = sign(n)*sqrt(x**2+(r0-y)**2)

        lat_r = 2*atan(pow(F/r,1/n))-0.5*pi
        lon_r = self.cll_r[1]+atan(x/(r0-y))/n

        return _Projection.wraptype(p, degrees(lat_r), degrees(lon_r))

# https://mathworld.wolfram.com/MercatorProjection.html
# Params: ll = Lat/Lon, clon = Center Lon
class Mercator(_Projection):
    def __init__(self, clon):
        self.clon_r = radians(clon)

    def __call__(self, ll):
        if depth(ll) > 1: return [self.__call__(l) for l in ll]
        ll_r = [radians(ll[0]), radians(ll[1])]

        # Handle wrap-around
        while ll_r[1]-self.clon_r > pi: ll_r[1] = ll_r[1] - 2*pi
        while ll_r[1]-self.clon_r < -pi: ll_r[1] = ll_r[1] + 2*pi

        x = ll_r[1]-self.clon_r
        y = asinh(tan(ll_r[0]))

        ll[0] = x
        ll[1] = -y
        #return _Projection.wraptype(ll, x, -y)

    def inv(self, p):
        if depth(p) > 1: return [self.inv(i) for i in p]
        x = p[0]
        y = -p[1]

        lat_r = atan(sinh(y))
        lon_r = self.clon_r+x

        return _Projection.wraptype(p, degrees(lat_r), degrees(lon_r))



class _Transform:
    def __init__(self, M):
        self.M = M

    def __call__(self, data):
        if len(data) == 0: return
        if itertype(data): data.bbox = None
        if itertype(data) or itertype(data[0]) or depth(data) > 1:
            for d in data: self.__call__(d)
            return
        a = matmul(self.M, [[data[0]],[data[1]],[1]])
        data[0] = a[0][0]
        data[1] = a[1][0]

    def __mul__(self, other):
        return _Transform(matmul(self.M, other.M))


class Transform:
    def __init__(self, translate=(0,0), scale=(1,1), rotate=0, center=(0,0)):
        r = radians(rotate)
        Me = [[1,0,translate[0]],[0,1,translate[1]],[0,0,1]]
        Md = [[1,0,center[0]],[0,1,center[1]],[0,0,1]]
        Mc = [[scale[0],0,0],[0,scale[1],0],[0,0,1]]
        Mb = [[cos(r),-sin(r),0],[sin(r),cos(r),0],[0,0,1]]
        Ma = [[1,0,-center[0]],[0,1,-center[1]],[0,0,1]]
        self.M = matmul(Me, matmul(Md, matmul(Mc, matmul(Mb, Ma))))

    def __call__(self, data):
        _Transform(self.M).__call__(data)

    def __mul__(self, other):
        return _Transform(self.M).__mul__(other)

    @classmethod
    def move(cls, pfrom, pto):
        return cls(translate=(pto[0]-pfrom[0], pto[1]-pfrom[1]))

class Bounds:
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def enlarge(self, other):
        if other.min is None or other.max is None:
            return

        if self.min is None or self.max is None:
            self.min = other.min
            self.max = other.max
            return

        self.min = (min(self.min[0], other.min[0]), min(self.min[1], other.min[1]))
        self.max = (max(self.max[0], other.max[0]), max(self.max[1], other.max[1]))

    def intersect(self, other):
        if self.min is None or other.min is None or self.max is None or other.max is None:
            return False
        return (
            (self.min[0] <= other.min[0] <= self.max[0] and self.min[1] <= other.min[1] <= self.max[1]) or
            (self.min[0] <= other.max[0] <= self.max[0] and self.min[1] <= other.max[1] <= self.max[1]) or
            (other.min[0] <= self.min[0] <= other.max[0] and other.min[1] <= self.min[1] <= other.max[1]) or
            (other.min[0] <= self.max[0] <= other.max[0] and other.min[1] <= self.max[1] <= other.max[1])
        )

    #def __lt__(a, b):
    #    if a.min is None or b.min is None or a.max is None or b.max is None:
    #        return False
    #    return a.max[0] < b.min[0] or a.max[1] < b.min[1]

    #@classmethod
    #def empty(cls):
    #    return cls(None, None)

    @classmethod
    def union(cls, bds):
        bds = list(filter(None, bds))
        return cls(
                (min(bds, key=lambda b: b.min[0]).min[0], min(bds, key=lambda b: b.min[1]).min[1]),
                (max(bds, key=lambda b: b.max[0]).max[0], max(bds, key=lambda b: b.max[1]).max[1])
            ) if len(bds) > 0 else None


class Group:
    def __init__(self, items):
        self.items = items
        self.bbox = None

    def add(self, item): self.items.add(item)
    def update(self, extra):
        for i in self.items: i.update(extra)

    def __iter__(self): return self.items.__iter__()
    def __getitem__(self, key): return self.items.__getitem__(key)
    def __len__(self): return len(self.items)

    def split(self, filt, returnsplit=True, removesplit=True):
        self.bbox = None
        return Group([i.split(filt, returnsplit=returnsplit, removesplit=removesplit) for i in self.items])

    def bounds(self):
        if self.bbox is not None: return self.bbox
        bounds = [i.bounds() for i in self.items]
        self.bbox = Bounds.union(bounds) if len(bounds) > 0 else None
        return self.bbox

    def apply(self, f):
        self.bbox = None
        for i in self.items: i.apply(f)

    def tojson(self):
        return [i for item in self.items for i in item.tojson()]


class Polygons:
    def __init__(self, polys, extra={}):
        self.polys = polys
        self.extra = extra
        self.bbox = None

    def update(self, extra):
        self.extra.update(extra)

    def __iter__(self): return self.polys.__iter__()
    def __getitem__(self, key): return self.polys.__getitem__(key)
    def __len__(self): return len(self.polys)

    def split(self, filt, returnsplit=True, removesplit=True):
        self.bbox = None
        splitd = [any(filt(p) for p in poly) for poly in self.polys]
        newpolys = None
        if returnsplit: newpolys = Polygons([self.polys[i] for i in range(len(self.polys)) if splitd[i]], extra=deepcopy(self.extra))
        if removesplit: self.polys = [self.polys[i] for i in range(len(self.polys)) if not splitd[i]]
        return newpolys

    def bounds(self):
        if self.bbox is not None: return self.bbox
        xs = [p[0] for poly in self.polys for p in poly]
        ys = [p[1] for poly in self.polys for p in poly]
        self.bbox = Bounds((min(xs), min(ys)), (max(xs), max(ys))) if len(xs) > 0 else None
        return self.bbox

    def apply(self, f):
        self.bbox = None
        for poly in self.polys:
            for p in poly:
                f(p)

    def tosvgpath(self):
        cmds = []
        for poly in self.polys:
            cmds.extend(["M", fmt(poly[0][0]), fmt(poly[0][1])])
            
            lastcmd = None
            deltas = [[poly[i+1][0]-poly[i][0], poly[i+1][1]-poly[i][1]] for i in range(len(poly)-1)]

            for i in range(len(deltas)):
                d = deltas[i]
                th = 10**-numfmt
                if abs(d[0]) < th and abs(d[1]) < th:
                    if i < len(deltas)-1:
                        deltas[i+1][0] = deltas[i+1][0]+d[0]
                        deltas[i+1][1] = deltas[i+1][1]+d[1]
                    continue
                elif abs(d[0]) < th: cmd = ["v", fmt(d[1])]
                elif abs(d[1]) < th: cmd = ["h", fmt(d[0])]
                else: cmd = ["l", fmt(d[0]), fmt(d[1])]
                cmds.extend(cmd if cmd[0] != lastcmd else cmd[1:])
                lastcmd = cmd[0]
            cmds.append("z")

        data = []
        for i in range(len(cmds)):
            if i > 0 and not cmds[i-1][-1].isdigit(): data.append(cmds[i])
            elif cmds[i][0].isdigit(): data.extend([" ", cmds[i]])
            else: data.append(cmds[i])
        return "".join(data)

    def tojson(self):
        j = {'type': 'path', 'd': self.tosvgpath()}
        j.update(self.extra)
        return [j]


class Points:
    def __init__(self, points, extra={}):
        self.points = points
        self.extra = extra
        self.bbox = None

    def update(self, extra):
        self.extra.update(extra)

    def __iter__(self): return self.points.__iter__()
    def __getitem__(self, key): return self.points.__getitem__(key)
    def __len__(self): return len(self.points)

    def split(self, filt, returnsplit=True, removesplit=True):
        self.bbox = None
        splitd =  [filt(point) for point in self.points]
        newpoints = None
        if returnsplit: newpoints = Points([self.points[i] for i in range(len(self.points)) if splitd[i]], extra=deepcopy(self.extra))
        if removesplit: self.points = [self.points[i] for i in range(len(self.points)) if not splitd[i]]
        return newpoints

    def splitinside(self, polys, returnsplit=True, removesplit=True):
        self.bbox = None
        bounds = polys.bounds()
        shpolys = [ShPolygon([(point[0], point[1]) for point in poly]) for poly in polys.polys]
        return self.split(lambda p: any(
                p[0] >= bounds.min[0] and p[0] <= bounds.max[0] and
                p[1] >= bounds.min[1] and p[1] <= bounds.max[1] and
                shpoly.contains(ShPoint(p[0], p[1]))
            for shpoly in shpolys), returnsplit, removesplit)

    def bounds(self):
        if self.bbox is not None: return self.bbox
        xs = [point[0] for point in self.points]
        ys = [point[1] for point in self.points]
        self.bbox = Bounds((min(xs), min(ys)), (max(xs), max(ys))) if len(xs) > 0 else None
        return self.bbox

    def apply(self, f):
        self.bbox = None
        for p in self.points: f(p)

    def __fmt(self, pt):
        pt = deepcopy(pt)
        pt[0] = int(pt[0])
        pt[1] = int(pt[1])
        return pt

    def tojson(self):
        j = {'type': 'points', 'points': map(self.__fmt, self.points)}
        j.update(self.extra)
        return [j]


class Circle:
    def __init__(self, center, radius, extra={}):
        if depth(radius): self.points = [center, radius]
        else: self.points = [center, [center[0]+radius, center[1]]]
        self.extra = extra
        self.bbox = None

    def update(self, extra):
        self.extra.update(extra)

    def __iter__(self): return self.points.__iter__()
    def __getitem__(self, key): return self.points.__getitem__(key)
    def __len__(self): return 1

    def radius(self):
        return sqrt((self.points[0][0]-self.points[1][0])**2 + (self.points[0][1]-self.points[1][1])**2)

    def within(self, point):
        return sqrt((self.points[0][0]-point[0])**2 + (self.points[0][1]-point[1])**2) < self.radius()

    def bounds(self):
        if self.bbox is not None: return self.bbox
        r = self.radius()
        self.bbox = Bounds((self.points[0][0]-r, self.points[0][1]-r), (self.points[0][0]+r, self.points[0][1]+r))

    def apply(self, f):
        self.bbox = None
        for p in self.points: f(p)

    def tojson(self):
        j = {'type': 'circle', 'cx': fmt(self.points[0][0]), 'cy': fmt(self.points[0][1]),'r': fmt(self.radius())}
        j.update(self.extra)
        return [j]


class Map:
    def __init__(self, name, extra={}):
        self.name = name
        self.regions = []
        self.extra = extra

    def add(self, region):
        if type(region) == list: self.regions.extend(region)
        else: self.regions.append(region)

    def viewbox(self):
        bounds = Bounds.union([r.bounds() for r in self.regions])
        #if bounds is None: bounds = Bounds((0,0), (0,0))
        return {'x': bounds.min[0], 'y': bounds.min[1], 'width': bounds.max[0]-bounds.min[0], 'height': bounds.max[1]-bounds.min[1]}

    def maxbounds(self, maxwidth, maxheight):
        vb = self.viewbox()
        return min(maxwidth/vb['width'], maxheight/vb['height'])

    def apply(self, f):
        for r in self.regions: r.apply(f)

    def tojson(self, scale=1.0, maxbounds=None, sortf=None):
        if maxbounds is not None: scale = self.maxbounds(*maxbounds)
        Transform(scale=(scale, scale))(self.regions)
        vb = self.viewbox()
        j = {'name': self.name, 'viewbox': {'x': int(vb['x']), 'y': int(vb['y']), 'width': int(vb['width']), 'height': int(vb['height'])}, 'regions': [r for region in self.regions for r in region.tojson()]}
        if sortf is not None: j['regions'].sort(key=sortf)
        j.update(self.extra)
        return j
