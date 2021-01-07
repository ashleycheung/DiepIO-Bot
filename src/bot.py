import cv2
import math
import time
from game_parser import GameParser
from game_parser import *
from controller import *
from config import *
from pynput import keyboard, mouse
from environment import *
from behavior import *
from render import *


HELP_MSG = """Thank you for using this bot. 
Press 'esc' to quit the bot and 'p' to pause the bot"""

################################################################################
#Bot Classes
################################################################################

    

"""This is the main bot class"""
class Bot:
    def __init__(self, capture_size, display_view = True):
        self.display_view = display_view
        self.screen_cap = ScreenCapture(capture_size)
        self.render = BotRender()
        self.game_parser = GameParser(TRACKING_RATE)
        self.environment = Environment(capture_size)
        self.behaviour = Behavior()

        #Used to pause or quit bot
        self.playing = True
        self.paused = True

        #Listener for quitting bot
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_keypress
        )
        self.keyboard_listener.start()
        #Configure bot
        self.configure()
        self.control = BotController(
            Vector2.from_tuple(self.screen_cap.position))

    """Called by keyboard listener"""
    def on_keypress(self, key):
        try:
            if key == keyboard.Key.esc:
                self.playing = False
            elif key.char == 'p':
                self.paused = not self.paused
        except:
            pass

    """Configures the bot"""
    def configure(self):
        #Configure capture
        self.screen_cap.configure()

        #Get frame and select player
        frame = self.screen_cap.get_frame()

        #Get bbox to search player
        player_search_bbox = BBoxOps.centre_to_bbox(
            self.screen_cap.get_view_centre(), Vector2(100,100))

        #Initialise parser
        self.game_parser.init(frame, player_search_bbox)


    """Check if the bot is paused"""
    def check_if_paused(self):
        #Pause loop
        if self.paused:
            print("Bot has been paused. Press 'p' to resume")
            while self.paused and self.playing:
                pass
            print("Bot has been unpaused.")


    """Lets the bot play"""
    def play(self):
        print(HELP_MSG)
        #Make video writere
        # output_video = cv2.VideoWriter('output.avi'
        #     ,cv2.VideoWriter_fourcc('M','J','P','G'), 10
        #     , CAPTURE_SIZE)
        while self.playing:
            #Get the current game frame
            frame = self.screen_cap.get_frame()

            #Update the environment
            self.game_parser.update(frame, self.environment)

            #Apply the bot action
            self.behaviour.action(self.environment, self.control, frame)

            #Render view if option is true
            if self.display_view:
               self.render.render_view(frame, self.environment)

            #output_video.write(frame)

            #Check if the bot is paused
            self.check_if_paused()

        print(f"Average fps {self.render.get_average_fps()}")
        #output_video.release()
        #Close all windows
        cv2.destroyAllWindows()
        print("Bot has shutdown. Goodbye.")


if __name__ == "__main__":
    bot = Bot(CAPTURE_SIZE)
    bot.play()
