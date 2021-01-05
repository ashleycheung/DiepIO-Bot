"""This file parses the game by analysing it each frame"""

import cv2
import time
import numpy as np
import pyautogui
from pynput import mouse
from PIL import ImageGrab
from environment import *
from config import *
from render import BotRender

MIN_OBJECT_AREA = 500

"""This class captures the screen"""
class ScreenCapture:
    def __init__(self, size):
        self.mouse_listener = None
        self.centre = None
        self.size = size
        self.rect = None

    """Return the centre position vector relative to the captured screen"""
    def get_view_centre(self):
        if self.centre is None or self.rect is None:
            return None
        centre = Vector2(self.centre[0], self.centre[1])
        view_origin = Vector2(self.rect[0], self.rect[1])
        return centre - view_origin

    @property
    def position(self):
        if self.rect is None:
            return None
        return (self.rect[0], self.rect[1])

    """Gets the frame for the screen capture"""
    def get_frame(self):
        rect = self.get_rect()
        if rect == None:
            return None
        #Grab image
        pil_img = ImageGrab.grab(rect)
        #Convert to numpy array
        frame = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_BGR2RGB)
        return frame

    """Returns the view rectangle"""
    def get_rect(self):
        if self.centre == None:
            return None
        #Get rectangle if it hasnt been calculated yet
        if self.rect is None:
            x_coor = max(0, self.centre[0] - self.size[0] / 2)
            y_coor = max(0, self.centre[1] - self.size[1] / 2)

            self.rect = (x_coor, y_coor, x_coor + self.size[0]
                , y_coor + self.size[1])
        return self.rect

    """Configures"""
    def configure(self):
        print("Press the player tank")
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
        )
        self.mouse_listener.start()
        while self.centre == None:
            pass
        self.mouse_listener.stop()

    """Called by mouse listener"""
    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            print("clicked")
            self.centre = pyautogui.position()


"""This is used to detect what shape an object is"""
class ShapeDetector:
    @staticmethod    
    def detect(contour):
        shape = GameObject.UNKNOWN
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        vertices_num = len(approx)
        #Check if it is a triangle
        if vertices_num == 3:
            shape = GameObject.TRIANGLE
        elif vertices_num == 4:
            #Check the aspect ratio
            (x, y, w, h) = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            if aspect_ratio >= 0.95 and aspect_ratio <= 1.05:
                shape = GameObject.SQUARE
            else:
                shape = GameObject.SHAPE_GROUP
        elif vertices_num == 5:
            shape = GameObject.PENTAGON
        
        return shape


"""Stores a collection of tracked objects"""
class TrackedObjects:
    def __init__(self, objects, tracking_buffer=(20,20)):
        self.trackers = []
        self.objects = objects
        self.tracking_buffer = tracking_buffer

    """Intialize the tracked objects"""
    def init(self, frame):
        for obj in self.objects:
            #Make new tracker
            new_tracker = cv2.TrackerMOSSE_create()
            #Initialise tracker and make buffer for object bbox
            new_tracker.init(frame, BBoxOps.make_buffer(obj.bbox
                ,self.tracking_buffer))
            #Add tracker to list of trackers
            self.trackers.append(new_tracker)

    """
    Update all tracked objects
    returns successes list and the updated objects
    """
    def update(self, frame, detect_alg):
        #Update all the bboxes in the tracked objects
        for i in range(len(self.objects)):
            success, new_bbox = self.trackers[i].update(frame)
            game_obj = self.objects[i]
            if success:
                game_obj.bbox = BBoxOps.remove_buffer(new_bbox
                    , self.tracking_buffer)
                game_obj.is_tracked = True
            else:
                #Redetect object from previous position
                search_bbox = BBoxOps.make_buffer(game_obj.bbox, self.tracking_buffer)
                new_obj = TrackedObjects.redetect(frame
                    , search_bbox, detect_alg)

                if new_obj:
                    self.objects[i] = new_obj
                    self.objects[i].is_tracked = True
                    self.trackers[i] = cv2.TrackerMOSSE_create()
                    self.trackers[i].init(frame
                        , BBoxOps.make_buffer(new_obj.bbox,self.tracking_buffer))
                else:
                    self.objects[i].is_tracked = False

            #Update to is tracked
        return self.objects

    """Attempts to redetect an object given its previous bbox """
    @staticmethod
    def redetect(frame, search_bbox, detect_alg):
        frame_size = (frame.shape[0], frame.shape[1])
        #Redetect object from previous position
        b = BBoxOps.fit_bbox_in_frame(search_bbox, frame_size)
        b = BBoxOps.bbox_to_positions(b)
        b = BBoxOps.make_int(b)
        old_bbox_pos = (search_bbox[0], search_bbox[1])
        cropped_frame = frame[b[1]:b[3], b[0]:b[2]]

        #Detect the object
        detected_objs = detect_alg.detect(cropped_frame
                , 1, old_bbox_pos)

        #Return the object if redetected
        if len(detected_objs) != 0:
            return detected_objs[0]
        return None


