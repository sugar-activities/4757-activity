# -*- coding: utf-8 -*-
#Copyright (c) 2010-13 Walter Bender

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import os

import gtk
import gobject
import cairo

from random import uniform
from math import sin, cos, pi, sqrt
from taconstants import (TURTLE_LAYER, DEFAULT_TURTLE_COLORS, DEFAULT_TURTLE,
                         CONSTANTS, Color, ColorObj)
from tasprite_factory import SVG, svg_str_to_pixbuf
from tacanvas import wrap100, COLOR_TABLE
from sprites import Sprite
from tautils import (debug_output, data_to_string, round_int, get_path,
                     image_to_base64)
from TurtleArt.talogo import logoerror
from point3d import Point3D

SHAPES = 36
DEGTOR = pi / 180.
RTODEG = 180. / pi


def generate_turtle_pixbufs(colors):
    ''' Generate pixbufs for generic turtles '''
    shapes = []
    svg = SVG()
    svg.set_scale(1.0)
    for i in range(SHAPES):
        svg.set_orientation(i * 10)
        shapes.append(svg_str_to_pixbuf(svg.turtle(colors)))
    return shapes


class Turtles:

    def __init__(self, turtle_window):
        ''' Class to hold turtles '''
        self.turtle_window = turtle_window
        self.sprite_list = turtle_window.sprite_list
        self.width = turtle_window.width
        self.height = turtle_window.height
        self.dict = {}
        self._default_pixbufs = []
        self._active_turtle = None
        self._default_turtle_name = DEFAULT_TURTLE

    def get_turtle(self, turtle_name, append=False, colors=None):
        ''' Find a turtle '''
        if turtle_name in self.dict:
            return self.dict[turtle_name]
        elif not append:
            return None
        else:
            if colors is None:
                Turtle(self, turtle_name)
            elif isinstance(colors, (list, tuple)):
                Turtle(self, turtle_name, colors)
            else:
                Turtle(self, turtle_name, colors.split(','))
            return self.dict[turtle_name]

    def get_turtle_key(self, turtle):
        ''' Find a turtle's name '''
        for turtle_name in iter(self.dict):
            if self.dict[turtle_name] == turtle:
                return turtle_name
        return None

    def turtle_count(self):
        ''' How many turtles are there? '''
        return(len(self.dict))

    def add_to_dict(self, turtle_name, turtle):
        ''' Add a new turtle '''
        self.dict[turtle_name] = turtle

    def remove_from_dict(self, turtle_name):
        ''' Delete a turtle '''
        if turtle_name in self.dict:
            del(self.dict[turtle_name])

    def show_all(self):
        ''' Make all turtles visible '''
        for turtle_name in iter(self.dict):
            self.dict[turtle_name].show()

    def spr_to_turtle(self, spr):
        ''' Find the turtle that corresponds to sprite spr. '''
        for turtle_name in iter(self.dict):
            if spr == self.dict[turtle_name].spr:
                return self.dict[turtle_name]
        return None

    def get_pixbufs(self):
        ''' Get the pixbufs for the default turtle shapes. '''
        if self._default_pixbufs == []:
            self._default_pixbufs = generate_turtle_pixbufs(
                ["#008000", "#00A000"])
        return(self._default_pixbufs)

    def turtle_to_screen_coordinates(self, pos):
        ''' The origin of turtle coordinates is the center of the screen '''
        return [self.width / 2.0 + pos[0], self._invert_y_coordinate(pos[1])]

    def screen_to_turtle_coordinates(self, pos):
        ''' The origin of the screen coordinates is the upper-left corner '''
        return [pos[0] - self.width / 2.0, self._invert_y_coordinate(pos[1])]

    def _invert_y_coordinate(self, y):
        ''' Positive y goes up in turtle coordinates, down in sceeen
        coordinates '''
        return self.height / 2.0 - y

    def reset_turtles(self):
        for turtle_name in iter(self.dict):
            self.set_turtle(turtle_name)
            if not self._active_turtle.get_remote():
                self._active_turtle.set_color(0)
                self._active_turtle.set_shade(50)
                self._active_turtle.set_gray(100)
                if self.turtle_window.coord_scale == 1:
                    self._active_turtle.set_pen_size(5)
                else:
                    self._active_turtle.set_pen_size(1)
                self._active_turtle.reset_shapes()
                self._active_turtle.set_heading(0.0)
                self._active_turtle.reset_3D()
                self._active_turtle.set_pen_state(False)
                self._active_turtle.move_turtle((0.0, 0.0))
                self._active_turtle.set_pen_state(True)
                self._active_turtle.set_fill(False)
                self._active_turtle.hide()
        self.set_turtle(self._default_turtle_name)

    def get_turtle_x(self, turtle_name):
        if turtle_name not in self.dict:
            debug_output('%s not found in turtle dictionary' % (turtle_name),
                         self.turtle_window.running_sugar)
            raise logoerror("#syntaxerror")
        return self.dict[turtle_name].get_x()

    def get_turtle_y(self, turtle_name):
        if turtle_name not in self.dict:
            debug_output('%s not found in turtle dictionary' % (turtle_name),
                         self.turtle_window.running_sugar)
            raise logoerror("#syntaxerror")
        return self.dict[turtle_name].get_y()

    def get_turtle_heading(self, turtle_name):
        if turtle_name not in self.dict:
            debug_output('%s not found in turtle dictionary' % (turtle_name),
                         self.turtle_window.running_sugar)
            raise logoerror("#syntaxerror")
        return self.dict[turtle_name].get_heading()

    def set_turtle(self, turtle_name, colors=None):
        ''' Select the current turtle and associated pen status '''
        if turtle_name not in self.dict:
            # if it is a new turtle, start it in the center of the screen
            self._active_turtle = self.get_turtle(turtle_name, True, colors)
            self._active_turtle.set_heading(0.0, False)
            self._active_turtle.set_xy(0.0, 0.0, share=False, pendown=False)
            self._active_turtle.set_pen_state(True)
        elif colors is not None:
            self._active_turtle = self.get_turtle(turtle_name, False)
            self._active_turtle.set_turtle_colors(colors)
        else:
            self._active_turtle = self.get_turtle(turtle_name, False)
        self._active_turtle.show()
        self._active_turtle.set_color(share=False)
        self._active_turtle.set_gray(share=False)
        self._active_turtle.set_shade(share=False)
        self._active_turtle.set_pen_size(share=False)
        self._active_turtle.set_pen_state(share=False)

    def set_default_turtle_name(self, name):
        self._default_turtle_name = name

    def get_default_turtle_name(self):
        return self._default_turtle_name

    def set_active_turtle(self, active_turtle):
        self._active_turtle = active_turtle

    def get_active_turtle(self):
        return self._active_turtle


