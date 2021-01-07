"""
This file has the all the environment specific classes
"""
import math
import cv2

"""Every game object is stored in this"""
class GameObject:
    UNKNOWN = 'Unknown'
    TRIANGLE = 'Triangle'
    SQUARE = 'Square'
    PENTAGON = 'Pentagon'
    PLAYER = 'Player'
    ENEMY = 'Enemy'
    ALLY = 'ALLY'
    def __init__(self, bbox, object_type, distance = None):
        self.bbox = bbox
        self.type = object_type
        self.distance = distance
        #Stores whether the game object has still been tracked
        self.is_tracked = False

    @property
    def centre(self):
        return BBoxOps.bbox_centre(self.bbox)

    @staticmethod
    def make_player(bbox):
        return GameObject(bbox, GameObject.PLAYER)


MIN_OBJECT_AREA = 500

"""
This is an environment use to store game information
Makes it easier for the AI to make choices
All objects are stored as bboxes in form (x,y,w,h)
Vector AB is in form (x, y)
"""
class Environment:
    def __init__(self, size):
        #Stores all objects other than the player
        self.__objects = []
        #Stores the player as a game object
        #Default value is just middle of screen
        self.__player = GameObject.make_player((size[0]/2, size[1]/2,1,1))
        self.size = size
        #Stores all the objects that collide with player
        self.collisions = []
        #Stores whether the collisions have been calculated
        #For the frame
        self.has_calculated_collisions = False
        #Stores the game frame
        self.frame = None

    @property
    def objects(self):
        return self.__objects

    @objects.setter
    def objects(self, value):
        self.__objects = value
        self.reset_collisions()

    @property
    def player(self):
        return self.__player

    @player.setter
    def player(self, value):
        self.__player = value
        self.reset_collisions()

    """Resets the collisions in the environment"""
    def reset_collisions(self):
        self.collisions = []
        self.has_calculated_collisions = False


"""Represents a vector"""
class Vector2:
    def __init__(self, x, y, precision = 4):
        self.precision = precision
        self.x = round(x, precision)
        self.y = round(y, precision)

    """Returns the magnitude/length of the vector"""
    @property
    def length(self):
        return round(math.sqrt(self.length_squared), self.precision)

    """Returns the length squared. There wont be any rounding"""
    @property
    def length_squared(self):
        return self.x * self.x + self.y * self.y

    """Setter for length"""
    @length.setter
    def length(self, size):
        n_vec = self.normalize()
        self.x = n_vec.x * size
        self.y = n_vec.y * size

    """Angle of the vector in radians"""
    @property
    def angle(self):
        return round(math.atan2(self.y, self.x), self.precision)

    """Sets the angle given it in radians"""
    @angle.setter
    def angle(self, size):
        self.x = round(math.cos(size), self.precision)
        self.y = round(math.sin(size), self.precision)

    """Adds this vector to the input vector and returns it"""
    def __add__(self, in_vector):
        return Vector2(self.x + in_vector.x, self.y + in_vector.y)

    """
    Subtracts this vector with input vector.
    Returns a new output vector
    """
    def __sub__(self, in_vector):
        return Vector2(self.x - in_vector.x, self.y - in_vector.y)

    """Return a copy of the vector multiplied by a scalar"""
    def __mul__(self, scalar):
        new_vec = self.copy()
        new_vec.length = new_vec.length * scalar
        return new_vec

    """Used for the print function"""
    def __str__(self):
        return f"Vector2({self.x},{self.y})"

    """Override equals"""
    def __eq__(self, obj):
        if type(obj) == Vector2 and obj.x == self.x and obj.y == self.y:
            return True
        return False

    """Returns a copy of the current vector"""
    def copy(self):
        return Vector2(self.x, self.y)

    """Returns a copy of this vector rotated by the given angle in radians"""
    def rotate(self, angle):
        new_vec = self.copy()
        new_vec.angle = new_vec.angle + angle
        return new_vec

    """Return normalized copy of this vector"""
    def normalize(self):
        magnitude = float(math.sqrt(self.x * self.x + self.y * self.y))
        #Return (0,0) if magnitude is 0
        if not magnitude:
            return Vector2(0,0)
        return Vector2(self.x / magnitude, self.y /magnitude)

    """Returns whether the vector is inside the given rectangle"""
    def inside_rect(self, rect):
        if self.x > rect[0] and self.x < rect[2] and self.y < rect[3] and self.y > rect[1]:
            return True
        return False

    """Returns the distance from this vector to the target vector"""
    def distance_to(self, target):
        return round(math.sqrt(self.distance_to_squared(target))
            , self.precision)
    
    """Returns the distance to a vector squared"""
    def distance_to_squared(self, target):
        x_dif = self.x - target.x
        y_dif = self.y - target.y
        return x_dif * x_dif + y_dif * y_dif

    """Returns the vector as a tuple"""
    def to_tuple(self):
        return (int(self.x), int(self.y))

    """Creates a new vector given in a tuple"""
    @staticmethod
    def from_tuple(in_tuple):
        return Vector2(in_tuple[0], in_tuple[1])


