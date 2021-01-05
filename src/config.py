"""
This is the configurations file
"""

################################################################################
#Bot Parameters
################################################################################

#This is the minimum area an object must be for the bot to notice
CAPTURE_SIZE = (800,400)

#This is the rate at which the bot run object tracking rather than detection
#Detection is expensive so tracking is preferred
#Higher TRACKING RATE means better fps on video
#But lower bot performance (It doesnt see new objects as fast)
TRACKING_RATE = 15