"""Class used to detect objects"""
class DetectionAlgorithm:
    """
    Given a frame, detect and return a list of detected game objects
    object limit is how many objects it will detect
    If None, there is no limit
    origin is where the origin of frame is. Game object will be offsetted
    based on origin
    If player bbox is given, it will be ignored from the detected objects
    """
    def detect(self, frame, object_limit = None, origin=(0,0), player_bbox=None):
        #Get contours
        edged = cv2.Canny(frame, 100, 200)

        contours, hierarchy = cv2.findContours(
            edged,  
            cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )
        #Empty the list of nearby objects
        nearby_objects = []
        num_detected = 0
        #Gets the bbox of all the contours
        for contour in contours:
            #Check if limit has been reached
            if not object_limit is None and num_detected >= object_limit:
                break
            
            #Get object bbox, apply origin offset and buffer
            o_bbox = cv2.boundingRect(contour)
            o_bbox = (o_bbox[0] + origin[0]
                , o_bbox[1] + origin[1], o_bbox[2], o_bbox[3])

            #Check if overlaps with player bbox
            if player_bbox and BBoxOps.bbox_overlap(player_bbox, o_bbox):
                continue

            #Skip if the object is too small
            if cv2.contourArea(contour) < MIN_OBJECT_AREA:
                continue
            shape = ShapeDetector.detect(contour)
            #Make game object
            game_object = GameObject(o_bbox, shape)
            nearby_objects.append(game_object)
            num_detected += 1
        return nearby_objects


"""Used to parse the game"""
class GameParser:
    def __init__(self, detect_rate):
        self.trackers = []
        self.frames_passed = 0
        #Stores how many frames before detection happens again
        self.detect_rate = detect_rate
        self.tracked_objects = None
        self.detect_alg = DetectionAlgorithm()
        self.player_tracker = self.make_player_tracker()

    """Makes the tracker for the player"""
    def make_player_tracker(self):
        return cv2.TrackerKCF_create()

    """Sets the player of the game"""
    def init(self, frame, player_bbox):
        self.player_tracker.init(frame, player_bbox)

    """Updates the environment given a frame"""
    def update(self, frame, environment):
        #Track Player
        success, new_bbox = self.player_tracker.update(frame)
        if not success:
            print("Redetecting player")
            #Redetect player from previous position
            old_bbox = environment.player.bbox
            new_player = TrackedObjects.redetect(frame, old_bbox, self.detect_alg)

            #If player can be redetected reinitialise player
            if new_player:
                new_player.type = GameObject.PLAYER
                environment.player = new_player
                self.player_tracker = self.make_player_tracker()
                self.player_tracker.init(frame, new_player.bbox)
        else:
            environment.player = GameObject.make_player(new_bbox)

        #Detect tracked objects if necessary
        if self.tracked_objects is None or self.frames_passed == 0:
            #Make detection
            objects_list = self.detect_alg.detect(frame, player_bbox=new_bbox)

            self.tracked_objects = TrackedObjects(objects_list)
            self.tracked_objects.init(frame)
        else:
            #Else update existing tracked objects
            self.tracked_objects.update(frame, self.detect_alg)
        
        #Update environment objects
        environment.objects = self.tracked_objects.objects

        #Iterate
        if self.detect_rate > 0:
            self.frames_passed = (self.frames_passed + 1) % self.detect_rate
        return self.tracked_objects


if __name__ == '__main__':
    s = ScreenCapture(CAPTURE_SIZE)
    s.configure()
    td = GameParser()
    prev_time = None
    total_fps = 0
    fps_detects = 0
    while True:
        frame = s.get_frame()

        #Get fps
        if prev_time is None:
            prev_time = time.time()
        else:
            curr_time = time.time()
            time_elapsed = curr_time - prev_time
            prev_time = curr_time
            fps = 1.0 / time_elapsed
            total_fps += fps
            fps = round(fps, 0)
            fps_detects += 1
            BotRender.draw_text(frame, 'fps: ' + str(fps), (10,30))

        # tracked_objects = td.update(frame)

        # has_lost_track = False
        # for t in tracked_objects.objects:
        #     if t.is_tracked:
        #         BotRender.draw_rect(t.bbox, frame, (0,255,0))
        #     else:
        #         BotRender.draw_rect(t.bbox, frame, (0,0,255))
        #         has_lost_track = True
        #     BotRender.draw_text(frame, str(t.type), (int(t.bbox[0]), int(t.bbox[1])))

        cv2.imshow("trackng", frame)
        #If esc is pressed
        if cv2.waitKey(1) == 27:
            break
    
    print(f"Average fps {total_fps / fps_detects}")