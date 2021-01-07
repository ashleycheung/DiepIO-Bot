"""
This file stores all the behaviours and algorithms of the bot
"""
import cv2
import math
import random
from environment import *
from render import *

"""This is the behaviour of the AI. It is essentially a state machine"""
class Behavior:
    def __init__(self):
        self.curr_state = ExploreState(self)

    """Called each frame for the AI to decide suitable action"""
    def action(self, environment, controller, frame):
        self.curr_state.action(environment, controller, frame)


"""This is a state the bot uses"""
class State:
    def __init__(self, state_machine):
        self.state_machine = state_machine

    """This is to be overridden"""
    def action(self, environment, controller, frame=None):
        pass

DIR_CHANGE_CHANCE = 0.01

"""In this state, the AI explores the world randomly searching for targets"""
class ExploreState(State):
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.avoid = CollisionAvoidance()
        #Initialise random explore direction
        self.dir = Vector2(1,0).rotate(random.uniform(0, 2 * math.pi))

    """Overrides"""
    def action(self, environment, controller, frame=None):
        #Check if there are neighbour objects
        if len(environment.objects) > 0:
            self.state_machine.curr_state = TargetState(self.state_machine)
            return

        #Get move direction
        move_dir = self.get_direction()
        #Pass it through collision avoidance
        if not environment.player is None:
            move_dir = self.avoid.get_direction(move_dir, environment, frame)
        #Move the AI
        controller.move(move_dir)

    """Get the next direction to walk"""
    def get_direction(self):
        #Get new direction
        if random.uniform(0,99) < DIR_CHANGE_CHANCE * 100:
            #Generate a random angle
            angle = random.uniform(0, 2 * math.pi)
            self.dir.angle = angle

        return self.dir


"""Finds a target to follow"""
class TargetState(State):
    def __init__(self, state_machine, tracking_buffer=(20,20)):
        super().__init__(state_machine)
        self.avoid = CollisionAvoidance()
        self.sort_alg = ImportanceSort()

    """Given an environment return the target object"""
    def find_target(self, environment):
        objects = environment.objects

        #Calculate importance for all the objects
        object_importances = []
        player_pos = environment.player.centre
        for o in environment.objects:
            object_importances.append((o, self.get_importance(o, player_pos)))

        #Sort the neighbours based on importance
        objects = self.sort_alg.sort(object_importances)

        if len(objects) == 0:
            return None
        #Get the most important object as the target
        return objects[0][0]

    """Get the importance of a game object"""
    def get_importance(self, game_object, player_pos):
        importance = 0
        if game_object.type == GameObject.SQUARE:
            importance += 10
        elif game_object.type == GameObject.TRIANGLE:
            importance += 100
        elif game_object.type == GameObject.PENTAGON:
            importance += 200
        dist = player_pos.distance_to(game_object.centre)
        importance += (max(200 - dist, 0) / 10)
        return importance

    """Overrides"""
    def action(self, environment, controller, frame=None):
        #Get optimal target based on heuristics
        target = self.find_target(environment)

        #If no target can be found, return to explore state
        if target is None:
            self.state_machine.curr_state = ExploreState(self.state_machine)
            return
        
        #Render of frame if passed in
        if not frame is None:
            BotRender.draw_rect(target.bbox, frame, color=(0,0,255))
            BotRender.draw_text(frame, "Target", target.centre.to_tuple(), color=(0,0,255))

        #Get move direction
        move_dir = target.centre - environment.player.centre
        #Pass it through collision avoidance
        move_dir = self.avoid.get_direction(move_dir, environment, frame)
        #Move the AI
        controller.move(move_dir)
        #Shoot
        controller.shoot(target.centre)



#This is the max distance the bot sees for the collision avoidance algorithm
MAX_SEE_AHEAD = 80
#The higher the factor the sharper the turn
AVOIDANCE_FACTOR = 0.02
MAX_AVOIDANCE_FORCE = 1300
MIN_AVOIDANCE_FORCE = 1
DIRECTION_FORCE = 200
SIGHT_OFFSET = 70

