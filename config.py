RPI = False                     # Enable optimizations for the RPi
LINE_IN = False                 # Enable a second audio input

DEVICE_1_ID = 1 if RPI else 2   # The device ID for the primary input
DEVICE_2_ID = 2                 # The device ID for the secondary inpuy (opt.)

CHANNELS = 1                    # The number of channels the device has
FORMAT = 8                      # The audio format for the input devices (int16)
CHUNK = 1024                    # The amount of data to request per loop
RATE = 44100                    # The sampling rate of the device

QUIET_MUSIC = 15                # The lower threshold for music
LOUD_MUSIC = 3                  # The upper threshold for music

QUIET_SPEECH = 30               # The lower threshold for speech
LOUD_SPEECH = 12                # The upper threshold for speech

SCREEN_HEIGHT = 320             # The default display height
SCREEN_WIDTH = 480              # The default display width

AVERAGE_SAMPLES = 20            # The number of samples to average for
GRAPH_SAMPLES = 200             # The number of samples to show on the graph

SPLIT_FREQUENCY = 125           # The frequency to split at in split mode

ROUND_CORNERS = True            # Should the corners of pannels be rounded

GRAPH_COLOUR_2 = (130, 60, 70)  # The secondary colour on the graph
BORDER_COLOUR = (15, 15, 15)    # The borders between pannels
BORDER_LIGHT = (90, 95, 100)    # A lighter border shade
GRAPH_COLOUR = (60, 130, 70)    # The primary colour on the graph
TEXT_COLOUR = (80, 100, 120)    # The colour of foreground text
BG_COLOUR = (60, 80, 110)       # The background colour
BG_DARKER = (50, 60, 90)        # A darkened background
FG_COLOUR = (0, 0, 0)           # The colour of text on pannels

LIGHT_BLUE = (80, 180, 220)     # The colour of the "VU" bars
DARK_BLUE = (10, 35, 60)        # The colour of the "VU" bars' background
ORANGE = (230, 190, 45)         # The colour for when the audio is too quiet
GREEN = (50, 150, 80)           # The colour for when the audio is okay
RED = (215, 45, 50)             # The colour for when the audio is too loud

SOURCE_1_LABEL = 'MIC'          # The label for the primary source
SOURCE_2_LABEL = 'OUT'          # The label for the secondary source

S1_SPLIT_LABEL = 'HIGH'         # The label for the highpass in split mode
S2_SPLIT_LABEL = 'LOW'          # The label for the lowpass in split mode

BUTTON_COLOUR = [               # The colour pallette for an unusable button
    (64 , 87 , 54 ),
    (129, 146, 114),
    (43 , 55 , 31 ),
    (51 , 64 , 38 )
]
BUTTON_DGREY_COLOUR = [         # The colour pallette for a dissabled button
    (66 , 67 , 65 ),
    (81 , 81 , 82 ),
    (45 , 45 , 45 ),
    (43 , 43 , 43 )
]
BUTTON_GREY_COLOUR = [          # The colour pallette for an inactive button
    (132, 134, 131),
    (162, 163, 165),
    (91 , 91 , 91 ),
    (87 , 87 , 87 )
]
BUTTON_BLUE_COLOUR = [          # The colour pallette for an active button
    (117, 206, 240),
    (140, 231, 255),
    (28 , 109, 139),
    (72 , 168, 208)
]

BIG_FONT_SIZE = 20              # The font size for buttons and pannel labels
FONT_SIZE = 10                  # The font size for the "UV" meter labels

FPS = 30 if RPI else 60         # The FPS to refresh the display at

BUTTON_PADDING = 2              # The padding around buttons
COLOUR_PADDING = 4              # The internal padding around coloured regions

WATERMARK = True                # Toggle the mark in the bottom right
