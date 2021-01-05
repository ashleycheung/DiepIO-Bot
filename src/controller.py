"""These classes are used by the bot to control the game"""
import math
import threading
import time
import pyautogui
from pynput import keyboard, mouse
from environment import *


"""This class is used by the bot to control the game"""
class BotController:
    """
    Origin is the point (0,0) of the screen capture 
    relative to the actual screen
    """
    def __init__(self, origin):
        self.origin = origin
        self.keyboard = keyboard.Controller()
        self.mouse = mouse.Controller()
        #Stores current move direction
        self.move_direction = Vector2(0,0)
        self.pressed_keys = {}

    """
    Given the player position relative to the screen capture
    and the direction, move that way on the game
    """
    def move(self, direction : Vector2):
        if direction.normalize() != self.move_direction:
            #Release all pressed keys
            for key in self.pressed_keys:
                self.keyboard.release(key)

            #Move in a new direction
            self.move_direction = direction.normalize()

            #If direction is Vector2(0,0) dont move
            if self.move_direction.length == 0:
                return

            #Move in x direction
            if self.move_direction.x > math.cos(3 * math.pi / 8):
                self.keyboard.press('d')
                self.pressed_keys['d'] = True
            elif self.move_direction.x < math.cos(5 * math.pi / 8):
                self.keyboard.press('a')
                self.pressed_keys['a'] = True

            #Move in y direction
            if self.move_direction.y > math.sin(math.pi / 8):
                self.keyboard.press('s')
                self.pressed_keys['s'] = True
            elif self.move_direction.y < math.sin(math.pi / -8):
                self.keyboard.press('w')
                self.pressed_keys['w'] = True
    
    """
    Shoot in a given direction. If player_pos is passed in
    it will shoot with greater accuracy
    """
    def shoot(self, shoot_pos):
        pos_on_screen = self.origin + shoot_pos
        self.mouse.position = pos_on_screen.to_tuple()
        self.mouse.press(mouse.Button.left)
        #Make thread to release
        threading.Thread(target=self.release_shoot, args=(0.1,)).start()
        

    """Release shoot button after delay"""
    def release_shoot(self, wait_time):
        time.sleep(wait_time)
        self.mouse.release(mouse.Button.left)

    """Returns the mouse position relative to the origin"""
    def get_mouse_pos(self):
        x, y = pyautogui.position()
        return Vector2(x - self.origin.x, y - self.origin.y)