class Turtle:

    def __init__(self, turtles, turtle_name, turtle_colors=None):
        ''' The turtle is not a block, just a sprite with an orientation '''
        self.spr = None
        self.label_block = None
        self._turtles = turtles
        self._shapes = []
        self._custom_shapes = False
        self._name = turtle_name
        self._hidden = False
        self._remote = False
        self._x = 0.0
        self._y = 0.0
        self._3Dz = 0.0
        self._3Dx = 0.0
        self._3Dy = 0.0
        self._heading = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._direction = [0.0, 1.0, 0.0]
        self._camera = [0, 0, -10]
        self._half_width = 0
        self._half_height = 0
        self._drag_radius = None
        self._pen_shade = 50
        self._pen_color = 0
        self._pen_gray = 100
        if self._turtles.turtle_window.coord_scale == 1:
            self._pen_size = 5
        else:
            self._pen_size = 1
        self._pen_state = True
        self._pen_fill = False
        self.xyz_points = [{'color': None, 'xyz': [0., 0., 0.], 'pen': 1}]
        self.xyz_surfaces = []
        self._poly_points = []
        self._3D_poly_points = []

        self._prep_shapes(turtle_name, self._turtles, turtle_colors)

        # Create a sprite for the turtle in interactive mode.
        if turtles.sprite_list is not None:
            self.spr = Sprite(self._turtles.sprite_list, 0, 0, self._shapes[0])

            self._calculate_sizes()

            # Choose a random angle from which to attach the turtle
            # label to be used when sharing.
            angle = uniform(0, pi * 4 / 3.0)  # 240 degrees
            width = self._shapes[0].get_width()
            radius = width * 0.67
            # Restrict the angle to the sides: 30-150; 210-330
            if angle > pi * 2 / 3.0:
                angle += pi / 2.0  # + 90
                self.label_xy = [int(radius * sin(angle)),
                                 int(radius * cos(angle) + width / 2.0)]
            else:
                angle += pi / 6.0  # + 30
                self.label_xy = [int(radius * sin(angle) + width / 2.0),
                                 int(radius * cos(angle) + width / 2.0)]

        self._turtles.add_to_dict(turtle_name, self)

    def _calculate_sizes(self):
        self._half_width = int(self.spr.rect.width / 2.0)
        self._half_height = int(self.spr.rect.height / 2.0)
        self._drag_radius = ((self._half_width * self._half_width) +
                            (self._half_height * self._half_height)) / 6

    def set_remote(self):
        self._remote = True

    def get_remote(self):
        return self._remote

    def _prep_shapes(self, name, turtles=None, turtle_colors=None):
        # If the turtle name is an int, we'll use a palette color as the
        # turtle color
        try:
            int_key = int(name)
            use_color_table = True
        except ValueError:
            use_color_table = False

        if turtle_colors is not None:
            self.colors = turtle_colors[:]
            self._shapes = generate_turtle_pixbufs(self.colors)
        elif use_color_table:
            fill = wrap100(int_key)
            stroke = wrap100(fill + 10)
            self.colors = ['#%06x' % (COLOR_TABLE[fill]),
                           '#%06x' % (COLOR_TABLE[stroke])]
            self._shapes = generate_turtle_pixbufs(self.colors)
        else:
            if turtles is not None:
                self.colors = DEFAULT_TURTLE_COLORS
                self._shapes = turtles.get_pixbufs()

    def set_turtle_colors(self, turtle_colors):
        ''' reset the colors of a preloaded turtle '''
        if turtle_colors is not None:
            self.colors = turtle_colors[:]
            self._shapes = generate_turtle_pixbufs(self.colors)
            self.set_heading(self._heading, share=False)

    def set_shapes(self, shapes, i=0):
        ''' Reskin the turtle '''
        n = len(shapes)
        if n == 1 and i > 0:  # set shape[i]
            if i < len(self._shapes):
                self._shapes[i] = shapes[0]
        elif n == SHAPES:  # all shapes have been precomputed
            self._shapes = shapes[:]
        else:  # rotate shapes
            if n != 1:
                debug_output("%d images passed to set_shapes: ignoring" % (n),
                             self._turtles.turtle_window.running_sugar)
            if self._heading == 0.0:  # rotate the shapes
                images = []
                w, h = shapes[0].get_width(), shapes[0].get_height()
                nw = nh = int(sqrt(w * w + h * h))
                for i in range(SHAPES):
                    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, nw, nh)
                    context = cairo.Context(surface)
                    context = gtk.gdk.CairoContext(context)
                    context.translate(nw / 2.0, nh / 2.0)
                    context.rotate(i * 10 * pi / 180.)
                    context.translate(-nw / 2.0, -nh / 2.0)
                    context.set_source_pixbuf(shapes[0], (nw - w) / 2.0,
                                              (nh - h) / 2.0)
                    context.rectangle(0, 0, nw, nh)
                    context.fill()
                    images.append(surface)
                self._shapes = images[:]
            else:  # associate shape with image at current heading
                j = int(self._heading + 5) % 360 / (360 / SHAPES)
                self._shapes[j] = shapes[0]
        self._custom_shapes = True
        self.show()
        self._calculate_sizes()

    def reset_shapes(self):
        ''' Reset the shapes to the standard turtle '''
        if self._custom_shapes:
            self._shapes = generate_turtle_pixbufs(self.colors)
            self._custom_shapes = False
            self._calculate_sizes()

    def _apply_rotations(self):
        
	self._direction = [0., 1., 0.]
	angle = self._heading * DEGTOR * -1.0
        temp = []
        temp.append((self._direction[0] * cos(angle)) - 
                    (self._direction[1] * sin(angle)))
        temp.append((self._direction[0] * sin(angle)) + 
                    (self._direction[1] * cos(angle)))
        temp.append(self._direction[2] * 1.0)
        self._direction = temp[:]

	angle = self._roll * DEGTOR * -1.0
        temp = []
        temp.append(self._direction[0] * 1.0)
        temp.append((self._direction[1] * cos(angle)) - 
                    (self._direction[2] * sin(angle)))
        temp.append((self._direction[1] * sin(angle)) + 
                    (self._direction[2] * cos(angle)))
        self._direction = temp[:]

	angle = self._pitch * DEGTOR * -1.0
        temp = []
        temp.append((self._direction[0] * cos(angle)) + 
                    (self._direction[2] * sin(angle)))
        temp.append(self._direction[1] * 1.0)
        temp.append((self._direction[0] * -1.0 * sin(angle)) + 
                    (self._direction[2] * cos(angle)))
        self._direction = temp[:]

    def set_heading(self, heading, share=True):
        ''' Set the turtle heading (one shape per 360/SHAPES degrees) ''' 

        self._heading = heading
        self._heading %= 360
 
        self._apply_rotations()

        self._update_sprite_heading()

        if self._turtles.turtle_window.sharing() and share:
            event = 'r|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._heading)]))
            self._turtles.turtle_window.send_event(event)
    
    def set_roll(self, roll):
        ''' Set the turtle roll '''

        self._roll = roll
        self._roll %= 360

        self._apply_rotations()

    def set_pitch(self, pitch):
        ''' Set the turtle pitch '''

        self._pitch = pitch
        self._pitch %= 360
 
        self._apply_rotations()

    def _update_sprite_heading(self):

        ''' Update the sprite to reflect the current heading '''
        i = (int(self._heading + 5) % 360) / (360 / SHAPES)
        if not self._hidden and self.spr is not None:
            try:
                self.spr.set_shape(self._shapes[i])
            except IndexError:
                self.spr.set_shape(self._shapes[0])

    def set_color(self, color=None, share=True):
        ''' Set the pen color for this turtle. '''
        if isinstance(color, ColorObj):
            # See comment in tatype.py TYPE_BOX -> TYPE_COLOR
            color = color.color
        if color is None:
            color = self._pen_color
        # Special case for color blocks from CONSTANTS
        elif isinstance(color, Color):
            self.set_shade(color.shade, share)
            self.set_gray(color.gray, share)
            if color.color is not None:
                color = color.color
            else:
                color = self._pen_color

        self._pen_color = color

        self._turtles.turtle_window.canvas.set_fgcolor(shade=self._pen_shade,
                                                       gray=self._pen_gray,
                                                       color=self._pen_color)

        if self._turtles.turtle_window.sharing() and share:
            event = 'c|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._pen_color)]))
            self._turtles.turtle_window.send_event(event)

    def set_gray(self, gray=None, share=True):
        ''' Set the pen gray level for this turtle. '''
        if gray is not None:
            self._pen_gray = gray

        if self._pen_gray < 0:
            self._pen_gray = 0
        if self._pen_gray > 100:
            self._pen_gray = 100

        self._turtles.turtle_window.canvas.set_fgcolor(shade=self._pen_shade,
                                                       gray=self._pen_gray,
                                                       color=self._pen_color)

        if self._turtles.turtle_window.sharing() and share:
            event = 'g|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._pen_gray)]))
            self._turtles.turtle_window.send_event(event)

    def set_shade(self, shade=None, share=True):
        ''' Set the pen shade for this turtle. '''
        if shade is not None:
            self._pen_shade = shade

        self._turtles.turtle_window.canvas.set_fgcolor(shade=self._pen_shade,
                                                       gray=self._pen_gray,
                                                       color=self._pen_color)

        if self._turtles.turtle_window.sharing() and share:
            event = 's|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._pen_shade)]))
            self._turtles.turtle_window.send_event(event)

    def set_pen_size(self, pen_size=None, share=True):
        ''' Set the pen size for this turtle. '''
        if pen_size is not None:
            self._pen_size = max(0, pen_size)

        self._turtles.turtle_window.canvas.set_pen_size(
            self._pen_size * self._turtles.turtle_window.coord_scale)

        if self._turtles.turtle_window.sharing() and share:
            event = 'w|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._pen_size)]))
            self._turtles.turtle_window.send_event(event)

    def set_pen_state(self, pen_state=None, share=True):
        ''' Set the pen state (down==True) for this turtle. '''
        if pen_state is not None:
            self._pen_state = pen_state

        if self._turtles.turtle_window.sharing() and share:
            event = 'p|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              self._pen_state]))
            self._turtles.turtle_window.send_event(event)

    def set_fill(self, state=False):
        self._pen_fill = state
        if not self._pen_fill:
            self._poly_points = []
            self._3D_poly_points = []

    def set_poly_points(self, poly_points=None):
        if poly_points is not None:
            self._poly_points = poly_points[:]

    def start_fill(self):
        self._pen_fill = True
        self._poly_points = []
        self._3D_poly_points = []

    def stop_fill(self, share=True):
        self._pen_fill = False

        if len(self._3D_poly_points) == 0:
            self.xyz_surfaces.append(
                {'color': [self._pen_color, self._pen_shade, self._pen_gray],
                 'face': None})
            return
        else:
            self.xyz_surfaces.append(
                {'color': [self._pen_color, self._pen_shade, self._pen_gray],
                 'face': self._3D_poly_points[:]})

        self._turtles.turtle_window.canvas.fill_polygon(self._poly_points)

        if self._turtles.turtle_window.sharing() and share:
            shared_poly_points = []
            for p in self._poly_points:
                x, y = self._turtles.turtle_to_screen_coordinates(
                    (p[1], p[2]))
                if p[0] in ['move', 'line']:
                    shared_poly_points.append((p[0], x, y))
                elif p[0] in ['rarc', 'larc']:
                    shared_poly_points.append((p[0], x, y, p[3], p[4], p[5]))
                event = 'F|%s' % (data_to_string(
                        [self._turtles.turtle_window.nick,
                         shared_poly_points]))
            self._turtles.turtle_window.send_event(event)
        self._poly_points = []
        self._3D_poly_points = []

    def hide(self):
        if self.spr is not None:
            self.spr.hide()
        if self.label_block is not None:
            self.label_block.spr.hide()
        self._hidden = True

    def show(self):
        if self.spr is not None:
            self.spr.set_layer(TURTLE_LAYER)
            self._hidden = False
        if self._x is not None and self._y is not None:
            self.move_turtle_spr((self._x, self._y))
            self.set_heading(self._heading, share=False)
        if self.label_block is not None:
            self.label_block.spr.set_layer(TURTLE_LAYER + 1)

    def move_turtle(self, pos=None):
        ''' Move the turtle's position '''
        if pos is None:
            pos = self.get_xy()

        self._x, self._y = pos[0], pos[1]
        if self.spr is not None:
            self.move_turtle_spr(pos)

    def move_turtle_spr(self, pos):
        ''' Move the turtle's sprite '''
        pos = self._turtles.turtle_to_screen_coordinates(pos)

        pos[0] -= self._half_width
        pos[1] -= self._half_height

        if not self._hidden and self.spr is not None:
            self.spr.move(pos)
        if self.label_block is not None:
            self.label_block.spr.move((pos[0] + self.label_xy[0],
                                       pos[1] + self.label_xy[1]))
    def reset_3D(self):
        self._3Dx, self._3Dy, self._3Dz = 0.0, 0.0, 0.0
        self._direction = [0.0, 1.0, 0.0]
        self._roll, self._pitch = 0.0, 0.0
        self.xyz_points = [{'color': None, 'xyz': [0., 0., 0.], 'pen': 1}]
        self._faces = []
        self._camera = [0, 0, -10]

    def set_camera(self, value):
        ''' Set the value of camera '''
        self._camera[:] = value

    def set_camera_xyz(self, x, y, z):
        self._camera = [x, y, z]

    def right(self, degrees, share=True):
        ''' Rotate turtle clockwise '''
        self._heading += degrees
        self._heading %= 360

        self._apply_rotations()

        self._update_sprite_heading()

        if self._turtles.turtle_window.sharing() and share:
            event = 'r|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              round_int(self._heading)]))
            self._turtles.turtle_window.send_event(event)

    def left(self, degrees, share=True):
        degrees = 0 - degrees
        self.right(degrees, share)

    def _draw_line(self, old, new, pendown):
        if self._pen_state and pendown:
            self._turtles.turtle_window.canvas.set_source_rgb()
            pos1 = self._turtles.turtle_to_screen_coordinates(old)
            pos2 = self._turtles.turtle_to_screen_coordinates(new)
            self._turtles.turtle_window.canvas.draw_line(pos1[0], pos1[1],
                                                         pos2[0], pos2[1])
            if self._pen_fill:
                if self._poly_points == []:
                    self._poly_points.append(('move', pos1[0], pos1[1]))
                self._poly_points.append(('line', pos2[0], pos2[1]))
                self.store_data(append=False)
                self._3D_poly_points.append([self._3Dx, self._3Dy, self._3Dz])

    def forward(self, distance, share=True):
        scaled_distance = distance * self._turtles.turtle_window.coord_scale

        old = self.get_xy() #Projected Point
        old_3D = self.get_3Dpoint() #Actual Point

        #xcor = old[0] + scaled_distance * sin(self._heading * DEGTOR)
        #ycor = old[1] + scaled_distance * cos(self._heading * DEGTOR)

        xcor = old_3D[0] + scaled_distance * self._direction[0]
        ycor = old_3D[1] + scaled_distance * self._direction[1]
        zcor = old_3D[2] + scaled_distance * self._direction[2]

        width = self._turtles.turtle_window.width
        height = self._turtles.turtle_window.height
        
        # Old point as Point3D object
        old_point = Point3D(old_3D[0], old_3D[1], old_3D[2])
        # Projected Old Point
        p = old_point.project(width, height, self._camera)
        new_x, new_y = p.x, p.y
        pair1 = [new_x, new_y]
        pos1 = self._turtles.screen_to_turtle_coordinates(pair1)
        
        self._3Dx, self._3Dy, self._3Dz = xcor, ycor, zcor
        self.store_data()

        new_point = Point3D(xcor, ycor, zcor) # New point as 3D object
        p = new_point.project(width, height, self._camera) # Projected New Point
        new_x, new_y = p.x, p.y
        pair2 = [new_x, new_y]
        pos2 = self._turtles.screen_to_turtle_coordinates(pair2)

        self._draw_line(pos1, pos2, True)
        self.move_turtle((pos2[0], pos2[1]))

        if self._turtles.turtle_window.sharing() and share:
            event = 'f|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              int(distance)]))
            self._turtles.turtle_window.send_event(event)

    def backward(self, distance, share=True):
        distance = 0 - distance
        self.forward(distance, share)

    def set_xy(self, x, y, share=True, pendown=True, dragging=False):
        old = self.get_xy()
        if dragging:
            xcor = x
            ycor = y
        else:
            xcor = x * self._turtles.turtle_window.coord_scale
            ycor = y * self._turtles.turtle_window.coord_scale

        self._draw_line(old, (xcor, ycor), pendown)
        self.move_turtle((xcor, ycor))

        if self._turtles.turtle_window.sharing() and share:
            event = 'x|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              [round_int(xcor),
                                               round_int(ycor)]]))
            self._turtles.turtle_window.send_event(event)

    def set_xyz(self, x, y, z):
        ''' Set the x, y and z coordinates '''

        self._3Dx, self._3Dy, self._3Dz = x, y, z
        self.store_data()
        point_3D = Point3D(x, y, z)
        width = self._turtles.turtle_window.width
        height = self._turtles.turtle_window.height
        p = point_3D.project(width, height, self._camera)
        new_x, new_y = p.x, p.y
        pair = [new_x, new_y]
        pos = self._turtles.screen_to_turtle_coordinates(pair)
        self.set_xy(pos[0], pos[1])

    def store_data(self, append=True):

        if(abs(self._3Dx) < 0.0001):
            self._3Dx = 0.
        if(abs(self._3Dy) < 0.0001):
            self._3Dy = 0.
        if(abs(self._3Dz) < 0.0001):
            self._3Dz = 0.
        self._3Dx = round(self._3Dx, 2)
        self._3Dy = round(self._3Dy, 2)
        self._3Dz = round(self._3Dz, 2)

        if append:
            if (self._pen_state):
                pen = 1
            else:
                pen = 0
            self.xyz_points.append(
                {'xyz': [self._3Dx, self._3Dy, self._3Dz], 'pen': pen})

    def arc(self, a, r, share=True):
        ''' Draw an arc '''
        if self._pen_state:
            self._turtles.turtle_window.canvas.set_source_rgb()
        if a < 0:
            pos = self.larc(-a, r)
        else:
            pos = self.rarc(a, r)

        self.move_turtle(pos)

        if self._turtles.turtle_window.sharing() and share:
            event = 'a|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              [round_int(a), round_int(r)]]))
            self._turtles.turtle_window.send_event(event)

    def rarc(self, a, r):
        ''' draw a clockwise arc '''
        r *= self._turtles.turtle_window.coord_scale
        if r < 0:
            r = -r
            a = -a
        pos = self.get_xy()
        cx = pos[0] + r * cos(self._heading * DEGTOR)
        cy = pos[1] - r * sin(self._heading * DEGTOR)
        if self._pen_state:
            npos = self._turtles.turtle_to_screen_coordinates((cx, cy))
            self._turtles.turtle_window.canvas.rarc(npos[0], npos[1], r, a,
                                                    self._heading)

            if self._pen_fill:
                self._poly_points.append(('move', npos[0], npos[1]))
                self._poly_points.append(('rarc', npos[0], npos[1], r,
                                          (self._heading - 180) * DEGTOR,
                                          (self._heading - 180 + a) * DEGTOR))

        self.right(a, False)
        return [cx - r * cos(self._heading * DEGTOR),
                cy + r * sin(self._heading * DEGTOR)]

    def larc(self, a, r):
        ''' draw a counter-clockwise arc '''
        r *= self._turtles.turtle_window.coord_scale
        if r < 0:
            r = -r
            a = -a
        pos = self.get_xy()
        cx = pos[0] - r * cos(self._heading * DEGTOR)
        cy = pos[1] + r * sin(self._heading * DEGTOR)
        if self._pen_state:
            npos = self._turtles.turtle_to_screen_coordinates((cx, cy))
            self._turtles.turtle_window.canvas.larc(npos[0], npos[1], r, a,
                                                    self._heading)

            if self._pen_fill:
                self._poly_points.append(('move', npos[0], npos[1]))
                self._poly_points.append(('larc', npos[0], npos[1], r,
                                          (self._heading) * DEGTOR,
                                          (self._heading - a) * DEGTOR))

        self.right(-a, False)
        return [cx + r * cos(self._heading * DEGTOR),
                cy - r * sin(self._heading * DEGTOR)]

    def draw_pixbuf(self, pixbuf, a, b, x, y, w, h, path, share=True):
        ''' Draw a pixbuf '''
        self._turtles.turtle_window.canvas.draw_pixbuf(
            pixbuf, a, b, x, y, w, h, self._heading)

        if self._turtles.turtle_window.sharing() and share:
            if self._turtles.turtle_window.running_sugar:
                tmp_path = get_path(self._turtles.turtle_window.activity,
                                    'instance')
            else:
                tmp_path = '/tmp'
            tmp_file = os.path.join(
                get_path(self._turtles.turtle_window.activity, 'instance'),
                'tmpfile.png')
            pixbuf.save(tmp_file, 'png', {'quality': '100'})
            data = image_to_base64(tmp_file, tmp_path)
            height = pixbuf.get_height()
            width = pixbuf.get_width()

            pos = self._turtles.screen_to_turtle_coordinates((x, y))

            event = 'P|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              [round_int(a), round_int(b),
                                               round_int(pos[0]),
                                               round_int(pos[1]),
                                               round_int(w), round_int(h),
                                               round_int(width),
                                               round_int(height),
                                               data]]))
            gobject.idle_add(self._turtles.turtle_window.send_event, event)

            os.remove(tmp_file)

    def draw_text(self, label, x, y, size, w, share=True):
        ''' Draw text '''
        self._turtles.turtle_window.canvas.draw_text(
            label, x, y, size, w, self._heading,
            self._turtles.turtle_window.coord_scale)

        if self._turtles.turtle_window.sharing() and share:
            event = 'W|%s' % (data_to_string([self._turtles.turtle_window.nick,
                                              [label, round_int(x),
                                               round_int(y), round_int(size),
                                               round_int(w)]]))
            self._turtles.turtle_window.send_event(event)

    def read_pixel(self):
        """ Read r, g, b, a from the canvas and push b, g, r to the stack """
        r, g, b, a = self.get_pixel()
        self._turtles.turtle_window.lc.heap.append(b)
        self._turtles.turtle_window.lc.heap.append(g)
        self._turtles.turtle_window.lc.heap.append(r)

    def get_color_index(self):
        r, g, b, a = self.get_pixel()
        color_index = self._turtles.turtle_window.canvas.get_color_index(
            r, g, b)
        return color_index

    def get_name(self):
        return self._name

    def get_xy(self):
        return [self._x, self._y]
    
    def get_3Dpoint(self):
        return [self._3Dx, self._3Dy, self._3Dz]
    
    def get_x(self):
        return self._3Dx

    def get_y(self):
        return self._3Dy

    def get_z(self):
        return self._3Dz

    def get_heading(self):
        return self._heading
    
    def get_roll(self):
        return self._roll

    def get_pitch(self):
        return self._pitch

    def get_color(self):
        return self._pen_color

    def get_gray(self):
        return self._pen_gray

    def get_shade(self):
        return self._pen_shade

    def get_pen_size(self):
        return self._pen_size

    def get_pen_state(self):
        return self._pen_state

    def get_fill(self):
        return self._pen_fill

    def get_poly_points(self):
        return self._poly_points

    def get_pixel(self):
        pos = self._turtles.turtle_to_screen_coordinates(self.get_xy())
        return self._turtles.turtle_window.canvas.get_pixel(pos[0], pos[1])

    def get_drag_radius(self):
        if self._drag_radius is None:
            self._calculate_sizes()
        return self._drag_radius