"""Segment class representing a Segment on the screen"""
class Segment:
    def __init__(self, x1, y1, x2, y2):
        self.p = Vector2(x1, y1)
        self.q = Vector2(x2, y2)

    """Override"""
    def __str__(self):
        return f"Segment({self.p.x}, {self.p.y}, {self.q.x}, {self.q.y})"

    """
    Returns whether this segment goes through the given point
    The point is given as a position vector
    """
    def through_point(self, point):
        p2point = self.p.distance_to(point)
        q2point = self.q.distance_to(point)
        p2q = self.p.distance_to(self.q)
        return round(p2q - p2point - q2point
            , min(self.p.precision, self.q.precision) - 1) == 0


    """Given a vector and its tail vector, turn it into a segment"""
    @staticmethod
    def vector_to_segment(vector, pos_vector):
        return Segment(pos_vector.x, pos_vector.y, 
            pos_vector.x + vector.x, pos_vector.y + vector.y)

    @staticmethod
    def on_segment(p, q, r): 
        if ( (q.x <= max(p.x, r.x)) and (q.x >= min(p.x, r.x)) and 
            (q.y <= max(p.y, r.y)) and (q.y >= min(p.y, r.y))): 
            return True
        return False

    #Checks the orientation of 3 points
    @staticmethod
    def orientation(p, q, r): 
        val = (float(q.y - p.y) * (r.x - q.x)) - (float(q.x - p.x) * (r.y - q.y)) 
        if (val > 0): 
            return 1
        elif (val < 0): 
            return 2
        else: 
            return 0

    """Returns if the two segments intersect"""
    @staticmethod
    def segments_intersect(segment_1, segment_2):
        p1 = segment_1.p
        q1 = segment_1.q
        p2 = segment_2.p
        q2 = segment_2.q
        # Find the 4 orientations required for  
        # the general and special cases 
        o1 = Segment.orientation(p1, q1, p2) 
        o2 = Segment.orientation(p1, q1, q2) 
        o3 = Segment.orientation(p2, q2, p1) 
        o4 = Segment.orientation(p2, q2, q1) 
        # General case 
        if ((o1 != o2) and (o3 != o4)): 
            return True
        # Special Cases 
        # p1 , q1 and p2 are colinear and p2 lies on segment p1q1 
        if ((o1 == 0) and Segment.on_segment(p1, p2, q1)): 
            return True
        # p1 , q1 and q2 are colinear and q2 lies on segment p1q1 
        if ((o2 == 0) and Segment.on_segment(p1, q2, q1)): 
            return True
        # p2 , q2 and p1 are colinear and p1 lies on segment p2q2 
        if ((o3 == 0) and Segment.on_segment(p2, p1, q2)): 
            return True
        # p2 , q2 and q1 are colinear and q1 lies on segment p2q2 
        if ((o4 == 0) and Segment.on_segment(p2, q1, q2)): 
            return True
        # If none of the cases 
        return False


