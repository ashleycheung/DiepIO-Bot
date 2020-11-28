import pyautogui
import numpy as np
import cv2
import sys
import threading
import time
import math
from pynput import keyboard, mouse


class BoxConfigure:
    def __init__(self):
        self.mouse_listener = None
        self.rect_top = None
        self.rect_size = None

    """Runs configuration loop and returns the box"""
    def configure(self):
        print("Click top corner of rectangle")
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
        )
        self.mouse_listener.start()
        while self.rect_top == None or self.rect_size == None:
            pass
        return (
            self.rect_top[0],
            self.rect_top[1],
            self.rect_size[0],
            self.rect_size[1]
        )


    """Called by mouse listener"""
    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            if self.rect_top == None:
                self.rect_top = pyautogui.position()
                print("Rect_top set to " + str(self.rect_top))
                return
            elif self.rect_size == None:
                new_pos = pyautogui.position()
                new_rect_size = (
                    new_pos[0] - self.rect_top[0], 
                    new_pos[1] - self.rect_top[1]
                )

                if new_rect_size[0] <= 0 or new_rect_size[1] <= 0:
                    print("Error: Invalid end point. Resetting...")
                    self.rect_top = None
                    return

                #Valid size
                self.rect_size = new_rect_size
                print("Rect_size set to " + str(self.rect_size))
                return



