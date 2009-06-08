#!/usr/bin/python
# art3d.py, original mplot3d version by John Porter
# Parts rewritten by Reinier Heeres <reinier@heeres.eu>

'''
Module containing 3D artist code and functions to convert 2D
artists into 3D versions which can be added to an Axes3D.
'''

from matplotlib import lines, text as mtext, path as mpath, colors as mcolors
from matplotlib.collections import Collection, LineCollection, \
        PolyCollection, PatchCollection
from matplotlib.patches import Patch
from matplotlib.colors import Normalize
from matplotlib.cbook import iterable

import numpy as np
import math
import proj3d

def norm_angle(a):
    """Return angle between -180 and +180"""
    a = (a + 360) % 360
    if a > 180:
        a = a - 360
    return a

def norm_text_angle(a):
    """Return angle between -90 and +90"""
    a = (a + 180) % 180
    if a > 90:
        a = a - 180
    return a

def get_dir_vector(zdir):
    if zdir == 'x':
        return np.array((1, 0, 0))
    elif zdir == 'y':
        return np.array((0, 1, 0))
    elif zdir == 'z':
        return np.array((0, 0, 1))
    elif zdir == None:
        return np.array((0, 0, 0))
    elif iterable(zdir) and len(zdir) == 3:
        return zdir
    else:
        raise ValueError("'x', 'y', 'z', None or vector of length 3 expected")

class Text3D(mtext.Text):
    '''
    Text object with 3D position and (in the future) direction.
    '''

    def __init__(self, x=0, y=0, z=0, text='', zdir='z'):
        mtext.Text.__init__(self, x, y, text)
        self.set_3d_properties(z, zdir)

    def set_3d_properties(self, z=0, zdir='z'):
        x, y = self.get_position()
        self._position3d = np.array((x, y, z))
        self._dir_vec = get_dir_vector(zdir)

    def draw(self, renderer):
        proj = proj3d.proj_trans_points([self._position3d, \
                self._position3d + self._dir_vec], renderer.M)
        dx = proj[0][1] - proj[0][0]
        dy = proj[1][1] - proj[1][0]
        if dx==0. and dy==0.:
            # atan2 raises ValueError: math domain error on 0,0
            angle = 0.
        else:
            angle = math.degrees(math.atan2(dy, dx))
        self.set_position((proj[0][0], proj[1][0]))
        self.set_rotation(norm_text_angle(angle))
        mtext.Text.draw(self, renderer)

def text_2d_to_3d(obj, z=0, zdir='z'):
    """Convert a Text to a Text3D object."""
    obj.__class__ = Text3D
    obj.set_3d_properties(z, zdir)

class Line3D(lines.Line2D):
    '''
    3D line object.
    '''

    def __init__(self, xs, ys, zs, *args, **kwargs):
        lines.Line2D.__init__(self, [], [], *args, **kwargs)
        self._verts3d = xs, ys, zs

    def set_3d_properties(self, zs=0, zdir='z'):
        xs = self.get_xdata()
        ys = self.get_ydata()
        try:
            zs = float(zs)
            zs = [zs for x in xs]
        except:
            pass
        self._verts3d = juggle_axes(xs, ys, zs, zdir)

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_data(xs, ys)
        lines.Line2D.draw(self, renderer)

def line_2d_to_3d(line, zs=0, zdir='z'):
    '''
    Convert a 2D line to 3D.
    '''
    line.__class__ = Line3D
    line.set_3d_properties(zs, zdir)

def path_to_3d_segment(path, z=0, zdir='z'):
    '''Convert a path to a 3D segment.'''
    seg = []
    for (pathseg, code) in path.iter_segments():
        seg.append(pathseg)
    seg3d = [juggle_axes(x, y, z, zdir) for (x, y) in seg]
    return seg3d

def paths_to_3d_segments(paths, zs=0, zdir='z'):
    '''Convert paths from a collection object to 3D segments.'''

    try:
        zs = float(zs)
        zs = [zs] * len(paths)
    except:
        pass

    segments = []
    for path, z in zip(paths, zs):
        segments.append(path_to_3d_segment(path, z, zdir))
    return segments

