"""
A Cairo backend for matplotlib implemented using pycairo
Author: Steve Chaplin
 
Cairo is a vector graphics library with cross-device output support.
Features of Cairo:
 * anti-aliasing
 * alpha channel 
 * in-memory image buffers
 * image files:
   - PNG
   - PostScript (50% complete)
   - SVG        (in development)
   - PDF        (proposed, 0% complete)

http://www.freedesktop.org/Cairo/Home
http://cairographics.org
Requires (in order, all available from Cairo website):
    libpixman, cairo, libsvg, libsvg-cairo, pycairo

Naming Conventions
  * classes MixedUpperCase
  * varables lowerUpper
  * functions underscore_separated


backend_cairo requires Cairo functions that are not (yet?) wrapped by pycairo

/* Add the following to pycairo/cairo/pycairo-context.c */
static PyObject *
pycairo_set_target_png(PyCairoContext *self, PyObject *args)
{
    FILE *file;
    char *filename;
    cairo_format_t format;
    int width, height;

    if (!PyArg_ParseTuple(args, "siii", &filename, &format, &width, &height))
	return NULL;

    if ((file = fopen (filename, "w")) == NULL) {
        PyErr_SetString(PyExc_IOError, "file open failed");
	return NULL;
	}

    cairo_set_target_png(self->ctx, file, format, width, height);
    if (pycairo_check_status(cairo_status(self->ctx)))
	return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
pycairo_set_target_ps(PyCairoContext *self, PyObject *args)
{
    FILE *file;
    char *filename;
    double width_inches, height_inches;
    double x_pixels_per_inch, y_pixels_per_inch;

    if (!PyArg_ParseTuple(args, "sdddd:Context.set_target_ps",
			  &filename, &width_inches, &height_inches, 
			  &x_pixels_per_inch, &y_pixels_per_inch))
	return NULL;

    if ((file = fopen (filename, "w")) == NULL) {
        PyErr_SetString(PyExc_IOError, "file open failed"); /* add err string */
	return NULL;
	}

    cairo_set_target_ps(self->ctx, file, width_inches, height_inches, 
			x_pixels_per_inch, y_pixels_per_inch);
    if (pycairo_check_status(cairo_status(self->ctx)))
	return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
pycairo_show_page(PyCairoContext *self)
{
    cairo_show_page(self->ctx);
    if (pycairo_check_status(cairo_status(self->ctx)))
	return NULL;
    Py_INCREF(Py_None);
    return Py_None;
}

/* Add to static PyMethodDef pycairo_methods[] = { */
    { "set_target_png", (PyCFunction)pycairo_set_target_png, METH_VARARGS },
    { "set_target_ps", (PyCFunction)pycairo_set_target_ps, METH_VARARGS },
    { "show_page", (PyCFunction)pycairo_show_page, METH_NOARGS },
"""

from __future__ import division

import os
import sys
def _fn_name(): return sys._getframe(1).f_code.co_name

from matplotlib import verbose
from matplotlib.numerix import asarray, pi #, fromstring, UInt8, zeros, where, transpose, nonzero, indices, ones, nxfrom matplotlib._matlab_helpers import Gcf
from matplotlib.backend_bases import RendererBase, GraphicsContextBase,\
     FigureManagerBase, FigureCanvasBase, error_msg
from matplotlib.cbook import enumerate, True, False
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

try:
    import cairo
    # version > x, check - later
except:
    verbose.report_error('PyCairo is required to run the Matplotlib Cairo backend')
    raise SystemExit()
backend_version = '0.1.23' # cairo does not report version, yet


DEBUG = False

# the true dots per inch on the screen; should be display dependent
# see http://groups.google.com/groups?q=screen+dpi+x11&hl=en&lr=&ie=UTF-8&oe=UTF-8&safe=off&selm=7077.26e81ad5%40swift.cs.tcd.ie&rnum=5 for some info about screen dpi
PIXELS_PER_INCH = 96

# Image formats that this backend supports - for print_figure()
IMAGE_FORMAT          = ['png', 'ps', 'svg']
IMAGE_FORMAT_DEFAULT  = 'png'


