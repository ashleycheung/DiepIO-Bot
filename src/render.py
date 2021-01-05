"""This class is responsible for rendering"""
import cv2
import time

class BotRender:
    def __init__(self):
        self.show_player = True
        self.show_objects = False
        self.last_render_time = None
        self.total_fps = 0
        self.fps_detects = 0


    """Renders the view for humans to see"""
    def render_view(self, frame, environment):
        self.calculate_fps(frame)
        #Show player
        if not environment.player is None and self.show_player:
            frame = BotRender.draw_rect(environment.player.bbox, frame, (108,238,163))
        #Show nearby objectsawd
        if self.show_objects:
            for game_object in environment.objects:
                frame = BotRender.draw_rect(game_object.bbox, frame, (74, 252, 255))
                text_pos = (int(game_object.bbox[0]), int(game_object.bbox[1]))
                frame = BotRender.draw_text(frame, game_object.type, text_pos)
        #Shows frame
        cv2.imshow("Bot view", frame)
        cv2.waitKey(1)

    """Calculates the fps and displays it on the frame"""
    def calculate_fps(self, frame):
        if self.last_render_time is None:
            self.last_render_time = time.time()
        else:
            curr_time = time.time()
            time_elapsed = curr_time - self.last_render_time
            self.last_render_time = curr_time
            fps = 1.0 / time_elapsed
            self.total_fps += fps
            self.fps_detects += 1
            fps = round(fps, 0)
            BotRender.draw_text(frame, 'fps: ' + str(fps), (10,30))

    def get_average_fps(self):
        return self.total_fps / self.fps_detects

    """
    Given a frame, draw a bbox on it
    bbox is in form (top_left_x, top_left_y, width, height)
    """
    @staticmethod
    def draw_rect(bbox, frame, color = (255,0,255), thickness=2):
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        return cv2.rectangle(frame, (x, y), ((x + w), (y + h)), color, thickness)

    """
    Draws a line on the frame
    The points are Vector2
    """
    @staticmethod
    def draw_line(frame, start_point, end_point, color=(255,255,0), thickness=2):
        frame = cv2.line(frame, start_point.to_tuple()
            , end_point.to_tuple(), color, thickness)
        return frame

    """
    Draws a circle on the frame
    """
    @staticmethod
    def draw_circle(frame, circle, color=(255,0,0), thickness=2):
        frame = cv2.circle(frame, circle.centre.to_tuple()
            , circle.radius, color, thickness)
        return frame

    """
    Puts text
    """
    @staticmethod
    def draw_text(frame, text, pos, font=cv2.FONT_HERSHEY_SIMPLEX
        ,fontScale=1, color=(0,0,0), thickness=1):
        frame = cv2.putText(frame, text, pos, font
            , fontScale, color, thickness, cv2.LINE_AA)
        return frame