class Line3DCollection(LineCollection):
    '''
    A collection of 3D lines.
    '''

    def __init__(self, segments, *args, **kwargs):
        LineCollection.__init__(self, segments, *args, **kwargs)

    def set_segments(self, segments):
        '''
        Set 3D segments
        '''
        self._segments3d = segments
        LineCollection.set_segments(self, [])

    def do_3d_projection(self, renderer):
        '''
        Project the points according to renderer matrix.
        '''
        xyslist = [
            proj3d.proj_trans_points(points, renderer.M) for points in
            self._segments3d]
        segments_2d = [zip(xs, ys) for (xs, ys, zs) in xyslist]
        LineCollection.set_segments(self, segments_2d)

        minz = 1e9
        for (xs, ys, zs) in xyslist:
            minz = min(minz, min(zs))
        return minz

    def draw(self, renderer, project=False):
        if project:
            self.do_3d_projection(renderer)
        LineCollection.draw(self, renderer)

def line_collection_2d_to_3d(col, zs=0, zdir='z'):
    """Convert a LineCollection to a Line3DCollection object."""
    segments3d = paths_to_3d_segments(col.get_paths(), zs, zdir)
    col.__class__ = Line3DCollection
    col.set_segments(segments3d)

class Patch3D(Patch):
    '''
    3D patch object.
    '''

    def __init__(self, *args, **kwargs):
        zs = kwargs.pop('zs', [])
        zdir = kwargs.pop('zdir', 'z')
        Patch.__init__(self, *args, **kwargs)
        self.set_3d_properties(zs, zdir)

    def set_3d_properties(self, verts, zs=0, zdir='z'):
        if not iterable(zs):
            zs = [zs] * len(verts)
        self._segment3d = [juggle_axes(x, y, z, zdir) \
                for ((x, y), z) in zip(verts, zs)]
        self._facecolor3d = Patch.get_facecolor(self)

    def get_path(self):
        return self._path2d

    def get_facecolor(self):
        return self._facecolor2d

    def do_3d_projection(self, renderer):
        s = self._segment3d
        xs, ys, zs = zip(*s)
        vxs, vys,vzs, vis = proj3d.proj_transform_clip(xs, ys, zs, renderer.M)
        self._path2d = mpath.Path(zip(vxs, vys))
        # FIXME: coloring
        self._facecolor2d = self._facecolor3d
        return min(vzs)

    def draw(self, renderer):
        Patch.draw(self, renderer)

def patch_2d_to_3d(patch, z=0, zdir='z'):
    """Convert a Patch to a Patch3D object."""
    verts = patch.get_verts()
    patch.__class__ = Patch3D
    patch.set_3d_properties(verts, z, zdir)

class Patch3DCollection(PatchCollection):
    '''
    A collection of 3D patches.
    '''

    def __init__(self, *args, **kwargs):
        PatchCollection.__init__(self, *args, **kwargs)

    def set_3d_properties(self, zs, zdir):
        xs, ys = zip(*self.get_offsets())
        self._offsets3d = juggle_axes(xs, ys, zs, zdir)
        self._facecolor3d = self.get_facecolor()
        self._edgecolor3d = self.get_edgecolor()

    def do_3d_projection(self, renderer):
        xs, ys, zs = self._offsets3d
        vxs, vys, vzs, vis = proj3d.proj_transform_clip(xs, ys, zs, renderer.M)
        #FIXME: mpl allows us no way to unset the collection alpha value
        self._alpha = None
        self.set_facecolors(zalpha(self._facecolor3d, vzs))
        self.set_edgecolors(zalpha(self._edgecolor3d, vzs))
        PatchCollection.set_offsets(self, zip(vxs, vys))

        return min(vzs)

    def draw(self, renderer):
        PatchCollection.draw(self, renderer)