class RendererCairo(RendererBase):
    """
    The renderer handles all the drawing primitives using a graphics
    context instance that controls the colors/styles
    """
    fontweights = {
        100          : cairo.FONT_WEIGHT_NORMAL,
        200          : cairo.FONT_WEIGHT_NORMAL,
        300          : cairo.FONT_WEIGHT_NORMAL,
        400          : cairo.FONT_WEIGHT_NORMAL,
        500          : cairo.FONT_WEIGHT_NORMAL,
        600          : cairo.FONT_WEIGHT_BOLD,
        700          : cairo.FONT_WEIGHT_BOLD,
        800          : cairo.FONT_WEIGHT_BOLD,
        900          : cairo.FONT_WEIGHT_BOLD,
        'ultralight' : cairo.FONT_WEIGHT_NORMAL,
        'light'      : cairo.FONT_WEIGHT_NORMAL,
        'normal'     : cairo.FONT_WEIGHT_NORMAL,
        'medium'     : cairo.FONT_WEIGHT_NORMAL,
        'semibold'   : cairo.FONT_WEIGHT_BOLD,
        'bold'       : cairo.FONT_WEIGHT_BOLD,
        'heavy'      : cairo.FONT_WEIGHT_BOLD,
        'ultrabold'  : cairo.FONT_WEIGHT_BOLD,
        'black'      : cairo.FONT_WEIGHT_BOLD,
                   }
    fontangles = {
        'italic'  : cairo.FONT_SLANT_ITALIC,
        'normal'  : cairo.FONT_SLANT_NORMAL,
        'oblique' : cairo.FONT_SLANT_OBLIQUE,
        }
    

    def __init__(self, surface, matrix, width, height, dpi):
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        self.surface = surface
        self.matrix  = matrix
        self.width   = width
        self.height  = height
        self.dpi     = dpi    # should not need dpi? Cairo is device independent


    def get_canvas_width_height(self):
        'return the canvas width and height in display coords'
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        return self.width, self.height
    

    def get_text_scale(self):
        """
        Return the scale factor for fontsize taking screendpi and pixels per
        inch into account
        """
        # copied from backend_gtk, is this needed for Cairo?
        return self.dpi.get()/PIXELS_PER_INCH


    def get_text_width_height(self, s, prop, ismath):
        """
        get the width and height in display coords of the string s
        with FontPropertry prop
        """
        #return 1, 1
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        if ismath:
            print 'ismath get_text_width_height() not implemented yet'
            return 1, 1
        else:
            ctx = cairo.Context() # later - save a ctx specifically for this op?
            ctx.select_font (prop.get_name(),
                             self.fontangles [prop.get_style()],
                             self.fontweights[prop.get_weight()])
            scale = self.get_text_scale()
            size  = prop.get_size_in_points()
            ctx.scale_font (scale*size)
        
            w, h = ctx.text_extents (s)[2:4]
            return w, h

                              
    def draw_arc(self, gc, rgbFace, x, y, width, height, angle1, angle2):
        """
        Draw an arc centered at x,y with width and height and angles
        from 0.0 to 360.0.
        If rgbFace is not None, fill the arc with it.
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        # cairo draws circular arcs (width=height) only?
        # could curve_to() and draw a spline instead?
        radius = (height + width) / 4
        ctx    = gc.ctx
        ctx.new_path()
        ctx.arc (x, self.height - y, radius, angle1 * pi/180.0, angle2 * pi/180.0)

        if rgbFace:
            ctx.save()
            ctx.set_rgb_color (*rgbFace)
            ctx.fill()
            ctx.restore()
        ctx.stroke()
    
    
    def draw_image(self, x, y, im, origin, bbox):
        """
        Draw the Image instance into the current axes; x is the
        distance in pixels from the left hand side of the canvas. y is
        the distance from the origin.  That is, if origin is upper, y
        is the distance from top.  If origin is lower, y is the
        distance from bottom

        origin is 'upper' or 'lower'

        bbox is a matplotlib.transforms.BBox instance for clipping, or
        None
        """
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        pass
        # how does cairo do this?
    

    def draw_line(self, gc, x1, y1, x2, y2):
        """
        Draw a single line from x1,y1 to x2,y2
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        ctx = gc.ctx
        ctx.new_path()
        ctx.move_to (x1, self.height - y1)
        ctx.line_to (x2, self.height - y2)
        ctx.stroke()


    def draw_lines(self, gc, x, y):
        """
        x and y are equal length arrays, draw lines connecting each
        point in x, y
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        y = [self.height - y for y in y]
        points = zip(x,y)
        x, y = points.pop(0)
        ctx = gc.ctx
        ctx.new_path()
        ctx.move_to (x, y)

        for x,y in points:
            ctx.line_to (x, y)
        ctx.stroke()


    def draw_point(self, gc, x, y):
        """
        Draw a single point at x,y
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        # render by drawing a 0.5 radius circle
        gc.ctx.new_path()
        gc.ctx.arc (x, self.height - y, 0.5, 0, 2*pi)
        gc.ctx.fill()


    def draw_polygon(self, gc, rgbFace, points):
        """
        Draw a polygon.  points is a len vertices tuple, each element
        giving the x,y coords a vertex.
        If rgbFace is not None, fill the rectangle with it.
        """
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        points = [(x, (self.height-y)) for x,y in points]

        ctx = gc.ctx
        ctx.new_path()
        #x, y = points.pop(0)
        x, y = points[0]
        ctx.move_to (x, y)
        #for x,y in points:
        for x,y in points[1:]:
            ctx.line_to (x, y)
        ctx.close_path()

        if rgbFace:
            ctx.save()
            ctx.set_rgb_color (*rgbFace)
            ctx.fill()
            ctx.restore()
        ctx.stroke()


    def draw_rectangle(self, gc, rgbFace, x, y, width, height):
        """
        Draw a non-filled rectangle at x,y (lower left) with width and height,
        using the GraphicsContext gcEdge.
        Draw a filled rectangle within it of color rgbFace, if rgbFace is not
        None.
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        ctx = gc.ctx
        ctx.new_path()
        ctx.rectangle (x, self.height - y - height, width, height)
        if rgbFace:
            ctx.save()
            ctx.set_rgb_color (*rgbFace)
            ctx.fill()
            ctx.restore()
        ctx.stroke()


    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):    
        """
        Render the matplotlib.text.Text instance at x, y in window
        coords using GraphicsContext gc
        """
        #return
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        ctx = gc.ctx

        if ismath:
            verbose.report_error('Mathtext not implemented yet')
            #self._draw_mathtext(gc, x, y, s, prop, angle)
        else:
            # see also get_text_width_height()
            # text is looking too small - size, scale problem?
            ctx.new_path()
            ctx.move_to (x, y)
            ctx.select_font (prop.get_name(),
                             self.fontangles [prop.get_style()],
                             self.fontweights[prop.get_weight()])
            scale = self.get_text_scale()
            size  = prop.get_size_in_points()

            # rotated text
            # drawable (gtk) target surface - it looks awful
            # yet on the png and ps targets surfaces its fine
            ctx.save()
            if angle:
                ctx.rotate (-angle * pi / 180)
            ctx.scale_font (scale*size)
            ctx.show_text (s)
            ctx.restore()

         
    def flipy(self):
        """return true if y small numbers are top for renderer"""
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        return True  # GTK/GDK default, 0,0 top left origin
        #return False  # Cairo using affine transform (matrix)

    
    def new_gc(self):
        """
        Return an instance of a GraphicsContextCairo
        """
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        gc = GraphicsContextCairo (renderer=self)
        gc.ctx.set_target_surface (self.surface)
        gc.ctx.set_matrix (self.matrix)
        return gc


    def points_to_pixels(self, points):
        """
        Convert points to display units (as a float).
        """
        if DEBUG: print 'backend_cairo.RendererCairo.%s()' % _fn_name()
        return points * PIXELS_PER_INCH/72.0 * self.dpi.get()/72.0


class GraphicsContextCairo(GraphicsContextBase):
    """
    The graphics context provides the color, line styles, etc...
    """
    _joind = {
        'bevel' : cairo.LINE_JOIN_BEVEL,
        'miter' : cairo.LINE_JOIN_MITER,
        'round' : cairo.LINE_JOIN_ROUND,
        }

    _capd = {
        'butt'       : cairo.LINE_CAP_BUTT,
        'projecting' : cairo.LINE_CAP_SQUARE,
        'round'      : cairo.LINE_CAP_ROUND,
        }

    
    def __init__(self, renderer):
        GraphicsContextBase.__init__(self)
        self.renderer = renderer
        self.ctx = cairo.Context()

        
    def set_alpha(self, alpha):
        """
        Set the alpha value used for blending
        """
        self._alpha = alpha
        self.ctx.set_alpha(alpha)


    def set_capstyle(self, cs):
        """
        Set the capstyle as a string in ('butt', 'round', 'projecting')
        """
        if cs in ('butt', 'round', 'projecting'):
            self._capstyle = cs
            self.ctx.set_line_cap (self._capd[cs])
        else:
            error_msg('Unrecognized cap style.  Found %s' % cs)


    def set_clip_rectangle(self, rectangle):
        """
        Set the clip rectangle with sequence (left, bottom, width, height)
        """
        # Cairo clipping is currently extremely slow, so I disabled it
        # cairo/BUGS lists it as a known bug
        self._cliprect = rectangle
        return

        x,y,w,h = rectangle
        ctx = self.ctx
        ctx.new_path()
        ctx.rectangle (x, self.renderer.height - h - y, w, h)

        #ctx.save()     # uncomment to view the clip rectangle
        #ctx.set_rgb_color(1,0,0)
        #ctx.set_line_width(6)
        #ctx.stroke()
        #ctx.restore()        

        ctx.clip ()
        

    def set_dashes(self, offset, dashes):
        self._dashes = offset, dashes
        if dashes == None:
            self.ctx.set_dash([], 0)  # switch dashes off
        else:
            dashes_pixels = self.renderer.points_to_pixels(asarray(dashes))
            self.ctx.set_dash(dashes_pixels, offset)
        

    def set_foreground(self, fg, isRGB=None):
        """
        Set the foreground color.  fg can be a matlab format string, a
        html hex color string, an rgb unit tuple, or a float between 0
        and 1.  In the latter case, grayscale is used.
        """
        GraphicsContextBase.set_foreground(self, fg, isRGB)
        self.ctx.set_rgb_color(*self._rgb)


    def set_joinstyle(self, js):
        """
        Set the join style to be one of ('miter', 'round', 'bevel')
        """
        if js in ('miter', 'round', 'bevel'):
            self._joinstyle = js
            self.ctx.set_line_join(self._joind[js])
        else:
            error_msg('Unrecognized join style.  Found %s' % js)


    def set_linewidth(self, w):
        """
        Set the linewidth in points
        """
        self._linewidth = w
        self.ctx.set_line_width (self.renderer.points_to_pixels(w))

        
########################################################################
#    
# The following functions and classes are for matlab compatibility
# mode (matplotlib.matlab) and implement window/figure managers,
# etc...
#
########################################################################

def draw_if_interactive():
    """
    This should be overriden in a windowing environment if drawing
    should be done in interactive python mode
    """
    if DEBUG: print 'backend_cairo.%s()' % _fn_name()
    pass


def show():
    """
    This is usually the last line of a matlab script and tells the
    backend that it is time to draw.  In interactive mode, this may be
    a do nothing func.  See the GTK backend for an example of how to
    handle interactive versus batch mode
    """
    if DEBUG: print 'backend_cairo.%s()' % _fn_name()
    for manager in Gcf.get_all_fig_managers():
        manager.canvas.realize()


def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    if DEBUG: print 'backend_cairo.%s()' % _fn_name()
    thisFig = Figure(*args, **kwargs)
    canvas  = FigureCanvasCairo(thisFig)
    manager = FigureManagerBase(canvas, num)
    return manager


class FigureCanvasCairo(FigureCanvasBase):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc...

    Public attribute

      figure - A Figure instance
    """

    def draw(self): # not required?
        """
        Draw the figure using the renderer
        """
        if DEBUG: print 'backend_cairo.FigureCanvasCairo.%s()' % _fn_name()
        pass
        #renderer = RendererCairo()  # height, width, figure.dpi
        #self.figure.draw(renderer)
        
        
    def print_figure(self, filename, dpi=150, facecolor='w', edgecolor='w',
                     orientation='portrait'):
        """
        Render the figure to hardcopy.  Set the figure patch face and
        edge colors.  This is useful because some of the GUIs have a
        gray figure face color background and you'll probably want to
        override this on hardcopy

        orientation - only currently applies to PostScript printing.
        """
        if DEBUG: print 'backend_cairo.FigureCanvasCairo.%s()' % _fn_name()

        root, ext = os.path.splitext(filename)       
        ext = ext[1:]
        if ext == '':
            ext      = IMAGE_FORMAT_DEFAULT
            filename = filename + '.' + ext

        # save figure state
        origDPI       = self.figure.dpi.get()
        origfacecolor = self.figure.get_facecolor()
        origedgecolor = self.figure.get_edgecolor()
        
        # settings for printing
        self.figure.dpi.set(dpi)
        self.figure.set_facecolor(facecolor)
        self.figure.set_edgecolor(edgecolor)        

        ext = ext.lower()
        if ext == 'png':
            width, height = self.figure.get_width_height()
            width, height = int(width), int(height)
            ctx = cairo.Context()
            ctx.set_target_png (filename, cairo.FORMAT_ARGB32, width, height) # 4 png formats supported
            renderer = RendererCairo (ctx.target_surface, ctx.matrix, width, height, self.figure.dpi)
            self.figure.draw(renderer)
            ctx.show_page()
            
        elif ext == 'ps': # Cairo produces PostScript Level 3
            # 'ggv' can't read cairo ps files, but 'gv' can
            dpi = 72.0   # ignore the passsed dpi setting for PS
            page_w_in, page_h_in = defaultPaperSize = 8.5, 11
            page_w,    page_h    = page_w_in * dpi, page_h_in * dpi

            self.figure.dpi.set (dpi)    
            l,b, width, height = self.figure.bbox.get_bounds()
            dx = (page_w - width)  / 2.0
            dy = (page_h - height) / 2.0
        
            ctx = cairo.Context()
            ctx.set_target_ps (filename, page_w_in, page_h_in, dpi, dpi)

            orientation = 'portrait' # landscape not supported yet
            if orientation == 'portrait': # default orientation
                # lines look a little jagged - just 'gv', cairo problem, or problem
                # with the way cairo is used?

                # center the figure on the page
                matrix = cairo.Matrix (tx=dx, ty=dy)
                ctx.set_matrix (matrix)
                # TODO? scale figure to maximize yet leave space for margin/border round page?
                # the figure already has a 'margin', so could use full page width?

            else: # landscape
                # cairo/src/cairo_ps_surface.c
                # '%%Orientation: Portrait' is always written to the file header
                # '%%Orientation: Landscape' would possibly cause problems
                # since some printers would rotate again ?
                # TODO:
                # 1) needs -pi/2 rotation, centered (and maximised?)
                #    don't know how to rotate without text being distorted
                # 2) add portrait/landscape checkbox to FileChooser
                pass
        
            renderer = RendererCairo (ctx.target_surface, ctx.matrix, width, height, self.figure.dpi)
            self.figure.draw(renderer)
            
            show_fig_border = False  # for testing figure orientation and scaling
            if show_fig_border:
                print 'Page w,h:', page_w, page_h
                print 'Fig  w,h:', width, height
                print 'dx,dy   :', dx, dy
                ctx.rectangle(0, 0, width, height)
                ctx.set_line_width(1)
                ctx.set_rgb_color(1,0,0)
                ctx.stroke()
                ctx.move_to(30,30)
                ctx.select_font('sans-serif')
                ctx.scale_font(20)
                ctx.show_text('Origin corner')
            ctx.show_page()

        elif ext == 'svg':  # backend_svg, later - use Cairo to write svg?
            from backend_svg import FigureCanvasSVG as FigureCanvas
            fc = self.switch_backends(FigureCanvas)
            fc.print_figure(filename, dpi, facecolor, edgecolor, orientation)

        else:
            error_msg('Format "%s" is not supported.\nSupported formats: %s.' %
                      (ext, ', '.join(IMAGE_FORMAT)))

        # restore the new params and redraw the screen if necessary
        self.figure.dpi.set(origDPI)
        self.figure.set_facecolor(origfacecolor)
        self.figure.set_edgecolor(origedgecolor)
        
        
    #def realize(self, *args): # is not required in cairo?
    #    """
    #    This method will be called when the system is ready to draw,
    #    eg when a GUI window is realized
    #    """
    #    if DEBUG: print 'backend_cairo.FigureCanvasCairo.%s()' % _fn_name()
    #    self._isRealized = True  
    #    self.draw()