"""This is the Collision Avoidance algorithm"""
class CollisionAvoidance:
    """
    Adds an avoidance force to the direction
    """
    def add_avoidance_force(self, collidable, player_pos, new_dir, frame):
        #Get object center
        object_center = BBoxOps.bbox_centre(collidable)
        #Get distance from player to the object
        dist = player_pos.distance_to(object_center)
        dir_to_object = object_center - player_pos

        #Closer the object, the more to move away
        avoid_size = math.exp(-1 * AVOIDANCE_FACTOR * dist
            + math.log(MAX_AVOIDANCE_FORCE * MIN_AVOIDANCE_FORCE)) + MIN_AVOIDANCE_FORCE
        avoidance_vector = dir_to_object.normalize() * avoid_size * -1

        new_dir = new_dir + avoidance_vector

        if not frame is None:
            frame = cv2.line(frame, object_center.to_tuple()
            , (object_center + avoidance_vector).to_tuple() 
            , (255,0,0), 5)
        
        return new_dir

    """
    Given a desired direction and the environment
    Return the actual direction that should be moved to avoid obstacles
    If the frame is passed, the sight radius will be drawn
    """
    def get_direction(self, direction, environment, frame = None):
        direction = direction.normalize() * DIRECTION_FORCE
        sight_offset = direction.normalize() * SIGHT_OFFSET

        if environment.player is None:
            return
        player_pos = environment.player.centre

        #Get the sight range
        sight_range = Circle(player_pos + sight_offset, MAX_SEE_AHEAD)
        #Get surrounding sight range
        surround_range = Circle(player_pos, MAX_SEE_AHEAD)

        new_dir = direction

        #Check whether the sight vector colllide with any objects in the environment
        for collidable in environment.objects:
            #Check if collision occurs
            if sight_range.intersects_rect(collidable.bbox):
                new_dir = self.add_avoidance_force(collidable.bbox, player_pos, new_dir, frame)
            if surround_range.intersects_rect(collidable.bbox):
                new_dir = self.add_avoidance_force(collidable.bbox, player_pos, new_dir, frame)

        #Draw sight radius
        if not frame is None:
            cv2.circle(frame, sight_range.centre.to_tuple()
            , sight_range.radius, (255,0,0), 1)
            cv2.circle(frame, surround_range.centre.to_tuple()
            , surround_range.radius, (255,0,0), 1)

        return new_dir


"""Implements the merge sort algorithm"""
class MergeSort:
    def __init__(self, descending = False):
        self.descending = descending

    """Sort an array"""
    def sort(self, array):
        print("split: " +str(array))
        if len(array) <= 1:
            return array
        mid = len(array)//2
        #Divide objects into two parts
        left = array[:mid]
        right = array[mid:]
        #Sort the left
        left = self.sort(left)
        right = self.sort(right)
        return self.__merge(left, right)

    """Merge two arrays in sorted order"""
    def __merge(self, arr1, arr2):
        temp = []
        while len(arr1) > 0 or len(arr2) > 0:
            if len(arr1) == 0:
                temp.append(arr2.pop(0))
            elif len(arr2) == 0:
                temp.append(arr1.pop(0))
            elif self.compare(arr1[0], arr2[0]) == -1:
                if self.descending:
                    temp.append(arr2.pop(0))
                else:
                    temp.append(arr1.pop(0))
            else:
                if self.descending:
                    temp.append(arr1.pop(0))
                else:
                    temp.append(arr2.pop(0))
        return temp

    """Checks if the algorithm should insert i given j is highest"""
    def __should_insert(self, i, j):
        if self.descending and self.compare(i, j) == 1:
            return True
        elif not self.descending and self.compare(i,j) == -1:
            return True
        return False

    """
    Given two elements i and j
    return -1 if i < j
    return 0 if i == j
    return 1 if i > j
    """
    def compare(self, i, j):
        if i < j:
            return -1
        elif i == j:
            return 0
        else:
            return 1


"""Sort game objects based on importance"""
class ImportanceSort(MergeSort):
    def __init__(self):
        #Make sure merge sort is done descendingly
        super().__init__(True)

    """Overrides"""
    def compare(self, i, j):
        if i[1] < j[1]:
            return -1
        elif i[1] == j[1]:
            return 0
        else:
            return 1