"""
Defines a circle class
Centre is a position vector
"""
class Circle:
    def __init__(self, centre, radius):
        self.centre = centre
        self.radius = radius

    """Returns whether the circle intersects with a rectangle"""
    def intersects_rect(self, rect):
        #Find the closest point from rect to center of circle
        #This is done by clamping
        top_corner = Vector2(rect[0], rect[1])
        bottom_corner = Vector2(rect[0] + rect[2], rect[1] + rect[3])
        #What max(rx1, min(cx, rx2)) does is that it finds the value that
        #is in the center when you order the three x coordinates in order
        #Since rx2 is always greater than rx1 (definition of rect) then
        #finding min then max will give the middle coordinate
        closest_point = Vector2(
            max(top_corner.x, min(self.centre.x, bottom_corner.x)),
            max(top_corner.y, min(self.centre.y, bottom_corner.y))
        )

        #If distance from closest point to center is less than radius
        #the circle intersects
        return closest_point.distance_to_squared(self.centre) < self.radius * self.radius


"""Class responsible for BBox operations"""
class BBoxOps:
    """
    Given a bbox in the form: 
    (top_left_x, top_left_y, size_x, size_y), return its centre
    """
    @staticmethod
    def bbox_centre(bbox):
        return Vector2(bbox[0] + bbox[2]/2, bbox[1] + bbox[3]/2)

    """
    Given a bbox (x,y,w,h) return it in the form
    (x1, y1, x2, y2)
    """
    @staticmethod
    def bbox_to_positions(bbox):
        return (bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3])


    """
    Fits the given bbox into a frame
    """
    @staticmethod
    def fit_bbox_in_frame(bbox, frame_size):
        x1 = max(bbox[0], 0)
        y1 = max(bbox[1], 0)
        x2 = min(bbox[2], frame_size[0])
        y2 = min(bbox[3], frame_size[1])
        return (x1, y1, x2, y2)

    """
    Makes all the values in the bbox integers
    """
    @staticmethod
    def make_int(bbox):
        return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

    """Makes a buffer around the bbox"""
    @staticmethod
    def make_buffer(bbox, buffer_size):
        x = bbox[0] - buffer_size[0]
        y = bbox[1] - buffer_size[1]
        w = bbox[2] + buffer_size[0] * 2
        h = bbox[3] + buffer_size[1] * 2
        return (x,y,w,h)

    """Removes a buffer around a bbox"""
    @staticmethod
    def remove_buffer(bbox, buffer_size):
        x = bbox[0] + buffer_size[0]
        y = bbox[1] + buffer_size[1]
        w = max(bbox[2] - buffer_size[0] * 2, 0)
        h = max(bbox[3] - buffer_size[1] * 2, 0)
        return (x,y,w,h)

    """Given the centre of a bbox and its size, return the bbox"""
    @staticmethod
    def centre_to_bbox(centre, size):
        top_x = centre.x - size.x / 2
        top_y = centre.y - size.y / 2
        return (top_x, top_y, size.x, size.y)

    """Returns whether two bboxes overlap or not"""
    @staticmethod
    def bbox_overlap(bbox1, bbox2):
        #If one rect is on left side of another rect
        if bbox1[0] >= bbox2[0] + bbox2[2]:
            return False
        elif bbox2[0] >= bbox1[0] + bbox1[2]:
            return False
        #If one rect is above the other
        elif bbox1[1] >= bbox2[1] + bbox2[3]:
            return False
        elif bbox2[1] >= bbox1[1] + bbox1[3]:
            return False
        return True

    """Given a bbox rect, return whether they intersect or not"""
    @staticmethod
    def intersects_rect(in_segment, rect):
        top_edge = Segment(rect[0], rect[1], rect[0] + rect[2], rect[1])
        bottom_edge = Segment(rect[0], rect[1] + rect[3]
            , rect[0] + rect[2], rect[1] + rect[3])
        right_edge = Segment(rect[0] + rect[2], rect[1]
            , rect[0] + rect[2], rect[1] + rect[3])
        left_edge = Segment(rect[0], rect[1], rect[0], rect[1] + rect[3])
        #Check if the segment intersects with any of the 4 sides
        if Segment.segments_intersect(in_segment, top_edge):
            return True
        elif Segment.segments_intersect(in_segment, bottom_edge):
            return True
        elif Segment.segments_intersect(in_segment, right_edge):
            return True
        elif Segment.segments_intersect(in_segment, left_edge):
            return True
        #Check if the segment is inside the rectangle
        elif in_segment.p.inside_rect(rect) and in_segment.q.inside_rect(rect):
            return True
        return False