class ObjectTracker:
    def __init__(self):
        self.show_view = True
        self.playing = True
        self.k_listener = keyboard.Listener(
            on_press = self.on_key_pressed
        )
        self.k_listener.start()
        #Tracks the player
        self.p_tracker = None
        self.p_rect_pos = None
        #Load view
        self.view_rect = BoxConfigure().configure()
        #Create view
        self.create_view(self.view_rect)
        self.closest_target = None
        self.bot = None

    @property
    def p_center(self):
        if self.p_rect_pos != None:
            return self.get_bbox_center(self.p_rect_pos)

    def create_view(self, region):
        if self.show_view:
            threading.Thread(target=self.load_view, args=(region,)).start()


    def load_view(self, region):
        while self.playing:
            # capture computer screen
            img = pyautogui.screenshot(region = region)
            # convert image to numpy array
            img_np = np.array(img)
            img_np = self.process_image(img_np)
            # convert color space from BGR to RGB
            frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
            # show image on OpenCV frame
            cv2.imshow("Screen", frame)

            if cv2.waitKey(1) == 27:
                break


    def draw_box(self, img, bbox, text = "Tracking", fontscale = 0.7, line_thickness = 2, 
        text_colour = (255,0,0), box_colour = (219, 173, 237)
    ):
        output_img = img
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        output_img = cv2.rectangle(output_img, (x, y), ((x + w), (y + h)), box_colour, 3, 3 )
        text_offset = (20,10)
        if text != None:
            output_img = cv2.putText(
                output_img, 
                text,   #Text string
                (x - text_offset[0],y - text_offset[1]),    #Position
                cv2.FONT_HERSHEY_SIMPLEX,   #Font
                fontscale,  #Fontscale
                text_colour,  #Colour
                line_thickness,  #Line thickness
                cv2.LINE_AA
            )
        return output_img


    """Finds the object needle in haystack and draws a rectangle"""
    def find_object(self, haystack):
        output_image = haystack
        match_method = cv2.TM_CCORR
        needle = cv2.imread("../images/square_2.png")
        w, h = (100,100)

        #Search template
        res = cv2.matchTemplate(needle, haystack, match_method)

        # threshold = 0.8
        # loc = np.where( res >= threshold)

        # for pt in zip(*loc[::-1]):
        #     output_image = cv2.rectangle(output_image, pt, (pt[0] + w, pt[1] + h), (0,0,255), 2)

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        #Draw rectangle
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        haystack = cv2.rectangle(haystack,top_left, bottom_right, 255, 2)
        return output_image


    """Returns the center of an object"""
    def get_bbox_center(self, bbox):
        return (
            int(bbox[0] + bbox[2] / 2),
            int(bbox[1] + bbox[3] / 2)
        )

    """Gets the distance between two points"""
    def get_dist(self, p1, p2):
        x_squared = (p1[0] - p2[0]) ** 2
        y_squared = (p1[1] - p2[1]) ** 2
        return math.sqrt(x_squared + y_squared)


    def find_contours(self, img):
        output_img = img
        edged = cv2.Canny(output_img,100,200)
        contours, hierarchy = cv2.findContours(
            edged,  
            cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        closest_dist = None

        #Add rectangles
        for contour in contours:
            bbox = cv2.boundingRect(contour)

            #Ensures rectangles of certain size
            if cv2.contourArea(contour) < 600:
                continue
            
            dist = -1
            if self.p_rect_pos != None:
                dist = int(self.get_dist(self.get_bbox_center(bbox), self.get_bbox_center(self.p_rect_pos)))

            #Do not track if too close
            if dist < 20:
                continue
            
            if closest_dist == None or dist < closest_dist:
                closest_dist = dist
                self.closest_target = bbox

            text = "Dist: " + str(dist)
            output_img = self.draw_box(output_img, bbox, text=text, text_colour = (0,0,0), line_thickness = 1)

        #Draw closest target
        if self.closest_target != None:
            output_img = self.draw_box(output_img, self.closest_target, text=None, box_colour = (255,0,0), line_thickness = 1)

        return output_img


    def track_object(self, img):
        output_img = img

        #Init tracker if doesnt exist
        if self.p_tracker == None:
            target_bbox = cv2.selectROI("Screen",output_img, False)
            self.p_tracker = cv2.TrackerMOSSE_create()
            self.p_tracker.init(img, target_bbox)

            if self.bot == None:
                self.bot = Bot(self)
                self.bot.play()
        
        #Update tracker
        success, bbox = self.p_tracker.update(output_img)
        if success:
            self.p_rect_pos = bbox
            output_img = self.draw_box(output_img, bbox, box_colour=(44,252,3))
        else:
            print("Lost")
        
        return output_img


    def process_image(self, img):
        output_img = img
        output_img = self.track_object(output_img)
        output_img = self.find_contours(output_img)
        #output_img = self.find_object(output_img)
        return output_img


    def on_key_pressed(self, key):
        if key == keyboard.Key.esc:
            print("Bot quit")
            self.playing = False
            sys.exit()


class Bot:
    def __init__(self, object_tracker):
        super().__init__()
        self.tracker = object_tracker
        self.controller = GameController(object_tracker)
        self.kiting_dist = 150

    def play(self):
        threading.Thread(target=self.next_move).start()

    def next_move(self):
        while self.tracker.playing:
            if self.tracker.closest_target != None:
                self_pos = self.tracker.p_center
                target_pos = self.tracker.get_bbox_center(self.tracker.closest_target)
                self.controller.attack(target_pos)

                dist = self.tracker.get_dist(self_pos, target_pos)

                #Walk towards target
                if dist > self.kiting_dist:
                    self.controller.move_in_dir((
                        target_pos[0] - self_pos[0],
                        target_pos[1] - self_pos[1]
                    ))
                else:
                    #Move away from target
                    self.controller.move_in_dir((
                        -1 * target_pos[0] + self_pos[0],
                        -1 * target_pos[1] + self_pos[1]
                    ))


class GameController:
    def __init__(self, object_tracker):
        super().__init__()
        self.keyboard = keyboard.Controller()
        self.mouse = mouse.Controller()
        self.tracker = object_tracker

    """
    Move in a certain direction given a vector tuple
    """
    def move_in_dir(self, dir, travel_time = 1):        
        pressed_keys = []

        #Move in x direction
        if dir[0] > 0:
            self.keyboard.press('d')
            pressed_keys.append('d')
        else:
            self.keyboard.press('a')
            pressed_keys.append('a')

        #Move in y direction
        if dir[1] > 0:
            self.keyboard.press('s')
            pressed_keys.append('s')
        else:
            self.keyboard.press('w')
            pressed_keys.append('w')

        time.sleep(travel_time)

        #Release all pressed keys
        for key in pressed_keys:
            self.keyboard.release(key)


    """Attack at a particular position"""
    def attack(self, pos):
        #Get displacement vector
        view_rect = self.tracker.view_rect

        #Convert to screen position
        screen_pos = (
            view_rect[0] + pos[0],
            view_rect[1] + pos[1]
        )

        #Attack
        pyautogui.click(screen_pos[0],screen_pos[1])
        self.mouse.press(mouse.Button.left)
        time.sleep(1)
        self.mouse.release(mouse.Button.left)


if __name__ == '__main__':
    ObjectTracker()