def patch_collection_2d_to_3d(col, zs=0, zdir='z'):
    """Convert a PatchCollection to a Patch3DCollection object."""
    col.__class__ = Patch3DCollection
    col.set_3d_properties(zs, zdir)

class Poly3DCollection(PolyCollection):
    '''
    A collection of 3D polygons.
    '''

    def __init__(self, verts, *args, **kwargs):
        PolyCollection.__init__(self, verts, *args, **kwargs)
        self.set_3d_properties()

    def get_vector(self, segments3d):
        """Optimize points for projection"""
        si = 0
        ei = 0
        segis = []
        points = []
        for p in segments3d:
            points.extend(p)
            ei = si+len(p)
            segis.append((si, ei))
            si = ei
        xs, ys, zs = zip(*points)
        ones = np.ones(len(xs))
        self._vec = np.array([xs, ys, zs, ones])
        self._segis = segis
        self._sort_zpos = min(zs)

    def set_verts(self, verts, closed=True):
        self.get_vector(verts)
        # 2D verts will be updated at draw time
        PolyCollection.set_verts(self, [], closed)

    def set_3d_properties(self):
        self._zsort = 1
        self._facecolors3d = PolyCollection.get_facecolors(self)
        self._edgecolors3d = self.get_edgecolors()

    def do_3d_projection(self, renderer):
        txs, tys, tzs = proj3d.proj_transform_vec(self._vec, renderer.M)
        xyzlist = [(txs[si:ei], tys[si:ei], tzs[si:ei]) \
                for si, ei in self._segis]
        colors = self._facecolors3d

        # if required sort by depth (furthest drawn first)
        if self._zsort:
            z_segments_2d = [(min(zs), zip(xs, ys), c) for
                             (xs, ys, zs), c in zip(xyzlist, colors)]
            z_segments_2d.sort()
            z_segments_2d.reverse()
        else:
            raise ValueError, "whoops"
        segments_2d = [s for z, s, c in z_segments_2d]
        colors = [c for z, s, c in z_segments_2d]
        PolyCollection.set_verts(self, segments_2d)
        self._facecolors2d = colors

        # Return zorder value
        zvec = np.array([[0], [0], [self._sort_zpos], [1]])
        ztrans = proj3d.proj_transform_vec(zvec, renderer.M)
        return ztrans[2][0]

    def get_facecolors(self):
        return self._facecolors2d
    get_facecolor = get_facecolors

    def draw(self, renderer):
        return Collection.draw(self, renderer)

def poly_collection_2d_to_3d(col, zs=None, zdir='z'):
    """Convert a PolyCollection to a Poly3DCollection object."""
    segments_3d = paths_to_3d_segments(col.get_paths(), zs, zdir)
    col.__class__ = Poly3DCollection
    col.set_verts(segments_3d)
    col.set_3d_properties()

def juggle_axes(xs, ys, zs, zdir):
    """
    Reorder coordinates so that zdir
    """
    if zdir == 'x':
        return zs, xs, ys
    elif zdir == 'y':
        return xs, zs, ys
    else:
        return xs, ys, zs

def iscolor(c):
    try:
        return (len(c) == 4 or len(c) == 3) and hasattr(c[0], '__float__')
    except (IndexError):
        return False

def get_colors(c, num):
    """Stretch the color argument to provide the required number num"""

    if type(c) == type("string"):
        c = mcolors.colorConverter.to_rgba(c)

    if iscolor(c):
        return [c] * num
    if len(c) == num:
        return c
    elif iscolor(c):
        return [c] * num
    elif iscolor(c[0]):
        return [c[0]] * num
    else:
        raise ValueError, 'unknown color format %s' % c

def zalpha(colors, zs):
    """Modify the alphas of the color list according to depth"""
    colors = get_colors(colors, len(zs))
    norm = Normalize(min(zs), max(zs))
    sats = 1 - norm(zs) * 0.7
    colors = [(c[0], c[1], c[2], c[3] * s) for c, s in zip(colors, sats)]
    return colors
