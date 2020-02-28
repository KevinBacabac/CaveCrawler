# REWRITE IN PROGRESS
# Verify multiplayer
# TODO make a class for main menu and setting the gamemode dupe code removal
# TODO rewrite the cache system, keeping in mind that cached maps are treated as players
# Separate GUI and leave it unaffected by levelDarkness
# Don't let tunnels spawn player in lava
# Consider removing support for python 2 if android can work on other platform, as super inheritance is only python 3
# Finish item rewrite
from __future__ import division, print_function

try:
    from future import standard_library
    raise ImportError
except ImportError:
    import pickle
    USING_PYTHON_TWO = False
else:
    import cPickle as pickle
    standard_library.install_aliases()
    USING_PYTHON_TWO = True

try:
    import android
except ImportError:
    android = None

import pygame
import pygame.gfxdraw
import pygame.freetype
import pygame.font
import pygame.ftfont
import fnmatch
import sys
import random
import time
import math
import shelve
import os
import copy
import datetime
import shutil

# Networking modules
import socket
import threading
import struct  # , ssl
import pickletools  # For optimizing pickles

try:
    import numpy as np
    print('Using numpy.')

except ImportError:
    np = None
    print('Not using numpy.')

useNumpy = True


def usingNumpy():
    return np is not None and useNumpy


try:
    import optimize_dirty_rects
except ImportError:
    optimize_dirty_rects = None

if USING_PYTHON_TWO:
    def mathFloor(x):
        return int(math.floor(x))

    def round(x):
        return int(round(x))
    xrange = range

else:
    mathFloor = math.floor

HOST_IP = '0.0.0.0'
DEVELOPER_MODE = True  # Set to false before exporting game

FPS = 40
TAU = 2 * math.pi

# Finds local IP address for broadcasting sockets
LAN_IP = socket.gethostbyname(socket.gethostname())

MAIN_PORT = 24000
BROADCAST_PORT = MAIN_PORT + 1

pygame.init()

mainClock = pygame.time.Clock()

INTERNAL_WIDTH = 1024
INTERNAL_HEIGHT = 768
INTERNAL_SIZE = (INTERNAL_WIDTH, INTERNAL_HEIGHT)


if android:
    android.init()
    android.map_key(android.KEYCODE_BACK, pygame.K_ESCAPE)

    import android.mixer as soundMixer

    '''
    Due to the graphical bugs when pgs4a runs a window with a different screen resolution,
    the mobile game runs with displaySurface and windowSurface. displaySurface has the
    exact same resolution as the desired device and contains only a black screen.
    On this, the windowSurface is centered and the surface is blitted on the displaySurface.
    '''

    windowSurface = pygame.Surface(INTERNAL_SIZE)

    DEVICE_WIDTH = 1280
    DEVICE_HEIGHT = 800

    displaySurface = pygame.display.set_mode((DEVICE_WIDTH, DEVICE_HEIGHT))

    offsetX, offsetY = (DEVICE_WIDTH - INTERNAL_WIDTH) / 2, (DEVICE_HEIGHT - INTERNAL_HEIGHT) / 2

else:
    import pygame.mixer as soundMixer
    # Better sound than the default settings
    soundMixer.pre_init(frequency=44100, channels=2, buffer=1024)

    windowSurface = pygame.display.set_mode(INTERNAL_SIZE,
                                            pygame.DOUBLEBUF | pygame.HWSURFACE)

pygame.scrap.init()
clipboard = None


def imgLoad(path, alpha=False):
    return pygame.image.load(path)


logo_path = os.path.join("images", "Icon.png")
logoIcon = imgLoad(logo_path).convert_alpha()
pygame.display.set_icon(logoIcon)

SCREEN_RECT = pygame.Rect(0, 0, *INTERNAL_SIZE)
pygame.display.set_caption('Cave Explorer', logo_path)

mouseDown = False
mouseDownTimer = FPS / 2

WHITE = pygame.Color('White')
CONSOLE_GREY = pygame.Color(192, 192, 192)
GREY = pygame.Color(128, 128, 128)
DARKER_GREY = pygame.Color(92, 92, 92)
DARK_GREY = pygame.Color(48, 48, 48)
BLACK = pygame.Color('Black')
RED = pygame.Color('Red')
ORANGE = pygame.Color('Orange')
GOLD = pygame.Color('Gold')
GREEN = pygame.Color('Green')
BLUE = pygame.Color('Blue')

# LPK means localPlayerKey
# Save files can contain multiple players, when opened locally the game loads
# player info like bankBalance, warehouseInv, player class, etc using
# either players[LPK] and pl_Info[LPK]
# For this reason, a player name as an empty string '' is not allowed to
# connect to any server.

LPK = ''


def PK():  # PK -> playerKey
    if isClient:
        return options['playerName']

    else:
        return LPK


def addServer(name, ip):
    for i, server in enumerate(serverList):
        if server is None:
            index = i
            break

    else:
        print('No spaces in server list.')
        raise NotImplemented  # TODO

    newServerList = setServer(name, ip, index)
    return newServerList


def setServer(name, ip, index):
    nameTR = TextRect(touchScreenFont, 'Server Name: ' + name, WHITE)
    nameTR.rect.topleft = multiPlayMenuList[index].topleft
    nameTR.rect.top += 10
    nameTR.rect.left += 10

    ipTR = TextRect(touchScreenFont, 'Server IP: ' + ip, WHITE)
    ipTR.rect.topleft = nameTR.rect.topleft
    ipTR.rect.top += 40

    serverList[index] = {'Name': name,
                         'IP': ip,
                         'Name TR': nameTR,
                         'IP TR': ipTR}

    return serverList


onOffString = {True: 'On',
               False: 'Off'}

# Default options, will be overriden if options file present
NAMES = ('Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon')
options = {'ambience': True,
           'autoCombat': False,
           'CVD': False,
           'dirtyRect': False,
           'fullscreen': False,
           'highlightCombat': False,
           'lighting': 'Colour',
           'music': True,
           'playerName': random.choice(NAMES),
           'showDamage': True,
           'sound': True,
           'tooltips': True}

if android:
    options['touchScreen'] = True
    options['phoneMode'] = True

else:
    options['touchScreen'] = False
    options['phoneMode'] = False

if DEVELOPER_MODE:
    options['testWorld'] = True

else:
    options['testWorld'] = False


def hasFile(pattern, path=None):
    if path is None:
        path = os.getcwd()

    files = os.listdir(path)
    return bool(fnmatch.filter(files, pattern))


if hasFile('options*'):
    optionFile = shelve.open('options')

    serverList = optionFile['Server List']

    for i in options:
        options[i] = optionFile[i]

else:
    serverList = []
    for i in range(10):
        serverList.append(None)

    #serverList[0] = addServer('Local', 'localhost')

    optionFile = shelve.open('options')
    optionFile['Server List'] = serverList

    for i in options:
        optionFile[i] = options[i]

    # By default make all menus maximized
    optionFile['Menu Maximized'] = True, True, True

optionFile.close()

if options['testWorld']:
    testWorldString = 'Test World'

else:
    testWorldString = 'Normal World'

if options['dirtyRect']:
    dirtyRectEnabledString = 'Optimized'

else:
    dirtyRectEnabledString = 'Fail-safe'

if options['fullscreen']:
    pygame.display.set_mode(INTERNAL_SIZE,
                            pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)

debugMode = False


class DebugLine:
    def __init__(self, prefix):
        self.prefix = prefix
        self.surface = None
        self.value = None

    def updateValue(self, newValue):
        if newValue != self.value:
            self.value = newValue
            self.surface = font.render(self.getDisplayText(), True, WHITE, BLACK)

    def draw(self, currentColumn):
        if self.surface is not None:
            dirtyRects.append(windowSurface.blit(self.surface, (0, currentColumn * 20)))

        return dirtyRects

    def getDisplayText(self):
        return self.prefix + ' - ' + str(self.value)


class DebugPercentageLine(DebugLine):
    def getDisplayText(self):
        return self.prefix + ' - ' + str(round(self.value * 100000)/1000) + '%'


DEBUG_ORDER = ('xCoord', 'yCoord', 'blockType', 'FPS', 'useNumpy',
               'mainLoopLightTimer', 'lightRegionTimer') + tuple(range(13))

debugInfo = {}


for key, prefix in zip(('xCoord', 'yCoord', 'blockType', 'FPS', 'useNumpy'),
                       ('X-coordinate', 'Y-coordinate', 'Block Type', 'FPS', 'Using Numpy')):
    debugInfo[key] = DebugLine(prefix)

for key, prefix in zip(('mainLoopLightTimer', 'lightRegionTimer'),
                       ('Main loop light timer', 'Light region timer')):
    debugInfo[key] = DebugPercentageLine(prefix)

for key in range(13):
    debugInfo[key] = DebugPercentageLine(str(key))

serverName = None

playerNames = {}  # Name above players head
playerToIP = {}

entitiesLock = threading.Lock()

# Sound effects
ambientSounds = []

openChestSound = soundMixer.Sound('sound/Chest Opening.ogg')
pickUpGoldSound = soundMixer.Sound('sound/Gold Sound.ogg')
pickUpItemSound = soundMixer.Sound('sound/Pick Up Item.ogg')
swordWieldSound = soundMixer.Sound('sound/swordWield.ogg')
potionDrinkSound = soundMixer.Sound('sound/potionDrink.ogg')
bowShotSound = soundMixer.Sound('sound/tool/bowShot.ogg')

arrowHitSound = []
for i in range(1, 3 + 1):
    arrowHitSound.append(soundMixer.Sound('sound/tool/arrow_hit' +
                                          str(i) + '.ogg'))

miningSound = []
for i in range(1, 3 + 1):
    miningSound.append(soundMixer.Sound('sound/pickaxe_hit'
                                        + str(i) + '.ogg'))

# Menu
backButtonSound = soundMixer.Sound('sound/Menu Back.ogg')
menuButtonSound = soundMixer.Sound('sound/Menu Select.ogg')

# When clicking arrows to change value
adjustValueSound = soundMixer.Sound('sound/adjustValue.ogg')
errorSound = soundMixer.Sound('sound/Error.ogg')

# Ambience
lavaSound = soundMixer.Sound('sound/ambience/Lava Loop.ogg')
waterDripSound = soundMixer.Sound('sound/ambience/cave-drips.ogg')
flowingWaterSound = soundMixer.Sound('sound/ambience/Water Drip.wav')

caveUnderSeaSound = soundMixer.Sound('sound/ambience/caveUnderSea.ogg')

# Path used for underground city "music" loop
fireplaceSoundPath = 'sound/ambience/Fireplace.ogg'
fireplaceSound = soundMixer.Sound(fireplaceSoundPath)

# Cave environment events
earthquakeSound = soundMixer.Sound('sound/cave environments/earthquake.ogg')

# Player
waterSplashSound = soundMixer.Sound('sound/ambience/Water Splash.ogg')

# Other
doorSound = soundMixer.Sound('sound/ambience/Door.ogg')

# Weather
rainSound = soundMixer.Sound('sound/weather/rain.ogg')
snowSound = soundMixer.Sound('sound/weather/snow.ogg')

deleteMode = False

BLOCK_SIZE = 32
ITEM_SIZE = (32, 32)

'''This is used when the player fights the dragon
The combatRect['Centre'] is used only to describe the area that should remain unaffected
by the darkening of the screen. The combatSurfaces includes the actual surfaces that
are blitted on the screen to darken parts of it. '''
combatRect = {'Centre': None,
              'Top': None, 'Bottom': None,
              'Left': None, 'Right': None}
combatSurfaces = None

TRANSPARENT_BLOCKS = ('Air', 'Torch', 'Rope', 'Ladder')
MOVABLE_BLOCKS = ('Water', 'Lava') + TRANSPARENT_BLOCKS
LIQUIDS = ('Water', 'Lava', 'Rope', 'Ladder')


# Sky textures
def makeWeatherSurface(filename):
    weatherImagePath = os.path.join("images", filename)
    weatherImage = imgLoad(weatherImagePath).convert_alpha()

    h = INTERNAL_HEIGHT + weatherImage.get_height()
    weatherSurface = pygame.Surface((INTERNAL_WIDTH, h), pygame.SRCALPHA, 32)

    for x in range(weatherSurface.get_width() // weatherImage.get_width()):
        for y in range(weatherSurface.get_height() // weatherImage.get_height() + 1):
            weatherSurface.blit(weatherImage, (x * weatherImage.get_width(),
                                               y * weatherImage.get_height()))

    return weatherSurface


class Weather:
    IMAGE_SIZE = 128

    ASH = makeWeatherSurface('ashFall.png')
    RAIN = makeWeatherSurface('rain.png')
    SNOW = makeWeatherSurface('snow.png')
    VALID = ("Ash", "Rain", "Snow")

    def __init__(self):
        self.offsetY = self.IMAGE_SIZE

    def draw(self, window, weather):
        if weather in self.VALID:
            window.blit(self.getSurface(weather), (0, self.offsetY))
            self.offsetY += self.getSpeed(weather)

            while self.offsetY >= 0:
                self.offsetY -= self.IMAGE_SIZE  # Height of rain image

    @staticmethod
    def getSpeed(weather):
        speed = {
            "Ash": 20,
            "Rain": 80,
            "Snow": 40
        }[weather]

        return speed / FPS

    @staticmethod
    def getSurface(weather):
        return {
            "Ash": Weather.ASH,
            "Rain": Weather.RAIN,
            "Snow": Weather.SNOW
        }[weather]


weatherManager = Weather()

possibleFonts = 'HelveticaNeue, Helvetica, Arial'
FREESANSBOLD_FONT = 'fonts/freesansbold.ttf'
CONSOLE_FONT = pygame.font.Font('fonts/console.ttf', 12)

if android:
    MENU_FONT_SIZE = 60
    FONT_SIZE = 25
    TOUCHSCREEN_FONT_SIZE = 30

    drawLine = pygame.draw.line

else:
    MENU_FONT_SIZE = 50
    FONT_SIZE = 16
    TOUCHSCREEN_FONT_SIZE = 25

    drawLine = pygame.draw.aaline


# TODO, look into breaking up if / else blocks and having bold=True
if ('helveticaneue' in pygame.font.get_fonts()
    or 'helvetica' in pygame.font.get_fonts()
    or 'arial' in pygame.font.get_fonts()):

    # Use system fonts if possible, make them bold
    menuFont = pygame.freetype.SysFont(possibleFonts, MENU_FONT_SIZE, True)
    l_menuFont = pygame.font.SysFont(possibleFonts, 50, True)
    textParticleFont = pygame.freetype.SysFont(possibleFonts, 16, True)
    typeTextFont = pygame.ftfont.SysFont(possibleFonts, 50, True)  # Used only for typeText
    font = pygame.ftfont.SysFont(possibleFonts, FONT_SIZE, True)
    buildingLabelFont = pygame.freetype.SysFont(possibleFonts, FONT_SIZE, True)
    # Detailed text for menus active when playing and can be minimized such as Player Info
    submenuFont = pygame.ftfont.SysFont(possibleFonts, 12, True)
    warehouseFont = pygame.ftfont.SysFont(possibleFonts, 36, True)  # Warehouse search box
    touchScreenFont = pygame.ftfont.SysFont(possibleFonts, 25, True)
    chatFont = pygame.ftfont.SysFont(possibleFonts, 22, True)

else:  # Fallback no need to make bold
    menuFont = pygame.freetype.Font(FREESANSBOLD_FONT, MENU_FONT_SIZE)
    l_menuFont = pygame.font.Font(FREESANSBOLD_FONT, MENU_FONT_SIZE)
    textParticleFont = pygame.freetype.Font(FREESANSBOLD_FONT, 12)
    typeTextFont = pygame.ftfont.Font(FREESANSBOLD_FONT, 50)
    font = pygame.ftfont.Font(FREESANSBOLD_FONT, FONT_SIZE)
    buildingLabelFont = pygame.freetype.Font(FREESANSBOLD_FONT, FONT_SIZE)
    submenuFont = pygame.ftfont.Font(FREESANSBOLD_FONT, 12)
    warehouseFont = pygame.ftfont.Font(FREESANSBOLD_FONT, 40)
    touchScreenFont = pygame.ftfont.SysFont(FREESANSBOLD_FONT, 25)
    chatFont = pygame.ftfont.SysFont(FREESANSBOLD_FONT, 22)

fontLookup = {'menuFont': menuFont,
              'textParticleFont': textParticleFont,
              'typeTextFont': typeTextFont,
              'font': font,
              'buildingLabelFont': buildingLabelFont,
              'submenuFont': submenuFont,
              'warehouseFont': warehouseFont,
              'touchScreenFont': touchScreenFont,
              'chatFont': chatFont,
              'consoleFont': CONSOLE_FONT}


def loadScaledImage(path):
    return pygame.transform.smoothscale(imgLoad(path), (24, 24)).convert_alpha()


woodSwordImage = imgLoad('images/wood_sword.png').convert_alpha()
stoneSwordImage = imgLoad('images/stone_sword.png').convert_alpha()
ironSwordImage = loadScaledImage('images/items/iron_sword.png')
goldSwordImage = imgLoad('images/gold_sword.png').convert_alpha()

oldPickaxeImage = imgLoad('images/items/pick_bronze.png').convert_alpha()
ironPickaxeImage = imgLoad('images/items/pick_iron.png').convert_alpha()

goldImage = imgLoad('images/gold.png').convert_alpha()

grassImage = imgLoad('images/grass.png').convert()
dirtImage = imgLoad('images/dirt.png').convert()
stoneImage = imgLoad('images/stone.png').convert()
obsidianImage = imgLoad('images/obsidian.png').convert()
fragileStoneImage = imgLoad('images/Fragile Stone.png').convert()
softStoneImage = imgLoad('images/Soft Stone.png').convert()
waterImage = imgLoad('images/water.png').convert()
lavaImage = imgLoad('images/lava.png').convert()
glassImage = imgLoad('images/glass.png').convert_alpha()
woodPlankImage = imgLoad('images/wood_plank.png').convert()
woodPlankBackImage = imgLoad('images/wood_plank_back.png').convert()
ladderImage = imgLoad('images/tempLadder.png').convert_alpha()
ashDirtImage = imgLoad('images/blocks/ashDirt.png').convert()
volcanicStoneImage = imgLoad('images/blocks/volcanicStone.png').convert()

menuStoneImage = pygame.transform.scale2x(imgLoad('images/stone.png')).convert()

crackedBlock = []
for i in range(1, 10 + 1):
    crackedBlock.append(imgLoad('images/block_break/destroy_stage_'
                                + str(i) + '.png'))

# Miniature block images
smallStoneImage = imgLoad('images/stone_small.png').convert()

# Surface of small blocks
caveBackground = pygame.Surface(INTERNAL_SIZE)

GREY_SCREEN = pygame.Surface(INTERNAL_SIZE)
GREY_SCREEN.set_alpha(40)
GREY_SCREEN.fill(GREY)

# Scale 2x is used instead of smoothscale to make the buildings look sharp
buildingImage = pygame.transform.scale2x(imgLoad('images/building.png')).convert_alpha()

logoImage = imgLoad('images/Logo Scaled.png').convert_alpha()

logoRect = logoImage.get_rect()
logoRect.centerx = INTERNAL_WIDTH // 2
logoRect.top = logoRect.height / 4

# Cave objects
tentImage = imgLoad('images/cave objects/tent.png').convert_alpha()

poorRuby = imgLoad('images/ore/poor_ruby.png').convert_alpha()
normalRuby = imgLoad('images/ore/normal_ruby.png').convert_alpha()
goodRuby = imgLoad('images/ore/good_ruby.png').convert_alpha()

poorSapphire = imgLoad('images/ore/poor_sapphire.png').convert_alpha()
normalSapphire = imgLoad('images/ore/normal_sapphire.png').convert_alpha()
goodSapphire = imgLoad('images/ore/good_sapphire.png').convert_alpha()

poorEmerald = imgLoad('images/ore/poor_emerald.png').convert_alpha()
normalEmerald = imgLoad('images/ore/normal_emerald.png').convert_alpha()
goodEmerald = imgLoad('images/ore/good_emerald.png').convert_alpha()

diamondOreImages = (imgLoad('images/ore/stone_diamond.png').convert_alpha(),
                    imgLoad('images/ore/stone_diamond_alt.png').convert_alpha())

goldOreImages = (imgLoad('images/ore/stone_gold.png').convert_alpha(),
                 imgLoad('images/ore/stone_gold_alt.png').convert_alpha())

ironOreImages = (imgLoad('images/ore/stone_iron.png').convert_alpha(),
                 imgLoad('images/ore/stone_iron_alt.png').convert_alpha())

torchImage = imgLoad('images/torch.png').convert_alpha()
goldIngotImage = imgLoad('images/gold_ingot.png').convert_alpha()
ironIngotImage = imgLoad('images/iron_ingot.png').convert_alpha()
ropeImage = imgLoad('images/items/rope.png').convert_alpha()
arrowImage = imgLoad('images/items/arrow.png').convert_alpha()

diamondImage = loadScaledImage('images/items/diamond.png')
bowImage = loadScaledImage('images/items/bow.png')
arrowsImage = loadScaledImage('images/items/arrows.png')
healthPotionImage = loadScaledImage('images/items/healthPotion.png')
watchImage = loadScaledImage('images/items/watch.png')

backpackImage = loadScaledImage('images/items/backpack.png')
goldShieldImage = loadScaledImage('images/items/goldShield.png')
ironShieldImage = loadScaledImage('images/items/ironShield.png')
gildedShieldImage = loadScaledImage('images/items/gildedShield.png')
fortifiedShieldImage = loadScaledImage('images/items/fortifiedShield.png')
expensiveBootArmorImage = loadScaledImage('images/items/expensiveBootArmor.png')
expensiveChestplateImage = loadScaledImage('images/items/expensiveChestplate.png')
expensiveGloveArmorImage = loadScaledImage('images/items/expensiveGloveArmor.png')
regularBootArmorImage = loadScaledImage('images/items/regularBootArmor.png')
regularChestplateImage = loadScaledImage('images/items/regularChestplate.png')
regularGloveArmorImage = loadScaledImage('images/items/regularGloveArmor.png')
redScrollImage = loadScaledImage('images/items/redScroll.png')
blueScrollImage = loadScaledImage('images/items/blueScroll.png')

ashesImage = imgLoad('images/items/ashes.png').convert_alpha()
saltImage = imgLoad('images/items/salt.png').convert_alpha()
stardustImage = imgLoad('images/items/stardust.png').convert_alpha()

# This list is used for giving images to inventory
# TODO - make items into classes and make the draw code a method which accesses the itemGraphicLocator
itemGraphicLocator = {'Gold Sword': goldSwordImage, 'Arrows': arrowsImage,
                      'Torch': torchImage, 'Golden Ingot': goldIngotImage,
                      'Watch': watchImage, 'Backpack': backpackImage,
                      'Rope': ropeImage, 'Iron Ingot': ironIngotImage,
                      'Iron Ore': ironOreImages[0], 'Gold Ore': goldOreImages[0],
                      'Ashes': ashesImage, 'Arrow': arrowImage,
                      'Salt': saltImage, 'Stardust': stardustImage
                      }

ALL_ITEMS = list(itemGraphicLocator.keys())

# Cave 2
REGULAR_ORES = ('Ruby', 'Sapphire', 'Emerald')
# Cave 3
RARE_ORES = ('Gold Nugget', 'Pyrite', 'Diamond')

ORE_QUALITIES = ('Poor', 'Normal', 'Good')

for prefix in ORE_QUALITIES:
    for oreType in RARE_ORES:
        ALL_ITEMS.append(prefix + ' ' + oreType)

ALL_ITEMS = tuple(ALL_ITEMS)

inventorySpaceImage = imgLoad('images/inventorySpace.png').convert_alpha()
selectedInventorySpaceImage = imgLoad('images/selectedInventorySpace.png').convert_alpha()
INVENTORY_SLOT_SIZE = inventorySpaceImage.get_size()

bigInventorySpaceImage = pygame.transform.scale2x(inventorySpaceImage)

BLACK_SCREEN = pygame.Surface(INTERNAL_SIZE)
BLACK_SCREEN.fill(BLACK)

WHITE_SCREEN = pygame.Surface(INTERNAL_SIZE)
WHITE_SCREEN.fill(WHITE)

deathDisplay = None  # Stores whether opacity of black is increasing or decreasing
deathDisplayCounter = None

# Hostile mob combat variables
goldLoss = None
removeEntity = None
deathScreen = None

stoneBackground = pygame.Surface(INTERNAL_SIZE)

size = menuStoneImage.get_width()  # width=height=64
for i in range(math.ceil(INTERNAL_WIDTH / size)):  # How many scaled 2x stone blocks fit horizontally
    for j in range(math.ceil(INTERNAL_HEIGHT / size)):
        stoneBackground.blit(menuStoneImage, (i * size, j * size))

highlightInventoryImage = pygame.Surface(INVENTORY_SLOT_SIZE)
highlightInventoryImage.set_alpha(64)
highlightInventoryImage.fill(WHITE)

bigHighlightInventoryImage = pygame.transform.scale2x(highlightInventoryImage)

mouseoverSlot = None  # What box the mouse is currently on

# Stores which box mouse is over, used in warehouse to store which inventory is selected
currentMenu = None

# Music variables
currentMusic = None

# For choosing new music
if not android:
    MUSIC_END = pygame.USEREVENT + 2
    soundMixer.music.set_endevent(MUSIC_END)

# Autosaving
AUTOSAVE_TIMER = pygame.USEREVENT + 4
pygame.time.set_timer(AUTOSAVE_TIMER, 1000 * 20)  # 20 seconds

SECOND_TIMER = pygame.USEREVENT + 5
pygame.time.set_timer(SECOND_TIMER, 1000)

STOCK_TIMER = pygame.USEREVENT + 5
pygame.time.set_timer(STOCK_TIMER, 10000)

pauseBackground = None


class TextRect:
    def __init__(self, font, displayText, foreColour, backColour=None):
        self.font = font

        self.lastDisplayText = None
        self.displayText = displayText

        self.lastForeColour = None
        self.foreColour = foreColour

        self.lastBackColour = None
        self.backColour = backColour

        # No need on initialization
        self.checkSurfaceUpdate(updateDirtyRects=False)
        self.rect = self.surface.get_rect()

    def checkSurfaceUpdate(self, updateDirtyRects=True):
        textChanged = self.displayText != self.lastDisplayText

        if (textChanged or
            self.backColour != self.lastBackColour or
                self.foreColour != self.lastForeColour):

            #Antialias is True
            self.surface = self.font.render(self.displayText, True,
                                            self.foreColour, self.backColour)

            self.lastBackColour = self.backColour
            self.lastForeColour = self.foreColour
            self.lastDisplayText = self.displayText

        # Resized
        if textChanged and updateDirtyRects:
            dirtyRects.append(self.rect.copy())
            self.realignRect()
            dirtyRects.append(self.rect)

    def draw(self):
        self.checkSurfaceUpdate()
        dirtyRects.append(windowSurface.blit(self.surface, self.rect))

    def realignRect(self):
        oldCenter = self.rect.center
        self.rect.size = self.surface.get_size()
        self.rect.center = oldCenter


class VariableTextRect(TextRect):
    def __init__(self, font, prefix, foreColour, backColour=None):
        self.prefix = prefix
        self.value = None
        super().__init__(font, '', foreColour, backColour)

    def setText(self, value):
        self.displayText = self.prefix + ': ' + str(value)

    def updateSurface(self, value):
        if value != self.value:
            self.value = value
            self.setText(value)


class GoldEquivVTR(TextRect):
    def __init__(self, foreColour, backColour):
        self.setText(0, 0)
        self.leftQuantity = None
        self.rightQuantity = None

        TextRect.__init__(self, font, '', foreColour, backColour)

    def setText(self, leftQuantity, rightQuantity):
        self.leftQuantity, self.rightQuantity = leftQuantity, rightQuantity
        self.displayText = str(leftQuantity) + ' - Gold Equivalent - ' + str(rightQuantity)

    def updateSurface(self, leftQuantity, rightQuantity):
        if self.leftQuantity != leftQuantity or rightQuantity != self.rightQuantity:
            self.setText(leftQuantity, rightQuantity)

# TODO: May need to be re-enabled or set to None, if game works, remove line
# worldID = 1 #Matches world numbers (does not start at 0)


# For displaying the image of the world upon highlight
lastHighlightedWorld = {'ID': None,
                        'Preview': None,
                        'Date': None}

# TODO make into options
chronologicalMode = True
autoShuffle = True


def shuffleScreenshots():
    if os.path.isdir('screenshots'):
        # Find all files
        screenshots = os.listdir(os.path.join(os.getcwd(), 'screenshots'))

        for file in screenshots[:]:  # Removes anything which isn't a png
            # Checks for any folders and deletes them so there are only files
            filePath = os.path.join(os.getcwd(), 'screenshots', file)
            if not os.path.isfile(filePath):
                screenshots.remove(file)

            # Checks if files are not png files
            elif os.path.splitext(filePath)[1] != '.png':  # Check extension
                screenshots.remove(file)

    else:
        screenshots = ()

    SCREENSHOT_COUNT = 4

    if len(screenshots) > SCREENSHOT_COUNT:
        # If this is the first time screenshots are generated, pick a random
        # starting index from which to grab screenshots. Otherwise, make the
        # starting index the screenshot after the most recent one shown.

        if mainMenuScreenshots['Index'] == [] or chronologicalMode:  # First time
            start = random.randint(0, len(screenshots) - 1)

        else:  # Start after most recent
            start = mainMenuScreenshots['Index'][-1] + 1

        # Create and get new indices for screenshots
        mainMenuScreenshots['Index'] = []

        for index in range(start + SCREENSHOT_COUNT):
            # Modulo makes indices loopback
            mainMenuScreenshots['Index'].append(index % len(screenshots))

    else:
        mainMenuScreenshots['Index'] = []

        for i in range(len(screenshots)):
            mainMenuScreenshots['Index'].append(i)

        # Leave a None to represent an empty spot with no image
        for i in range(SCREENSHOT_COUNT - len(mainMenuScreenshots['Index'])):
            mainMenuScreenshots['Index'].append(None)

    # Set new images
    for i, j in zip(range(len(mainMenuScreenshots['Index'])),
                    mainMenuScreenshotOrder):

        if mainMenuScreenshots['Index'][i] is None:
            mainMenuScreenshots['Image'][j] = None
            mainMenuScreenshots['TextRect'][j] = None

        else:
            filename = screenshots[mainMenuScreenshots['Index'][i]]
            mainMenuScreenshots['Image'][j] = imgLoad('screenshots/' + filename)

            mainMenuScreenshots['Image'][j] = pygame.transform.smoothscale(mainMenuScreenshots['Image'][j],
                                                                           mainMenuScreenshotSize[j].size)

            # [:-4] removes the .png from title
            mainMenuScreenshots['TextRect'][j] = TextRect(font, filename[:-4],
                                                          BLACK, GREY)
            mainMenuScreenshots['TextRect'][j].rect.midbottom = mainMenuScreenshots['Outline'][j].midtop

    return mainMenuScreenshots


def loadMainMenu():
    gamemode = 'Main Menu'
    mainMenuScreenshots = shuffleScreenshots()

    return gamemode, mainMenuScreenshots


# Cycle through screenshots
# For the width, the top images stop at 20 pixels left of the beginning of the logo
# Bottom images stop 10 pixels forward
# Both rects subtract 20 pixels because they start 20 pixels from left of screen
mainMenuScreenshotSize = {'Top Left': pygame.Rect(20, 40, logoRect.left - 20 - 20, 0),
                          'Bottom Left': pygame.Rect(20, 0, logoRect.left + 10 - 20, 0)}

# Find height by using the height width ratio
for i in ('Top Left', 'Bottom Left'):
    mainMenuScreenshotSize[i].height = (
        INTERNAL_HEIGHT / INTERNAL_WIDTH) * mainMenuScreenshotSize[i].width

mainMenuScreenshotSize['Bottom Left'].bottom = INTERNAL_HEIGHT - 35

mainMenuScreenshotSize['Top Right'] = mainMenuScreenshotSize['Top Left'].copy()
mainMenuScreenshotSize['Bottom Right'] = mainMenuScreenshotSize['Bottom Left'].copy()

mainMenuScreenshotSize['Top Right'].right = INTERNAL_WIDTH - mainMenuScreenshotSize['Top Left'].left
mainMenuScreenshotSize['Bottom Right'].right = INTERNAL_WIDTH - \
    mainMenuScreenshotSize['Bottom Left'].left

mainMenuScreenshotOrder = ('Top Left', 'Top Right', 'Bottom Left', 'Bottom Right')

mainMenuScreenshots = {'Index': [], 'Image': {},
                       'TextRect': {}, 'Outline': {}}

for i in mainMenuScreenshotSize:
    mainMenuScreenshots['Outline'][i] = pygame.Rect(mainMenuScreenshotSize[i].x - 10,
                                                    mainMenuScreenshotSize[i].y - 10,
                                                    # Add 20 because it starts 10 pixels to the left
                                                    mainMenuScreenshotSize[i].width + 20,
                                                    mainMenuScreenshotSize[i].height + 20)

gamemode, mainMenuScreenshots = loadMainMenu()
previousGamemode = []

MENUS = ('Main Menu', 'Multiplayer Menu', 'Singleplayer Menu',
         'Multiplayer Menu - Add Server', 'Multiplayer Menu - Edit')

# Menus that can be accessed while in game, they may display the game
# in the background rather than default stone background
INGAME_MENUS = ('Options', 'Controls', 'Sound Options', 'Advanced Options')

cheatMode = None
bankMode = 'Main'
marketMode = 'Main'
libraryMode = 'Main'
stockMarketMode = 'Main'
warehouseMode = 'Main'

loadScreenOnce = False  # If changing gamemode, refresh screen at beginning
loadFrameOnce = False  # If updating current screen
''' #TODO, better documentation & wording
loadFrameOnce is the variable checked to reload a screen. loadScreenOnce is set when changing a window
because if loadFrameOnce is set, it may be reset by an if statement also checking for loadFrameOnce.
As a result, the very beginning of any code after finding gamemode is to look for loadScreenOnce
and if the screen must be reloaded, the variable is made True and loadFrameOnce is made False
'''

dirtyRects = []
oldDirtyRects = []

sandOverlayImage = imgLoad('images/blocks/sandOverlay.png').convert_alpha()

sandyStoneImage = stoneImage.copy()
sandyStoneImage.blit(sandOverlayImage, (0, 0))

typeToSurface = {'Stone': stoneImage, 'Obsidian': obsidianImage,
                 'Fragile Stone': fragileStoneImage, 'Water': waterImage,
                 'Lava': lavaImage, 'Grass': grassImage, 'Dirt': dirtImage,
                 'Glass': glassImage, 'Torch': torchImage, 'Plank': woodPlankImage,
                 'Ladder': ladderImage, 'Rope': waterImage, 'Ash Dirt': ashDirtImage,
                 'Soft Stone': softStoneImage, 'Volcanic Stone': volcanicStoneImage,
                 'Sandy Stone': sandyStoneImage}

# Get list of ores
oreList = ['Iron']

for oreType in REGULAR_ORES + RARE_ORES:
    for oreQuality in ORE_QUALITIES:
        oreList.append(oreQuality + ' ' + oreType)

minableBlocks = list(oreList)  # Copies variable
minableBlocks.append('Fragile Stone')
minableBlocks.append('Soft Stone')
minableBlocks = tuple(minableBlocks)

oreList = tuple(oreList)

# Menus


class Menu:
    def __init__(self, rect, titleText):
        self.mainRect = rect

        self.titleText = font.render(titleText, True, BLACK, GREY)
        self.titleRect = self.titleText.get_rect()
        self.titleRect.midbottom = self.mainRect.midtop
        self.maximized = True

    def draw(self):
        # Tooltip triangles
        drawRightTriangles(GREY, self.titleRect)
        windowSurface.blit(self.titleText, self.titleRect)

        if self.maximized:
            pygame.draw.rect(windowSurface, GREY, self.mainRect)

    def toggleVisibility(self):
        self.maximized = not self.maximized

        dirtyRects.append(addTooltipDirtyRects(self.titleRect).copy())

        if self.maximized:
            self.titleRect.bottom = self.mainRect.top

        else:
            self.titleRect.bottom = INTERNAL_HEIGHT

        dirtyRects.append(self.mainRect)
        dirtyRects.append(addTooltipDirtyRects(self.titleRect))

        return dirtyRects


playerInfoMenu = Menu(pygame.Rect(0, INTERNAL_HEIGHT - 5 * BLOCK_SIZE,
                                  6 * BLOCK_SIZE, 5 * BLOCK_SIZE),
                      'Player Info')

PLAYER_INFO_ORDER = ('Gold', 'Location', 'Cave Type',
                     'Cave Depth', 'Direction', 'Health')

# Inventory menu 'Left' is the right of screen subtracted by width of menu
# Top is bottom of window subtracted by height
# Width 32 + 3 for item box dimensions and spacing multiplied by the 9 boxes in the menu and additional 20 width for menu space
# Height is the bottom 5 blocks of the game

inventoryMenu = Menu(pygame.Rect(INTERNAL_WIDTH - (BLOCK_SIZE + 3) * 10 + 20,
                                 INTERNAL_HEIGHT - 5 * BLOCK_SIZE,
                                 (BLOCK_SIZE + 3) * 9 + 20,
                                 5 * BLOCK_SIZE),
                     'Inventory')


class InventoryMenu:
    def __init__(self, backRectX, backRectY, width, height,
                 slotSpacing, slotSize):

        spacingX = slotSize[0] + slotSpacing
        spacingY = slotSize[1] + slotSpacing
        margin = 10

        self.slots = []
        for y in range(height):
            for x in range(width):
                self.slots.append(pygame.Rect((backRectX + margin + x * spacingX,
                                               backRectY + margin + y * spacingY),
                                              slotSize))

        self.backRect = pygame.Rect(backRectX, backRectY,
                                    spacingX * 8 + margin * 2,
                                    spacingY * 9 + margin * 2)

    def draw(self):
        # Draw boxes for warehouse inventory
        pygame.draw.rect(windowSurface, GREY, self.backRect)

    def makeInventoryList(self):
        # Creates inventory array with length of the # of buttons
        inventory = []
        for i in range(len(self.slots)):
            inventory.append(None)

        return inventory


# Left, starts at 10 right from menu's left and increases by 35 for each item box
# Top starts at 10 which is size of box and additional 10 space gap
# Width and height are 32 for size of box
# TODO port (possibly forge) inventory to classes and add a draw method
# TODO merge pl_InventoryGUI and inventoryMenu (have the class just do slots and mix with composition?
pl_InventoryGUI = InventoryMenu(inventoryMenu.mainRect.x, inventoryMenu.mainRect.y,
                                9, 4, 3, INVENTORY_SLOT_SIZE)

INVENTORY_MENU_GAMEMODES = ('Play', 'Warehouse', 'Market', 'Forge', 'Blacksmith')
BUILDING_GAMEMODES = ('Bank', 'Library', 'Market', 'Stock Market', 'Warehouse',
                      'Forge', 'Blacksmith', 'Locked House')

# NPC Trading Menu
tempRect = pygame.Rect(0, INTERNAL_HEIGHT - 5 * BLOCK_SIZE, 5 * BLOCK_SIZE, 5 * BLOCK_SIZE)
tempRect.right = inventoryMenu.mainRect.left - BLOCK_SIZE

NPC_TradingMenu = Menu(tempRect, 'NPC Trading')

NPC_Trading = {'Visible': False,
               'Item Offer': None,
               'Gold Offer': None,
               'Gold Offer Label': None,
               'Counter Offer': [None, None, None],
               'Counter Offer Label': TextRect(font, 'Counter Offer',
                                               BLACK, GREY)}

NPC_Trading['Item Offer Rect'] = inventorySpaceImage.get_rect()
NPC_Trading['Item Offer Rect'].centerx = NPC_TradingMenu.mainRect.centerx
# 10 aligns it with pl_InventoryGUI.slots, and 35 shifts it down to match the second row
NPC_Trading['Item Offer Rect'].top = NPC_TradingMenu.mainRect.top + 10 + 35

NPC_Trading['Counter Offer Label'].rect.centerx = NPC_TradingMenu.mainRect.centerx
# Center text where 3rd row of inventory would be
NPC_Trading['Counter Offer Label'].rect.y = NPC_Trading['Item Offer Rect'].y + 35

NPC_Trading['Counter Offer Rect'] = []
initialX = NPC_TradingMenu.mainRect.centerx - (35 * 4) / 2
initialY = NPC_Trading['Counter Offer Label'].rect.y + 35  # Align with 4th inventory row
for i in range(len(NPC_Trading['Counter Offer'])):
    NPC_Trading['Counter Offer Rect'].append(pygame.Rect((initialX + 35 * i,
                                                          initialY),
                                                         INVENTORY_SLOT_SIZE))

# Load Menu Maximized settings
optionFile = shelve.open('options')
(playerInfoMenu.maximized, inventoryMenu.maximized,
 NPC_TradingMenu.maximized) = optionFile['Menu Maximized']
optionFile.close()

# Warehouse inventory info
# X, Y, width, height are similar to inventoryMenu but inventory slots are twice as big (64)
warehouseInvGUI = InventoryMenu(32, 64, 8, 9, 11,
                                bigHighlightInventoryImage.get_size())

warehouseSearchBoxBackRect = pygame.Rect(inventoryMenu.mainRect.x, warehouseInvGUI.backRect.y,
                                         inventoryMenu.mainRect.right - inventoryMenu.mainRect.x - 24, 50)

warehouseSearchResults = []
warehouseSearchResultsBackground = pygame.Rect(warehouseSearchBoxBackRect.x,
                                               warehouseSearchBoxBackRect.bottom,
                                               warehouseSearchBoxBackRect.width,
                                               8 * 30)

warehouseSearchResultSelectRect = []
for i in range(8):
    warehouseSearchResultSelectRect.append(pygame.Rect(warehouseSearchBoxBackRect.x,
                                                       warehouseSearchBoxBackRect.bottom + i * 30,
                                                       warehouseSearchBoxBackRect.width,
                                                       30))


class GUI_Divider:
    def __init__(self, centerx, centery, width, height, name):
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = centerx, centery

        self.textSurface = font.render(name, True, WHITE, BLACK)
        self.textRect = self.textSurface.get_rect()

        self.updateRect()

    def draw(self):
        windowSurface.blit(self.textSurface, self.textRect)
        pygame.draw.rect(windowSurface, DARK_GREY, self.rect)

    def updateRect(self):
        self.textRect.midbottom = self.rect.midtop
        self.textRect.y -= 10


class Transparent_GUI_Divider(GUI_Divider):
    def __init__(self, centerx, centery, width, height, name):
        GUI_Divider.__init__(self, centerx, centery, width, height, name)

        # Overwrite the GUI_Divider's textSurface which has black background for text
        self.textSurface = font.render(name, True, WHITE)
        self.backRectSurface = pygame.Surface(self.rect.size)
        self.backRectSurface.set_alpha(32)
        self.backRectSurface.fill(WHITE)

    def draw(self):
        windowSurface.blit(self.textSurface, self.textRect)
        windowSurface.blit(self.backRectSurface, self.rect)


# Forge refinery info
SMELTABLE_ITEMS = {'Iron Ore': 'Iron Ingot',
                   'Wooden Sword': 'Ashes',
                   'Iron Sword': 'Iron Ingot',
                   'Gold Ore': 'Golden Ingot'}

FORGE_INVENTORY_NUMBER = 5
FORGE_OPERATION_TIME = 30  # In seconds
FORGE_OPERATION_COST = 25

width = (64 + 10) * FORGE_INVENTORY_NUMBER + 30
forgeInvSelection = Transparent_GUI_Divider(INTERNAL_WIDTH // 4 + 20, 0, width, 64 * 2 + 250,
                                            'Current Operations')
forgeInvSelection.rect.y = 280
forgeInvSelection.updateRect()

forgeStartText = {}
for i in ('Orange', 'Green', 'Red', 'White'):
    forgeStartText[i] = TextRect(font, 'Start', pygame.Color(i))
forgeStartTextRect = forgeStartText['White'].rect

forgeInvRect = {'Input': [], 'Output': [], 'Start Rect': [],
                'Progress': {'Outer': [], 'Inner': []}}

INPUT_OUTPUT_DISTANCE = 250

for i in ('Input', 'Output'):
    for j in range(FORGE_INVENTORY_NUMBER):
        # Similar to pl_InventoryGUI.slots
        forgeInvRect[i].append(pygame.Rect((forgeInvSelection.rect.left + 15 + j * (64 + 10),
                                            forgeInvSelection.rect.top + 15),
                                           bigHighlightInventoryImage.get_size()))

        if i == 'Input':
            forgeInvRect[i][j].y += INPUT_OUTPUT_DISTANCE

PROGRESS_BAR_WIDTH_DIFF = 15
PROGRESS_BAR_HEIGHT_DIFF = 10

# Display progress of smelting
for i in range(FORGE_INVENTORY_NUMBER):
    forgeInvRect['Start Rect'].append(forgeStartTextRect.copy())

    xCoord = forgeInvRect['Input'][i].left
    width = forgeInvRect['Input'][i].width

    xCoord += PROGRESS_BAR_WIDTH_DIFF
    width -= PROGRESS_BAR_WIDTH_DIFF * 2

    yCoord = forgeInvRect['Output'][i].bottom
    height = forgeInvRect['Input'][i].top - forgeInvRect['Output'][i].bottom

    yCoord += PROGRESS_BAR_HEIGHT_DIFF
    height -= PROGRESS_BAR_HEIGHT_DIFF + forgeInvRect['Start Rect'][i].height

    forgeInvRect['Progress']['Outer'].append(pygame.Rect(xCoord, yCoord, width, height))
    forgeInvRect['Progress']['Inner'].append(forgeInvRect['Progress']['Outer'][i].inflate(-15, -15))

    forgeInvRect['Start Rect'][i].midbottom = forgeInvRect['Input'][i].midtop

humanWalkImage = []

humanWalkImageSize = []

# Create array and add frames
for i in range(1, 6 + 1):
    humanWalkImage.append({False: imgLoad('images/player/walk/Frame ' +
                                          str(i) + '.png').convert_alpha()})
    humanWalkImage[-1][True] = pygame.transform.flip(humanWalkImage[-1][False],
                                                     True, False)

    humanWalkImageSize.append(humanWalkImage[-1][False].get_size())

# TODO: Add stance with code to make it randomly select a stance for each battle,
# Also make a bounding rect for each frame
'''
playerSlashImage = []

for i in range(6):
    playerSlashImage.append(imgLoad('images/player/slash/Frame ' +
                                         str(i + 1) + '.png').convert_alpha())
'''
playerStanceImage = []

for i in range(1, 2 + 1):
    playerStanceImage.append(imgLoad('images/player/stance/Frame ' +
                                     str(i) + '.png').convert_alpha())

humanStopImage = {False: imgLoad('images/player/pause.png').convert_alpha()}
humanStopImage[True] = pygame.transform.flip(humanStopImage[False], True, False)

SMALL_TOWN_HILLS = 'Small Town Hills'
SMALL_TOWN = 'Small Town'
SECOND_TOWN = 'Second Town'
INDUSTRIAL_TOWN = 'Industrial Town'
OUTPOST_TOWN = 'Outpost Town'
# Should the focus shift from science, tech, and alchemy to rare goods like furniture and exotic super-expensive items?
CAPITAL_CITY = 'Capital City'
# TODO: Player will be able to buy rare books from capital city's markets
# TODO: Add mountainous background graphic for mining town
MINING_TOWN = 'Mining Town'
VOLCANIC_TOWN = 'Volcanic Town'
QUIET_TOWN = 'Quiet Town'  # Similar to small town - an event should give the player a special item
BEACH_TOWN = 'Beach Town'  # Caves nearby use hydrophone sound https://www.freesound.org/people/geyr/sounds/324753/
ABANDONED_TOWN_LEFT = 'Abandoned Town - Left'
ABANDONED_TOWN_CENTRE = 'Abandoned Town - Centre'
ABANDONED_TOWN_RIGHT = 'Abandoned Town - Right'
GUARD_POST = 'Guard Post'
DUNGEON_TOP = 'Dungeon - Top'
DUNGEON_BOTTOM = 'Dungeon - Bottom'

UNDERGROUND_CITY = 'Underground City'
UNDERGROUND_CITY_EXIT = 'Underground City Exit'

leaveCave = None

OLD_TOWNS = (SMALL_TOWN, SECOND_TOWN)
ABANDONED_TOWN = (ABANDONED_TOWN_LEFT, ABANDONED_TOWN_CENTRE, ABANDONED_TOWN_RIGHT)
DUNGEONS = (DUNGEON_TOP, DUNGEON_BOTTOM)


class TownClass:
    def __init__(self, string, buildings, villagerCount):
        self.string = string
        self.townBuildings = TownBuildings((buildings))
        self.villagerCount = villagerCount

        TOWNS[self.string] = self

    def draw(self):
        self.townBuildings.draw()

    def generate(self, town, player):
        player.setCityLocation(town)

        (ambientSounds, blockGrid, backgroundBlocks, entities,
         mapData) = outsideMapGenerator(INTERNAL_HEIGHT / 2)

        entities = spawnEntity(entities, self.villagerCount, 'Villager',
                               bottomCoord=mapData['groundY'])

        # Lets function work when not loading an abandoned town
        newCaveBackground = caveBackground

        return (player, ambientSounds, blockGrid,
                backgroundBlocks, entities, mapData,
                newCaveBackground)


class VolcanicTown(TownClass):
    def generate(self, town, player):
        (player, ambientSounds, blockGrid,
         backgroundBlocks, entities, mapData,
         newCaveBackground) = TownClass.generate(self, town, player)

        blockGrid = makeAshenEarth(blockGrid)

        return (player, ambientSounds, blockGrid,
                backgroundBlocks, entities, mapData,
                newCaveBackground)


class TranslucentText:
    def __init__(self, text, textColour):
        self.initialized = False  # Must run updateBackTextRect once

        self.textSurface, self.textRect = buildingLabelFont.render(text, textColour)

        # Surface of rectangle which is background of text to be blitted with transparency
        self.backTextRect = self.textRect.copy()
        self.backTextRect.inflate_ip(14, 10)

        self.backTextRectSurface = {}
        for i in (True, False):
            self.backTextRectSurface[i] = pygame.Surface(self.backTextRect.size)
            self.backTextRectSurface[i].set_alpha(128)

        # When mousing over text rect, turn gray instead of black
        self.backTextRectSurface[True].fill(GREY)
        self.backTextRectSurface[False].fill(BLACK)

    def draw(self):
        assert self.initialized
        windowSurface.blit(self.backTextRectSurface[mouseover(self.backTextRect)],
                           self.backTextRect)
        windowSurface.blit(self.textSurface, self.textRect)

    def updateBackTextRect(self):
        self.initialized = True
        self.backTextRect.center = self.textRect.center


class TownBuildings:
    def __init__(self, buildings):
        self.buildingRect = {}

        self.translucentText = {}

        # Surface of rectangle which is background of text to be blitted with transparency
        self.backTextRect = {}
        self.backTextRectSurface = {}

        for i, building in enumerate(buildings):
            self.buildingRect[building] = buildingImage.get_rect()
            self.buildingRect[building].centerx = INTERNAL_WIDTH * (i + 1) / (len(buildings) + 1)
            self.buildingRect[building].bottom = 12 * BLOCK_SIZE

            self.translucentText[building] = TranslucentText(building, WHITE)
            self.translucentText[building].textRect.center = self.buildingRect[building].center
            self.translucentText[building].updateBackTextRect()

    def draw(self):
        for i in self.buildingRect:
            windowSurface.blit(buildingImage, self.buildingRect[i])
            self.translucentText[i].draw()

    def clickBuilding(self, player, single_pl_Info):
        playSound(doorSound)

        consoleIntroText(player, single_pl_Info, gamemode)
        # Clicking on any building requires this, this
        # also only runs if player clicked on building
        loadScreenOnce = False

        player, heldKey = resetInput(player)

        return loadScreenOnce, player, heldKey


TOWNS = {}
# Initializing towns automatically adds to TOWN_DATA
TownClass(SMALL_TOWN, ('Bank', 'Library', 'Market'), 2)
TownClass(SECOND_TOWN, ('Bank', 'Library', 'Market', 'Stock Market', 'Warehouse'), 5)
TownClass(INDUSTRIAL_TOWN, ('Bank', 'Library', 'Market', 'Forge', 'Blacksmith'), 10)
# Outpost town lacks a bank, small outpost
TownClass(OUTPOST_TOWN, ('Library', 'Market'), 2)
# In future split capital city into two
TownClass(CAPITAL_CITY, ('Bank', 'Library', 'Market', 'Stock Market',
                         'Warehouse', 'Forge', 'Blacksmith'), 12)
TownClass(MINING_TOWN, ('Market', 'Warehouse', 'Forge', 'Blacksmith'), 8)
VolcanicTown(VOLCANIC_TOWN, ('Bank', 'Market'), 4)  # Merchandise would include rare ores, cinnabar
TownClass(QUIET_TOWN, ('Bank', 'Library', 'Market', 'Locked House'), 3)
TownClass(BEACH_TOWN, ('Library', 'Market', 'Sea Market'), 5)

TOWN_STRINGS = tuple(TOWNS)

OUTSIDE_LOCATIONS = TOWN_STRINGS + (GUARD_POST, SMALL_TOWN_HILLS) + ABANDONED_TOWN

# Dict key is initial location, element is destination when moving left
LEFT_MAP = {SECOND_TOWN: SMALL_TOWN,
            INDUSTRIAL_TOWN: SECOND_TOWN,
            ABANDONED_TOWN_LEFT: INDUSTRIAL_TOWN,
            ABANDONED_TOWN_CENTRE: ABANDONED_TOWN_LEFT,
            ABANDONED_TOWN_RIGHT: ABANDONED_TOWN_CENTRE,
            OUTPOST_TOWN: ABANDONED_TOWN_RIGHT,
            CAPITAL_CITY: OUTPOST_TOWN,
            MINING_TOWN: CAPITAL_CITY,
            VOLCANIC_TOWN: MINING_TOWN,
            QUIET_TOWN: VOLCANIC_TOWN}

# Same as LEFT_Map but inverted
# http://stackoverflow.com/questions/483666/python-reverse-inverse-a-mapping
RIGHT_MAP = {v: k for k, v in LEFT_MAP.items()}

textParticles = []


class TextParticle:
    def __init__(self, value, center):
        self.value = value
        self.text = str(value)
        self.textSurface, self.rect = textParticleFont.render(self.text, self.getColour())
        self.frame = 0

        self.rect.center = center

    def draw(self):
        newDirtyRects = dirtyRects
        if options['showDamage'] or self.type in ('Gold Gain', 'Gold Loss'):
            self.frame += 1 / FPS
            self.rect.y -= 60 / FPS

            newDirtyRects.append(windowSurface.blit(self.textSurface, self.rect))

        if self.frame > 3:
            textParticles.remove(self)

        return newDirtyRects


class AttackText(TextParticle):
    type = 'Attack'

    def getColour(self):
        assert self.value >= 0
        if self.value == 0:
            return GREY

        else:
            return RED


class DefenseText(TextParticle):
    type = 'Defense'

    def getColour(self):
        assert self.value >= 0
        return BLUE


class GoldGainText(TextParticle):
    type = 'Gold Gain'

    def getColour(self):
        assert self.value >= 0
        return GOLD


class GoldLossText(TextParticle):
    type = 'Gold Loss'

    def getColour(self):
        return RED


def dropGold(goldQuantityLeft, XY_Coords):
    XY_Coords = (XY_Coords[0] + random.randint(-5, 5),
                 XY_Coords[1] + random.randint(-5, 5))
    newEntities = entities
    while goldQuantityLeft:
        goldQuantity = random.randint(1, 3)
        if goldQuantity > goldQuantityLeft:
            goldQuantity = goldQuantityLeft

        # Drop gold on ground
        newEntities.append(DroppedGold(XY_Coords, goldQuantity))
        goldQuantityLeft -= goldQuantity  # Remove from chest

    assert goldQuantityLeft == 0
    return newEntities


class Stock:
    def __init__(self, initialValue, changeRate):
        self.float = initialValue
        self.int = initialValue

        # e.g. changeRate 0.1, minChangeRate 0.9, and maxChangeRate 1.101..
        self.minChangeRate = 1 - changeRate
        self.maxChangeRate = 1 / self.minChangeRate

        self.oldFloatValue = []

    def updateValue(self):
        self.float *= random.uniform(self.minChangeRate, self.maxChangeRate)
        self.int = round(self.float)
        self.oldFloatValue.append(self.float)

        if len(self.oldFloatValue) > longTermStockGraph.linesOfHeight:
            del self.oldFloatValue[0]


basicButtonImage = imgLoad('images/menu/button.jpg').convert_alpha()


def createHighlightSurface(size):
    highlightSurface = pygame.Surface(size)
    highlightSurface.set_alpha(50)
    highlightSurface.fill(WHITE)

    return highlightSurface


class Button:
    def __init__(self, text, desiredFont):
        self.textSurface, self.textRect = desiredFont.render(text, WHITE)

        self.rect = self.textRect.inflate(40, 20)

        self.buttonImage = pygame.transform.smoothscale(basicButtonImage,
                                                        self.rect.size)

        self.flatButtonImage = pygame.Surface((self.rect.size))
        self.flatButtonImage.fill(DARK_GREY)

        self.highlightSurface = createHighlightSurface(self.rect.size)

    def draw(self):
        if inGame:
            windowSurface.blit(self.flatButtonImage, self.rect)

        else:
            windowSurface.blit(self.buttonImage, self.rect)

        windowSurface.blit(self.textSurface, self.textRect)

        if self.mouseover():
            windowSurface.blit(self.highlightSurface, self.rect)

    def alignTextRect(self):
        self.textRect.center = self.rect.center

    def mouseover(self):
        return mouseover(self.rect)


class ToggleButton(Button):
    def changeText(self, text, desiredFont):
        self.textSurface, self.textRect = desiredFont.render(text, WHITE)
        self.alignTextRect()


class ToggleOptionButton(ToggleButton):
    def __init__(self, displayName, toggleVariable):
        self.toggleVariable = toggleVariable
        self.displayName = displayName

        buttonText = self.getText()
        ToggleButton.__init__(self, buttonText, menuFont)

    def updateText(self):
        buttonText = self.getText()
        ToggleButton.changeText(self, buttonText, menuFont)

    # Called when player clicks anywhere
    def checkClick(self, optionFile):
        global options
        dirtyRects.append(self.rect.copy())

        if (self.mouseover()):
            options[self.toggleVariable] = not options[self.toggleVariable]

            optionFile[self.toggleVariable] = options[self.toggleVariable]
            self.updateText()

        playSound(menuButtonSound)
        dirtyRects.append(self.rect)

        return dirtyRects, options[self.toggleVariable], optionFile

    def getText(self):
        global options
        return self.displayName + ' - ' + onOffString[options[self.toggleVariable]]


class DeleteButton(ToggleButton):
    def __init__(self, text):
        self.text = text
        Button.__init__(self, self.text, menuFont)

    def toggleDeleteButton(self):
        newDeleteMode = not deleteMode

        if newDeleteMode:
            fontColour = RED

        else:
            fontColour = WHITE

        self.textSurface, self.textRect = menuFont.render(self.text, fontColour)
        self.alignTextRect()

        dirtyRects.append(self.rect)

        return newDeleteMode, dirtyRects


# Main Menu buttons
mainMenuButtons = {}
for i, text in enumerate(('Single Player', 'Multiplayer', 'Options', 'Quit')):
    mainMenuButtons[text] = Button(text, menuFont)

    mainMenuButtons[text].rect.center = (INTERNAL_WIDTH // 2,
                                         (INTERNAL_HEIGHT - logoRect.height * 1.5) * (i + 1) / 5 + logoRect.height * 1.25)
    mainMenuButtons[text].alignTextRect()

# Options buttons
optionButtons = {}

for optionName in ('Sound', 'Controls', 'Advanced Options'):
    optionButtons[optionName] = Button(optionName, menuFont)

for displayName, toggleVariable in zip(('Fullscreen', 'Item Tooltips', 'Touch Screen', 'Auto Combat'),
                                       ('fullscreen', 'tooltips', 'touchScreen', 'autoCombat')):

    optionButtons[toggleVariable] = ToggleOptionButton(displayName, toggleVariable)

optionButtons['Dirty Rect'] = ToggleButton(dirtyRectEnabledString + ' Mode', menuFont)
optionButtons['Lighting'] = ToggleButton('Lighting - ' + options['lighting'], menuFont)

# Set coords of option buttons
optionButtons['Advanced Options'].rect.bottomright = INTERNAL_SIZE

for i, optionName in enumerate(('Sound', 'fullscreen', 'Dirty Rect', 'Controls')):
    optionButtons[optionName].rect.center = INTERNAL_WIDTH * 1 // 4, INTERNAL_HEIGHT * (i + 1) // 5

for i, optionName in enumerate(('tooltips', 'touchScreen', 'autoCombat', 'Lighting')):
    optionButtons[optionName].rect.center = INTERNAL_WIDTH * 3 // 4, INTERNAL_HEIGHT * (i + 1) // 5

for i in optionButtons:
    optionButtons[i].alignTextRect()

# Advanced Options buttons
advancedOptionButtons = {}
for i, displayName in enumerate(('Colourblind Mode', 'Combat Highlighting',
                                 'Show Damage')):
    toggleVariable = ('CVD', 'highlightCombat', 'showDamage')[i]

    advancedOptionButtons[toggleVariable] = ToggleOptionButton(displayName, toggleVariable)
    advancedOptionButtons[toggleVariable].rect.center = INTERNAL_WIDTH // 2, INTERNAL_HEIGHT * \
        (i + 1) // 4
    advancedOptionButtons[toggleVariable].alignTextRect()

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
heldKey = set()

class TouchScreenControl:
    KEYS = ("Up", "Left", "Right", "Menu")
    IMAGES = {"Up": "upArrow.png",
              "Left": "leftArrow.png",
              "Right": "rightArrow.png",
              "Menu": "pause.png"}

    def __init__(self):
        # Touchscreen buttons code
        # 64 is size of button
        self.buttons = {"Rect": {},
                        "Surface": {},
                        "Held Down": {},
                        "Background Rect":
                        pygame.Rect(80, 380,
                                    64 * 2.5,
                                    64 * 2)}

        for key in self.KEYS:
            if key != "Menu":
                self.buttons["Held Down"][key] = False

            imageFile = self.IMAGES[key]

            path = os.path.join("images", "menu", "touchscreen", imageFile)
            self.buttons["Surface"][key] = imgLoad(path).convert_alpha()
            self.buttons["Rect"][key] = self.buttons["Surface"][key].get_rect()

        self.buttons["Rect"]["Up"].midtop = self.buttons["Background Rect"].midtop
        self.buttons["Rect"]["Left"].bottomleft = self.buttons["Background Rect"].bottomleft
        self.buttons["Rect"]["Right"].bottomright = self.buttons["Background Rect"].bottomright

        self.buttons["Rect"]["Menu"].top = self.buttons["Rect"]["Left"].bottom + 20
        self.buttons["Rect"]["Menu"].centerx = self.buttons["Rect"]["Up"].centerx

    def check_buttons(self, holdMouseDown):
        for key in ('Up', 'Left', 'Right'):
            if mouseover(self.buttons['Rect'][key]) and holdMouseDown:
                self.buttons['Held Down'][key] = True

            else:
                self.buttons['Held Down'][key] = False

    def draw(self):
        for key in self.buttons['Surface']:
            windowSurface.blit(self.buttons['Surface'][key],
                               self.buttons['Rect'][key])

    def get_held(self, heldKey):
        for key in ('Up', 'Left', 'Right'):
            if self.buttons['Held Down'][key]:
                heldKey.add(key)

            elif key in heldKey:
                heldKey.remove(key)

        return heldKey

touchScreenButtons = TouchScreenControl()

def get_key_held_down(event, controls, heldKey):
    if event.key == controls['Jump']:
        heldKey.add('Up')

    if event.key == controls['Left']:
        heldKey.add('Left')

    if event.key == controls['Right']:
        heldKey.add('Right')

    return heldKey

def get_key_held_up(event, controls, heldKey):
    if event.key == controls['Jump'] and 'Up' in heldKey:
        heldKey.remove('Up')

    if event.key == controls['Left'] and 'Left' in heldKey:
        heldKey.remove('Left')

    if event.key == controls['Right'] and 'Right' in heldKey:
        heldKey.remove('Right')

    return heldKey

chooseCave = False
selectCaveButtons = {"Rect": [],
                     "Surface": [],
                     "Held Down": [],
                     "Aligned": True}

for i in range(3):
    selectCaveButtons["Held Down"].append(False)
    selectCaveButtons["Surface"].append(pygame.Surface((32, 32), pygame.SRCALPHA, 32))
    selectCaveButtons["Rect"].append(selectCaveButtons["Surface"][i].get_rect())

    textSurface = touchScreenFont.render(str(i + 1), True, BLACK)
    textRect = textSurface.get_rect()
    textRect.center = 16, 16
    selectCaveButtons["Surface"][i].blit(textSurface, textRect)

selectedControlButton = None


class ControlButton(ToggleButton):
    def __init__(self, optionName, keyCode, i):
        self.optionName = optionName
        self.text = optionName + " - " + pygame.key.name(keyCode)
        ToggleButton.__init__(self, self.text, menuFont)

        self.rect.centerx = INTERNAL_WIDTH // 2
        self.rect.centery = INTERNAL_HEIGHT * (i + 1) // 7
        self.alignTextRect()

    # e.g. keyVariable may be controls["Jump"] amd can have different keycodes associated
    def keyDown(self, newKeycode, controls):
        # TODO paste in old code from old revision, fix calls to keyDown method
        self.text = self.optionName + " - " + pygame.key.name(newKeycode)

        # Recenter button
        self.textSurface, self.textRect = menuFont.render(self.text, WHITE)

        self.alignTextRect()
        # TODO implement support for dirtyRects

        controls[self.optionName] = newKeycode
        return controls

    def draw(self):
        ToggleButton.draw(self)  # Draw button

        # Show highlight
        if self.optionName == selectedControlButton:
            windowSurface.blit(self.highlightSurface, self.rect)


controls = {}
controlButtons = {}
for i, buttonName in enumerate(("Jump", "Left", "Right", "Open Chat",
                                "Open Inventory", "Open Map")):

    controls[buttonName] = (pygame.K_w, pygame.K_a, pygame.K_d, pygame.K_t,
                            pygame.K_e, pygame.K_m)[i]

    controlButtons[buttonName] = ControlButton(buttonName, controls[buttonName], i)


class SoundButton(ToggleOptionButton):
    def __init__(self, displayName, toggleVariable):
        ToggleOptionButton.__init__(self, displayName, toggleVariable)

        # Volume has not yet been implemented and is unused
        self.volume = 1


soundOptionButtons = {}

for i, displayText in enumerate(('Sound', 'Music', 'Ambience')):
    toggleVariable = ('sound', 'music', 'ambience')[i]

    soundOptionButtons[toggleVariable] = SoundButton(displayText, toggleVariable)

    soundOptionButtons[toggleVariable].rect.centerx = INTERNAL_WIDTH // 2
    soundOptionButtons[toggleVariable].rect.centery = INTERNAL_HEIGHT * (i + 1) // 4
    soundOptionButtons[toggleVariable].alignTextRect()

backButton = Button('Back', menuFont)
backButton.rect.bottomleft = 0, INTERNAL_HEIGHT
backButton.alignTextRect()


class TextField:
    def __init__(self, value, desiredFont, sizeLimit):
        self.value = value
        self.sizeLimit = sizeLimit

        self.desiredFont = desiredFont  # String
        self.font = self.getFont()

        self.surface = self.getSurface()
        self.text = self.createText()

        self.rect = self.surface.get_rect()
        self.changingField = False

    def createText(self):
        return self.value

    def draw(self):
        windowSurface.blit(self.surface, self.rect)

    def getColour(self):
        if self.changingField:
            return DARK_GREY

        else:
            return GREY

    def getSurface(self):
        return self.font.render(self.createText(), True, WHITE, GREY)

    def setValue(self, newValue):
        self.value = newValue
        self.text = self.createText()
        self.makeNewSurface()

    def typeText(self):
        if (self.changingField and
                event.key not in (pygame.K_ESCAPE,) + ENTER_KEYS):  # Invalid keys

            if event.key == pygame.K_BACKSPACE:
                # Enable backspace if beyond initial text
                if len(self.value) > 0:
                    self.value = self.value[:-1]

            # Special commands when using Ctrl
            elif pygame.key.get_mods() & pygame.KMOD_CTRL:
                if event.key == pygame.K_v and clipboard is not None:
                    self.value += clipboard.decode().replace('\x00', '')

            elif len(self.value) < self.sizeLimit:
                self.value += event.unicode

            self.text = self.createText()
            self.makeNewSurface()

        return dirtyRects

    def makeNewSurface(self):
        colour = self.getColour()
        self.surface = self.font.render(self.createText(), True, WHITE, colour)

        dirtyRects.append(self.rect.copy())
        self.rect.width = self.surface.get_width()
        dirtyRects.append(self.rect)

    def getFont(self):
        return fontLookup[self.desiredFont]

    def __getstate__(self):
        state = dict(self.__dict__)
        del state['surface']
        del state['font']
        return state

    def __setstate__(self, dict):
        self.__dict__ = dict
        self.font = self.getFont()
        self.surface = self.font.render(self.createText(), True, WHITE, GREY)


class PrefixTextField(TextField):
    def __init__(self, initialText, value, desiredFont, sizeLimit):
        self.initialText = initialText
        TextField.__init__(self, value, desiredFont, sizeLimit)

    def createText(self):
        return self.initialText + ": " + self.value


class WarehouseSearch(PrefixTextField):
    def __init__(self):
        PrefixTextField.__init__(self, "Item", "", "warehouseFont", 20)
        self.changingField = True

    def getColour(self):
        return GREY


class ToggleTextField(PrefixTextField):
    def toggleChangingField(self):
        if mouseover(self.rect):
            self.changingField = True

        else:
            self.changingField = False

        self.makeNewSurface()


changeName = PrefixTextField("Name", options["playerName"], "font", 14)
changeName.changingField = True
changeName.rect.bottomleft = 0, INTERNAL_HEIGHT

addServerName = ToggleTextField("Server Name", "", "typeTextFont", 50)
addServerName.rect.x = 200
addServerName.rect.centery = INTERNAL_HEIGHT // 2 - 50

addIP = ToggleTextField("Server IP", "", "typeTextFont", 45)
addIP.rect.topleft = addServerName.rect.bottomleft

warehouseSearchBox = WarehouseSearch()
warehouseSearchBox.rect.topleft = warehouseSearchBoxBackRect.topleft

disconnectMessage = {"Text": None}

# Key of dictionary is phoneMode
changeAndroidMode = {}

for i in (True, False):
    if i:
        text = "PHONE MODE"

    else:
        text = "TABLET MODE"

    changeAndroidMode[i] = TextRect(l_menuFont, text, WHITE, GREY)

    changeAndroidMode[i].rect.centerx = INTERNAL_WIDTH / 2
    changeAndroidMode[i].rect.bottom = INTERNAL_HEIGHT

description = "Optimized breaks sunrises, sunsets, and lighting."
dirtyRectInfo = TextRect(submenuFont, description, BLACK, GREY)

changingLocation = False


def checkFolder(path):
    os.makedirs(path, exist_ok=True)


def getSaveFile(saveFolder):
    return os.path.join(saveFolder, "level")


def getSaveFolder(worldID):
    return os.path.join("saves", "World %s/" % worldID)


def checkSaveDirectory(worldID, createFolder):
    checkFolder("saves")

    saveFolder = getSaveFolder(worldID)

    if createFolder:
        checkFolder(saveFolder)

    return saveFolder


def checkServerSaveDirectory():
    checkFolder("servers")
    saveFolder = os.path.join("servers", serverIP + "/")
    checkFolder(saveFolder)

    return saveFolder


class WorldButtons:
    def __init__(self):
        # Single player menu buttons
        self.buttons = {}

        for i in range(1, 4 + 1):
            if os.path.isdir(getSaveFolder(worldID=i)):
                fontString = 'World ' + str(i)
            else:
                fontString = 'Create World'

            self.buttons[i] = ToggleButton("Create World", menuFont)
            self.buttons[i].changeText(fontString, menuFont)

            # Repeat of above, center by 1/5, 2/5, 3/5...
            self.buttons[i].rect.center = (INTERNAL_WIDTH // 2,
                                           INTERNAL_HEIGHT * i / 5)

    def draw(self):
        if not loadFrameOnce:
            for i in range(1, 4 + 1):  # Update text boxes
                # TODO: merge with updateWorldMenuButtons
                saveFolder = checkSaveDirectory(i, False)
                path = getSaveFile(saveFolder)

                if os.path.isfile(path):
                    fontString = 'World ' + str(i)

                else:
                    fontString = 'Create World'

                self.buttons[i].changeText(fontString, menuFont)

        for i in self.buttons:
            self.buttons[i].draw()

    def mouseover(self):
        if self.get_mouseover() is not None:
            playSound(menuButtonSound)

    def get_mouseover(self):
        for i in self.buttons:
            if mouseover(self.buttons[i].rect):
                return i

        else:
            return None

worldButtons = WorldButtons()


# Single player menu buttons
singlePlayMenuButtons = {}

# Default color of delete button comes from Button class which
# is white, same as button when deleteMode is false
singlePlayMenuButtons["Delete World"] = DeleteButton("Delete World")
singlePlayMenuButtons["Delete World"].rect.bottomright = INTERNAL_SIZE
singlePlayMenuButtons["Delete World"].alignTextRect()

# Initially load toggle button with Normal World so button is maximum possible size for testWorldString
singlePlayMenuButtons["World Type"] = ToggleButton("Normal World", menuFont)
singlePlayMenuButtons["World Type"].changeText(testWorldString, menuFont)
singlePlayMenuButtons["World Type"].rect.midbottom = INTERNAL_WIDTH / 2, INTERNAL_HEIGHT
singlePlayMenuButtons["World Type"].alignTextRect()

multiPlayMenuButtons = {}

for i, text in enumerate(('Refresh', 'Connect', 'Edit', 'Add Server')):
    multiPlayMenuButtons[text] = Button(text, menuFont)

multiPlayMenuButtons['Delete'] = DeleteButton('Delete')

for i, text in enumerate(('Refresh', 'Connect', 'Edit')):
    multiPlayMenuButtons[text].rect.centerx = (i + 1) / 4 * INTERNAL_WIDTH
    multiPlayMenuButtons[text].rect.bottom = INTERNAL_HEIGHT - 90

for i, text in enumerate(('Add Server', 'Delete')):
    multiPlayMenuButtons[text].rect.centerx = (i + 1) / 3 * INTERNAL_WIDTH
    multiPlayMenuButtons[text].rect.bottom = INTERNAL_HEIGHT - 20

for i in multiPlayMenuButtons:
    multiPlayMenuButtons[i].alignTextRect()

addServerMenuButtons = {}

for i, text in enumerate(('Continue',)):
    addServerMenuButtons[text] = Button(text, menuFont)

addServerMenuButtons['Continue'].rect.bottomright = INTERNAL_SIZE
addServerMenuButtons['Continue'].alignTextRect()

multiPlayMenuList = []
spacing = 30
width = INTERNAL_WIDTH / 2 - spacing * 2
height = 90

for i in range(5):
    multiPlayMenuList.append(pygame.Rect(spacing, spacing + i * (height + spacing),
                                         width, height))

for i in range(5):
    multiPlayMenuList.append(pygame.Rect(INTERNAL_WIDTH / 2 + spacing, spacing + i * (height + spacing),
                                         width, height))

selectedServerID = None

# Bow GUI
bowDegrees = 0

# Buttons when game is paused
pauseButtons = {}
for i, text in enumerate(("Resume", "Start Server", "Options", "Save and Quit")):
    if text == "Start Server":
        index = "Toggle Server"

    elif text == "Save and Quit":
        index = "Quit Game"

    if text in ("Start Server", "Save and Quit"):
        pauseButtons[index] = ToggleButton(text, menuFont)

    else:
        index = text
        pauseButtons[index] = Button(text, menuFont)

    # center by 1/5, 2/5, 3/5...
    pauseButtons[index].rect.center = INTERNAL_WIDTH // 2, INTERNAL_HEIGHT * (i + 1) / 5
    pauseButtons[index].alignTextRect()

# Bank images
changeArrow1 = imgLoad('images/menu/bank/change1.png').convert_alpha()
changeArrow5 = imgLoad('images/menu/bank/change5.png').convert_alpha()

if android:
    changeArrow1 = pygame.transform.scale2x(changeArrow1)
    changeArrow5 = pygame.transform.scale2x(changeArrow5)

# Vertically flipped copy
changeArrow1Inv = pygame.transform.flip(changeArrow1, 0, 1)
changeArrow5Inv = pygame.transform.flip(changeArrow5, 0, 1)

bankText = {}

bankText['Bank'] = TextRect(font, 'Bank', WHITE, BLACK)
bankText['Bank'].rect.centerx = INTERNAL_WIDTH // 2
bankText['Bank'].rect.top = 5

bankText["Inventory"] = VariableTextRect(font, "Inventory", GOLD, BLACK)
bankText["Inventory"].rect.center = INTERNAL_WIDTH // 2, INTERNAL_HEIGHT * 2 / 5

bankText["Current Balance"] = VariableTextRect(font, "Current Balance", GOLD, BLACK)
bankText["Current Balance"].rect.center = (bankText["Inventory"].rect.centerx,
                                           bankText["Inventory"].rect.centery + 20)


class Graph:
    def __init__(self, linesOfWidth, linesOfHeight, H_Line_Dist, V_Line_Dist):
        self.linesOfWidth = linesOfWidth
        self.linesOfHeight = linesOfHeight

        self.H_Line_Dist = H_Line_Dist
        self.V_Line_Dist = V_Line_Dist

        self.surface = []
        self.surfaceRect = []

        self.lastOldValues = None

        self.rect = pygame.Rect(0, 0,  # Set x,y coords later
                                (self.linesOfHeight - 1) * self.H_Line_Dist,
                                (self.linesOfWidth - 1) * self.V_Line_Dist)

    def draw(self, oldValues):
        self.redrawGraph(oldValues)

        if options['CVD']:
            # Lines that convey value across graph
            GRID_COLOUR = pygame.Color('Yellow')
            GRAPH_COLOUR = BLUE

        else:
            GRID_COLOUR = GREEN
            GRAPH_COLOUR = RED

        # Draw lines to create grid
        for i in range(self.linesOfWidth):
            # Horizontal rows
            y = self.rect.y + i * self.V_Line_Dist
            pygame.draw.line(windowSurface, GRID_COLOUR, (self.rect.x, y),
                             (self.rect.right, y))

            # Draw the labels for vertical axis
            windowSurface.blit(self.surface[i], self.surfaceRect[i])

        # Vertical columns
        for i in range(self.linesOfHeight):
            x = self.rect.x + i * self.H_Line_Dist
            pygame.draw.line(windowSurface, GRID_COLOUR, (x, self.rect.y),
                             (x, self.rect.bottom))

        # Draw lines connecting points
        # Examples of oldValues are oldBankBalance
        for i in range(len(oldValues) - 1):  # 14 connecting lines for the 15 points
            # Multiply self.verticalInterval by 1 less than number of rows because the 1st row is 0
            point1 = (oldValues[i] / (self.verticalInterval *
                                      (self.linesOfWidth - 1))) * self.rect.height

            # multiply by 330 which is vertical size of graph (? multiplies by 300)
            point2 = (oldValues[i + 1] / (self.verticalInterval *
                                          (self.linesOfWidth - 1))) * self.rect.height

            drawLine(windowSurface, GRAPH_COLOUR,
                     (self.rect.x + i * self.H_Line_Dist,
                      self.rect.bottom - point1),

                     # Use i+1 because line connects to point in front of it
                     (self.rect.x + (i + 1) * self.H_Line_Dist,
                      self.rect.bottom - point2))

    # Only called from inside
    def redrawGraph(self, oldValues):
        assert len(oldValues) == self.linesOfHeight

        if oldValues != self.lastOldValues:
            # Don't do by reference
            self.lastOldValues = oldValues.copy()
            # Add old labels to dirty rects
            for rect in self.surfaceRect:
                dirtyRects.append(rect)

            '''
            1. Take the maximum and minimum of the oldValues
            2. Subtract max by min and then divide by 10 because there are 11 rows on the bank graph with one of them used by 0
            3. Round up
            '''
            self.verticalInterval = math.ceil(max(oldValues) / (self.linesOfWidth - 1) * 100)
            self.verticalInterval /= 100
            if self.verticalInterval == 0:
                self.verticalInterval = 1

            self.surface = []
            self.surfaceRect = []

            for i in range(self.linesOfWidth):  # Number of rows in graph
                displayNumber = i * self.verticalInterval

                if displayNumber > 1 or displayNumber == 0:
                    text = str(round(displayNumber))

                else:
                    text = str(displayNumber)

                self.surface.append(font.render(text, True, GREEN, BLACK))

                self.surfaceRect.append(self.surface[i].get_rect())
                self.surfaceRect[i].right = self.rect.x - 5
                # Align and center axis label with line on graph
                self.surfaceRect[i].centery = self.rect.bottom - i * self.V_Line_Dist

                # Add new labels to dirty rects
                dirtyRects.append(self.surfaceRect[i])

            # Add entire graph except for labels to dirty rects (red & green lines)
            dirtyRects.append(self.rect)

    def appendData(self, oldValues, newValue):
        oldValues.append(newValue)
        if len(oldValues) > self.linesOfHeight:
            del oldValues[0]

        return oldValues


bankGraph = Graph(linesOfWidth=11, linesOfHeight=15, H_Line_Dist=60, V_Line_Dist=30)
bankGraph.rect.topleft = 85, INTERNAL_HEIGHT // 2

# 'Left' is shifted 5 right from last arrow
# Top is defined afterwards
# Width and height are the vertical size of top arrow and spacing from arrow below


class ChangeValueButton:
    def __init__(self, title, centerx, top):
        # Arrows
        self.arrow1Rect = changeArrow1.get_rect()
        self.arrow5Rect = changeArrow5.get_rect()
        self.arrow1DownRect = changeArrow1.get_rect()
        self.arrow5DownRect = changeArrow5.get_rect()

        # Text
        self.title = TextRect(font, title, WHITE, BLACK)
        self.title.rect.midtop = centerx, top

        # Position
        # Centers the arrows a bit more with title
        self.arrow5Rect.left = self.title.rect.centerx - 15
        self.arrow5Rect.top = self.title.rect.bottom + 8  # 8 is a gap

        self.arrow5DownRect.left = self.arrow5Rect.left
        self.arrow5DownRect.top = self.arrow5Rect.bottom + 5

        self.arrow1Rect.left = self.arrow5Rect.right + 5
        self.arrow1Rect.top = self.arrow5Rect.top

        self.arrow1DownRect.left = self.arrow5DownRect.right + 5
        self.arrow1DownRect.top = self.arrow5DownRect.top

        # Square
        self.finalizeButton = pygame.Rect(self.arrow1Rect.right + 5, 0,
                                          self.arrow1DownRect.y - self.arrow1Rect.y,
                                          self.arrow1DownRect.y - self.arrow1Rect.y)

        self.finalizeButton.centery = (self.arrow5Rect.bottom + self.arrow5DownRect.top) / 2

        self.displayValue = None
        self.value = 0
        self.updateValueSurface(updateDirtyRects=False)

        self.allButtons = (self.arrow1Rect,
                           self.arrow5Rect,
                           self.arrow1DownRect,
                           self.arrow5DownRect,
                           self.finalizeButton)

    def draw(self, bounds):
        windowSurface.blit(changeArrow5, self.arrow5Rect)
        windowSurface.blit(changeArrow5Inv, self.arrow5DownRect)
        windowSurface.blit(changeArrow1, self.arrow1Rect)
        windowSurface.blit(changeArrow1Inv, self.arrow1DownRect)

        self.keepBounds(bounds)
        self.updateValueSurface()
        windowSurface.blit(self.valueSurface, self.valueRect)

        pygame.draw.rect(windowSurface, GREEN, self.finalizeButton)
        self.title.draw()

    def changeValue(self, bounds):
        if mouseover(self.arrow5Rect):
            self.value += 5

        elif mouseover(self.arrow5DownRect):
            self.value -= 5

        elif mouseover(self.arrow1Rect):
            self.value += 1

        elif mouseover(self.arrow1DownRect):
            self.value -= 1

    def updateValueSurface(self, updateDirtyRects=True):
        if self.value != self.displayValue:
            self.displayValue = self.value
            self.valueSurface = font.render(str(self.value), True, WHITE, BLACK)

            if updateDirtyRects:
                dirtyRects.append(self.valueRect.copy())

            self.valueRect = self.valueSurface.get_rect()
            self.valueRect.right = self.arrow5Rect.left - 10
            self.valueRect.centery = (self.arrow5Rect.bottom + self.arrow5DownRect.top) / 2

            if updateDirtyRects:
                dirtyRects.append(self.valueRect)

        return dirtyRects


class DepositButton(ChangeValueButton):
    def keepBounds(self, playerGold):
        self.value = min(self.value, playerGold)
        self.value = max(self.value, 0)


class WithdrawButton(ChangeValueButton):
    def keepBounds(self, localBankBalance):
        self.value = min(self.value, localBankBalance)
        self.value = max(self.value, 0)


bankDeposit = DepositButton('Deposit', INTERNAL_WIDTH * 1 / 3, 150)
bankWithdraw = WithdrawButton('Withdraw', INTERNAL_WIDTH * 2 / 3, 150)


class LibraryInterior:
    def __init__(self, name, displayTexts):
        self.text = {}

        for text in (name,) + displayTexts:
            self.text[text] = {}
            self.text[text] = TextRect(font, text, WHITE, BLACK)

        self.text[name].rect.midtop = INTERNAL_WIDTH // 2, 5

    def draw(self):
        windowSurface.fill(BLACK)

        windowSurface.blit(bookImage, bookRect)
        windowSurface.blit(cavePreview['Surface'], cavePreview['Rect'])
        windowSurface.blit(bookOverlayImage, bookRect)

        # Begin displaying Cave Info area
        pygame.draw.rect(windowSurface, DARK_GREY,
                         libraryCaveInfoMenu['Background Rect'])

        # Check if there is cave info
        if libraryCaveInfoMenu['Cave Size'] is not None:
            libraryCaveInfoMenu['Cave Size'].draw()
            libraryCaveInfoMenu['Cave Type'].draw()

        # Iterate through list of texts for library
        for i in self.text:
            self.text[i].draw()

        # Cave adventure selection
        for textRect, backgroundRect in zip(adventureSelection['TextRect'],
                                            adventureSelection['Back Rect']):

            pygame.draw.rect(windowSurface, GREY, backgroundRect)
            textRect.draw()

        # Draw selection outline over selected box
        centerRect = adventureSelection['Back Rect'][selectedAdventure -
                                                     adventureSelection['Offset'] - 1]
        outlineRect(centerRect, 10)

        # Draw gold triangle selector
        pygame.gfxdraw.filled_trigon(windowSurface, centerRect.right - 15, centerRect.centery,
                                     centerRect.right + 15, centerRect.centery - 10,
                                     centerRect.right + 15, centerRect.centery + 10, GOLD)

        # Cave compartment selection
        for (backRect, image, imageRect, numberSurface, numberRect,
             i) in zip(compartmentSelection["Back Rect"],
                       compartmentSelection["Image"],
                       compartmentSelection["Image Rect"],
                       compartmentSelection["Number Surface"],
                       compartmentSelection["Number Rect"],
                       range(len(compartmentSelection["Back Rect"]))):

            pygame.draw.rect(windowSurface, DARK_GREY, backRect)

            windowSurface.blit(image, imageRect)
            windowSurface.blit(numberSurface, numberRect)

            if mouseover(backRect):
                windowSurface.blit(highlightCompartmentSurface, backRect)

            if i + compartmentSelection["Offset"] == selectedCompartment:
                outlineRect(backRect, 5)

        # Cave compartment selection arrows

        if mouseover(compartmentSelection["Left Arrow Rect"]):
            color = DARK_GREY

        else:
            color = GREY

        pygame.gfxdraw.filled_trigon(windowSurface,
                                     *compartmentSelection["Left Arrow Rect"].topright,
                                     *compartmentSelection["Left Arrow Rect"].bottomright,
                                     *compartmentSelection["Left Arrow Rect"].midleft,
                                     color)

        if mouseover(compartmentSelection["Right Arrow Rect"]):
            color = DARK_GREY

        else:
            color = GREY

        pygame.gfxdraw.filled_trigon(windowSurface,
                                     *compartmentSelection["Right Arrow Rect"].topleft,
                                     *compartmentSelection["Right Arrow Rect"].bottomleft,
                                     *compartmentSelection["Right Arrow Rect"].midright,
                                     color)


library = LibraryInterior('Library', ('Adventure', 'Depth', 'Cave Info'))

library.text['Adventure'].rect.x = 20
library.text['Adventure'].rect.y = 50

library.text['Cave Info'].rect.right = INTERNAL_WIDTH - 100
library.text['Cave Info'].rect.y = library.text['Adventure'].rect.y

library.text['Depth'].rect.centerx = INTERNAL_WIDTH / 2

width = 630
bookRect = pygame.Rect(130, 70, width, width / 4 * 3)
bookImage = pygame.transform.smoothscale(imgLoad("images/book.png"), bookRect.size)
bookOverlayImage = pygame.transform.smoothscale(imgLoad("images/bookLightingOverlay.png"),
                                                bookRect.size)

library.text['Depth'].rect.top = bookRect.bottom + 10

class LibraryCavePreview:
    def __init__(self):
        # For the image of cave in library - 10 pixels smaller in each directory
        self.rect = bookRect.inflate(-100, -100)

        # Shift the preview up a bit to align preview with paper on book image
        self.rect.y -= 10
        self.surface = None

cavePreview = LibraryCavePreview()

libraryCaveInfoMenu = {"Background Rect": pygame.Rect(0, 0, 220, 200),
                       "Cave Size": None,
                       "Cave Type": None
                       }

libraryCaveInfoMenu["Background Rect"].centerx = library.text["Cave Info"].rect.centerx
libraryCaveInfoMenu["Background Rect"].top = library.text['Cave Info'].rect.bottom + 20

compartmentSelection = {"Back Rect": [],  # Includes image rect and number rect
                        "Image": [],
                        "Image Rect": [],
                        "Number Surface": [],
                        "Number Rect": [],
                        "Offset": 0,
                        "Left Arrow Rect": None,
                        "Right Arrow Rect": None}

highlightCompartmentSurface = pygame.Surface((135, 180))
highlightCompartmentSurface.set_alpha(64)
highlightCompartmentSurface.fill((WHITE))


# Currently only supports loading new caves, add support for changing offset
def updateCompartmentSelection(caveAdventures):
    numberOfCompartments = len(caveAdventures[selectedAdventure - 1]["Compartment"])

    if numberOfCompartments > 6:
        length = 6

    else:
        length = numberOfCompartments

    for i in ("Back Rect", "Image", "Image Rect", "Number Surface", "Number Rect"):
        compartmentSelection[i] = []

    backRectWidth, backRectHeight = highlightCompartmentSurface.get_size()

    imageWidth = highlightCompartmentSurface.get_width()
    imageHeight = int(imageWidth / 4 * 3)

    # TODO: split this into 2 for loops, the first one loads images as fast as possible
    # TODO: Future - Make it so that a mouseover draws a translucent rect over the back rect
    for i in range(length):
        if isClient:
            saveFolder = checkServerSaveDirectory()

        else:
            saveFolder = checkSaveDirectory(worldID, True)

        checkFolder(saveFolder + 'caves')

        if not os.path.isdir(saveFolder + 'caves/' + str(selectedAdventure)):
            # Add support for corrupted saves
            assert False

        saveFolder = (saveFolder + "caves/" + str(selectedAdventure) +
                      "/" + str(i + compartmentSelection["Offset"]))

        checkFolder(saveFolder)

        compartmentSelection['Back Rect'].append(pygame.Rect(INTERNAL_WIDTH - 6 * backRectWidth + i * backRectWidth - 3 * 15,
                                                             INTERNAL_HEIGHT - backRectHeight,

                                                             backRectWidth, backRectHeight))

        compartmentSelection['Image Rect'].append(pygame.Rect(compartmentSelection['Back Rect'][i].x,
                                                              INTERNAL_HEIGHT - imageHeight,
                                                              imageWidth, imageHeight))

        thumbnail_path = os.path.join(saveFolder, "thumbnail.png")
        if os.path.isfile(thumbnail_path):
            image = imgLoad(thumbnail_path)

        else:
            image = pygame.Surface(INTERNAL_SIZE)
            image.fill(BLACK)

        # If iterating over selected compartment, get the preview rect
        if i + compartmentSelection['Offset'] == selectedCompartment:
            cavePreviewSurface = pygame.transform.smoothscale(image, cavePreview['Rect'].size)

        thumbnailImage = pygame.transform.smoothscale(image, (imageWidth, imageHeight))
        compartmentSelection['Image'].append(thumbnailImage)

        surf, rect = menuFont.render(str(i + 1 + compartmentSelection['Offset']), WHITE)
        compartmentSelection['Number Surface'].append(surf)

        # Only used for centering the number rect which is used to display a centered number
        numberBackRect = pygame.Rect(compartmentSelection["Back Rect"][i].topleft,

                                     (compartmentSelection["Back Rect"][i].width,

                                      compartmentSelection["Back Rect"][i].height -
                                      compartmentSelection["Image Rect"][i].height))

        compartmentSelection["Number Rect"].append(rect)
        compartmentSelection["Number Rect"][i].center = numberBackRect.center

    compartmentSelection["Left Arrow Rect"] = pygame.Rect(0, 0, 40, backRectHeight)
    compartmentSelection["Right Arrow Rect"] = compartmentSelection["Left Arrow Rect"].copy()

    compartmentSelection["Left Arrow Rect"].topright = compartmentSelection["Back Rect"][0].topleft
    compartmentSelection["Right Arrow Rect"].topleft = compartmentSelection["Back Rect"][-1].topright

    return compartmentSelection, cavePreviewSurface


adventureSelection = {"Back Rect": [],
                      "TextRect": [],
                      "Offset": 0}

verticalSpace = (INTERNAL_HEIGHT - library.text['Adventure'].rect.bottom - 20)  # Temp variable
for i in range(9):
    adventureSelection["Back Rect"].append(pygame.Rect(library.text["Adventure"].rect.centerx - (100 // 2),  # Center over adventure text
                                                       # Create nine rects in between the distance of 10 below adventure text
                                                       # and 10 above bottom of screen
                                                       verticalSpace // 9 * i +
                                                       library.text["Adventure"].rect.bottom + 10,
                                                       100,
                                                       verticalSpace // 9))

    # Create blank values so that the updateAdventureSelection function can run and change lists
    adventureSelection["TextRect"].append(None)

# Covers all of the list adventureSelection"s back rect | Used for
# dirty rects (although changing only the surfaces would be faster)
libraryAdventureSelectionRect = pygame.Rect(*adventureSelection["Back Rect"][0].topleft,
                                            adventureSelection["Back Rect"][0].width,

                                            adventureSelection["Back Rect"][-1].bottom -
                                            adventureSelection["Back Rect"][0].top)


def updateAdventureSelection(caveAdventures):
    for i in range(9):
        if i + 1 + adventureSelection['Offset'] <= len(caveAdventures):
            fontString = str(i + 1 + adventureSelection['Offset'])

        else:
            fontString = 'N/A'

        adventureSelection['TextRect'][i] = TextRect(l_menuFont, fontString, WHITE, GREY)
        adventureSelection['TextRect'][i].rect.center = adventureSelection['Back Rect'][i].center

    dirtyRects.append(libraryAdventureSelectionRect)

    return adventureSelection, dirtyRects


selectedAdventure = 1
selectedCompartment = 0


def marketValue(requestItem):
    # Market items
    itemValueList = {"Torch": 5, "Rope": 20, "Gold Sword": 100,
                     "Golden Ingot": 150, "Iron Ingot": 40,
                     "Backpack": 10, "Arrows": 5, "Arrow": 2,
                     "Watch": 100, "Iron Ore": 3, "Gold Ore": 10,
                     "Ashes": 0, "Salt": 50, "Stardust": 500}

    if requestItem in itemValueList:
        return itemValueList[requestItem]

    print('Unexpected item -', requestItem)
    raise ValueError  # Unexpected item


class Item:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.setID()

    # By default make the item's id it's name, will be overwritten by other classes
    def setID(self):
        self.id = self.name

    def getValue(self):
        return marketValue(self.name)

    def getSurface(self):
        if self.id in itemGraphicLocator:
            return itemGraphicLocator[self.id]

        else:
            raise Exception("Item ID is", self.id)

    def getDisplayText(self):
        return self.name


class OreItem(Item):
    def __init__(self, quality, type, name=None, description=None):
        if name is None:
            newName = quality + ' ' + type

        else:
            newName = name

        self.quality = quality
        self.type = type

        Item.__init__(self, newName, description)

    def getValue(self):
        if self.type in REGULAR_ORES:
            multiplier = {'Poor': 10, 'Normal': 25, 'Good': 50}
            return multiplier[self.quality]

        elif self.type in RARE_ORES:
            baseItemValue = {'Gold Nugget': 20, 'Pyrite': 0,
                             'Diamond': 80}[self.type]

            multiplier = {'Poor': 1, 'Normal': 2, 'Good': 3}

            return baseItemValue * multiplier[self.quality]

        raise ValueError

    def getSurface(self):
        if self.type == 'Diamond':
            return diamondImage

        # Pyrite graphic should be slightly too shiny
        elif self.type in ('Gold Nugget', 'Pyrite'):
            return goldIngotImage

        elif self.type in REGULAR_ORES:
            return {'Poor Ruby': poorRuby, 'Normal Ruby': normalRuby,
                    'Good Ruby': goodRuby, 'Poor Sapphire': poorSapphire,
                    'Normal Sapphire': normalSapphire, 'Good Sapphire': goodSapphire,
                    'Poor Emerald': poorEmerald, 'Normal Emerald': normalEmerald,
                    'Good Emerald': goodEmerald}[self.id]

    def setID(self):
        self.id = self.quality + ' ' + self.type


class Armor(Item):
    def __init__(self, quality, type, name=None, description=None):
        if name is None:
            newName = oreQuality + ' ' + oreType

        else:
            newName = name

        self.quality = quality
        self.type = type

        Item.__init__(self, newName, description)

    def getValue(self):
        # Get base value based on type of armor
        initialItemValue = {'Boot': 40, 'Chestplate': 150,
                            'Glove': 60}[self.type]

        if self.quality == 'Expensive':
            return initialItemValue * 4

        elif self.quality == 'Regular':
            return initialItemValue

        raise ValueError

    def getSurface(self):
        return {'Expensive Boot': expensiveBootArmorImage,
                'Expensive Chestplate': expensiveChestplateImage,
                'Expensive Glove': expensiveGloveArmorImage,
                'Regular Boot': regularBootArmorImage,
                'Regular Chestplate': regularChestplateImage,
                'Regular Glove': regularGloveArmorImage}[self.id]

    def setID(self):
        self.id = self.quality + ' ' + self.type


class Sword(Item):
    def __init__(self, swordType, name=None, description=None):
        if name is None:
            newName = swordType + ' Sword'

        else:
            newName = name

        self.swordType = swordType
        Item.__init__(self, newName, description)

    def getValue(self):
        return {'Wooden': 20, 'Stone': 40,
                'Iron': 100}[self.swordType]

    def getSurface(self):
        return {'Wooden': woodSwordImage, 'Stone': stoneSwordImage,
                'Iron': ironSwordImage}[self.swordType]

    def setID(self):
        self.id = self.swordType + ' Sword'


class Shield(Item):
    def __init__(self, shieldType, name=None, description=None):
        if name is None:
            newName = shieldType + ' Shield'

        else:
            newName = name

        self.shieldType = shieldType
        Item.__init__(self, newName, description)

    def getValue(self):
        return {'Fortified': 200, 'Iron': 250,
                'Gilded': 350, 'Gold': 650}[self.shieldType]

    def getSurface(self):
        return {'Fortified': fortifiedShieldImage, 'Iron': ironShieldImage,
                'Gilded': gildedShieldImage, 'Gold': goldShieldImage}[self.shieldType]

    def setID(self):
        self.id = self.shieldType + ' shieldType'


class Pickaxe(Item):
    def __init__(self, pickaxeType, name=None, description=None):
        self.pickaxeType = pickaxeType

        if name is None:
            name = self.pickaxeType + ' Pickaxe'

        Item.__init__(self, name, description)

    def getValue(self):
        return {'Old': 50, 'Iron': 500}[self.pickaxeType]

    def getSurface(self):
        return {'Old': oldPickaxeImage, 'Iron': ironPickaxeImage}[self.pickaxeType]

    def setID(self):
        self.id = self.pickaxeType + ' Pickaxe'


class Scroll(Item):
    def __init__(self, scrollColour, questText, name=None, description=None):
        self.scrollColour = scrollColour
        self.questText = questText

        if name is None:
            name = self.scrollColour + ' Scroll'

        Item.__init__(self, name, description)

    def getValue(self):
        return 0

    def getSurface(self):
        return {'Red': redScrollImage, 'Blue': blueScrollImage}[self.scrollColour]

    def setID(self):
        self.id = 'Scroll'


class Bow(Item):
    def __init__(self, bowType, name=None, description=None):
        if name is None:
            newName = bowType + ' Bow'

        else:
            newName = name

        self.bowType = bowType
        Item.__init__(self, newName, description)

    def drawTrajectory(self, playerCentre, targetCentre):
        drawLine(windowSurface, colour, targetCentre, playerCentre)

    def getValue(self):
        return {'Old': 75, 'Wooden': 200,
                'Metal': 450}[self.bowType]

    def getSurface(self):
        return {'Old': bowImage, 'Wooden': bowImage,
                'Metal': bowImage}[self.bowType]

    def setID(self):
        self.id = self.bowType + ' Bow'


class HealthPotion(Item):
    def __init__(self, strength, name=None, description=None):
        if name is None:
            newName = 'Health Potion'

        else:
            newName = name

        self.strength = strength
        Item.__init__(self, newName, description)

    def getValue(self):
        return 40 + round(math.sqrt(self.strength))

    def getDisplayText(self):
        return self.name + ' ' + '(' + str(self.strength) + ')'

    def setID(self):
        self.id = 'Health Potion'

    def getSurface(self):
        return healthPotionImage


class GoldItem(Item):
    def __init__(self):
        Item.__init__(self, 'Gold')

    def getSurface(self):
        return goldImage


# Market items and other info
merchandise = (Sword(swordType='Stone'), Item('Torch'), Item('Rope'),
               Pickaxe('Old'), Item('Golden Ingot'))

marketText = {}

marketText['Market'] = TextRect(font, 'Market', WHITE, BLACK)
marketText['Buy'] = TextRect(font, 'Buy', WHITE, DARK_GREY)
marketText['Sell'] = TextRect(font, 'Sell', WHITE, DARK_GREY)
marketText['Item Value'] = TextRect(font, 'Item Value', WHITE, BLACK)

marketText['Market'].rect.centerx = INTERNAL_WIDTH // 2
marketText['Market'].rect.top = 5

marketText['Buy'].rect.centerx = INTERNAL_WIDTH * 1 / 5
marketText['Buy'].rect.top = INTERNAL_HEIGHT * 1 / 6

marketText['Sell'].rect.centerx = INTERNAL_WIDTH // 2
marketText['Sell'].rect.top = INTERNAL_HEIGHT * 1 / 6

# X value set after the marketGraph
marketText['Item Value'].rect.top = INTERNAL_HEIGHT * 2 / 5

marketText['Inventory'] = VariableTextRect(font, 'Inventory', GOLD, BLACK)
marketText['Inventory'].rect.bottom = inventoryMenu.titleRect.top - 25
marketText['Inventory'].rect.centerx = inventoryMenu.titleRect.centerx

# 5 * 2 is a 5 pixel spacing
marketBuyMenu = {'Background Rect': pygame.Rect(0, 0, (32 + 5) * len(merchandise) + 5 * 2 + 60, 150),
                 'Inventory Item': [],
                 'Inventory Rect': []}

marketBuyMenu['Background Rect'].top = marketText['Buy'].rect.top - 8
marketBuyMenu['Background Rect'].centerx = marketText['Buy'].rect.centerx

for i in range(len(merchandise)):
    # Center box over the background rect and add distance based on spot in merchandise
    marketBuyMenu['Inventory Item'].append(merchandise[i])
    rect = pygame.Rect(((marketBuyMenu['Background Rect'].width - ((32 + 3) * len(merchandise))) // 2 +
                        marketBuyMenu['Background Rect'].x + 35 * i,
                        marketText['Buy'].rect.bottom + 15),
                       INVENTORY_SLOT_SIZE)
    marketBuyMenu['Inventory Rect'].append(rect.copy())  # 32 is size of item spot

# 8 pixel buffer
marketBuyMenu['Finish Rect'] = pygame.Rect((marketBuyMenu['Background Rect'].centerx - 32 // 2,
                                            marketBuyMenu['Background Rect'].bottom - 32 - 8),
                                           INVENTORY_SLOT_SIZE)

# Similar to buy menu
# Copy width and height
marketSellMenu = {'Background Rect': marketBuyMenu['Background Rect'].copy()}
marketSellMenu['Background Rect'].top = marketText['Sell'].rect.top - 8
marketSellMenu['Background Rect'].centerx = marketText['Sell'].rect.centerx


class MarketSellText(VariableTextRect):
    def __init__(self, text):
        super().__init__(submenuFont, text, BLACK, DARK_GREY)
        self.visible = False

    def draw(self):
        if self.visible:
            super().draw()


class MarketNameText(MarketSellText):
    def realignRect(self):
        self.rect.top = marketText['Sell'].rect.bottom + 8
        self.rect.x = marketSellMenu['Background Rect'].x + 15


class MarketValueText(MarketSellText):
    def realignRect(self):
        self.rect.top = marketSellMenu['Item Name'].rect.bottom + 8
        self.rect.x = marketSellMenu['Background Rect'].x + 15


marketSellMenu['Item Name'] = MarketNameText('Item Name')
marketSellMenu['Item Value'] = MarketValueText('Item Value')

# 32 is size of box, 8 pixel buffer
marketSellMenu['Finish Rect'] = pygame.Rect((marketSellMenu['Background Rect'].centerx - 32 // 2,
                                             marketSellMenu['Background Rect'].bottom - 32 - 8),
                                            INVENTORY_SLOT_SIZE)

marketGraph = Graph(linesOfWidth=11, linesOfHeight=15, H_Line_Dist=45, V_Line_Dist=40)
marketGraph.rect.midleft = 50, (INTERNAL_HEIGHT + marketText['Item Value'].rect.bottom) // 2

marketText['Item Value'].rect.centerx = marketGraph.rect.centerx

lastItemHighlighted = None
oldItemValue = []
for i in range(marketGraph.linesOfHeight):
    oldItemValue.append(0)

buyingItem = False
buyingItemID = None  # Index of item in merchandise which is being bought

# Stock market
stockMarketSelectedTab = 'Historic Value'

def take_screenshot(surface):
    # Create screenshot folder if non-existant
    checkFolder('screenshots')

    currentTime = datetime.datetime.now()
    numberOfAttempts = 0

    # This allows multiple screenshots in the same second
    while True:
        if numberOfAttempts == 0:
            fileSuffix = ""

        else:
            fileSuffix = f"_{numberOfAttempts}"

        date = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
        fileName = f"{date}{fileSuffix}.png"
        path = os.path.join("screenshots", fileName)

        if os.path.isfile(path):
            numberOfAttempts += 1

        else:
            break

    # Save surface
    pygame.image.save(surface, path)
    print('Screenshot captured and stored at ' + path)


class Tooltip:
    def __init__(self):
        self.lastDisplayText = None
        self.visible = False

    def draw(self, destPos):
        if self.visible:
            self.textRect.rect.bottomleft = destPos

            if self.textRect.rect.right > INTERNAL_WIDTH:
                self.textRect.rect.right = INTERNAL_WIDTH

            windowSurface.blit(self.backSurface, self.textRect.rect)
            dirtyRects.append(self.textRect.draw())

            # Not mousing over any menu
            if currentMenu is None:
                self.visible = False

    def initialize(self, item):
        itemName = item.getDisplayText()

        if self.lastDisplayText != itemName:
            self.visible = True
            self.lastDisplayText = itemName

            self.textRect = TextRect(font, itemName, WHITE)
            self.backSurface = pygame.Surface(self.textRect.rect.size)
            self.backSurface.set_alpha(128)
            self.backSurface.fill(DARK_GREY)


itemTooltip = Tooltip()

availableStocks = ('Miner Co.', 'Exploration Inc', 'Blocks and Crafts')

stockMarketText = {}
STOCK_MARKET_TABS = ('Historic Value', 'Past Values', 'Own Quantity')


class StockTab(TextRect):
    def draw(self):
        self.backColour = self.getColour()
        super().draw()
        drawRightTriangles(self.getColour(), self.rect)

    def getColour(self):
        # Pick color of tab based on whether it is selected
        if self.displayText == stockMarketSelectedTab:
            return GREY

        else:
            return DARK_GREY

    def getDirtyRect(self):
        return addTooltipDirtyRects(self.rect)


stockMarketText['Stock Market'] = TextRect(font, 'Stock Market', WHITE, BLACK)
for text in STOCK_MARKET_TABS:
    stockMarketText[text] = StockTab(font, text, WHITE, BLACK)

stockMarketText['Stock Market'].rect.centerx = INTERNAL_WIDTH // 2
stockMarketText['Stock Market'].rect.top = 5

stockMarketText['Gold Equivalent'] = GoldEquivVTR(GOLD, BLACK)

stockMarketText['Inventory'] = VariableTextRect(font, 'Inventory', GOLD, BLACK)
stockMarketText['Own Number of Stocks'] = VariableTextRect(
    font, 'Own Number of Stocks', GOLD, BLACK)


class SideMenu:
    def __init__(self, itemList, maximumWidth):
        self.visible = False
        self.text = {}
        self.textRect = {}
        self.selectRect = {}

        self.backRect = {'Minimized': pygame.Rect(0, 0, 15, INTERNAL_HEIGHT),
                         'Maximized': pygame.Rect(0, 0, maximumWidth, INTERNAL_HEIGHT)}

        self.itemList = itemList
        self.addItems(itemList)

    def addItems(self, itemList):
        for i, item in enumerate(itemList):
            self.text[item] = font.render(item, True, WHITE)
            self.textRect[item] = self.text[item].get_rect()
            self.textRect[item].top = 100 + i * 24
            self.selectRect[item] = self.textRect[item].copy()
            self.selectRect[item].width = self.backRect['Maximized'].width

    def checkMouseOver(self, dirtyRects):
        if not self.visible and mousePos[0] <= self.backRect['Minimized'].right:
            self.visible = True
            dirtyRects.append(self.backRect['Maximized'])

        elif self.visible and mousePos[0] >= self.backRect['Maximized'].right + 150:
            self.visible = False
            dirtyRects.append(self.backRect['Maximized'])

        return dirtyRects

    def draw(self, dirtyRects):
        if self.visible:
            pygame.draw.rect(windowSurface, GREY, self.backRect['Maximized'])

            # Show available elements
            for item in self.itemList:
                # Highlight items which are moused over
                if mouseover(self.selectRect[item]):
                    pygame.draw.rect(windowSurface, DARKER_GREY,
                                     self.selectRect[item])
                    dirtyRects.append(self.selectRect[item])

                windowSurface.blit(self.text[item], self.textRect[item])

        else:
            pygame.draw.rect(windowSurface, GREY, self.backRect['Minimized'])

        return dirtyRects


selectStock = SideMenu(availableStocks, 150)
selectedStock = availableStocks[0]

stockGraph = Graph(linesOfWidth=11, linesOfHeight=15, H_Line_Dist=40, V_Line_Dist=40)
longTermStockGraph = Graph(linesOfWidth=11, linesOfHeight=15 * 40, H_Line_Dist=1, V_Line_Dist=40)
ownQuantityStockGraph = Graph(linesOfWidth=11, linesOfHeight=15 * 40, H_Line_Dist=1, V_Line_Dist=40)

stockGraph.rect.bottomleft = 50, INTERNAL_HEIGHT - 20
longTermStockGraph.rect = stockGraph.rect
ownQuantityStockGraph.rect = stockGraph.rect

for key, xFraction in zip(STOCK_MARKET_TABS,
                          (1 / 6, 1 / 2, 5 / 6)):
    stockMarketText[key].rect.centerx = (stockGraph.rect.x +
                                         stockGraph.rect.width * xFraction)

for key in STOCK_MARKET_TABS:
    stockMarketText[key].rect.bottom = stockGraph.rect.top

# Logos
# Add more images in the future
stockMarketLogo = {'Text Rect': {},
                   'Logo Image': {},
                   'Logo Rect': {}}
# Merge into for loop with available stocks in the future
stockMarketLogo['Text Rect']['Miner Co.'] = selectStock.textRect['Miner Co.'].copy()
stockMarketLogo['Text Rect']['Miner Co.'].top = 5
stockMarketLogo['Text Rect']['Miner Co.'].centerx = INTERNAL_WIDTH - 55

stockMarketLogo['Logo Image']['Miner Co.'] = imgLoad('images/corporations/Miner Co.png')
stockMarketLogo['Logo Rect']['Miner Co.'] = stockMarketLogo['Logo Image']['Miner Co.'].get_rect()
stockMarketLogo['Logo Rect']['Miner Co.'].top = stockMarketLogo['Text Rect']['Miner Co.'].bottom + 10
stockMarketLogo['Logo Rect']['Miner Co.'].centerx = stockMarketLogo['Text Rect']['Miner Co.'].centerx


class BuyStockButton(ChangeValueButton):
    def keepBounds(self, playerGold):
        # Value refers to quantity of stock
        if round(self.value * stocks[selectedStock].float) > playerGold:
            self.value = mathFloor(playerGold / stocks[selectedStock].float)

        elif self.value < 0:
            self.value = 0


class SellStockButton(ChangeValueButton):
    def keepBounds(self, stockInv):
        # Quantity of stock player has
        if self.value > stockInv.count(selectedStock):
            self.value = stockInv.count(selectedStock)

        elif self.value < 0:
            self.value = 0


stockMarketBuy = BuyStockButton('Buy Stock', stockGraph.rect.left +
                                stockGraph.rect.width * 1 / 3, 120)

stockMarketSell = SellStockButton('Sell Stock', stockGraph.rect.left +
                                  stockGraph.rect.width * 2 / 3, 120)

# Center over buy and sell menus
stockMarketText['Gold Equivalent'].rect.centerx = (stockMarketBuy.title.rect.right +
                                                   stockMarketSell.title.rect.left) / 2
# Roughly the bottom of the buy sell menus
stockMarketText['Gold Equivalent'].rect.bottom = stockMarketBuy.arrow5DownRect.bottom + 30

stockMarketText['Own Number of Stocks'].rect.centerx = stockGraph.rect.centerx
stockMarketText['Own Number of Stocks'].rect.bottom = stockGraph.rect.top - 30

stockMarketText['Inventory'].rect.centerx = stockGraph.rect.centerx
stockMarketText['Inventory'].rect.bottom = stockGraph.rect.top - 50

warehouseText = []

warehouseText.append(TextRect(font, 'Warehouse', WHITE, BLACK))

warehouseText[0].rect.centerx = INTERNAL_WIDTH // 2
warehouseText[0].rect.top = 5

forgeText = {}

for text in ('Forge', 'Invest', 'Output', 'Input'):
    forgeText[text] = TextRect(font, text, WHITE, BLACK)

forgeText['Forge'].rect.centerx = INTERNAL_WIDTH // 2
forgeText['Forge'].rect.top = 5

forgeText['Invest'].rect.center = INTERNAL_WIDTH * 4 / 5, INTERNAL_HEIGHT // 5

forgeText['Output'].rect.centerx = 30
forgeText['Output'].rect.y = 320

forgeText['Input'].rect.centerx = 30
forgeText['Input'].rect.y = forgeText['Output'].rect.y + 230

forgeFireImage = imgLoad('images/forge/fire1.png').convert()
forgeFireRect = forgeFireImage.get_rect()
forgeFireRect.bottomleft = 0, INTERNAL_HEIGHT
assert forgeFireRect.width == INTERNAL_WIDTH

blacksmithText = {}

blacksmithText['Blacksmith'] = TextRect(font, 'Blacksmith', WHITE, BLACK)
blacksmithText['Desired Item'] = VariableTextRect(font, 'Desired Item', WHITE, BLACK)
blacksmithText['Operation Cost'] = VariableTextRect(font, 'Operation Cost', GOLD, BLACK)

blacksmithText['Blacksmith'].rect.centerx = INTERNAL_WIDTH // 2
blacksmithText['Blacksmith'].rect.top = 5

# Various parts of GUI are horizontally centered over this
BLACKSMITH_CRAFTING_LINE = INTERNAL_WIDTH // 4 + 100

blacksmithText['Desired Item'].rect.center = BLACKSMITH_CRAFTING_LINE, INTERNAL_HEIGHT // 3 - 100

blacksmithText['Operation Cost'].rect.center = (blacksmithText['Desired Item'].rect.centerx,
                                                blacksmithText['Desired Item'].rect.centery + 30)

blacksmithRequiredItemsSection = GUI_Divider(BLACKSMITH_CRAFTING_LINE, INTERNAL_HEIGHT * 2 / 3,
                                             300, 300, 'Required Items')

blacksmithInvestSection = GUI_Divider(0, 0, 420, 300, 'Invest')
blacksmithInvestSection.rect.topright = INTERNAL_WIDTH - 50, 100
blacksmithInvestSection.updateRect()

blacksmithUnlockInfoSection = GUI_Divider(0, 0, 420, 120, 'Unlock Info')
blacksmithUnlockInfoSection.rect.midtop = blacksmithInvestSection.rect.midbottom
blacksmithUnlockInfoSection.rect.y += 50
blacksmithUnlockInfoSection.updateRect()

blacksmithDesiredItem = {'Inventory': None}
blacksmithDesiredItem['Rect'] = bigInventorySpaceImage.get_rect()
blacksmithDesiredItem['Rect'].midtop = blacksmithText['Operation Cost'].rect.midbottom
blacksmithDesiredItem['Rect'].y += 10

# Required items GUI
REQUIRED_ITEMS_BOX_QUANTITY = 9
requiredItemSlots = []

# TODO: Add buying wood for recipe to make fortified shield
selectedBlueprint = 'Iron Pickaxe'
BLUEPRINT = {'Iron Pickaxe': {'Cost': 200, 'Recipe': ('Iron Ingot', 'Iron Ingot', 'Iron Ingot')},
             'Fortified Shield': {'Cost': 250, 'Recipe': ('Iron Ingot', 'Iron Ingot')},
             'Iron Shield': {'Cost': 350, 'Recipe': ('Iron Ingot', 'Iron Ingot',
                                                     'Iron Ingot', 'Iron Ingot')},
             'Gold Shield': {'Cost': 250, 'Recipe': ('Golden Ingot', 'Golden Ingot',
                                                     'Golden Ingot', 'Golden Ingot')},
             'Gold Sword': {'Cost': 100, 'Recipe': ('Golden Ingot', 'Golden Ingot')},
             'Gilded Shield': {'Cost': 200, 'Recipe': ('Golden Ingot', 'Golden Ingot', 'Golden Ingot')},
             'Regular Glove Armor': {'Cost': 120, 'Recipe': ('Iron Ingot', 'Iron Ingot')},
             'Regular Boot Armor': {'Cost': 250, 'Recipe': ('Iron Ingot', 'Iron Ingot',
                                                            'Iron Ingot')},
             'Regular Chestplate Armor': {'Cost': 400, 'Recipe': ('Iron Ingot', 'Iron Ingot', 'Iron Ingot',
                                                                  'Iron Ingot', 'Iron Ingot', 'Iron Ingot')},
             }

BLUEPRINT['Expensive Glove Armor'] = {'Cost': BLUEPRINT['Regular Glove Armor']['Cost'] + 30,
                                      'Recipe': BLUEPRINT['Regular Glove Armor']['Recipe'] + ('Golden Ingot',)}
BLUEPRINT['Expensive Boot Armor'] = {'Cost': BLUEPRINT['Regular Boot Armor']['Cost'] + 50,
                                     'Recipe': BLUEPRINT['Regular Boot Armor']['Recipe'] + ('Golden Ingot',)}
BLUEPRINT['Expensive Chestplate Armor'] = {'Cost': BLUEPRINT['Regular Chestplate Armor']['Cost'] + 70,
                                           'Recipe': BLUEPRINT['Regular Chestplate Armor']['Recipe'] + ('Golden Ingot',
                                                                                                        'Golden Ingot')}

class Map:
    def __init__(self):
        self.text = {}

        self.text['Map'] = TextRect(l_menuFont, 'Map', WHITE)
        self.text['Map'].rect.centerx = INTERNAL_WIDTH // 2
        self.text['Map'].rect.top = 105

        self.rect = pygame.Rect(100, 100, INTERNAL_WIDTH - 200, INTERNAL_HEIGHT - 200)
        self.image = pygame.transform.smoothscale(imgLoad('images/paper.png'),
                                                  self.rect.size)

    def draw(self, window):
        window.blit(self.image, self.rect)

        for i in self.text:
            self.text[i].draw()

map = Map()

# In game menus
inGameMenu = None

inGameMenuButtons = {}


class InGameMenuButton:
    def __init__(self, i, text):
        self.backRect = pygame.Rect(i * INTERNAL_WIDTH / 5, 0,
                                    math.ceil(INTERNAL_WIDTH / 5), 50)

        self.textRect = TextRect(warehouseFont, text, WHITE)
        self.textRect.rect.center = self.backRect.center

    def draw(self):
        # Highlight moused over button or show which menu is opened
        if mouseover(self.backRect) or inGameMenu == self.textRect.displayText:
            color = DARKER_GREY

        else:
            color = DARK_GREY

        pygame.draw.rect(windowSurface, color, self.backRect)
        self.textRect.draw()


buttonX = 0

for i, text in enumerate(('Inventory', 'Map', 'Journal', 'Quests', 'Player')):
    inGameMenuButtons[text] = InGameMenuButton(i, text)

NPC_Text = {'Main': {'Order': ('Trade', 'Leave')},
            'Trade': {'Order': ('Request Item', 'Sell', 'Stop Trading')},
            # These two below are the same
            'Request Item': {'Order': ('Accept', 'Exit')},
            'Sell': {'Order': ('Accept', 'Exit')}}

for i in NPC_Text:
    NPC_Text[i]['Back Rect'] = pygame.Rect(0, 0, 0, 0)
    NPC_Text[i]['Label'] = {}
    NPC_Text[i]['Rect'] = {}
    for menu in NPC_Text[i]['Order']:
        # Create surfaces
        NPC_Text[i]['Label'][menu] = font.render(menu, True,
                                                 BLACK, GREY)

        NPC_Text[i]['Rect'][menu] = NPC_Text[i]['Label'][menu].get_rect()
        NPC_Text[i]['Rect'][menu].y = NPC_Text[i]['Back Rect'].height

        NPC_Text[i]['Back Rect'].height += NPC_Text[i]['Rect'][menu].height

        # Store maximum width of text for menu background
        if NPC_Text[i]['Rect'][menu].width > NPC_Text[i]['Back Rect'].width:
            NPC_Text[i]['Back Rect'].width = NPC_Text[i]['Rect'][menu].width

'''The caveBackground variable is set when a new underground level
is loaded. It iterates through all the blocks in the backgroundBlocks layer
accordingly. (Blitting this takes a while so it is only be done once and
not updated like the regular blockGrid
'''
backgroundBlocks = []
for x in range(INTERNAL_WIDTH // BLOCK_SIZE * 4):
    backgroundBlocks.append([])
    for y in range(INTERNAL_HEIGHT // BLOCK_SIZE * 4):
        backgroundBlocks[x].append('Stone')

for x in range(INTERNAL_WIDTH // BLOCK_SIZE * 2):
    for y in range(INTERNAL_HEIGHT // BLOCK_SIZE * 2):
        coords = (x * BLOCK_SIZE // 2, y * BLOCK_SIZE // 2)
        # Background layer is made of stone, custom blocks can be added for detail
        # if backgroundBlocks[x][y] == 'Stone':
        caveBackground.blit(smallStoneImage, coords)

caveBackground.blit(GREY_SCREEN, (0, 0))

# Variables for moving sun and moon
DAY_LENGTH = 60 * 20  # In seconds
SUNRISE_LENGTH = DAY_LENGTH / 16

SUNSET_START = DAY_LENGTH / 2
SUNSET_END = SUNSET_START + SUNRISE_LENGTH

SUNRISE_START = 0
SUNRISE_END = SUNRISE_START + SUNRISE_LENGTH


class Flash:
    __slots__ = "alpha"

    MAX_ALPHA = 255
    RATE = 0.8

    def __init__(self):
        self.alpha = 0

    def animate(self, window):
        assert self.is_active()

        WHITE_SCREEN.set_alpha(self.alpha)
        window.blit(WHITE_SCREEN, (0, 0))
        self.alpha *= self.RATE

        if not self.is_active():
            self.alpha = 0

    def is_active(self):
        return self.alpha >= 1

    def start(self):
        self.alpha = self.MAX_ALPHA


flash = Flash()


class Shake:
    __slots__ = "angle", "radius", "x", "y"

    def __init__(self):
        self.angle = 0
        self.radius = 0
        self.calculate()

    def calculate(self):
        self.angle %= TAU
        self.x = math.sin(self.angle) * self.radius
        self.y = math.cos(self.angle) * self.radius

    # https://gamedev.stackexchange.com/a/47565
    def start(self, radius):
        self.angle = random.uniform(0, TAU)
        self.radius = radius
        self.calculate()

    def is_active(self):
        return self.radius > 0

    def animate(self, window):
        """
        Copy the screen and replace with black.
        Then blit the copied screen translated by x and y.
        """

        self.radius *= 0.9

        self.angle += (TAU/2 + random.uniform(-TAU/6, TAU/6))
        self.calculate()

        tempSurface = window.copy()
        window.fill(BLACK)
        window.blit(tempSurface, (self.x, self.y))

        # End screen shake
        if self.radius <= 1:
            self.x = 0
            self.y = 0
            self.radius = 0


shake = Shake()


# Variables for keeping track of which sky image to display
POLARIZED_NIGHT_LENGTH = DAY_LENGTH / 8
POLARIZED_NIGHT_START = DAY_LENGTH * 3 / 4 - POLARIZED_NIGHT_LENGTH / 2
POLARIZED_NIGHT_END = POLARIZED_NIGHT_START + DAY_LENGTH / 8

SKY_FADE_TIME = DAY_LENGTH / 16


class Timer:
    def __init__(self):
        self.sum = []
        self.totalTime = 0

    def reset(self):
        if self.totalTime != 0:
            self.sum.append(self.totalTime)

            if len(self.sum) == FPS * 5:
                del self.sum[0]

        self.totalTime = 0

    def start(self):
        self.time = time.time()

    def stop(self):
        self.totalTime += time.time() - self.time

    def getResult(self):
        if self.totalTime != 0:
            print(str(self.totalTime))

    def average(self):
        if len(self.sum) == 0:
            return 0

        else:
            return sum(self.sum) / len(self.sum)

    def percentage(self):
        return self.average() / (mainLightTimer.average() + entireTimer.average() +
                                 lightRegionTimer.average())


def clickGUI():
    return clickRectList((inventoryMenu.mainRect, playerInfoMenu.titleRect,
                          playerInfoMenu.mainRect, playerInfoMenu.titleRect))

# Verified to work with and without numpy


def Brush(r):
    blockSize = r * 2 + 1
    center = mathFloor(blockSize / 2)

    if np is None:
        newBrush = []

    else:
        newBrush = np.zeros((blockSize, blockSize), dtype=np.float32)

    for x in range(blockSize):
        if np is None:
            newBrush.append([])

        for y in range(blockSize):
            if np is None:
                newBrush[x].append(0)

            value = dist(x, center, y, center)
            if value > 0:
                newBrush[x][y] = value

            else:
                newBrush[x][y] = 1

    return newBrush


# Lighting code based on http://www.artofzombie.com/SideScroller/CodeTemplate.js
LIGHT_RES = 24
if android:
    LIGHT_RES *= 2

LIGHT_GRID_LENGTH = (INTERNAL_WIDTH + LIGHT_RES * 2) // LIGHT_RES
LIGHT_GRID_WIDTH = (INTERNAL_HEIGHT + LIGHT_RES * 2) // LIGHT_RES
MAX_COLOUR_ALPHA = round(0.3 * 255)


class LightingTimer(Timer):
    def percentage(self):
        return self.average() / mainLightTimer.average()


class Lighting:
    RES = 24
    SIZE = (LIGHT_GRID_LENGTH, LIGHT_GRID_WIDTH)

    def __init__(self):
        global debugInfo

        if np:  # Use the numpy library if possible to create a numpy array which is faster
            self.grid = np.zeros((LIGHT_GRID_LENGTH, LIGHT_GRID_WIDTH), dtype=np.float32)
            self.cGrid = np.zeros((LIGHT_GRID_LENGTH, LIGHT_GRID_WIDTH, 3), dtype=np.float32)

        else:
            self.grid = []
            self.cGrid = []

            for i in range(LIGHT_GRID_LENGTH):
                self.grid.append([])
                self.cGrid.append([])

                for j in range(LIGHT_GRID_WIDTH):
                    self.grid[i].append(0)
                    self.cGrid[i].append([0, 0, 0])  # Red, green, blue

        self.brushes = {}

        self.segments = []
        for key in range(13):
            debugInfo[key] = DebugPercentageLine(str(key))
            self.segments.append(LightingTimer())

    # Takes light source, finds/makes brush

    def light(self, x, y, r, intensity, color=WHITE):
        global lightRegionTimer, entireTimer

        radius = r

        if options['lighting'] == 'Off' or mapData['levelDarkness'] == 0:
            return

        else:
            if radius not in self.brushes:
                self.brushes[radius] = Brush(radius)

            entireTimer.stop()
            lightRegionTimer.start()

            self.calculateLight(x, y, radius, intensity, color)

            entireTimer.start()
            lightRegionTimer.stop()

    def calculateLight(self, x, y, r, intensity, colour):
        brushesR = self.brushes[r]

        # Superimposes b2 on b1
        def addArrays(b1, b2):
            v_range1 = slice(max(0, minX), max(min(minX + b2.shape[0], b1.shape[0]), 0))
            h_range1 = slice(max(0, minY), max(min(minY + b2.shape[1], b1.shape[1]), 0))

            v_range2 = slice(max(0, -minX), min(-minX + b1.shape[0], b2.shape[0]))
            h_range2 = slice(max(0, -minY), min(-minY + b1.shape[1], b2.shape[1]))

            b1[v_range1, h_range1] += b2[v_range2, h_range2]

            return b1

        centreX = mathFloor(x / self.RES) + 1
        centreY = mathFloor(y / self.RES) + 1

        brushOffsetX = centreX - r
        brushOffsetY = centreY - r

        if intensity > 0.01:
            minX = centreX - r
            maxX = centreX + r
            minY = centreY - r
            maxY = centreY + r

            # Check if any part is on screensegments
            if (maxX < LIGHT_GRID_LENGTH or  # Rightmost is to the left of right window
                minX >= 0 or  # The left is right of the left of window
                maxY < LIGHT_GRID_WIDTH or  # The bottom is above the bottom of window
                    minY >= 0):  # Top is below the top of window

                calculateColour = options['lighting'] == 'Colour'

                if np is None:
                    if minX < 0:
                        minX = 0

                    if maxX >= LIGHT_GRID_LENGTH:
                        maxX = LIGHT_GRID_LENGTH - 1

                    if minY < 0:
                        minY = 0

                    if maxY >= LIGHT_GRID_WIDTH:
                        maxY = LIGHT_GRID_WIDTH - 1

                    for x in range(minX, maxX + 1):
                        for y in range(minY, maxY + 1):
                            brushX = x - brushOffsetX
                            brushY = y - brushOffsetY

                            if brushesR[brushX][brushY] <= r:
                                brightnessIncrease = intensity * \
                                    (r / brushesR[brushX][brushY] - 1) * colour.a

                                self.grid[x][y] += brightnessIncrease
                                if calculateColour:
                                    brightnessIncrease /= 255
                                    self.cGrid[x][y][0] += brightnessIncrease * colour.r
                                    self.cGrid[x][y][1] += brightnessIncrease * colour.g
                                    self.cGrid[x][y][2] += brightnessIncrease * colour.b

                # Negative minX/minY indices work fine with addArrays function

                else:
                    # Sets the area outside brush lighting, but inside it's square as having intensity 0
                    # This is still inefficient as calculations are done here
                    brightnessIncrease = np.clip(brushesR, 0, r)
                    np.reciprocal(brightnessIncrease, out=brightnessIncrease)
                    brightnessIncrease *= r
                    brightnessIncrease -= 1
                    brightnessIncrease *= intensity

                    # Only manage brightnesses
                    brightnessIncrease *= colour[3]
                    self.grid = addArrays(self.grid, brightnessIncrease)

                    if calculateColour:
                        brightnessIncrease /= 255  # Turns 0 - 255 brightness into 0 - 100%
                        self.cGrid = addArrays(self.cGrid, np.array(
                            colour)[:-1] * brightnessIncrease[:, :, None])

    def draw(self, levelDarkness, lightingOption):
        self.segments[0].start()
        # Display lighting
        baseShade = levelDarkness / 255

        # Make the lightingSurface that is upscaled to the main screen later
        lightingSurface = pygame.Surface(self.SIZE, pygame.SRCALPHA, 32)
        lightingSurface.fill(BLACK)  # Set it to levelDarkness?

        self.segments[0].stop()

        if usingNumpy():
            # Set up alpha values
            # Caps brightness with a clip
            self.segments[1].start()
            Monochromatic_alphaArray = 255 - self.grid
            Monochromatic_alphaArray *= baseShade
            np.clip(Monochromatic_alphaArray, 0, 255, out=Monochromatic_alphaArray)
            self.segments[1].stop()

            self.segments[2].start()
            # Apply alpha to black and white lighting and fog
            lightingSurfaceAlpha = pygame.surfarray.pixels_alpha(lightingSurface)
            self.segments[2].stop()

            # Can't do direct assignment as this would remove the surfarray link
            self.segments[3].start()
            lightingSurfaceAlpha[:, :] = Monochromatic_alphaArray
            self.segments[3].stop()

        else:
            lightingSurfaceAlpha = pygame.PixelArray(lightingSurface)

        if lightingOption == 'Colour':
            self.segments[4].start()
            colourLightingSurface = pygame.Surface(self.SIZE, pygame.SRCALPHA, 32)
            self.segments[4].stop()

            if usingNumpy():
                self.segments[5].start()

                # RGB values
                # Cancels out white light
                self.cGrid -= self.cGrid.min(axis=2)[:, :, None]
                self.segments[5].stop()

                self.segments[6].start()
                # Sets RGB to be 255 at most
                colourSurfArray = pygame.surfarray.pixels3d(colourLightingSurface)
                # Sets value without erasing link with surfarray
                colourSurfArray[:, :, :] = np.where(self.cGrid.max(axis=2)[:, :, None] > 255,
                                                    self.cGrid * 255 /
                                                    self.cGrid.max(axis=2)[:, :, None],
                                                    self.cGrid)

                del colourSurfArray
                self.segments[6].stop()

                self.segments[7].start()
                # Alpha values for colours
                Colour_alphaArray = pygame.surfarray.pixels_alpha(colourLightingSurface)
                Colour_alphaArray[:, :] = np.clip(
                    255 - Monochromatic_alphaArray, 0, MAX_COLOUR_ALPHA)
                del Colour_alphaArray
                self.segments[7].stop()

            else:
                pixArray = pygame.PixelArray(colourLightingSurface)

        if not usingNumpy():
            for x in range(LIGHT_GRID_LENGTH):
                for y in range(LIGHT_GRID_WIDTH):
                    monochromaticShade = (255 - self.grid[x][y]) * baseShade

                    if monochromaticShade < 0:
                        monochromaticShade = 0

                    elif monochromaticShade > 255:
                        monochromaticShade = 255

                    tileAlpha = round(monochromaticShade)

                    if np is not None:
                        # If numpy is installed, the alpha value would not
                        # be an integer but a numpy variable
                        tileAlpha = int(tileAlpha)

                    if (lightingOption == 'Colour' and
                            not monochromaticColour(self.cGrid[x][y])):

                        colourTileAlpha = self.grid[x][y] * baseShade

                        if colourTileAlpha < 0:
                            colourTileAlpha = 0

                        elif colourTileAlpha > MAX_COLOUR_ALPHA:
                            colourTileAlpha = MAX_COLOUR_ALPHA

                        redValue, greenValue, blueValue = self.cGrid[x][y]

                        # Cancels out white light
                        if min(self.cGrid[x][y]) > 0:
                            minValue = min(self.cGrid[x][y])
                            redValue -= minValue
                            greenValue -= minValue
                            blueValue -= minValue

                        # Lowers RGB to be 255 at most
                        if max(self.cGrid[x][y]) > 255:
                            scaleFactor = 255 / max(self.cGrid[x][y])
                            redValue *= scaleFactor
                            greenValue *= scaleFactor
                            blueValue *= scaleFactor

                        redValue = round(redValue)
                        greenValue = round(greenValue)
                        blueValue = round(blueValue)

                        # Sets pixel on scaled down colourSurface
                        pixArray[x][y] = (redValue, greenValue, blueValue,
                                          colourTileAlpha)

                    self.grid[x][y] = 0
                    self.cGrid[x][y] = [0, 0, 0]

                    # Change opacity of black
                    lightingSurfaceAlpha[x][y] = (0, 0, 0, tileAlpha)

        self.segments[8].start()
        del lightingSurfaceAlpha

        if usingNumpy():
            # Reset light grid after displaying it
            self.grid = np.zeros_like(self.grid)
            self.cGrid = np.zeros_like(self.cGrid)

        else:
            if lightingOption == 'Colour':
                del pixArray

        assert not lightingSurface.get_locked()
        assert not colourLightingSurface.get_locked()
        self.segments[8].stop()

        self.segments[9].start()
        surf = pygame.transform.smoothscale(lightingSurface,
                                            INTERNAL_SIZE)
        self.segments[9].stop()
        self.segments[10].start()
        windowSurface.blit(surf, (0, 0))
        self.segments[10].stop()

        # Upscale and display the surface with colours
        if lightingOption == 'Colour':
            self.segments[11].start()
            surf = pygame.transform.smoothscale(colourLightingSurface,
                                                INTERNAL_SIZE)
            self.segments[11].stop()
            self.segments[12].start()
            windowSurface.blit(surf, (0, 0))
            self.segments[12].stop()


lighting = Lighting()


def dist(x1, x2, y1, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def playerPastDistance(player, distanceFromScreen):  # Returns boolean
    return ((player.direction == 'Left' and
             player.rect.centerx < distanceFromScreen) or

            (player.direction == 'Right' and
             player.rect.centerx > distanceFromScreen))


def monochromaticColour(colour):
    if colour[0] == colour[1] == colour[2]:
        return True

    return False


def get_time_phase(timeTick):
    if timeTick < SUNRISE_END:
        timePhase = 'Sunrise'

    elif timeTick < SUNSET_START:
        timePhase = 'Day'

    elif timeTick < SUNSET_END:
        timePhase = 'Sunset'

    else:
        # The rest of the 24hr day, can't be DAY_LENGTH because it is subtracted beforehand
        assert timeTick < DAY_LENGTH
        timePhase = 'Night'

    return timePhase


def get_level_brightness(timeTick, timePhase):
    NIGHT_BRIGHTNESS = 80

    if timePhase == 'Day':
        levelDarkness = 0

    elif timePhase == 'Sunset':
        delta = (timeTick - SUNSET_START) / SUNRISE_LENGTH
        levelDarkness = delta * NIGHT_BRIGHTNESS

    elif timePhase == 'Night':
        levelDarkness = NIGHT_BRIGHTNESS

    elif timePhase == 'Sunrise':
        delta = (timeTick - SUNRISE_START) / SUNRISE_LENGTH
        levelDarkness = (1 - delta) * NIGHT_BRIGHTNESS

    return levelDarkness

# Given the leftBounds, reflect by vertical axis through the middle of
# the map to find rightBounds for symmetrical bounds


def getCentralBounds(leftBounds):
    rightBounds = INTERNAL_WIDTH // BLOCK_SIZE - leftBounds

    randomShift = random.randint(-2, 2)
    leftBounds += randomShift
    rightBounds += randomShift

    return leftBounds, rightBounds


def collapseArea(leftBounds, rightBounds, topBounds, bottomBounds):
    newEntities = entities
    for x in range(leftBounds, rightBounds):
        for y in range(topBounds, bottomBounds):
            blockType = blockGrid[x][y]['Type']
            if blockType == 'Air':
                continue

            # Replace blocks with falling blocks
            newEntities.append(FallingBlock(x, y, blockGrid[x][y]))

            blockGrid[x][y] = {'Type': 'Air'}

    return newEntities, blockGrid


def quitGame():
    optionFile = shelve.open('options')
    (playerInfoMenu.maximized, inventoryMenu.maximized,
     NPC_TradingMenu.maximized) = optionFile['Menu Maximized']
    optionFile.close()

    if inGame:
        saveGame(librarySave=False)

    pygame.quit()
    sys.exit()


def loadCachedMap(map):
    blockGrid = map['Map']
    mapData = map['mapData']

    return blockGrid, mapData

# TODO: Rewrite cached maps system
# Cached maps don't send entities, rely on UDP to sync them ASAP


def sendCachedMap():
    cachedMap = {}
    cachedMap['Location'] = players[PK()].location
    cachedMap['Direction'] = players[PK()].direction
    cachedMap['Cave Depth'] = players[PK()].caveDepth
    cachedMap['Cave Type'] = players[PK()].caveType
    cachedMap['Previous Location'] = players[PK()].previousLocation

    cachedMap['Map'] = blockGrid
    cachedMap['mapData'] = mapData
    cachedMap['time'] = time.time()

    return cachedMap


def drawHealthBar(entityRect, entityHealth, maxEntityHealth):
    HEALTH_BAR_WIDTH = 100

    greyBarRect = pygame.Rect(entityRect.centerx - 50, entityRect.top - 20,
                              HEALTH_BAR_WIDTH, 10)
    pygame.draw.rect(windowSurface, GREY, greyBarRect)

    if entityHealth > 0:
        healthBarRect = pygame.Rect(entityRect.centerx - 50,
                                    entityRect.top - 20,
                                    HEALTH_BAR_WIDTH * entityHealth / maxEntityHealth,
                                    10)

        pygame.draw.rect(windowSurface, RED, healthBarRect)

    return greyBarRect


def enterNewLocation(player):
    speechBubbles = []
    NPC_Trading['Visible'] = False

    loadScreenOnce = False

    player.health = round(player.health + 5)
    if player.health > player.maxHealth:
        player.health = player.maxHealth

    # Music, change if different location but not if entering or leaving guard post unless going into town
    if (player.location != player.previousLocation and not
        (player.location == GUARD_POST or
         (player.previousLocation == GUARD_POST
          and player.location in TOWNS))):

        soundMixer.music.stop()  # Reshuffles music automatically because of MUSIC_END

    changingLocation = True

    return (speechBubbles, NPC_Trading['Visible'],
            loadScreenOnce, player, changingLocation)


def enterCave(player):
    player.setLocation('Cave')

    (newAmbientSounds, blockGrid, mapData, backgroundBlocks,
     entities, caveBackground, chatText) = generateCave(player)

    return (player, newAmbientSounds, blockGrid, mapData,
            backgroundBlocks, entities, consoleText, caveBackground,
            chatText)

# Add if statement on whether to run finishCave outside of this function if possible


def incrementCave(player, single_pl_Info, mapData):
    townDestination = None
    newChatText = chatText

    # Default for cave environments
    mapData['caveEnvData'] = {'Complete': False}

    # Make local copy of variables so function works if finishCave() is not run
    (newMarketBaseValue, newStocks,
     ) = (marketBaseValue, stocks)

    # Finished cave or will be forced to leave if depth is incremented
    if leaveCave is not None or player.caveDepth + 1 == caveSize:
        if player.caveDepth + 1 == caveSize:
            if player.direction == 'Left':
                townDestination = LEFT_MAP[player.previousTown]

            elif player.direction == 'Right':
                townDestination = RIGHT_MAP[player.previousTown]

        else:  # Player died
            townDestination = player.previousTown

        (player, ambientSounds, blockGrid,
         mapData, backgroundBlocks, entities, consoleText,
         caveBackground) = loadTown(townDestination, player, single_pl_Info)

        # Only if player completes cave
        if player.caveDepth + 1 == caveSize:
            (single_pl_Info, newMarketBaseValue,
             consoleText, newStocks) = finishCave(player,
                                                  single_pl_Info)

        # Reset data since it's no longer needed in case cave is finished
        player, mapData = resetCaveData(player, mapData)

    else:  # Not finished going through cave, make new level
        (player, ambientSounds,
         blockGrid, mapData, backgroundBlocks, entities, consoleText,
         caveBackground, newChatText) = enterCave(player)

        player.caveDepth += 1

    return (  # Variables from loading location
        player,
        ambientSounds, blockGrid, mapData, backgroundBlocks,
        entities, consoleText, caveBackground, newChatText,

        # Returned only when finishing cave
        single_pl_Info, newMarketBaseValue,
        newStocks
    )


def fillBlocks(blockGrid, block, rect):
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            blockGrid[x][y]['Type'] = block

    return blockGrid


def leftWaterRiver(x):  # Used for environment 9 when stream of lava and water meet
    return randomA_Value * (x - 8) * (x - 15) + 3


def rightLavaRiver(x):  # Used for environment 9 when stream of lava and water meet
    return randomA_Value * (x - 22) * (x - 16) + 3

# Used for cave environment in which lava flows and requires player to use tunnel (6)


def riverFunction(x):
    return randomA_Value * (x - 16) ** 2 + randomHeightOffset

# Used in Abandoned Town - Right


def mountainParabola(x):
    return -0.06 * (x - 16) ** 2 + 21

# Used in Small Town Hills


def smallTownHillsMountain(x):
    return -0.15 * (x - 4) ** 2 + 24


def makeParabola(blockGrid, blockType, equation, fillDirection,
                 bounds=None, boundsDirection=None):
    '''Equations rely on y increasing as one moves up
    While the reverse is true in the game
    '''
    for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
        y = equation(x)

        if y < 0 or y > INTERNAL_HEIGHT // BLOCK_SIZE:
            continue

        adjustedY = INTERNAL_HEIGHT // BLOCK_SIZE - round(y)
        if fillDirection == 'Down':
            verticalRange = range(adjustedY, INTERNAL_HEIGHT // BLOCK_SIZE)

        elif fillDirection == 'Up':
            verticalRange = range(16, adjustedY)

        # This fills in the parabola with the block type
        for blockY in verticalRange:
            blockGrid[x][blockY]['Type'] = blockType

    return blockGrid

# This may be used in the future to replace the map generator's parabolas


def findQuadraticSolutions(a, b, c):
    discriminantSquared = b ** 2 - 4 * a * c

    # If it's a negative number than there are no real solutions
    if discriminantSquared < 0:
        raise ValueError

    discriminant = math.sqrt(discriminantSquared)

    leftBounds = (-b + discriminant) / (2 * a)
    rightBounds = (-b - discriminant) / (2 * a)

    return leftBounds, rightBounds

# Unused


def drawBackgroundBlocks():
    for x in range(INTERNAL_WIDTH // BLOCK_SIZE * 2):
        for y in range(INTERNAL_HEIGHT // BLOCK_SIZE * 2):
            coords = (x * BLOCK_SIZE // 2, y * BLOCK_SIZE // 2)
            # Background layer is made of stone, custom blocks can be added for detail
            if backgroundBlocks[x][y] == 'Stone':
                caveBackground.blit(smallStoneImage, coords)

    caveBackground.blit(GREY_SCREEN, (0, 0))

    return caveBackground


def syncLocation(source, target):
    target.location = source.location
    target.direction = source.direction
    target.caveDepth = source.caveDepth
    target.caveType = source.caveType
    target.previousLocation = source.previousLocation

    return target


def teleportToPlayer(teleportedPlayer, targetPlayer):
    teleportedPlayer = syncLocation(targetPlayer, teleportedPlayer)

    # The rect isn't copied because the players may have
    # different frames with different widths and heights
    teleportedPlayer['Rect'].bottomleft = targetPlayer['Rect'].bottomleft

    return teleportedPlayer


def loadAbandonedTownLeft(player):
    global abandonedTown
    global consoleText  # No text is added
    player.setCityLocation(ABANDONED_TOWN_LEFT)

    # Map generation
    (newAmbientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    # TODO: Look into reducing duplicate code with loadAbandonedTownRight
    # Don't generate abandoned town map if already generated before
    if abandonedTown['Left']['Map'] is None:
        (newAmbientSounds, blockGrid, backgroundBlocks, entities,
         mapData) = generateAbandonedTown()

        # Buildings
        for building in (abandonedBankBuilding, abandonedMarketBuilding):
            for floor in building:
                blockGrid = building[floor].makeBuilding(blockGrid)

        for j in range(2):
            for i in range(7):
                # Make bank ladder
                blockGrid[j + 10][i + 9]['Type'] = 'Ladder'

            for i in range(6):
                # Make market ladder
                blockGrid[j + 24][i + 10]['Type'] = 'Ladder'

        # Make bank chests
        blockGrid[6][10]['Type'] = 'Chest'
        blockGrid[6][10]['Data'] = Chest(6 * BLOCK_SIZE, 10 * BLOCK_SIZE,
                                         gold=random.randint(200, 300))

        blockGrid[5][15]['Type'] = 'Chest'
        blockGrid[5][15]['Data'] = Chest(5 * BLOCK_SIZE, 15 * BLOCK_SIZE,
                                         gold=random.randint(40, 60))

        blockGrid[8][15]['Type'] = 'Chest'
        blockGrid[8][15]['Data'] = Chest(8 * BLOCK_SIZE, 15 * BLOCK_SIZE,
                                         gold=random.randint(70, 130))

        # Make market chests
        blockGrid[22][11]['Type'] = 'Chest'
        blockGrid[22][11]['Data'] = Chest(22 * BLOCK_SIZE, 11 * BLOCK_SIZE,
                                          items=[Sword(swordType='Iron'), ])

        blockGrid[21][15]['Type'] = 'Chest'  # Empty
        blockGrid[21][15]['Data'] = Chest(21 * BLOCK_SIZE, 15 * BLOCK_SIZE)

        blockGrid[27][15]['Type'] = 'Chest'  # Empty
        blockGrid[27][15]['Data'] = Chest(27 * BLOCK_SIZE, 15 * BLOCK_SIZE)

        # Save
        abandonedTown['Left']['Map'] = blockGrid

    else:
        # Revisiting an old abandoned town, game still needs groundY
        height = 8
        mapData['groundY'] = (24 - height) * BLOCK_SIZE

        # Map
        blockGrid = abandonedTown['Left']['Map']

    entities = makeClouds(player, entities)
    entities = spawnEntity(entities, 1, 'Slime', bottomCoord=mapData['groundY'])

    return (player, newAmbientSounds,
            blockGrid, mapData, backgroundBlocks,
            entities, consoleText, caveBackground)


def loadAbandonedTownCentre(player):
    global abandonedTown
    global consoleText  # No text is added
    player.setCityLocation(ABANDONED_TOWN_CENTRE)

    # Map generation
    (newAmbientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    # Don't generate abandoned town map if already generated before
    if abandonedTown['Right']['Map'] is None:
        (newAmbientSounds, blockGrid, backgroundBlocks, entities,
         mapData) = generateAbandonedTown()

        # Save
        abandonedTown['Right']['Map'] = blockGrid

    else:
        # Revisiting an old abandoned town, game still needs groundY
        height = 8
        mapData['groundY'] = (24 - height) * BLOCK_SIZE

        # Map
        blockGrid = abandonedTown['Right']['Map']

    entities = makeClouds(player, entities)
    entities = spawnEntity(entities, 4, 'Slime', bottomCoord=mapData['groundY'])

    return (player, newAmbientSounds, blockGrid, mapData,
            backgroundBlocks, entities, consoleText, caveBackground)


def loadAbandonedTownRight(player):
    global consoleText  # No text is added
    player.setCityLocation(ABANDONED_TOWN_RIGHT)

    (newAmbientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = generateAbandonedTownRight()

    entities = makeClouds(player, entities)
    entities = spawnEntity(entities, 6, 'Slime', bottomCoord=mapData['groundY'])

    return (player, newAmbientSounds,
            blockGrid, mapData, backgroundBlocks,
            entities, consoleText, caveBackground)


def loadOutdoors(player, mapData, ambientSounds):
    player.rect.bottom = mapData['groundY']
    ambientSounds = loadWeatherSounds(ambientSounds)

    return player, ambientSounds


def loadSmallTownHills(player):
    player.setLocation(SMALL_TOWN_HILLS)

    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = outsideMapGenerator(INTERNAL_HEIGHT * 4 / 5)

    blockGrid = makeParabola(blockGrid, 'Stone', smallTownHillsMountain,
                             fillDirection='Down')
    player, ambientSounds = loadOutdoors(player, mapData, ambientSounds)

    return (player, ambientSounds,
            blockGrid, backgroundBlocks, entities, mapData)

# Look into removing abandoned towns and move ambientSounds to outdoor function


def loadTown(town, player, single_pl_Info):
    newConsoleText = consoleText
    if town in OLD_TOWNS:
        consoleIntroText(player, single_pl_Info, town)

    if town in TOWNS:
        (player, ambientSounds, blockGrid,
         backgroundBlocks, entities, mapData,
         newCaveBackground) = TOWNS[town].generate(town, player)

    elif town == ABANDONED_TOWN_LEFT:
        (player, ambientSounds, blockGrid,
         mapData, backgroundBlocks,
         entities, newConsoleText,
         newCaveBackground) = loadAbandonedTownLeft(player)

    elif town == ABANDONED_TOWN_CENTRE:
        (player, ambientSounds, blockGrid,
         mapData, backgroundBlocks,
         entities, newConsoleText,
         newCaveBackground) = loadAbandonedTownCentre(player)

    elif town == ABANDONED_TOWN_RIGHT:
        (player, ambientSounds, blockGrid,
         mapData, backgroundBlocks,
         entities, newConsoleText,
         newCaveBackground) = loadAbandonedTownRight(player)

    else:
        assert False

    player, ambientSounds = loadOutdoors(player, mapData, ambientSounds)

    return (player,
            ambientSounds, blockGrid, mapData, backgroundBlocks,
            entities, newConsoleText, newCaveBackground)


def replaceBlockGrid(originalBlock, newBlock, blockGrid):
    for x in range(len(blockGrid)):
        for y in range(len(blockGrid[x])):
            if blockGrid[x][y]['Type'] == originalBlock:
                blockGrid[x][y]['Type'] = newBlock

    return blockGrid


def makeAshenEarth(blockGrid):
    blockGrid = replaceBlockGrid('Grass', 'Ash Dirt', blockGrid)
    return blockGrid


def loadWeatherSounds(ambientSounds):
    if weather == 'Rain':
        ambientSounds.append(rainSound)

    elif weather == 'Snow':
        ambientSounds.append(snowSound)

    playAmbientSounds(ambientSounds)

    return ambientSounds


def loadGuardPost(player):
    global mapData

    player.setLocation(GUARD_POST)

    # Only difference from town generation is the building
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = outsideMapGenerator(INTERNAL_HEIGHT / 2)

    # Create building interior
    blockGrid = guardBuilding.makeBuilding(blockGrid)

    entities.append(Guard(player, guardType='Keeper', bottomCoord=mapData['groundY']))
    entities.append(Guard(player, guardType='Superior', bottomCoord=mapData['groundY']))

    player, ambientSounds = loadOutdoors(player, mapData, ambientSounds)

    return (player, ambientSounds, blockGrid, mapData, backgroundBlocks,
            entities, consoleText)


def resetInput(player):
    # Prevent unintentional movement when resuming
    player.horizontalControls = None
    player.jumping = False

    heldKey = set()

    return player, heldKey


inGame = False  # Used to display option menus when in game and not in main menu


def pauseGame(player):
    gamemode = 'Paused'
    inGame = True
    loadScreenOnce = False
    pauseBackground = windowSurface.copy()

    # Prevent unintentional movement when resuming, also applies to manual saves
    player, heldKey = resetInput(player)

    return (gamemode, loadScreenOnce, pauseBackground, inGame,
            player, heldKey)


def setGamemode(newGamemode):
    previousGamemode.append(gamemode)  # Set previous gamemode to current gamemode
    loadScreenOnce = False

    return loadScreenOnce, previousGamemode, newGamemode


def clickBackButton():
    playSound(backButtonSound)
    loadScreenOnce = False
    gamemode = previousGamemode[-1]
    del previousGamemode[-1]

    return loadScreenOnce, gamemode, previousGamemode


def displayItemAndTooltip(itemTooltip, item, slot, alpha):
    if mouseover(slot):
        dirtyRects.append(slot)

        if options['tooltips'] and item is not None:
            itemTooltip.initialize(item)

        else:
            itemTooltip.visible = False

    if item is not None:
        drawItem(item, slot, alpha)

    return itemTooltip, dirtyRects


def displayItemSlot(itemTooltip, item, slot, alpha=0, invSpaceImage=inventorySpaceImage):
    assert invSpaceImage.get_size() == inventorySpaceImage.get_size()
    windowSurface.blit(invSpaceImage, slot)

    if mouseover(slot):
        windowSurface.blit(highlightInventoryImage, slot)

    itemTooltip, dirtyRects = displayItemAndTooltip(itemTooltip, item, slot, alpha)

    return dirtyRects, itemTooltip


def displayBigItemSlot(itemTooltip, item, slot, alpha=0):
    windowSurface.blit(bigInventorySpaceImage, slot)

    if mouseover(slot):
        windowSurface.blit(bigHighlightInventoryImage, slot)

    itemTooltip, dirtyRects = displayItemAndTooltip(itemTooltip, item, slot, alpha)

    return dirtyRects, itemTooltip


def update_NPC_TradingLabel(text):
    NPC_Trading['Item Offer Label'] = TextRect(font, text, BLACK, GREY)

    NPC_Trading['Item Offer Label'].rect.centerx = NPC_TradingMenu.mainRect.centerx
    # Center text where 1st row of inventory would be
    NPC_Trading['Item Offer Label'].rect.y = NPC_Trading['Item Offer Rect'].y - 35

    return NPC_Trading


def addTooltipDirtyRects(tooltipRect):
    return pygame.Rect(tooltipRect.left - tooltipRect.height,
                       tooltipRect.y,
                       tooltipRect.width + tooltipRect.width * 2,
                       tooltipRect.height
                       )


def marketSellItem(player, item):
    player.gold += round(item.getValue() * marketBaseValue)
    playSound(pickUpItemSound)
    item = None

    return item, player.gold


def updateWarehouseResults(warehouseInv):
    warehouseSearchResults = []

    for i, item in enumerate(warehouseInv):
        if item is None:
            continue  # Skip if empty box

        itemName = item.getDisplayText()
        if warehouseSearchBox.value.lower() in itemName.lower():
            textSurface = font.render(itemName, True, BLACK)
            warehouseSearchResults.append({'Item': item,
                                           'Text Surface': textSurface,
                                           'Index': i})

            # Stop finding items if eight items are found (fits in menu)
            if len(warehouseSearchResults) == 8:
                break

    return warehouseSearchResults


def buyStock(player, single_pl_Info):
    player.gold -= round(stockMarketBuy.value * stocks[selectedStock].float)
    for i in range(stockMarketBuy.value):
        single_pl_Info['stockInv'].append(selectedStock)

    return player, single_pl_Info, stockMarketBuy


def sellStock(player, single_pl_Info):
    player.gold += round(stockMarketSell.value * stocks[selectedStock].float)
    for i in range(stockMarketSell.value):
        single_pl_Info['stockInv'].remove(selectedStock)

    return player, single_pl_Info, stockMarketSell


def drawRightTriangles(colour, rect):
    pygame.gfxdraw.filled_trigon(windowSurface, rect.left, rect.top,
                                 rect.left, rect.bottom,
                                 rect.left - rect.height,
                                 rect.bottom, colour)

    pygame.gfxdraw.filled_trigon(windowSurface, rect.right, rect.top,
                                 rect.right, rect.bottom,
                                 rect.right + rect.height,
                                 rect.bottom, colour)


def serialize(x, pythonTwoClient):
    # Protocol 2 is used for support with python 2 which is run on android
    if pythonTwoClient or android:  # If sending to android or is running python 2
        pickleProtocol = 2
    else:
        pickleProtocol = 4  # pickle.HIGHEST_PROTOCOL in python 3
    return pickletools.optimize(pickle.dumps(x, protocol=pickleProtocol))


deserialize = pickle.loads


def mouseover(rect):
    if rect.collidepoint(mousePos):
        return True

    else:
        return False


def drawItem(item, rect, alpha=0):
    #print("DEBUG2", type(item))
    if type(item) is str:
        raise Exception(item)
    else:
        image = item.getSurface()

    if alpha != 0:
        # https://stackoverflow.com/questions/12879225/pygame-applying-transparency-to-an-image-with-alpha
        image.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)

    rect = windowSurface.blit(image, (rect.centerx - image.get_width() / 2,
                                      rect.centery - image.get_height() / 2))

    return rect  # Solely used for dirtyRects when item in mouseInventory


def dropItem(mouseInventory, itemPosition):
    entities.append(DroppedItem(mouseInventory, itemPosition))
    mouseInventory = None

    return entities, mouseInventory


def integer_input(input, consoleText):
    try:
        input = int(input)
    except ValueError:
        consoleText.addOutput('Please type an integer!')
    else:
        if input < 1:  # Check if input is less than 0, currently all prompts require values greater than 0
            consoleText.addOutput('Please pick a number greater than 0!')
        else:
            return consoleText, input

    return consoleText,


highlightedBlock = None


def highlightBlock(x, y, colour):
    surface = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
    surface.set_alpha(128)
    surface.fill((colour))

    dirtyRect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
    windowSurface.blit(surface, dirtyRect)

    return dirtyRect


def clickRectList(rects):
    for rect in rects:
        if mouseover(rect):
            return True

    else:
        return False


def createNewSave(saveFolder):
    path = getSaveFile(saveFolder)

    saveFile = shelve.open(path, writeback=True)

    saveFile['players'] = {}
    saveFile['playersInfo'] = {}

    saveFile['players'][LPK] = {}
    saveFile['playersInfo'][LPK] = {}

    saveFile.close()


def saveGame(librarySave):  # If true, then the game is saving a cave for library
    if isClient:
        saveFolder = checkServerSaveDirectory()

    else:
        saveFolder = checkSaveDirectory(worldID, True)

    if librarySave:  # Make the code to checkFolders into a function - similar code in updateCompartmentSeleciton
        path = os.path.join(saveFolder, "caves")
        checkFolder(path)
        path = os.path.join(path, str(len(pl_Info[PK()]['caveAdventures'])))
        checkFolder(path)

        saveFolder = os.path.join(path, str(players[PK()].caveDepth))
        checkFolder(saveFolder)
        createNewSave(saveFolder)

    save_path = getSaveFile(saveFolder)
    saveFile = shelve.open(save_path, writeback=True)

    # Prevents player from moving when save file is resumed
    # This is needed when an autosave takes place
    # Verify that this does not influence the player while playing during autosave
    saveFile['players'] = players
    saveFile['players'][PK()].jumping = False
    saveFile['players'][PK()].horizontalControls = None

    saveFile['pl_Info'] = (pl_Info, consoleText, chatText, blockGrid,
                           backgroundBlocks, mapData)

    saveFile['marketBaseValue'] = marketBaseValue, oldMarketBaseValue
    saveFile['timeTick'] = timeTick
    saveFile['weather'] = weather, weatherDuration
    saveFile['oldCaveData'] = oldCaveData
    saveFile['entities'] = entities

    saveFile['stocks'] = stocks

    saveFile['Cave Info'] = caveSize

    saveFile['undergroundCity'] = undergroundCity
    saveFile['abandonedTown'] = abandonedTown

    saveFile['Speech Bubbles'] = speechBubbles

    # e.g. 'Thursday, January 01, 2015  10:01 PM'
    FORMAT = '%A, %B %d, %Y  %I:%M %p'
    saveFile['Time Last Played'] = datetime.datetime.now().strftime(FORMAT)

    saveFile.close()

    if pauseBackground is None:
        thumbnail = windowSurface.copy()

    else:
        thumbnail = pauseBackground

    if librarySave:
        path = os.path.join(saveFolder, "thumbnail.png")
        pygame.image.save(thumbnail, path)

    else:  # Don't create default thumbnail if a library save
        path = os.path.join("saves", "thumbnails")
        checkFolder(path)

        path = os.path.join(path, str(worldID) + '.png')
        pygame.image.save(thumbnail, path)


def killSocket(TCP_STREAM, UDP_STREAM):
    TCP_STREAM.shutdown(socket.SHUT_RDWR)
    TCP_STREAM.close()

    UDP_STREAM.shutdown(socket.SHUT_RDWR)
    UDP_STREAM.close()
    return TCP_STREAM, UDP_STREAM


def clickedBlock():
    x, y = mousePos

    return {'Type': blockGrid[x // BLOCK_SIZE][y // BLOCK_SIZE]['Type'],
            'x': x // BLOCK_SIZE,
            'y': y // BLOCK_SIZE}


def drawPlayerLabel(player, surfaceRect):
    surfaceRect.centerx = player.rect.centerx
    surfaceRect.bottom = player.rect.top - 10

    PADDING = 3
    surfaceRect.left = max(surfaceRect.left, PADDING)
    surfaceRect.right = min(surfaceRect.right, INTERNAL_WIDTH - PADDING)

    return surfaceRect


def createOtherPlayerFile(otherPlayerName):
    # Prevents the server's own "players" variable from being editted
    newOtherPlayers = copy.deepcopy(players)

    # Don't try to remove player data the client won't see if client info is unknown
    if otherPlayerName in newOtherPlayers:
        # .copy() is used because variable can't be changed while being iterated over
        for name in newOtherPlayers.copy():
            if not sameLocation(newOtherPlayers[otherPlayerName], newOtherPlayers[name]):
                del newOtherPlayers[name]

    return newOtherPlayers


def findPlayerInfo(playerName):
    saveFolder = checkSaveDirectory(worldID, True)
    path = getSaveFile(saveFolder)
    saveFile = shelve.open(path, writeback=True)

    # Creates other players key if it does not exist
    if 'Other Players' not in saveFile:
        saveFile['Other Players'] = {'Names': [], 'Data': []}

    if playerName in saveFile['Other Players']['Names']:
        playerData = saveFile['Other Players']['Data'][playerName]

    else:
        playerData = Player(mapData['groundY'])

    saveFile.close()
    return playerData


killThread = False

# Sound Ids for playing sounds with networking
pickUpGoldString = 0
pickUpItemString = 1

# Universal networking variables


def createNetworkingStreams():
    # TCP_STREAM = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM),
    #                             ca_certs='cert/server.crt')
    TCP_STREAM = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    TCP_STREAM.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    UDP_STREAM = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        TCP_STREAM.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
    except PermissionError:
        print('Could not enable TCP_NODELAY')

    return TCP_STREAM, UDP_STREAM


SEND_BROADCAST_STREAM = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SEND_BROADCAST_STREAM.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
SEND_BROADCAST_STREAM.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

serverOn = False
isClient = False
serverName = None

scanServerTimeout = 5
timeScanningServers = 0

playersLock = threading.Lock()
pl_Info = {}  # pl_Info -> playersInfo
pl_Info_Lock = threading.Lock()

LAN_ServerList = {}
LAN_ServerListLock = threading.Lock()

# Variables to show server list
LAN_ServerListX = 100
LAN_ServerListY = 100
LAN_ServerListDimensions = pygame.Rect(0, 0, INTERNAL_WIDTH - 200, 150)

# Server variables
serverMapCache = {}  # Stores the maps of all players in real time (every 10 seconds)
serverMapCacheLock = threading.Lock()

TCP_ServerBuffer = {}
TCP_ServerBufferLock = threading.Lock()

# This is kept like the map cache so that the server can download all the
# client's entities if they're in the same map and take over all the physics
otherPlayerEntities = {}
otherPlayerEntitiesLock = threading.Lock()

# Client variables
clientMapCache = []  # Only stores 2 maps from left and right of player, server sends client these maps
clientMapCacheLock = threading.Lock()

TCP_ClientBuffer = []
TCP_ClientBufferLock = threading.Lock()

disconnectClient = False
clientNetworkingThreads = []

# This is populated with player keys when running a server,
# setting the key to true disconnects the client
disconnectServerLock = threading.Lock()
disconnectServer = {}


def tryDisconnectClient():
    pauseButtons['Quit Game'].changeText('Save and Quit',
                                         menuFont)

    gamemode = 'Multiplayer Menu'

    # Send TCP disconnect message
    disconnectClient = True
    # Disable receives so that the threads don't get stuck waiting for server
    # But allow sends so server can be notified
    TCP_STREAM.shutdown(socket.SHUT_RD)
    UDP_STREAM.shutdown(socket.SHUT_RD)

    return pauseButtons['Quit Game'], gamemode, disconnectClient, TCP_STREAM, UDP_STREAM


def toggleKillthread(networkingThreads, threadType):
    networkingThreads.remove(threadType)
    if len(networkingThreads) == 0:
        # Done killing networking threads when no more are left
        newDisconnectClient = False
        isClient = False

    else:
        newDisconnectClient = disconnectClient
        isClient = True

    print('Killthread -', threadType)

    return newDisconnectClient, networkingThreads, isClient

# http://stupidpythonideas.blogspot.ca/2013/05/sockets-are-byte-streams-not-message.html


def send_one_message(sock, data, pythonTwoClient):
    sentData = serialize(data, pythonTwoClient)

    length = len(sentData)
    try:
        sock.sendall(struct.pack('!I', length))
        sock.sendall(sentData)

    except ConnectionAbortedError:  # Should only trigger if client disconnects
        pass


def get_TCP_Message(conn, disconnectCurrentClient):
    disconnectReason = None
    reply = ()

    try:
        # Receive from client
        reply = recv_one_message(conn)

    except TypeError:
        # If client has disconnected, a None will be received
        disconnectReason = 'TypeError'
        disconnectCurrentClient = True

    except ConnectionResetError:
        disconnectReason = 'ConnectionResetError'
        disconnectCurrentClient = True

    except ConnectionAbortedError:
        disconnectReason = 'ConnectionAbortedError'
        disconnectCurrentClient = True

    except BrokenPipeError:
        # Client has shutdown socket
        disconnectReason = 'BrokenPipeError'
        disconnectCurrentClient = True

    return reply, disconnectReason, disconnectCurrentClient


def recv_one_message(sock):
    lengthbuf = recvall(sock, 4)
    length, = struct.unpack('!I', lengthbuf)

    data = deserialize(recvall(sock, length))
    return data


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)

    return buf


def splitCommand(chatInput):
    # Get arguments for command
    separatedInput = chatInput.split(' ')

    arguments = separatedInput.copy()
    del arguments[0]  # Delete the initial /(command name)

    command = separatedInput[0]

    assert command.startswith('/')
    command = command[1:]  # Remove the /, by removing first character

    return tuple(arguments), command

# TODO: look into making all commands into classes and use inheritance


class Command:
    def __init__(self):
        pass

    def sayInvalidNumber(self):
        return ()


class ItemCommandClass(Command):
    def call(self, arguments, targetPlayer):
        if len(arguments) == 0:
            output = ('Invalid number of arguments. 2 were expected.',
                      'e.g. /i torch 10')

        elif arguments[0]:
            output = ('Invalid item argument, first argument must be an item.',)

        elif len(arguments) == 1:
            targetPlayer, dirtyRects = appendPlayerInventory(Item(arguments[0]),
                                                             player=targetPlayer,
                                                             returnDirtyRects=True)
            output('Added ' + arguments[0] + ' to inventory.',)
            playSound(pickUpItemSound)

        elif len(arguments) == 2:
            try:
                quantity = int(arguments[1])

            except ValueError:
                output = ('Invalid number argument, second argument must be a number.',)

            else:
                for i in range(quantity):
                    targetPlayer, dirtyRects = appendPlayerInventory(Item(arguments[0]),
                                                                     player=targetPlayer,
                                                                     returnDirtyRects=True)

                output = ('Added ' + arguments[0] + ' to inventory ' + str(quantity) + ' times.',)
                playSound(pickUpItemSound)

        return output, targetPlayer, dirtyRects


itemCommand = ItemCommandClass()


def tpto(arguments, targetPlayer):
    if len(arguments) != 1:
        output = ('Invalid number of arguments. 1 was expected.',)

    elif arguments[0] in players:
        otherPlayer = players[arguments[0]]
        targetPlayer = teleportToPlayer(targetPlayer, otherPlayer)
        output = ('Teleported to ' + arguments[0] + '.',)

    else:
        output = ('The other player name (' +
                  arguments[0] + ') was not recognized.',)

    return output, targetPlayer

# UDP functions only receive


def UDP_server(otherPlayerName):
    global players, playersLock
    global otherPlayerEntities, otherPlayerEntitiesLock
    global disconnectServer, disconnectServerLock

    # Only receives data from client
    while not killThread and not disconnectServer[otherPlayerName]:
        try:  # TODO - reduce buffer size and figure out a system for entities in abandoned town
            clientData = deserialize(UDP_STREAM.recv(32768))

        except (ConnectionResetError, OSError):
            # ConnectionResetError - Should only be triggered when client is disconnecting
            # OSError - Should only happen when more data is sent than buffer can handle
            disconnectServerLock.acquire()
            disconnectServer[otherPlayerName] = True
            disconnectServerLock.release()
            break

        playersLock.acquire()
        players[otherPlayerName] = clientData['Player']
        playersLock.release()

        otherPlayerEntitiesLock.acquire()
        otherPlayerEntities[otherPlayerName] = clientData['Entities']
        otherPlayerEntitiesLock.release()


def UDP_client():
    global players, playersLock, entities, entitiesLock  # Synchronizing world
    global clientMapCache, clientMapCacheLock
    global clientNetworkingThreads, disconnectClient, isClient

    global TCP_STREAM, UDP_STREAM, pauseButons, gamemode  # For initiating a disconnect
    clientNetworkingThreads.append('UDP')
    # Only receives data from server

    while not disconnectClient:
        try:
            serverData = deserialize(UDP_STREAM.recv(32768))
        except OSError:
            (pauseButtons['Quit Game'], gamemode, disconnectClient,
             TCP_STREAM, UDP_STREAM) = tryDisconnectClient()

        playersLock.acquire()
        local = copy.deepcopy(players[PK()])
        players = serverData['Players']
        players[PK()] = local
        playersLock.release()

        # Don't synchronize guards
        if 'Entities' in serverData and players[PK()].location != GUARD_POST:
            entitiesLock.acquire()
            entities = serverData['Entities']
            entitiesLock.release()

    UDP_STREAM.shutdown(socket.SHUT_RDWR)
    UDP_STREAM.close()
    (disconnectClient, clientNetworkingThreads,
     isClient) = toggleKillthread(clientNetworkingThreads, 'UDP')
    print('Ending UDP Client')


scanningServers = False


def UDP_Broadcast():
    global LAN_ServerList, LAN_ServerListLock
    global RECV_BROADCAST_STREAM  # For using shutdown on main loop
    global scanningServers
    print('Start searching.')
    scanningServers = True

    RECV_BROADCAST_STREAM = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    RECV_BROADCAST_STREAM.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    RECV_BROADCAST_STREAM.bind((HOST_IP, BROADCAST_PORT))

    while scanningServers:
        # TODO add a 0.5 second timeout
        serverData = deserialize(RECV_BROADCAST_STREAM.recv(8192))

        # TODO: Have the server broadcast number of players
        IP_Address = serverData[0]

        LAN_ServerListLock.acquire()
        if IP_Address not in LAN_ServerList:
            LAN_ServerList[IP_Address] = {'playersOnline': 0}
            LAN_ServerList[IP_Address]['TextRect'] = TextRect(
                l_menuFont, IP_Address, WHITE, DARK_GREY)
            print('New Server -', IP_Address)
            serverList = addServer('Autodetected Server', IP_Address)

        LAN_ServerListLock.release()

    scanningServers = False
    RECV_BROADCAST_STREAM.shutdown(socket.SHUT_RDWR)
    print('Stopped searching.')


'''
The exchange of data in the TCP_ServerBuffer serves a secondary purpose
of functioning as a way to check if the connection is ever broken.
In the future, make it so that if no TCP_Buffer is received in
a certain number of seconds, the connection is closed. End of stream.
'''


def disconnectNewPlayer(message, conn, addr, pythonTwoClient):
    send_one_message(conn, {'Disconnect': {'Message': message}}, pythonTwoClient)
    print('Disconnected Player at', addr)


def TCP_server():
    global killThread, TCP_STREAM, UDP_STREAM, TCP_ServerBuffer, TCP_ServerBufferLock, playerToIP
    global entities, blockGrid  # To send variable to client and synchronize server with client actions
    global players, playersLock
    global serverMapCache, serverMapCacheLock
    global disconnectServerLock, disconnectServer
    global pl_Info, pl_Info_Lock, chatText
    conn, addr = TCP_STREAM.accept()
    print('Connected by', addr)

    otherPlayerName, pythonTwoClient = recv_one_message(conn)
    print('otherPlayerName', otherPlayerName)

    if otherPlayerName in players:
        disconnectNewPlayer('Username already taken.', conn, addr, pythonTwoClient)
        threading.Thread(target=TCP_server).start()  # Get ready for another client
        return

    elif otherPlayerName == LPK:
        disconnectNewPlayer('Invalid username. Name must have at least one character.',
                            conn, addr, pythonTwoClient)
        threading.Thread(target=TCP_server).start()  # Get ready for another client
        return

    else:
        send_one_message(conn, {'Client IP': addr}, pythonTwoClient)
        playerToIP[otherPlayerName] = addr
        print(otherPlayerName, 'entered the game.')
        chatText.addOutput(otherPlayerName + ' entered the game.')

    # Send information to create world and initialize world
    (pl_Info[otherPlayerName], consoleText,
     localChatText) = createPlayerData()  # TODO: Load this from playersInfo

    playersLock.acquire()
    players[otherPlayerName] = findPlayerInfo(otherPlayerName)

    message = (pl_Info[otherPlayerName], weatherDuration, weather,
               createOtherPlayerFile(otherPlayerName), timeTick, blockGrid,
               backgroundBlocks, marketBaseValue, oldMarketBaseValue, caveSize,
               mapData, consoleText, localChatText,
               speechBubbles, oldCaveData, abandonedTown
               # Make oldCaveData player specific later
               )
    playersLock.release()

    print(str(message))
    send_one_message(conn, message, pythonTwoClient)

    message = (stocks,
               undergroundCity, entities,
               options['playerName']
               )

    send_one_message(conn, message, pythonTwoClient)

    disconnectServerLock.acquire()
    disconnectServer[otherPlayerName] = False
    disconnectServerLock.release()

    threading.Thread(target=TCP_server).start()  # Get ready for another client
    threading.Thread(target=UDP_server, args=(otherPlayerName,)).start()

    TCP_ServerBufferLock.acquire()
    TCP_ServerBuffer[otherPlayerName] = []
    TCP_ServerBufferLock.release()

    threadClock = pygame.time.Clock()
    while not killThread and not disconnectServer[otherPlayerName]:
        disconnectCurrentClient = False

        (reply, disconnectReason,
         disconnectCurrentClient) = get_TCP_Message(conn, disconnectCurrentClient)

        if disconnectCurrentClient:
            disconnectServerLock.acquire()
            disconnectServer[otherPlayerName] = True
            disconnectServerLock.release()

        for clientInfo in reply:
            if clientInfo['Type'] == 'Disconnect':
                disconnectReason = 'Client Quit'
                disconnectCurrentClient = True

            elif clientInfo['Type'] == 'Drop Item':
                # Trust the client to get rid of item
                # dropItem normally returns entities and empty mouse inventory
                entities = dropItem(clientInfo['Item'],
                                    clientInfo['Position'])[0]

            elif clientInfo['Type'] == 'Chat':
                # Send message to other clients
                chatText.broadcast(otherPlayerName + ': ' + clientInfo['Text'])

                if clientInfo['Text'].startswith('/'):
                    arguments, command = splitCommand(clientInfo['Text'])

                    if command == 'tpto':
                        playersLock.acquire()
                        output, players[otherPlayerName] = tpto(arguments, players[otherPlayerName])
                        playersLock.release()

                        TCP_ServerBufferLock.acquire()
                        for text in output:
                            TCP_ServerBuffer[otherPlayerName].append({'Type': 'Chat',
                                                                      'Text': text})
                        TCP_ServerBufferLock.release()

            elif clientInfo['Type'] == 'Map Cache':
                print('Received cache!')
                serverMapCacheLock.acquire()
                serverMapCache[otherPlayerName] = clientInfo['Map']
                serverMapCacheLock.release()

        TCP_ServerBufferLock.acquire()
        try:
            send_one_message(conn, TCP_ServerBuffer[otherPlayerName], pythonTwoClient)
        except ConnectionResetError:
            # Should only be triggered when client has disconnected
            disconnectCurrentClient = True
            disconnectReason = 'ConnectionResetError'
        else:
            TCP_ServerBuffer[otherPlayerName] = []

        TCP_ServerBufferLock.release()

        threadClock.tick()

    # Delete player data
    playersLock.acquire()
    try:
        del players[otherPlayerName]
    except KeyError:
        print(str(players))

    playersLock.release()

    pass  # TODO: Save player data

    TCP_ServerBufferLock.acquire()
    del TCP_ServerBuffer[otherPlayerName]
    TCP_ServerBufferLock.release()

    chatText.addOutput(otherPlayerName + ' disconnected.')

    print(otherPlayerName, 'disconnected.')
    if disconnectReason is None:
        disconnectReason = 'Unspecified Error'
    print('Reason -', disconnectReason)


'''
TODO: Break up the TCP client and server functions into a part that tries to connect
another part that gives all the initial data
and the last part which continually streams data until disconnected

'''


def TCP_client():
    global players, pl_Info, disconnectMessage, clientNetworkingThreads
    global TCP_STREAM, UDP_STREAM, serverName
    # Initialization variables
    global weatherDuration, weather, backgroundBlocks, marketBaseValue
    global caveSize, mapData, consoleText
    global chatText, undergroundCity
    global currentMusic, playerInfo, oldMarketBaseValue
    global stocks, entities
    global timeTick, speechBubbles, oldCaveData, abandonedTown
    # For changing gamemode once variables are loaded
    global gamemode

    global blockGrid
    global isClient, disconnectClient, clientNetworkingThreads  # For early disconnects

    clientNetworkingThreads.append('TCP')

    try:
        TCP_STREAM.connect((serverIP, MAIN_PORT))

    except ConnectionRefusedError:
        disconnectMessage['Text'] = 'Connection refused. Server not on?'
        return

    send_one_message(TCP_STREAM, (options['playerName'], USING_PYTHON_TWO), True)

    reply = recv_one_message(TCP_STREAM)

    if 'Client IP' in reply:
        clientIP = reply['Client IP']
        UDP_STREAM.bind(clientIP)
        print('Handshake!')

    elif 'Disconnect' in reply:
        # Disconnect client with reply['Message']
        disconnectMessage['Text'] = reply['Disconnect']['Message']
        (isClient, disconnectClient, clientNetworkingThreads,
         TCP_STREAM) = TCP_DisconnectClient(clientNetworkingThreads)
        return

    # Initialize world, similar to loading world code - Split in two
    recv1 = recv_one_message(TCP_STREAM)
    (pl_Info[PK()], weatherDuration, weather, players, timeTick,
     blockGrid, backgroundBlocks, marketBaseValue, oldMarketBaseValue,
     caveSize, mapData, consoleText, chatText,
     speechBubbles, oldCaveData, abandonedTown) = recv1

    recv2 = recv_one_message(TCP_STREAM)
    (stocks,
     undergroundCity, entities,
     serverName) = recv2

    currentMusic, playerInfo = initializeWorld()

    disconnectClient = False

    print('Finished initializing.')

    gamemode = 'Play'

    threading.Thread(target=UDP_client).start()
    threading.Thread(target=TCP_client_sync).start()


def TCP_client_sync():
    global disconnectClient, killThread, isClient
    global TCP_ClientBufferLock, TCP_ClientBuffer, TCP_STREAM, UDP_STREAM, clientNetworkingThreads
    global chatText, chatTextLock
    global timeTick, weather, weatherDuration
    global clientMapCacheLock, clientMapCache

    tempVariable_ServerUsingPythonTwo = True

    # This uses a while True and breaks manually to ensure that server is notified
    # when the client disconnects
    while True:
        # Send to server
        #print('Code 0')
        if disconnectClient:
            # Server will check if key exists
            TCP_ClientBufferLock.acquire()
            TCP_ClientBuffer.append({'Type': 'Disconnect'})
            TCP_ClientBufferLock.release()
            print('Sending disconnect message.')

        #print('Code 1')
        TCP_ClientBufferLock.acquire()
        send_one_message(TCP_STREAM, tuple(TCP_ClientBuffer), tempVariable_ServerUsingPythonTwo)
        TCP_ClientBuffer = []
        TCP_ClientBufferLock.release()
        #print('Code 2')

        # Only end after sending all required data
        if disconnectClient:
            print('Client - Disconnect')
            break

        # Receive from server
        #print('Code 4')
        (reply, disconnectReason,
         disconnectClient) = get_TCP_Message(TCP_STREAM, disconnectClient)
        #print('Code 5')

        for serverInfo in reply:
            if serverInfo['Type'] == 'Chat':
                # TODO add support for locks
                chatText.addOutput(serverInfo['Text'])

            elif serverInfo['Type'] == 'Weather':
                weather, weatherDuration = serverInfo['Weather']

            elif serverInfo['Type'] == 'timeTick':
                timeTick = serverInfo['timeTick']

            elif serverInfo['Type'] == 'Play Sound':
                if serverInfo['Sound'] == pickUpGoldString:
                    playSound(pickUpGoldSound)

                elif serverInfo['Sound'] == pickUpItemString:
                    playSound(pickUpItemSound)

            elif serverInfo['Type'] == 'Map Cache':
                # Load map cache
                clientMapCacheLock.acquire()
                clientMapCache = serverInfo['Map']
                clientMapCacheLock.release()

    print('Client out of while loop.')
    (isClient, disconnectClient, clientNetworkingThreads,
     TCP_STREAM) = TCP_DisconnectClient(clientNetworkingThreads)


def TCP_DisconnectClient(clientNetworkingThreads):
    # Reset flag
    (disconnectClient, clientNetworkingThreads,
     isClient) = toggleKillthread(clientNetworkingThreads, 'TCP')
    TCP_STREAM.shutdown(socket.SHUT_RDWR)
    TCP_STREAM.close()

    return isClient, disconnectClient, clientNetworkingThreads, TCP_STREAM


def pressEscape(event):
    return event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE


def leftClick(event):
    return (event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 1)


def rightClick(event):
    return (event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 3)


def scrollUp(event):
    return (event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 4)


def scrollDown(event):
    return (event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 5)


def playerNearTown(player, desiredTown):
    if (player.location == desiredTown or
            player.location == GUARD_POST and player.previousTown == desiredTown):

        return True

    return False


def playerNearTowns(player, desiredTowns):
    if (player.location in desiredTowns or
            player.location == GUARD_POST and player.previousTown in desiredTowns):

        return True

    return False


def sameLocation(player1, player2):
    # Same location
    if player1.location != player2.location:
        return False

    # Guard post but different posts
    elif (player1.location == GUARD_POST and player2.location == GUARD_POST
          and (player1.previousLocation != player2.previousLocation or
               player1.direction != player2.direction)):
        return False

    #Both in cave, difference in type or depth
    elif (player1.location == 'Cave' and player2.location == 'Cave' and
          (player1.caveType != player2.caveType or
           player1.caveDepth != player2.caveDepth)):
        return False

    else:
        return True


def sameMapLocation(map):
    player1 = players[PK()]

    # Same location
    if player1.location != map['Location']:
        return False

    # Guard post but different posts
    elif (player1.location == GUARD_POST and map['Location'] == GUARD_POST
          and (player1.previousLocation != map['Previous Location'] or
               player1.direction != map['Direction'])):
        return False

    #Both in cave, difference in type or depth
    elif (player1.location == 'Cave' and map['Location'] == 'Cave' and
          (player1.caveType != map['Cave Type'] or
           player1.caveDepth != map['Cave Depth'])):
        return False

    else:
        return True


class ScrollingField:
    def __init__(self):
        self.lines = []  # Takes dicts with Text and Type keys
        self.upArrowCount = 0

        self.field = self.getTextField()
        self.field.changingField = True

    def addText(self, string, mode):
        self.lines.append({'Text': string,
                           'Type': mode,
                           'Time': time.time()})

        self.upArrowCount = 0

        # Scroll
        while len(self.lines) > self.maxLines:
            del self.lines[0]

    def addInput(self):
        if self.field.value != '':
            self.addText(self.field.value, 'Input')
            self.field.setValue('')

    def addOutput(self, string):
        self.addText(string, 'Output')

    def getTextField(self):
        return TextField('', "font", 128)

    def keydown(self):
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            if event.key == pygame.K_UP:
                self.upArrowCount += 1

            elif event.key == pygame.K_DOWN and self.upArrowCount > 0:
                self.upArrowCount -= 1

            i = self.upArrowCount

            for line in reversed(self.lines):
                text, type = line['Text'], line['Type']

                if type == 'Input' and text != '':
                    i -= 1

                    if i == 0:
                        self.field.setValue(text)
                        break

        else:
            self.field.typeText()

    def getTimeLastMessage(self):
        assert len(self.lines) > 0
        return self.lines[-1]['Time']


class ConsoleField(ScrollingField):
    def __init__(self):
        super().__init__()
        self.rowHeight = 12
        self.maxLines = 63 - 1  # Subtract by 1 for room for the text field

    def addText(self, string, mode):
        ScrollingField.addText(self, string, mode)
        print(string)

    def draw(self):
        for i, line in enumerate(self.lines):
            drawWrappedText(windowSurface, line['Text'], CONSOLE_GREY,
                            pygame.Rect(0, i * self.rowHeight,
                                        INTERNAL_WIDTH,
                                        INTERNAL_HEIGHT - i * self.rowHeight),
                            CONSOLE_FONT, BLACK)

        self.field.rect.top = (i + 1) * self.rowHeight
        self.field.draw()

    def getTextField(self):
        return ConsoleTextField('', "consoleFont", 128)


class ConsoleTextField(TextField):
    def getSurface(self):
        return self.font.render(self.createText(), True, CONSOLE_GREY, BLACK)


class ChatField(ScrollingField):
    def __init__(self):
        super(ChatField, self).__init__()
        self.rowHeight = 25

        self.backRect = pygame.Rect(0, 0, INTERNAL_WIDTH, 30)
        self.backRect.bottom = INTERNAL_HEIGHT

        self.maxLines = mathFloor((INTERNAL_HEIGHT - self.backRect.height) /
                                  self.rowHeight) - 1
        self.field.rect.bottomleft = 0, INTERNAL_HEIGHT

    def addText(self, string, mode):
        ScrollingField.addText(self, string, mode)

    def broadcast(self, message):
        global TCP_ServerBufferLock, TCP_ServerBuffer

        # Send to all clients
        TCP_ServerBufferLock.acquire()
        for i in TCP_ServerBuffer:
            TCP_ServerBuffer[i].append({'Type': 'Chat',
                                        'Text': message})
        TCP_ServerBufferLock.release()

        # Return message to self
        self.addOutput(message)

    def draw(self):
        # TODO: Make the bottom of the text area be the bottom of the screen by
        # drawing the last text in the array first starting at the bottom and moving up
        for i, line in enumerate(self.lines):
            text = line['Text']
            color = {'Input': CONSOLE_GREY,
                     'Output': WHITE}[line['Type']]

            # TODO: Compensate for lines being more than one
            # line long by refactoring drawWrappedText
            drawWrappedText(windowSurface, text, color,
                            pygame.Rect(0, i * self.rowHeight,
                                        INTERNAL_WIDTH,
                                        INTERNAL_HEIGHT - i * self.rowHeight),
                            chatFont)

        pygame.draw.rect(windowSurface, DARK_GREY, self.backRect)
        self.field.draw()


def createPlayerData():
    consoleText = ConsoleField()
    chatText = ChatField()

    # Intro
    for text in ("   _____                            ______                  _                                         ",
                 "  / ____|                          |  ____|                | |                                        ",
                 " | |        __ _  __   __   ___    | |__    __  __  _ __   | |   ___    _ __    ___   _ __    *Alpha* ",
                 " | |       / _` | \ \ / /  / _ \   |  __|   \ \/ / | '_ \  | |  / _ \  | '__|  / _ \ | '__|           ",
                 " | |____  | (_| |  \ V /  |  __/   | |____   >  <  | |_) | | | | (_) | | |    |  __/ | |              ",
                 "  \_____|  \__,_|   \_/    \___|   |______| /_/\_\ | .__/  |_|  \___/  |_|     \___| |_|              ",
                 "                                                   | |                                                ",
                 "                                                   |_|                                     ",
                 "             By Kevin Bacabac                         Pre-Alpha Version",
                 ""):

        consoleText.addOutput(text)

    for text in ('You are an explorer and currently have about ' + str(players[PK()].gold) + ' gold.',
                 'To get more gold you have set your eyes on 3 caves which could make you wealthy or get you killed.',
                 'It is said that one of the caves is very small, the other very large, and the last one is dangerous but has vast sums of gold.',
                 'If you die you will lose some gold but you can try again until you lose all your gold.'):

        consoleText.addOutput(text)
        chatText.addOutput(text)

    oldBankBalance = []
    for i in range(bankGraph.linesOfHeight):
        oldBankBalance.append(0)

    stockInv = []
    warehouseInv = warehouseInvGUI.makeInventoryList()

    forgeInv = {'Input': [], 'Output': [], 'Progress': [], 'Started': []}
    for i in range(FORGE_INVENTORY_NUMBER):
        forgeInv['Progress'].append(0)
        forgeInv['Input'].append(None)
        forgeInv['Output'].append(None)
        forgeInv['Started'].append(False)

    requiredItemInventory = []
    for i in range(REQUIRED_ITEMS_BOX_QUANTITY):
        requiredItemInventory.append(None)

    if options['testWorld']:
        # Unlock everything
        availableBlueprints = list(BLUEPRINT.keys())

    else:
        availableBlueprints = ['Iron Pickaxe', 'Fortified Shield', 'Iron Shield']

    pl_Info = {'bankBalance': 0,
               'oldBankBalance': oldBankBalance,
               'warehouseInv': warehouseInv,
               'stockInv': stockInv,
               'forgeInv': forgeInv,
               'availableBlueprints': availableBlueprints,
               'requiredItemInventory': requiredItemInventory,
               'caveAdventures': []
               }

    return pl_Info, consoleText, chatText


class PlayerInfo:
    def __init__(self, prefix, property):
        self.prefix = prefix
        self.property = property
        self.surface = None
        self.value = None

    def getRect(self):
        if self.surface is None:
            return None

        else:
            i = PLAYER_INFO_ORDER.index(self.prefix)

            return pygame.Rect((playerInfoMenu.mainRect.x + 10,
                                playerInfoMenu.mainRect.y + 15 + i * 14),
                               self.surface.get_size())

    def updateSurface(self):
        value = getattr(players[PK()], self.property)

        # Only show rounded numbers
        if isinstance(value, float):
            value = round(value)

        # Change in value
        if value != self.value:
            self.value = value
            self.setText(value)

            if not android:
                textFont = submenuFont

            elif options['phoneMode']:
                textFont = touchScreenFont

            dirtyRects.append(self.getRect())
            self.surface = textFont.render(self.displayText, True, BLACK, GREY)
            dirtyRects.append(self.getRect())

    def setText(self, value):
        self.displayText = self.prefix + ' - ' + str(value)


def initializeWorld():
    # Initial code, starts music which normally only starts when changing location
    currentMusic = pickMusic(players[PK()])
    soundMixer.music.load(currentMusic)

    if options['music']:
        soundMixer.music.play()

    # Player info text boxes
    playerInfo = {}

    for prefix, property in zip(PLAYER_INFO_ORDER,
                                ('gold', 'location', 'caveType', 'caveDepth', 'direction', 'health')):
        playerInfo[prefix] = PlayerInfo(prefix, property)
        playerInfo[prefix].updateSurface()

    return currentMusic, playerInfo


def leaveBuilding():
    playSound(doorSound)
    gamemode = 'Play'
    loadScreenOnce = False
    consoleIntroText(players[PK()], pl_Info[PK()],
                     players[PK()].location)

    return gamemode, loadScreenOnce


def leaveBank():
    depositValue = 0
    withdrawValue = 0

    gamemode, loadScreenOnce = leaveBuilding()

    return depositValue, withdrawValue, gamemode, loadScreenOnce


def leaveMarket(player, buyingItem):
    if buyingItem:
        player.mouseInventory = None

    buyingItem = False
    buyingItemID = None

    gamemode, loadScreenOnce = leaveBuilding()

    return (gamemode, loadScreenOnce,
            buyingItem, buyingItemID, player)


def newMarketValue(oldMarketBaseValue):
    marketBaseValue = random.uniform(0.8, 1.2)
    oldMarketBaseValue.append(marketBaseValue)

    if len(oldMarketBaseValue) > marketGraph.linesOfHeight:  # 15
        del oldMarketBaseValue[0]

    return marketBaseValue, oldMarketBaseValue


def getItemIndex(itemID, inventory):
    for i, item in enumerate(inventory):
        if item is not None and item.id == itemID:
            return i

    else:
        return None


def cleanInventory(inventory):
    inventoryStrings = []

    for item in inventory:
        # Blank slots are represented as None
        if item is not None:
            inventoryStrings.append(item.name)

    exportString = ''
    for itemString in set(inventoryStrings):
        quantity = str(inventoryStrings.count(itemString))
        print(str(quantity))
        if quantity == 1:
            exportString += itemString

        else:
            exportString += quantity + ' ' + itemString + 's'

        exportString += ', '

    # Remove the last ", "
    exportString = exportString[:-2]

    # Find # of items, including those of same type
    length = str(len(inventoryStrings))

    return {'Str': exportString,
            'Len': length}


def appendInventory(inventory, item):
    assert inventory.count(None) > 0  # TODO
    index = inventory.index(None)
    inventory[index] = item

    return inventory, index


def appendPlayerInventory(item, player, returnDirtyRects):
    inventory = player.inventory
    inventory, index = appendInventory(inventory, item)

    if returnDirtyRects:
        dirtyRects.append(pl_InventoryGUI.slots[index])
        return player, dirtyRects

    else:
        return player


def appendWarehouseInventory(item, warehouseInv, returnDirtyRects):
    inventory = warehouseInv
    inventory, index = appendInventory(inventory, item)

    if returnDirtyRects:
        dirtyRects.append(warehouseInvGUI.slots[index])
        return warehouseInv, dirtyRects

    else:
        return warehouseInv

# TODO: Add dirty rects support - uses string system


def removeInventory(player, itemID):
    index = getItemIndex(itemID, player.inventory)

    player.inventory[index] = None
    return player


def stockCritic(oldStockValue):
    text = []

    baseChange = 0
    for i in range(len(oldStockValue) - 1):
        if oldStockValue[i] < oldStockValue[i + 1]:  # Lower stock to higher
            baseChange += 1
        elif oldStockValue[i] > oldStockValue[i + 1]:  # Higher to lower
            baseChange -= 1

    if baseChange == 0:
        text.append('That stock has increased and decreased an equal amount of times.')
    elif baseChange > 0:
        text.append('The economy is doing well, the stock market went up ' +
                    str(baseChange) + ' times.')
    elif baseChange < 0:
        text.append('The market isn\'t doing to well, it decreased ' +
                    str(baseChange * -1) + ' times.')

    baseChanges = [0, 0]
    for i in range(2):  # Check changes using ranges
        for j, k in zip(range(len(baseChanges)),
                        # 0, 2 is used so that the outer for loop checks over 1 - 3 and 3 - 5 elements in the lists
                        (0, 2)):
            # If value change is 90 - 95%
            if round(oldStockValue[i + j] * 0.9) <= oldStockValue[i + 1 + j] < round(oldStockValue[i + j] * 0.95):
                baseChanges[j] -= 2
            elif round(oldStockValue[i + j] * 0.95) <= oldStockValue[i + 1 + j] < round(oldStockValue[i + j] * 1):  # 95 - 99%
                baseChanges[j] -= 1
            # >100% - 105%
            elif round(oldStockValue[i + j] * 1) < oldStockValue[i + 1 + j] <= round(oldStockValue[i + j] * 1.05):
                baseChanges[j] += 1
            elif round(oldStockValue[i + j] * 1.05) < oldStockValue[i + 1 + j] <= round(oldStockValue[i + j] * 1.1):  # 106 - 110%
                baseChanges[j] += 2

    for baseChange, word in zip(baseChanges, ('first', 'second')):
        prefix = "The %s half " % word
        if baseChange in (-3, -4):
            text.append(prefix + 'decreased steeply.')
        elif baseChange in (-1, -2):
            text.append(prefix + 'decreased slightly.')
        elif baseChange == 0:
            text.append(prefix + 'did not see much change.')
        elif baseChange in (1, 2):
            text.append(prefix + 'increased somewhat.')
        elif baseChange in (3, 4):
            text.append(prefix + 'increased rapidly.')

    return tuple(text)


def updateStockValue():
    for i in stocks:
        stocks[i].updateValue()

    return stocks


CONSOLE_TIMER = pygame.USEREVENT + 1
pygame.time.set_timer(CONSOLE_TIMER, 1000)  # Run every second
consoleQueue = {'Timer': [],
                'Text': []}
sleepTime = 0

console = False
consoleTimer = 0

# Console variables
PROMPT_CITY_STRING = ('Please pick a location, "Small Town", "Second Town", '
                      '"Industrial Town", "Abandoned Town - Left", '
                      '"Abandoned Town - Centre," "Abandoned Town - Right" '
                      'or "Underground City".')

displayChat = False

# Guard Post
guardPostPause = False
guardPostAskCaveType = False


class PhysicsClass:
    def __init__(self, canFall=True):
        self.floatX = 0
        self.floatY = 0

        self.dx = 0
        self.dy = 0
        self.canFall = canFall

    def getMovement(self, quantity):
        movement = quantity / FPS
        intMovement = mathFloor(movement)
        floatMovement = movement - intMovement

        return intMovement, floatMovement

    def moveX(self, quantity):
        intMovement, floatMovement = self.getMovement(quantity)

        self.floatX += floatMovement
        self.rect.x += intMovement

        if abs(self.floatX) >= 1:
            self.rect.x += mathFloor(self.floatX)
            self.floatX -= mathFloor(self.floatX)

    def moveY(self, quantity):
        intMovement, floatMovement = self.getMovement(quantity)

        self.floatY += floatMovement
        self.rect.y += intMovement

        if abs(self.floatY) >= 1:
            self.rect.y += mathFloor(self.floatY)
            self.floatY -= mathFloor(self.floatY)

    def entityCollision(self):
        blockInfo = self.getBlockInfo()

        if self.ceilingCollision():
            self.dy = 0
            self.rect.top = blockInfo['Top Coordinate']

        if self.landedCheck():
            # If player is below ground then move to ground level and reset momentum
            if self.dy < 0:
                self.dy = 0

            self.rect.bottom = blockInfo['Bottom Coordinate']
            # TODO: Break fragile rock depending on vertical velocity, outside of this function

        if self.leftCollision():
            self.rect.left = blockInfo['Left Coordinate']

        if self.rightCollision():
            self.rect.right = blockInfo['Right Coordinate']

    def physicsUpdate(self):
        self.entityCollision()

        if self.canFall:
            if self.fallingCheck():
                self.dy -= 0.5  # Gravity

            elif self.inLiquidCheck():
                if -1.5 < self.dy < -0.5:
                    self.dy = -1

                elif self.dy <= -1.5:
                    # Subtract because velocity is already negative
                    self.dy -= self.dy / 10

                elif self.dy >= -0.5:
                    self.dy -= 0.5

        self.moveY(-self.dy * 40)
        self.moveX(self.dx)

    def getBlockInfo(self, rect=None):
        if rect is None:
            entityRect = self.rect

        else:
            entityRect = rect

        blockInfo = {'Top': [], 'Bottom': [], 'Left': [], 'Right': [],
                     'Coords': []}

        # Temporary variables
        leftID = math.ceil(entityRect.left / BLOCK_SIZE) - 1
        rightID = mathFloor(entityRect.right / BLOCK_SIZE)

        topID = math.ceil(entityRect.top / BLOCK_SIZE) - 1
        bottomID = mathFloor(entityRect.bottom / BLOCK_SIZE)

        def addCoords(key, x, y):
            nonlocal blockInfo

            try:
                blockInfo[key].append(blockGrid[x][y]['Type'])
            except IndexError:
                pass
            else:
                blockInfo['Coords'].append((x, y))
                if debugMode:
                    color = {'Top': BLUE,
                             'Bottom': GREEN,
                             'Left': RED,
                             'Right': GOLD}[key]

                    dirtyRects.append(highlightBlock(x, y, color))

        # Horizontal sections
        # Number of blocks entity is above or below
        for x in range(leftID, rightID + 1):
            addCoords('Top', x, topID)
            addCoords('Bottom', x, bottomID)

        # Vertical sections - Similar to above code
        for y in range(topID + 1, bottomID):
            addCoords('Left', leftID, y)
            addCoords('Right', rightID, y)

        # Add one because array starts at 0
        blockInfo['Top Coordinate'] = (topID + 1) * BLOCK_SIZE
        blockInfo['Bottom Coordinate'] = bottomID * BLOCK_SIZE

        blockInfo['Left Coordinate'] = (leftID + 1) * BLOCK_SIZE
        blockInfo['Right Coordinate'] = rightID * BLOCK_SIZE

        return blockInfo

    def checkBottomBlock(self, checkBlocks):
        result = True
        blockInfo = self.getBlockInfo()

        for block in blockInfo['Bottom']:
            # If all blocks are what's given
            if block not in checkBlocks:
                result = False
                break

        return result

    def fallingCheck(self):
        # If all blocks below are air
        falling = self.checkBottomBlock(TRANSPARENT_BLOCKS)

        return falling

    def inLiquidCheck(self):
        # If all blocks are liquids
        inLiquid = self.checkBottomBlock(LIQUIDS)

        return inLiquid

    def ceilingCollision(self):
        inCeiling = False
        blockInfo = self.getBlockInfo()

        if self.rect.top < blockInfo['Top Coordinate']:
            for block in blockInfo['Top']:
                if block not in MOVABLE_BLOCKS:  # If entity is inside ceiling block (ouch)
                    inCeiling = True
                    break

        return inCeiling

    def landedCheck(self):
        landed = False
        blockInfo = self.getBlockInfo()

        if self.rect.bottom >= blockInfo['Bottom Coordinate']:
            for block in blockInfo['Bottom']:
                if block not in MOVABLE_BLOCKS:  # One of the blocks are solid
                    landed = True
                    break

        return landed

    def leftCollision(self):
        collision = False
        blockInfo = self.getBlockInfo()

        if self.rect.left < blockInfo['Left Coordinate']:
            for block in blockInfo['Left']:
                if block not in MOVABLE_BLOCKS:
                    collision = True
                    break

        return collision

    def rightCollision(self):
        collision = False
        blockInfo = self.getBlockInfo()

        if self.rect.right >= blockInfo['Right Coordinate']:
            for block in blockInfo['Right']:
                if block not in MOVABLE_BLOCKS:
                    collision = True
                    break

        return collision

    def lavaCheck(self):
        if self.inLavaCheck():
            self.health -= LAVA_DAMAGE

    def inLavaCheck(self):
        return 'Lava' in self.getBlockInfo()['Bottom']


class Arrow(PhysicsClass):
    type = 'Arrow'

    def __init__(self, startX, startY, destX, destY, bowType):
        super().__init__()

        self.getInitialSpeed(startX, startY, destX, destY, bowType)
        self.rect = pygame.Rect((startX, startY), arrowsImage.get_size())

    def getInitialSpeed(self, startX, startY, destX, destY, bowType):
        if bowType == 'Old':
            strength = 1.2

        elif bowType == 'Wooden':
            strength = 1.5

        elif bowType == 'Metal':
            strength = 2

        distance = dist(startX, destX, startY, destY)
        speed = strength * distance

        yDist = destY - startY
        xDist = destX - startX

        angle = math.atan2(yDist / xDist)

        self.dx = Math.cos(angle) * speed
        self.dy = Math.sin(angle) * speed

    def update(self):
        self.physicsUpdate()

        if (self.landedCheck() or
            self.ceilingCollision() or
            self.leftCollision() or
                self.rightCollision()):

            # Replace arrow entity with Item class of an arrow
            entities.append(DroppedItem(Item('Arrow'), self.rect.midbottom))
            entities.remove(self)
            playSound(random.choice(arrowHitSound))

    def draw(self):
        windowSurface.blit(arrowsImage, self.rect)


class FallingBlock(PhysicsClass):
    type = 'Falling Block'

    def __init__(self, x, y, block):
        super().__init__()
        # X and Y being block coordinates
        self.x = x
        self.y = y

        self.block = block

        self.rect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE)

    def draw(self):
        windowSurface.blit(typeToSurface[self.block['Type']], self.rect)

    def update(self):
        self.physicsUpdate()

        blockInfo = self.getBlockInfo()

        try:
            condition = blockInfo['Bottom'][0] not in TRANSPARENT_BLOCKS + LIQUIDS

        except IndexError:
            condition = False

        if condition:
            X_Coord = self.rect.centerx // BLOCK_SIZE
            Y_Coord = self.rect.centery // BLOCK_SIZE

            if self.block['Type'] == 'Fragile Stone':
                blockGrid[X_Coord][Y_Coord] = makeFragileStone(X_Coord, Y_Coord)

            elif self.block['Type'] == 'Soft Stone':
                blockGrid[X_Coord][Y_Coord] = makeSoftStone(X_Coord, Y_Coord)

            else:
                blockGrid[X_Coord][Y_Coord] = self.block

            entities.remove(self)


class SmallFallingBlock(PhysicsClass):
    type = 'Small Falling Block'

    def __init__(self, x, y):
        super().__init__()
        self.x, self.y = x, y

        self.blockType = 'Stone'
        self.rect = pygame.Rect((x, y), smallStoneImage.get_size())

        self.damage = 5
        self.goldLoss = random.randint(1, 3)

    def draw(self):
        windowSurface.blit(smallStoneImage, self.rect)

    def update(self, removeEntity, player):
        self.physicsUpdate()
        blockInfo = self.getBlockInfo()

        (newTextParticles, newDirtyRects, newGoldLoss
         ) = (textParticles, dirtyRects, goldLoss)

        if self.rect.colliderect(player.rect):  # Break if collided with player
            (player, newTextParticles
             ) = reducePlayerHealth(self.damage, newTextParticles)

            if player.health <= 0:
                newGoldLoss = self.goldLoss
                removeEntity = self

            else:
                entities.remove(self)

        else:
            # Disappear after hitting ground
            if self.landedCheck():
                entities.remove(self)

                for entity in entities:
                    if entity in HOSTILE_MOBS and self.rect.colliderect(entity.rect):
                        entity.health -= self.damage

        return (player, newTextParticles,
                newDirtyRects, newGoldLoss, removeEntity)


class AnimatedClass:
    def __init__(self, frame=0):
        self.frame = frame
        self.frameCooldown = self.frameSpeed

    def animate(self):
        if self.frameCooldown > 0:
            self.frameCooldown -= 1
        else:
            self.frameCooldown = self.frameSpeed
            self.frame += 1

            if self.frame > self.maxFrame:
                self.frame = 0

    def draw(self):
        windowSurface.blit(pygame.transform.flip(self.image[self.frame],
                                                 self.flip, 0), self.rect)


class DroppedItem(PhysicsClass):
    type = 'Item'

    def __init__(self, containedItem, mouseCoordinates):
        super().__init__()

        self.containedItem = containedItem

        surf = self.containedItem.getSurface()

        self.rect = surf.get_rect()
        self.rect.center = mouseCoordinates
        # Physics
        self.dy = 0

        # Graphical movement
        self.sineValue = 0
        self.offsetY = 0
        self.moveDown = True

    def update(self, player, entities, dirtyRects):
        # Start attracting if less than 50 pixels from player
        if self.rect.colliderect(player.rect):
            if self.containedItem.name == 'Gold':
                player.gold += self.goldQuantity
                playSound(pickUpGoldSound)
                # TODO add local=false
                entities.remove(self)

            elif None in player.inventory:  # Spare slot
                player, dirtyRects = appendPlayerInventory(self.containedItem, player=player,
                                                           returnDirtyRects=True)
                playSound(pickUpItemSound)
                entities.remove(self)

        else:
            # If overall distance from player is less than 100
            if math.sqrt((player.rect.centerx - self.rect.centerx) ** 2 +
                         (player.rect.centery - self.rect.centery) ** 2) < 100:

                if abs(player.rect.centerx - self.rect.centerx) < 70:
                    if self.rect.centerx < player.rect.centerx:
                        self.rect.x += player.rect.centerx / self.rect.centerx

                    elif self.rect.centerx > player.rect.centerx:
                        self.rect.x -= player.rect.centerx / self.rect.centerx

                # Repeat with y axis
                if abs(player.rect.centery - self.rect.centery) < 70:
                    if self.rect.centery < player.rect.centery:
                        self.rect.y += player.rect.centery / self.rect.centery

                    elif self.rect.centery > player.rect.centery:
                        self.rect.y -= player.rect.centery / self.rect.centery

            self.move()

        return player, entities, dirtyRects

    def move(self):
        self.physicsUpdate()

        self.sineValue += math.pi / FPS
        self.offsetY = math.sin(self.sineValue) * 5  # Adds more movement

        if self.sineValue > TAU:
            self.sineValue -= TAU

    def draw(self):
        image = self.containedItem.getSurface()

        windowSurface.blit(image, (self.rect.x, self.rect.y - self.offsetY))

        self.visualRect = pygame.Rect((self.rect.x, self.rect.y - self.offsetY),
                                      self.rect.size)

        dirtyRects.append(self.visualRect)


class DroppedGold(DroppedItem):
    def __init__(self, coords, goldQuantity):
        super().__init__(GoldItem(), coords)
        self.goldQuantity = goldQuantity

# TODO: Add pathfinding - http://gamedevelopment.tutsplus.com/tutorials/a-pathfinding-for-2d-grid-based-platformers-making-a-bot-follow-the-path--cms-24913
# Randomly walks, parent class for some entities


class Walker(PhysicsClass):
    def createGoal(self):
        self.action = random.choice(('Move', 'Stop'))

        if self.action == 'Move':
            self.goalX = self.rect.centerx + random.randint(-400, 400)

            # If entity will move off screen to the left
            if self.goalX <= 0:
                self.goalX = abs(self.goalX)

            # If entity will move off screen to the right
            elif self.goalX >= INTERNAL_WIDTH:
                self.goalX = INTERNAL_WIDTH - (self.goalX - INTERNAL_WIDTH)

            # Going left
            if self.goalX < self.rect.centerx:
                self.flip = 1
                self.walkDirection = 'Left'

            else:  # Right
                self.flip = 0
                self.walkDirection = 'Right'

        else:
            self.time = random.uniform(50, 150) / 40

            # Villager needs a random direction to start facing
            self.flip = random.randint(0, 1)

    # Taken from the human class, may not work
    def jump(self):
        # Swimming
        if self.inLiquidCheck() and self.dy < 1.2:
            self.dy += 0.7

        # Contact with any solid and not swimming --> jumping
        elif self.landedCheck():
            self.dy = 5

    def randomWalk(self):
        if self.action == 'Move':
            self.walk()

            if self.walkDirection == 'Left' and self.rect.x <= self.goalX:
                self.createGoal()

            elif self.walkDirection == 'Right' and self.rect.x >= self.goalX:
                self.createGoal()

        elif self.action == 'Stop':
            self.time -= 1 / FPS
            if self.time <= 0:
                self.createGoal()

    def walk(self):
        blockInfo = self.getBlockInfo()

        try:
            if (self.walkDirection == 'Left' and blockInfo['Left'][-1] not in MOVABLE_BLOCKS
                and self.rect.left <= blockInfo['Left Coordinate'] or
                self.walkDirection == 'Right' and blockInfo['Right'][-1] not in MOVABLE_BLOCKS
                    and self.rect.right >= blockInfo['Right Coordinate']):

                self.verticalMovement = 'Up'

            else:
                self.verticalMovement = None

        except IndexError:  # Kludge until 2d pathfinding - occurs when entity is at borders
            self.verticalMovement = None

        # Check if jumping
        if self.verticalMovement == 'Up':
            self.jump()

        if self.walkDirection == 'Left':
            self.moveX(-self.speed)

        elif self.walkDirection == 'Right':
            self.moveX(self.speed)


class HostileMob:
    def __init__(self):
        # Vary the goldLosses and gains
        self.goldLoss = round(self.goldLoss * random.uniform(0.9, 1.1))
        self.goldGain = round(self.goldGain * random.uniform(0.9, 1.1))

        self.speed *= random.uniform(0.8, 1.2)

        self.playerAttack = None
        self.mobAttack = None

    def update(self, player, goldLoss, removeEntity,
               combatRect, combatSurfaces, loadFrameOnce):
        newDirtyRects = dirtyRects

        if self.rect.colliderect(player.rect) and self.aggressive:
            if combatRect['Centre'] is None:
                combatRect['Centre'] = pygame.Rect(0, 0, 0, 0)
                combatRect['Centre'].left = min(self.rect.left, player.rect.left)
                combatRect['Centre'].top = min(self.rect.top, player.rect.top)

                combatRect['Centre'].width = (max(self.rect.right,
                                                  player.rect.right) -
                                              combatRect['Centre'].left)

                combatRect['Centre'].height = (max(self.rect.bottom,
                                                   player.rect.bottom) -
                                               combatRect['Centre'].top)

                # Expand 20 pixels in each direction from its center
                combatRect['Centre'].inflate_ip(20, 20)

                if combatRect['Centre'].left < 0:
                    combatRect['Centre'].left = 0

                elif combatRect['Centre'].top < 0:
                    combatRect['Centre'].top = 0

                elif combatRect['Centre'].right > INTERNAL_WIDTH:
                    combatRect['Centre'].right = INTERNAL_WIDTH

                elif combatRect['Centre'].bottom > INTERNAL_HEIGHT:
                    combatRect['Centre'].bottom = INTERNAL_HEIGHT

            (player, goldLoss, removeEntity, combatRect,
             combatSurfaces, textParticles,
             newDirtyRects) = self.battle(player, goldLoss, removeEntity,
                                          combatRect, combatSurfaces)

            # Player is fighting dragon and the surface has not yet been made
            if combatRect['Centre'] is not None and combatSurfaces is None:
                # Cover everything above combat rect
                combatRect['Top'] = pygame.Rect(0, 0, INTERNAL_WIDTH, combatRect['Centre'].top)
                # Everything below
                combatRect['Bottom'] = pygame.Rect(0, combatRect['Centre'].bottom, INTERNAL_WIDTH,
                                                   INTERNAL_HEIGHT - combatRect['Centre'].bottom)
                # Everything to left, not including bottom and top
                combatRect['Left'] = pygame.Rect(0, combatRect['Centre'].top, combatRect['Centre'].left,
                                                 combatRect['Centre'].height)
                # Everything to right, not including bottom and top
                combatRect['Right'] = pygame.Rect(combatRect['Centre'].right, combatRect['Centre'].top,
                                                  INTERNAL_WIDTH - combatRect['Centre'].right,
                                                  combatRect['Centre'].height)

                combatSurfaces = {}
                for i in ('Top', 'Bottom', 'Left', 'Right'):
                    combatSurfaces[i] = pygame.Surface(combatRect[i].size)
                    combatSurfaces[i].fill(BLACK)
                    combatSurfaces[i].set_alpha(128)

                loadFrameOnce = False

        elif self.aggressive:
            self.targetPlayer(players[PK()])

        else:
            self.randomWalk()  # Use same random walking as villagers

        self.physicsUpdate()
        self.lavaCheck()

        return (player, goldLoss, removeEntity, combatRect, combatSurfaces,
                loadFrameOnce, newDirtyRects)

    def battle(self, player, goldLoss, removeEntity, combatRect, combatSurfaces):
        newTextParticles, newDirtyRects = textParticles, dirtyRects

        player.fightingMob = True  # Disable movement while battling

        # Data not yet generated
        if self.playerAttack is None and self.mobAttack is None:
            self.battleCalculation(player)

         # Update player's attack based on selected item every frame
        self.playerAttack = player.getAttack()

        if options['autoCombat']:
            '''Old combat code, modified so that the damage dealt isn't divided by 4
            Instead there is a 1 in 4 chance of an attack'''
            if random.randint(0, 3) == 3:
                (self.health,
                 newTextParticles) = reduceHealth(self.health, False, self.playerAttack,
                                                  self.rect.center, 'Attack',
                                                  newTextParticles)

            if random.randint(0, 3) == 3:
                (players[PK()], newTextParticles,
                 ) = reducePlayerHealth(self.mobAttack, newTextParticles)

        else:
            # The random chance to attack makes battles have random chances of an attack working
            '''In the future, when this attack misses provide feedback to player
            that an attack was dodged or blocked such as with the sound of a shield
            being hit. Also make it possible to increase the chance of dodging or
            more likely, blocking an attack with one's sword'''
            if random.randint(0, 3) == 3:
                # Deal damage
                (players[PK()], newTextParticles,
                 ) = reducePlayerHealth(self.mobAttack, newTextParticles)

        if self.health <= 0:
            XY_Coords = (self.rect.left + random.randint(5, self.rect.width - 5),
                         self.rect.top + random.randint(5, self.rect.height - 5))
            entities = dropGold(self.goldGain, XY_Coords)
            entities.remove(self)

        elif player.health <= 0:
            goldLoss = self.goldLoss
            removeEntity = self

        if self.health <= 0 or player.health <= 0:
            combatRect = {'Centre': None,
                          'Top': None, 'Bottom': None,
                          'Left': None, 'Right': None}
            combatSurfaces = None

            player.fightingMob = False

        # Dragon's health bar
        newDirtyRects.append(drawHealthBar(self.rect, self.health, self.maxHealth))

        return (player, goldLoss, removeEntity, combatRect, combatSurfaces,
                textParticles, newDirtyRects)

    def battleCalculation(self, player):
        '''
        Battle code
        Percentage of success is playerAttack * 10
        Battle system acts like a series of dice, the mob's strength is random while the player's
        strength depends on the sword held. A larger playerAttack makes it more likely to be greater than mob's
        '''
        # TODO: Add dual wielding ability which allows 50% additional strength from weaker sword
        playSound(swordWieldSound)
        self.mobAttack = random.uniform(1, self.strength)
        self.playerAttack = player.getAttack()

    def targetPlayerX(self, player):
        self.action = 'Move'
        # Choose flip and movement based on mob's position
        # TODO use moveX when PhysicsClass is implemented
        if player.rect.centerx <= self.rect.centerx:
            self.flip = 1
            self.rect.centerx -= 2

        elif player.rect.centerx > self.rect.centerx:
            self.flip = 0
            self.rect.centerx += 2

    def targetPlayer(self, player):
        self.targetPlayerX(player)


class Cloud(PhysicsClass):
    type = 'Cloud'

    images = []
    for i in range(1, 3 + 1):
        images.append(imgLoad('images/clouds/cloud' +
                              str(i) + '.png').convert_alpha())

    for img in images[:]:
        for k in (1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5):
            images.append(pygame.transform.smoothscale(img,
                                                       (round(img.get_width() * k),
                                                        round(img.get_height() * k))).convert_alpha())

    def __init__(self):
        super().__init__()
        self.imageType = random.randint(0, len(self.images) - 1)
        self.flip = random.choice((-1, 1))

        self.rect = self.images[self.imageType].get_rect()
        self.rect.x = random.randint(100, INTERNAL_WIDTH)

        self.remakeCloud()

    def update(self):
        self.moveX(self.dx)

        if self.rect.right < 0 or self.rect.left > INTERNAL_WIDTH:
            # Make a new cloud in a different place using same entity
            self.remakeCloud()

    def remakeCloud(self):
        self.rect.y = random.randint(0, 180)
        self.dx = random.uniform(2, 16) * random.choice((-1, 1))

        # Fix velocity to make cloud enter screen
        # At right of screen moving right
        if ((self.rect.left > INTERNAL_WIDTH and self.dx > 0) or
            # At left of screen moving left
                (self.rect.right < 0 and self.dx < 0)):
            self.dx *= -1

    def draw(self):
        windowSurface.blit(pygame.transform.flip(self.images[self.imageType],
                                                 self.flip, 0), self.rect)


class Human(AnimatedClass, PhysicsClass):
    frameSpeed = 5
    maxFrame = 5

    def __init__(self, bottomCoord=None):
        AnimatedClass.__init__(self)
        PhysicsClass.__init__(self)

        self.rect = humanWalkImage[self.frame][False].get_rect()

        if bottomCoord is None:
            self.rect.bottom = mapData['groundY']
        else:
            self.rect.bottom = bottomCoord

        self.stopFrame = True
        self.fightingMob = False

        self.verticalMovement = None
        self.health = 100

    def updateRect(self):
        self.rect.size = humanWalkImage[self.frame][False].get_size()

    def draw(self):
        image = self.getImage()
        windowSurface.blit(image, self.rect)

    def getImage(self):
        if self.stopFrame:
            image = humanStopImage[self.flip]

        elif self.fightingMob:
            image = playerStanceImage[0]
            image = pygame.transform.flip(image, self.flip, 0)

        else:
            image = humanWalkImage[self.frame][self.flip]

        return image

    def jump(self):
        # Swimming
        if self.inLiquidCheck() and self.dy < 1:
            self.dy += 0.6

        # Contact with any solid and not swimming --> jumping
        elif self.landedCheck():
            self.dy = 5

    def animate(self):
        if self.action == 'Move':
            AnimatedClass.animate(self)
            self.stopFrame = False

        else:  # Entity stopped, same stopFrame as player
            self.stopFrame = True


PLAYER_DEFAULT_HEALTH = 100


class Player(Human):
    SPEED = 250

    def __init__(self, bottomCoord, gold=100, maxHealth=100, flip=1, frame=0,
                 invincible=False, health=PLAYER_DEFAULT_HEALTH):
        super().__init__(bottomCoord)

        self.gold = gold
        self.horizontalControls = None
        self.rect = pygame.Rect(0, 0, BLOCK_SIZE, 75)
        self.jumping = False
        self.health = health
        self.fightingMob = False
        self.previousLocation = 'N/A'
        self.previousTown = 'N/A'
        self.direction = 'N/A'
        self.flip = flip
        self.frame = frame
        self.frameCooldown = Human.frameSpeed
        self.stopFrame = True
        self.caveType = 'N/A'
        self.caveDepth = 'N/A'
        self.invincible = invincible
        # Guard Post variables
        self.canPassGuardKeeper = False
        self.canPassGuardSuperior = False
        self.canPassCaveGuard = False
        self.payingCaveGuard = False
        self.mouseInventory = None  # Contains the item currently held my mouse
        self.maxHealth = maxHealth
        self.selectedInvSlot = 0

        self.inventory = pl_InventoryGUI.makeInventoryList()

        if options['testWorld']:
            self.location, self.previousTown = SECOND_TOWN, INDUSTRIAL_TOWN
            self.inventory[0] = Item('Iron Ingot')
            self.inventory[1] = Item('Iron Ingot')
            self.inventory[2] = Item('Iron Ingot')

            self.inventory[3] = Sword(swordType='Wooden')
            self.inventory[4] = OreItem('Good', 'Diamond')

            for i, item in enumerate(('Arrows', 'Watch')):
                self.inventory[i + 5] = Item(item)

            self.inventory[7] = HealthPotion(strength=20)
            self.inventory[8] = Bow(bowType='Old')
            self.inventory[9] = Bow(bowType='Wooden')
            self.inventory[15] = Bow(bowType='Metal')

            self.inventory[10] = Item('Gold Sword')

            self.inventory[11] = Pickaxe('Old')

            self.inventory[12] = OreItem('Good', 'Ruby')
            self.inventory[13] = OreItem('Normal', 'Ruby')
            self.inventory[14] = OreItem('Poor', 'Ruby')

            self.inventory[17] = Sword(swordType='Stone')

            for i, colour in enumerate(('Red', 'Blue')):
                self.inventory[i + 18] = Scroll(colour, 'Quest Text')

            for i, shieldType in enumerate(('Fortified', 'Gilded', 'Iron', 'Gold')):
                self.inventory[i + 20] = Shield(shieldType)

            self.inventory[24] = OreItem('Good', 'Sapphire')
            self.inventory[25] = OreItem('Normal', 'Sapphire')
            self.inventory[26] = OreItem('Poor', 'Sapphire')
            self.inventory[27] = Item('Backpack')

            self.inventory[28] = Armor('Expensive', 'Boot')
            self.inventory[29] = Armor('Expensive', 'Chestplate')

            self.inventory[30] = OreItem('Good', 'Emerald')
            self.inventory[31] = OreItem('Normal', 'Emerald')
            self.inventory[32] = OreItem('Poor', 'Emerald')

            for i, type in enumerate(('Glove', 'Boot', 'Chestplate')):
                self.inventory[i + 33] = Armor('Regular', type)

        else:
            self.location, self.previousTown = SMALL_TOWN, SMALL_TOWN

            self.inventory[0] = Sword(swordType='Wooden')

        self.rect.x = 200

        # This creates the cave effect in which player's light is absorbed
        self.pastCoords = []
        self.pastCoordsCounter = 0

    def animate(self):
        if self.horizontalControls is not None:
            AnimatedClass.animate(self)
            self.stopFrame = False

        else:  # Player stopped
            self.stopFrame = True

    def draw(self):
        image = self.getImage()
        imageRect = self.getImageRect()

        return windowSurface.blit(image, imageRect)

    def drawHealthBar(self):
        return drawHealthBar(self.rect, self.health, self.maxHealth)

    def getImageRect(self):
        imageRect = pygame.Rect((0, 0), humanWalkImageSize[self.frame])
        imageRect.midbottom = self.rect.midbottom

        return imageRect

    def getBlockInfo(self):
        blockInfo = PhysicsClass.getBlockInfo(self, rect=self.getCollisionRect())

        return blockInfo

    def getAttack(self):
        if isinstance(self.getHeldItem(), Sword):
            swordType = self.getHeldItem().swordType
            # Find the effectiveness of sword
            if swordType == 'Iron':
                playerAttack = 9
            elif swordType == 'Stone':
                playerAttack = 3
            elif swordType == 'Wooden':
                playerAttack = 1

        else:
            # If no weapon is held give a 1/10 chance of a 1 strength attack
            if random.randint(0, 9) == 0:
                playerAttack = 1

            else:
                playerAttack = 0

        return playerAttack

    def getCollisionRect(self):
        playerCollisionRect = self.rect.copy()
        playerCollisionRect.size = (32, 64)
        playerCollisionRect.midbottom = self.rect.midbottom

        return playerCollisionRect

    def getHeldItem(self):
        return self.inventory[self.selectedInvSlot]

    def getLightRadius(self, caveEnvironment):
        if caveEnvironment == 12:
            playerLightRadius = 15

        else:
            playerLightRadius = 10

        if self.getHeldItem() == 'Torch':
            playerLightRadius += 2

        return playerLightRadius

    def incrementPastCoords(self):
        self.pastCoordsCounter += 1

        if self.pastCoordsCounter > FPS // 20:
            self.pastCoordsCounter = 0
            self.pastCoords.insert(0, self.rect.center)  # Prepend

            while len(self.pastCoords) > 20:
                del self.pastCoords[-1]

    def get_speed(self):
        # Move player
        speed = Player.SPEED
        if self.fightingMob:
            speed /= 8

        if DEVELOPER_MODE:
            speed *= 4

        if mapData['caveEnvironment'] == 20:  # Thin air
            speed *= 1 / 2

        return speed

    def move(self):
        speed = self.get_speed()

        if self.horizontalControls == 'Left':
            self.moveX(-speed)
            self.flip = 1
        elif self.horizontalControls == 'Right':
            self.moveX(speed)
            self.flip = 0

        if self.jumping:
            self.jump()

        if self.fallingCheck():
            # Make player move faster in air to allow for better jumping
            if self.horizontalControls == 'Left':
                self.moveX(-160)
            elif self.horizontalControls == 'Right':
                self.moveX(160)

    def setLocation(self, location):
        self.pastCoords = []
        self.previousLocation = self.location
        self.location = location

    def setCityLocation(self, location):
        assert location in TOWN_STRINGS + ABANDONED_TOWN

        self.setLocation(location)
        self.previousTown = location


class Villager(Walker, Human):
    type = 'Villager'

    def __init__(self, bottomCoord):
        Human.__init__(self, bottomCoord)
        Walker.__init__(self)

        self.rect.centerx = random.randint(40, INTERNAL_WIDTH - 40)
        # Half chance to stay or leave
        self.stay = random.randint(0, 1)
        self.createGoal()
        self.speed = random.uniform(35, 45)

    def update(self):
        self.randomWalk()
        self.physicsUpdate()
        self.lavaCheck()

    def talk(self, player):
        speechBubbles.append(createSpeech(player, self))
        self.stop()

    def stop(self):
        self.action = 'Stop'  # Stop villager to make it look like talking
        self.time = random.uniform(3, 6)  # Stop for some time

        if self.rect.centerx < players[PK()].rect.centerx:
            self.flip = 0

        else:
            self.flip = 1

# TODO: Add different type of explorers, random walking, running away (forward or backwards), staying still resting (possibly at encampment)
# TODO: Add ability to talk about information, e.g. manipulating the stock market
# TODO: use the ability to set ignorePlayer for encampments


class Explorer(Villager):
    type = 'Explorer'

    def __init__(self, bottomY, ignorePlayer=None):
        super().__init__(bottomY)

        if ignorePlayer is None:
            self.ignorePlayer = random.choice((True, False))

        else:
            self.ignorePlayer = ignorePlayer

        self.stopped = False
        self.menu = None
        self.firstClick = False

        self.selectedItemID = None  # Index of inventory for buying

        # Trading variables
        self.itemOffer = None
        self.goldOffer = None

        # Empty rect by default
        self.inventoryRect = pygame.Rect(0, 0, 0, 0)

        # Required variable for walker code to work
        self.time = 0

        if self.ignorePlayer:
            self.action = 'Move'

            if self.rect.centerx <= players[PK()].rect.centerx:  # Move left
                self.walkDirection = 'Left'
                self.goalX = self.rect.centerx  # Distance until half of character is off screen
                self.flip = 1

            else:  # Move right
                self.walkDirection = 'Right'
                self.goalX = INTERNAL_WIDTH - self.rect.centerx  # Same as above
                self.flip = 0

        else:
            self.createGoal()

            self.inventory = []
            # For merchandise and other items, take a random index from 1 - their combined length, subtracting 1
            for i in range(random.randint(2, 6)):

                if random.randint(0, 1):
                    self.inventory.append(random.choice(merchandise))  # Add normal items

                else:  # Generate ores half the time
                    # Begin the ores
                    oreType = random.choice(REGULAR_ORES)

                    oreQuality = random.randint(1, 6)
                    if oreQuality <= 3:  # 50%
                        oreQuality = 'Poor'
                    elif oreQuality <= 5:  # 33%
                        oreQuality = 'Normal'
                    elif oreQuality == 6:  # 17%
                        oreQuality = 'Good'

                    self.inventory.append(OreItem(oreQuality, oreType))

    # Overrides the inherited talk method from Villager class
    def talk(self, consoleText):
        if not self.stopped and not self.ignorePlayer:
            output = 'You choose to speak to him, what do you want to do?'
            self.stopped = True
            self.stop()

            self.menu = 'Main'
            self.updateMenuBackRect()
        else:
            output = 'You see another explorer, he sees you but walks away. Maybe in the future you can trade?'
            self.menu = None

        if not self.firstClick:
            self.firstClick = True
            consoleText.addOutput(output)
            chatText.addOutput(output)

        if self.menu is not None:
            dirtyRect = NPC_Text[self.menu]['Back Rect']

        else:
            dirtyRect = None

        return dirtyRect

    def calculateItemValue(self, NPC_Trading, player):
        itemValue = NPC_Trading['Item Offer'].getValue()

        self.itemOffer = []

        # Pick items randomly from inventory
        for item in player.inventory:
            if item is None:
                continue

            playerItemValue = item.getValue()

            if playerItemValue <= itemValue:
                itemValue -= playerItemValue
                self.itemOffer.append(item)

        else:
            # Gold asked if remainder of item value
            self.goldOffer = itemValue

        # Add counter requested items to trading menu
        for i, item in enumerate(self.itemOffer):
            # Limit to requesting 3 items, with 1 space for gold
            if i == len(NPC_Trading['Counter Offer']) - 1:
                break

            NPC_Trading['Counter Offer'][i] = item
        # Add support for when the number of items is more than number of slots and player doesn't have enough gold
        while self.goldOffer > player.gold:
            requestedItem = random.choice(player.inventory)
            if requestedItem is None:
                continue

            self.itemOffer.append(requestedItem)
            self.goldOffer -= requestedItem.getValue()

        if self.goldOffer > 0:
            NPC_Trading['Gold Offer'] = self.goldOffer
            NPC_Trading['Gold Offer Label'] = TextRect(font, str(self.goldOffer), BLACK)

            # Set position as same as last item slot rect
            NPC_Trading['Gold Offer Label'].rect = NPC_Trading['Counter Offer Rect'][-1].copy()
            NPC_Trading['Gold Offer Label'].rect.x += 35  # Move to be the fourth trade slot

        else:
            NPC_Trading['Gold Offer'] = None
            NPC_Trading['Gold Offer Label'] = None

        return NPC_Trading

    def updateInventoryRects(self):
        dirtyRects.append(self.inventoryRect.copy())
        self.inventoryRect = pygame.Rect(0, 0,
                                         # 10 pixel spacing
                                         len(self.inventory) * 35 + 20,
                                         32 + 10 * 2)

        self.inventoryRect.centerx = self.rect.centerx
        if self.inventoryRect.centerx < 0:
            self.inventoryRect.centerx = 0

        self.inventoryRect.bottom = NPC_Text[self.menu]['Back Rect'].top - 10

        self.inventorySlot = []
        for i in range(len(self.inventory)):
            self.inventorySlot.append(pygame.Rect((self.inventoryRect.left + 35 * i + 10,  # Arbitrary spacing
                                                   self.inventoryRect.top + 10),
                                                  ITEM_SIZE))

        dirtyRects.append(self.inventoryRect)

        return dirtyRects

    def drawInventory(self, itemTooltip):
        pygame.draw.rect(windowSurface, DARK_GREY, self.inventoryRect)

        # Should a selected item dissapear or have a permanent highlight effect
        for item, slot, i in zip(self.inventory, self.inventorySlot,
                                 range(len(self.inventory))):

            # Display item if not selected for buying
            if i != self.selectedItemID:
                itemTooltip = displayItemSlot(itemTooltip, item, slot)[1]

            else:  # Make item fadeout if selected
                itemTooltip = displayItemSlot(itemTooltip, item, slot, alpha=128)[1]

        return itemTooltip

    def drawMenu(self):
        if self.stopped:
            # Background rect for menu
            pygame.draw.rect(windowSurface, GREY,
                             NPC_Text[self.menu]['Back Rect'])

            for menu in NPC_Text[self.menu]['Order']:
                windowSurface.blit(NPC_Text[self.menu]['Label'][menu],
                                   (NPC_Text[self.menu]['Back Rect'].left,
                                    NPC_Text[self.menu]['Back Rect'].top +
                                    NPC_Text[self.menu]['Rect'][menu].y))

    def clickTrade(self, NPC_Trading, player):
        if self.menu == 'Request Item' and mouseover(self.inventoryRect):
            for i, rect in enumerate(self.inventorySlot):
                if mouseover(rect):
                    NPC_Trading = clearNPC_TradeOffers()
                    self.selectedItemID = i
                    NPC_Trading['Item Offer'] = self.inventory[self.selectedItemID]
                    NPC_Trading = self.calculateItemValue(NPC_Trading, player)
                    break

            else:
                self.selectedItemID = None
                NPC_Trading['Item Offer'] = None

        return NPC_Trading

    def clickMenu(self, NPC_Trading, player, dirtyRects):
        for menu in NPC_Text[self.menu]['Order']:
            if mouseover(pygame.Rect((NPC_Text[self.menu]['Back Rect'].left,
                                      NPC_Text[self.menu]['Back Rect'].top +
                                      NPC_Text[self.menu]['Rect'][menu].y),

                                     (NPC_Text[self.menu]['Back Rect'].width,
                                      NPC_Text[self.menu]['Rect'][menu].height))):

                playSound(adjustValueSound)
                dirtyRects.append(NPC_Text[self.menu]['Back Rect'].copy())

                if self.menu == 'Main':
                    if menu == 'Trade':
                        self.menu = 'Trade'

                    elif menu == 'Leave':
                        self.stopped = False

                elif self.menu == 'Trade':
                    if menu == 'Request Item':
                        self.menu = 'Request Item'
                        NPC_Trading['Mode'] = 'Request Item'
                        NPC_Trading = update_NPC_TradingLabel('Requested Item')

                    elif menu == 'Sell':
                        self.menu = 'Sell'
                        NPC_Trading['Mode'] = 'Sell'
                        NPC_Trading = update_NPC_TradingLabel('Item Offer')

                    elif menu == 'Stop Trading':
                        self.menu = 'Main'

                    if menu in ('Request Item', 'Sell'):
                        NPC_Trading['Visible'] = True

                elif self.menu == 'Request Item':
                    # Click accept and item is being requested
                    if (menu == 'Accept' and
                        NPC_Trading['Item Offer'] is not None and
                            player.inventory.count(None) > 0):
                        # Give requested item to player
                        player, dirtyRects = appendPlayerInventory(NPC_Trading['Item Offer'],
                                                                   player=player, returnDirtyRects=True)
                        self.inventory.remove(NPC_Trading['Item Offer'])

                        # Remove items requested by NPC and give to NPC
                        for item in NPC_Trading['Counter Offer']:
                            if item is None:
                                continue

                            self.inventory.append(item)
                            player = removeInventory(player, item)

                        # Take gold
                        if NPC_Trading['Gold Offer'] is not None:
                            player.gold -= NPC_Trading['Gold Offer']

                elif self.menu == 'Sell':
                    # Click accept and item is being offered
                    if menu == 'Accept' and NPC_Trading['Item Offer'] is not None:
                        pass

                if self.menu in ('Request Item', 'Sell'):
                    if menu == 'Exit':
                        NPC_Trading['Visible'] = False
                        NPC_Trading['Item Offer'] = None
                        self.menu = 'Trade'

                    elif menu == 'Accept':
                        playSound(pickUpItemSound)
                        NPC_Trading = clearNPC_TradeOffers()

                # Updates back rect for display
                self.updateMenuBackRect()
                dirtyRects.append(NPC_Text[self.menu]['Back Rect'])

                # This needs the back rect in order to place inventory
                if self.menu in ('Trade', 'Request Item', 'Sell'):
                    dirtyRects = self.updateInventoryRects()

                else:
                    # Update dirty rects so it's deleted
                    dirtyRects.append(entity.inventoryRect)

                break

        return NPC_Trading, player, dirtyRects

    def updateMenuBackRect(self):
        NPC_Text[self.menu]['Back Rect'].x = self.rect.centerx
        NPC_Text[self.menu]['Back Rect'].y = self.rect.top - NPC_Text[self.menu]['Back Rect'].height


class CaveGuard:
    type = 'Cave Guard'

    def __init__(self, groundY):
        self.flip = 1  # Face left

        self.rect = humanStopImage[self.flip].get_rect()
        self.rect.bottom = groundY
        self.rect.centerx = INTERNAL_WIDTH * 1 // 3

        self.showInitialMessage = False
        self.showLastMessage = False

    def draw(self):
        windowSurface.blit(humanStopImage[self.flip], self.rect)


class Slime(Walker, AnimatedClass, HostileMob):
    type = 'Slime'

    frameSpeed = 10
    maxFrame = 5
    stopFrame = 0

    image = []

    for i in range(1, maxFrame + 2):
        path = os.path.join("images", "slime", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self, player, bottomCoord):
        AnimatedClass.__init__(self)
        Walker.__init__(self)

        self.aggressive = bool(random.randint(0, 1))
        self.health = self.maxHealth = 50

        if player.location == 'Cave':
            self.strength = 2
            self.goldLoss = 30
            self.goldGain = 30

        elif player.location in ABANDONED_TOWN:
            self.strength = 3

            self.goldLoss = 20
            self.goldGain = 10

        self.flip = 1

        self.rect = self.image[self.frame].get_rect()
        self.rect.centerx = random.randint(0 + 250, INTERNAL_WIDTH - 250)
        self.rect.bottom = bottomCoord

        # Battle variables
        self.speed = random.uniform(35, 45)
        HostileMob.__init__(self)

        self.createGoal()

    def updateRect(self):
        midBottom = self.rect.midbottom

        self.rect.size = self.image[self.frame].get_size()
        self.rect.midbottom = midBottom


class Guard(Human):
    type = 'Guard'

    def __init__(self, player, guardType, bottomCoord):
        super().__init__()
        # Allows resetting variables and making createSpeech detect change in variables
        self.ID = guardType
        assert self.ID in ('Keeper', 'Superior')

        if player.direction == 'Right':
            self.flip = 1

        elif player.direction == 'Left':
            self.flip = 0

        self.rect = humanStopImage[self.flip].get_rect()
        self.rect.bottom = bottomCoord
        self.stopFrame = True
        self.frame = 0  # For draw method

        # Create speech bubbles for before and after being allowed to pass guard
        self.speechBubbles = {}

        self.showFirstMessage = False
        self.showSecondMessage = False

        # This variable must be set before the createSpeech function is run
        # Make it false so createSpeech makes proper text
        # by having variable defined and not skipping elifs
        self.showThirdMessage = False

        # This also resets the can pass variables
        # Loop through True and False to generate both speech bubbles
        # TODO: changing the canPass variables should be changed when leaving the guard post
        if self.ID == 'Keeper':
            player.canPassGuardKeeper = False

            if player.direction == 'Right':
                self.rect.centerx = INTERNAL_WIDTH * 1 / 3

            elif player.direction == 'Left':
                self.rect.centerx = INTERNAL_WIDTH * 2 / 3

        elif self.ID == 'Superior':
            player.canPassGuardSuperior = False

            if player.direction == 'Right':
                self.rect.centerx = INTERNAL_WIDTH * 2 / 3

            elif player.direction == 'Left':
                self.rect.centerx = INTERNAL_WIDTH * 1 / 3

        self.speechBubbles['First'] = createSpeech(player, self)


class BaseDragon(AnimatedClass):
    type = 'Dragon'

    frameSpeed = 5
    maxFrame = 2
    stopFrame = 0

    image = []

    for i in range(1, maxFrame + 2):
        path = os.path.join("images", "dragon", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self):
        super().__init__()
        self.rect = self.image[0].get_rect()
        self.dy = 0
        self.rect.bottom = mapData['groundY']

    def animate(self):
        if self.action == 'Move':
            AnimatedClass.animate(self)

        else:
            self.frame = self.stopFrame

    def updateRect(self):
        self.rect.size = self.image[self.frame].get_size()


BATS = ('Small Bat', 'Big Bat')
HOSTILE_MOBS = ('Dragon', 'Slime') + BATS


class Dragon(Walker, BaseDragon, HostileMob):
    def __init__(self, player):
        Walker.__init__(self)
        BaseDragon.__init__(self)

        self.aggressive = bool(random.randint(0, 1))  # 50% chance the dragon attacks

        self.health = self.maxHealth = 100

        if player.caveType == '1':
            self.strength = 3
            self.goldLoss = 50
            self.goldGain = 200

        elif player.caveType == '2':
            self.strength = 5
            self.goldLoss = 50
            self.goldGain = 300

        elif player.caveType == '3':
            self.strength = 10
            self.goldLoss = 100
            self.goldGain = 500

        self.flip = 1
        self.rect.centerx = random.randint(0 + 250, INTERNAL_WIDTH - 250)

        # Battle variables
        self.speed = random.uniform(0.9, 1.1) * 40
        HostileMob.__init__(self)

        self.createGoal()


class ShadowEntity(Walker):  # Does not use randomWalk
    def __init__(self, player):
        super().__init__()
        # The player's position has not yet been reset so invert the if statements
        if player.rect.x > INTERNAL_WIDTH // 2:  # Comes from left
            self.goalX = INTERNAL_WIDTH + self.rect.width
            self.rect.right = INTERNAL_WIDTH - random.randint(0, 50)
            self.walkDirection = 'Right'
            self.flip = 0

        else:
            self.goalX = -self.rect.width
            self.rect.left = random.randint(0, 50)
            self.walkDirection = 'Left'
            self.flip = 1

        # This doesn't do anything other than ensure that when entities are
        # displayed the frames are cycled through
        self.action = 'Move'
        self.speed = random.uniform(0.9, 1.1) * 200  # Disappears quickly

    def update(self):
        # Shadow entities only run away
        self.walk()
        self.physicsUpdate()


class ShadowDragon(ShadowEntity, BaseDragon):
    type = 'Shadow Dragon'

    image = []

    for i in range(1, BaseDragon.maxFrame + 2):
        path = os.path.join("images", "shadow_dragon", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self, player):
        BaseDragon.__init__(self)
        ShadowEntity.__init__(self, player)


class ShadowExplorer(ShadowEntity, Human):
    type = 'Shadow Explorer'

    image = []
    for i in range(1, Human.maxFrame + 2):
        path = os.path.join("images", "shadow_player", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self, player):
        Human.__init__(self)
        ShadowEntity.__init__(self, player)


class Block_Drop_Item:
    def itemCoordinates(self, itemSurface):
        return (self.x + random.randint(0, BLOCK_SIZE - itemSurface.get_width()),
                self.y + random.randint(0, BLOCK_SIZE - itemSurface.get_height()))


'''
Minable block tier system
0 - no tool required
1 - old pickaxe required
2 - iron pickaxe required
'''


class Minable_Block:
    def __init__(self, x, y):
        self.x, self.y = x * BLOCK_SIZE, y * BLOCK_SIZE
        self.durability = len(crackedBlock) + 1

    def drawCracks(self):
        if self.durability < len(crackedBlock) + 1:
            windowSurface.blit(crackedBlock[self.durability - 1],
                               (self.x, self.y))

    def attemptMining(self, player):
        assert(self.tier in (0, 1, 2))
        item = player.getHeldItem()

        if self.tier == 0:
            self.mine()

        elif isinstance(item, Pickaxe):
            if self.tier <= 1 and item.pickaxeType == 'Old':
                self.mine()

            elif self.tier <= 2 and item.pickaxeType == 'Iron':
                self.mine()

    def mine(self):
        self.durability -= random.randint(1, 3)
        playSound(random.choice(miningSound))

        if self.durability <= 0:
            # Drops item if ore
            self.finishMining()
            # Destroy block
            blockGrid[self.x // BLOCK_SIZE][self.y // BLOCK_SIZE]['Type'] = 'Air'
            del blockGrid[self.x // BLOCK_SIZE][self.y // BLOCK_SIZE]['Data']


class BreakableStone(Minable_Block):
    def draw(self):
        self.drawCracks()

    def finishMining(self):
        pass  # Nothing happens when block is destroyed


class SoftStone(BreakableStone):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.tier = 0


def makeFragileStone(x, y):
    return {'Type': 'Fragile Stone',
            'Data': Fragile_Stone(x, y)}


def makeSoftStone(x, y):
    return {'Type': 'Soft Stone',
            'Data': SoftStone(x, y)}


class Fragile_Stone(BreakableStone):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.tier = 1


class Ore(Block_Drop_Item, Minable_Block):
    def __init__(self, x, y, oreType, oreQuality):
        Minable_Block.__init__(self, x, y)
        self.type = oreType
        self.setQuality(oreQuality)

        if self.type in REGULAR_ORES + ('Iron',):
            self.tier = 1

        elif self.type in RARE_ORES:
            self.tier = 2

        else:
            assert False  # Unexpected ore

        if self.type in ('Diamond', 'Iron', 'Gold Nugget', 'Pyrite'):
            # These ores may appear in multiple forms, image id is image chosen
            self.imageID = random.randint(0, 1)

        self.oreSurface = self.getSurface()

        self.oreOffsetX = random.randint(0, BLOCK_SIZE - self.oreSurface.get_width())
        self.oreOffsetY = random.randint(0, BLOCK_SIZE - self.oreSurface.get_height())

        del self.oreSurface  # Don't store surfaces in classes

    def draw(self):
        windowSurface.blit(stoneImage, (self.x, self.y))

        windowSurface.blit(self.getSurface(),
                           (self.x + self.oreOffsetX,
                            self.y + self.oreOffsetY))

        self.drawCracks()

    def finishMining(self):
        if random.randint(1, 4) == 1:
            entities.append(DroppedItem(self.droppedItem,
                                        self.itemCoordinates(itemGraphicLocator[self.droppedItem.name]
                                                             )))

    def getSurface(self):
        if self.type == 'Diamond':
            return diamondOreImages[self.imageID]

        elif self.type == 'Iron':
            return ironOreImages[self.imageID]

        elif self.type in ('Gold Nugget', 'Pyrite'):
            return goldOreImages[self.imageID]

        else:
            return itemGraphicLocator[self.quality + ' ' + self.type]

    # Only used outside of __init__ when making caves fragile
    def setQuality(self, quality):
        self.quality = quality

        if self.type != 'Iron':
            self.droppedItem = Item(self.quality + ' ' + self.type)

        else:
            self.droppedItem = Item('Iron Ore')


class SmallBlock:
    def __init__(self, blockX, blockY):
        self.rect = self.getImage().get_rect()

        # Centers a non 32x32 image over a slot in block grid
        self.xPixel = blockX * BLOCK_SIZE + BLOCK_SIZE // 2 - self.rect.width // 2
        self.yPixel = blockY * BLOCK_SIZE + BLOCK_SIZE - self.rect.height

    def draw(self):
        windowSurface.blit(self.getImage(), (self.xPixel, self.yPixel))


class SmallLightBlock(SmallBlock):
    def draw(self, lighting):
        SmallBlock.draw(self)

        lighting.light(self.xPixel + BLOCK_SIZE // 2,
                       self.yPixel + BLOCK_SIZE // 2,
                       10, 0.8, ORANGE)


class Torch(SmallLightBlock):
    def __init__(self, blockX, blockY):
        SmallBlock.__init__(self, blockX, blockY)

    def getImage(self):
        return torchImage

# TODO: Add smoke effects --> may require a particle class / array / sprite


class CampFire(SmallLightBlock, AnimatedClass):
    frameSpeed = 2
    maxFrame = 4

    image = []

    for i in range(1, maxFrame + 2):
        path = os.path.join("images", "campFire", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self, blockX, blockY):
        AnimatedClass.__init__(self)
        SmallBlock.__init__(self, blockX, blockY)

    def draw(self):
        SmallLightBlock.draw(self)
        self.animate()

    def getImage(self):
        return self.image[self.frame]


class Chest(Block_Drop_Item):
    frameSpeed = 4
    maxFrame = 5

    image = []

    for i in range(1, maxFrame + 2):
        path = os.path.join("images", "chest", "wood", f'Frame {i}.png')
        image.append(imgLoad(path).convert_alpha())

    def __init__(self, x, y, items=None, gold=None):
        self.x, self.y = x, y

        self.opened = False
        self.opening = False
        self.frame = 0
        self.frameCooldown = self.frameSpeed
        self.flip = random.choice((-1, 1))

        # Put items in chest
        if items is None:
            self.items = []

        else:
            self.items = items

        if gold is None:
            self.goldQuantity = 0

        else:
            self.goldQuantity = gold

    def adjacentPlayer(self):
        if not (self.opening or self.opened):
            self.opening = True
            playSound(openChestSound)

    def open(self):
        if self.opening:
            if self.frameCooldown > 0:
                self.frameCooldown -= 1

            else:
                self.frameCooldown = self.frameSpeed
                self.frame += 1

                dirtyRects.append(pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE,
                                              BLOCK_SIZE, BLOCK_SIZE))

                if self.frame == self.maxFrame:
                    self.opened = True
                    self.opening = False

                    # Open chest
                    consoleText.addOutput(self.returnText())
                    chatText.addOutput(self.returnText())

                    XY_Coords = self.itemCoordinates(goldImage)
                    entities = dropGold(self.goldQuantity, XY_Coords)

                    for item in self.items[:]:
                        entities.append(DroppedItem(item, self.itemCoordinates(item.getSurface())))
                        self.items.remove(item)

                    assert len(self.items) == 0

    def draw(self):
        if self.opening:
            self.open()

        windowSurface.blit(pygame.transform.flip(self.image[blockGrid[x][y]['Data'].frame],
                                                 self.flip, 0), coords)

    def returnText(self):
        pass  # No console message by default


class CaveChest(Chest):
    def __init__(self, caveType, x, y):
        super().__init__(x, y)

        if caveType == '1':
            self.type = 'Gold'
            self.description = 'chest of gold'
            self.goldQuantity = random.randint(5, 10)

        elif caveType == '2':
            self.type = random.choice(('Wood', 'Gold'))

            if self.type == 'Wood':
                self.description = 'old wooden chest'
                self.goldQuantity = random.randint(2, 4)

            elif self.type == 'Gold':
                self.description = 'chest made of gold'
                self.goldQuantity = random.randint(7, 12)

        elif caveType == '3':
            self.type = random.randint(0, 24)

            if self.type in range(10):  # Odds are 2/5
                self.type = 'Wood'
                self.description = 'old wooden chest'
                self.goldQuantity = random.randint(2, 4)

            elif self.type in range(10, 20):  # Odds are 2/5
                self.type = 'Empty'
                self.description = 'empty chest'
                self.goldQuantity = 0

            elif self.type in range(20, 24):  # Odds are 4/25
                self.type = 'Gold'
                self.description = 'chest made of gold'
                self.goldQuantity = random.randint(7, 12)

            elif self.type == 24:  # Odds are 1/25
                self.type = 'Diamond'
                self.description = 'diamond chest'
                self.goldQuantity = 250

    def returnText(self):
        return (f'You find a {self.description}, there is {self.goldQuantity}' +
                ' gold inside.')


class Bat(PhysicsClass, AnimatedClass, HostileMob):
    frameSpeed = 1

    canFall = False

    def __init__(self, player):
        AnimatedClass.__init__(self)
        PhysicsClass.__init__(self)

        if player.location == 'Cave':
            self.aggressive = True

        elif player.location in ABANDONED_TOWN:
            self.aggressive = bool(random.randint(0, 1))

        self.flip = 1

        self.rect = self.image[self.frame].get_rect()

        self.rect.centerx = random.randint(0 + 250, INTERNAL_WIDTH - 250)
        self.rect.centery = random.randint(0 + 250, INTERNAL_WIDTH - 350)

        # Battle variables
        if player.caveType == '1':
            self.strength = 1

        elif player.caveType == '2':
            self.strength = 2

        elif player.caveType == '3':
            self.strength = 4

        self.health = self.maxHealth = 20

        self.goldGain = 10
        self.goldLoss = 20

        # Battle variables
        self.speed = random.uniform(0.8, 1.2) * 50
        HostileMob.__init__(self)

    def targetPlayer(self, player):
        self.targetPlayerX(player)
        self.targetPlayerY(player)

    def targetPlayerY(self, player):
        # TODO: moving the bat up should decrease the frame cooldown
        # while moving down increases the cooldown
        # Choose direction based on mob's position
        if player.rect.centery <= self.rect.centery:
            self.moveY(-80)

        elif player.rect.centery > self.rect.centery:
            self.moveY(80)

    def updateRect(self):
        self.rect.size = self.image[self.frame].get_size()


class BigBat(Bat):
    type = 'Big Bat'
    image = []
    maxFrame = 17

    for i in range(maxFrame + 1):
        path = os.path.join("images", "batBig", f'bat_{i}.png')
        image.append(imgLoad(path).convert_alpha())


class SmallBat(Bat):
    type = 'Small Bat'
    image = []
    maxFrame = 36

    for i in range(maxFrame + 1):
        j = str(i)
        while len(j) < 3:
            j = '0' + j

        path = os.path.join("images", "batSmall", f'bat_{j}.png')
        image.append(imgLoad(path).convert_alpha())


def outlineRect(rect, lineThickness):
    # Horizontal top
    pygame.draw.rect(windowSurface, RED,
                     pygame.Rect(rect.x, rect.y,
                                 rect.width, lineThickness))
    # Horizontal bottom
    pygame.draw.rect(windowSurface, RED,
                     pygame.Rect(rect.x, rect.bottom - lineThickness,
                                 rect.width, lineThickness))

    # Vertical left
    pygame.draw.rect(windowSurface, RED,
                     pygame.Rect(rect.x, rect.y,
                                 lineThickness, rect.height))

    # Vertical right
    pygame.draw.rect(windowSurface, RED,
                     pygame.Rect(rect.right - lineThickness, rect.y,
                                 lineThickness, rect.height))


def clearNPC_TradeOffers():
    for i in range(len(NPC_Trading['Counter Offer'])):
        NPC_Trading['Counter Offer'][i] = None

    NPC_Trading['Item Offer'] = None
    NPC_Trading['Gold Offer'] = None
    NPC_Trading['Gold Offer Label'] = None

    return NPC_Trading


class GoldGivenClass(TextRect):
    def __init__(self):
        path = os.path.join(*('images/menu/payUndergroundGuard/Left Arrow.png'.split('/')))
        self.leftArrowSurface = imgLoad(path)
        self.rightArrowSurface = pygame.transform.flip(self.leftArrowSurface, True, False)

        self.quantity = 5
        # self.update()

    def draw(self):
        windowSurface.blit(self.surface, self.rect)
        windowSurface.blit(self.leftArrowSurface,
                           self.leftArrowRect)

        windowSurface.blit(self.rightArrowSurface,
                           self.rightArrowRect)

    def update(self):
        # Defines self.surface and self.rect
        TextRect.__init__(self, font, str(self.quantity), GOLD, GREY)

        for sb in speechBubbles:
            if sb['ID'] == 'Pay Cave Guard':
                self.rect.centerx = sb['Rect'].centerx
                self.rect.bottom = sb['Rect'].bottom - 10

        self.leftArrowRect = self.leftArrowSurface.get_rect()
        self.rightArrowRect = self.rightArrowSurface.get_rect()

        self.leftArrowRect.right = self.rect.x - 5
        self.rightArrowRect.left = self.rect.right + 5

        self.leftArrowRect.centery = self.rect.centery
        self.rightArrowRect.centery = self.rect.centery


goldGiven = GoldGivenClass()


def playSound(sound, time=0):
    if options['sound']:
        sound.play(time)


def pickMusic(player):
    while True:
        if playerNearTowns(player, (SMALL_TOWN, SMALL_TOWN_HILLS, OUTPOST_TOWN,
                                    VOLCANIC_TOWN, QUIET_TOWN, BEACH_TOWN)):
            newMusic = random.choice(('Pippin the Hunchback Full Mix.ogg',
                                      'Suonatore di Liuto.ogg',
                                      'Teller of the Tales.ogg',
                                      'Folk Round.ogg'))
            newMusic = os.path.join("sound", "music", newMusic)

        elif playerNearTowns(player, (SECOND_TOWN, INDUSTRIAL_TOWN,
                                      CAPITAL_CITY, MINING_TOWN)):
            newMusic = random.choice(('Angevin B.ogg',
                                      'Thatched Villagers.ogg',
                                      'Minstrel Guild.ogg',
                                      'Celtic Impulse.ogg'))
            newMusic = os.path.join("sound", "music", newMusic)

        elif playerNearTowns(player, ABANDONED_TOWN):
            # TODO: add Constancy as possible music
            newMusic = 'sound/music/Comfortable Mystery.ogg'
            break

        elif player.location in ('Cave',) + DUNGEONS:
            if player.caveType == '3' or player.location in DUNGEONS:
                newMusic = random.choice(('Black Vortex.ogg',
                                          'Volatile Reaction.ogg',
                                          'Drums of the Deep.ogg'))

            else:
                newMusic = random.choice(('Night Cave.ogg',
                                          'Lord of the Land.ogg',
                                          'Skye Cuillin.ogg',
                                          'Comfortable Mystery.ogg'))
            newMusic = os.path.join("sound", "music", newMusic)

        elif player.location == UNDERGROUND_CITY:
            if undergroundCity['Lighting'] in ('Torches', 'Electric'):
                newMusic = {'Torches': fireplaceSoundPath,
                            'Electric': 'sound/music/Master of the Feast.ogg'}[undergroundCity['Lighting']]
                break

            elif undergroundCity['Lighting'] == 'Lava':
                newMusic = random.choice(('Industrial Revolution.ogg',
                                          'The Complex.ogg'))
                newMusic = os.path.join("sound", "music", newMusic)

        elif player.location == UNDERGROUND_CITY_EXIT:
            newMusic = fireplaceSoundPath
            break

        if newMusic != currentMusic:
            break

    return newMusic


def updateBlacksmithInfo(getDirtyRects):
    newRequiredItemSlots = requiredItemSlots

    for i, slot in enumerate(newRequiredItemSlots):
        # Player can't change blueprint while items are in requied items inventory
        assert pl_Info[PK()]['requiredItemInventory'][i] is None
        if getDirtyRects:
            dirtyRects.append(slot.copy())

    numberOfRequiredItemSlots = len(BLUEPRINT[selectedBlueprint]['Recipe'])
    newRequiredItemSlots = []
    MAX_ROW_LENGTH = 3  # Number of slots that can fit in a row
    ITEM_SLOT_GAP = 30
    columnCount = math.ceil(numberOfRequiredItemSlots / MAX_ROW_LENGTH)
    bigInventoryImageWidth = bigHighlightInventoryImage.get_size()[0]
    for y in range(columnCount):  # Iterate vertically
        # Find number of remaining slots left
        currentRowLength = numberOfRequiredItemSlots - y * MAX_ROW_LENGTH
        if currentRowLength > 3:
            currentRowLength = 3

        rowWidth = (bigInventoryImageWidth + ITEM_SLOT_GAP) * currentRowLength - ITEM_SLOT_GAP

        for x in range(currentRowLength):  # Iterate horizontally
            indice = y * MAX_ROW_LENGTH + x
            requiredItem = Item(BLUEPRINT[selectedBlueprint]['Recipe'][indice])

            startX = BLACKSMITH_CRAFTING_LINE - rowWidth / 2
            rectX = startX + (bigInventoryImageWidth + ITEM_SLOT_GAP) * x

            initialY = blacksmithRequiredItemsSection.rect.y + 15
            offsetY = (ITEM_SLOT_GAP + bigHighlightInventoryImage.get_size()[1]) * y

            rect = pygame.Rect((rectX, initialY + offsetY), bigHighlightInventoryImage.get_size())
            newRequiredItemSlots.append({'Rect': rect.copy(),
                                         'Desired Item': requiredItem,
                                         'Inventory': None})

    if getDirtyRects:
        for i, slot in enumerate(newRequiredItemSlots):
            dirtyRects.append(slot)

        return dirtyRects, newRequiredItemSlots

    else:
        return newRequiredItemSlots


def emptyBlacksmithInventory(player):
    newDirtyRects = dirtyRects
    for slot in requiredItemSlots:
        if slot['Inventory'] is not None:
            (player,
             newDirtyRects) = appendPlayerInventory(slot['Inventory'], player=player,
                                                    returnDirtyRects=True)

    return player, newDirtyRects


def leaveBlacksmith(player):
    gamemode, loadScreenOnce = leaveBuilding()
    player, dirtyRects = emptyBlacksmithInventory(player)

    return gamemode, loadScreenOnce, player


def toggleLightingMode(newLightingMode):
    optionFile['Lighting'] = newLightingMode

    text = 'Lighting - ' + newLightingMode
    optionButtons['Lighting'].changeText(text, menuFont)

    return (newLightingMode, optionFile['Lighting'],
            optionButtons['Lighting'])


def toggleFullscreen():
    newFullscreenOn = not options['fullscreen']
    DEFAULT_FLAG = pygame.DOUBLEBUF | pygame.HWSURFACE

    if newFullscreenOn:
        flag = DEFAULT_FLAG | pygame.FULLSCREEN

    else:
        flag = DEFAULT_FLAG

    pygame.display.set_mode(INTERNAL_SIZE, flag)


    optionFile['fullscreen'] = newFullscreenOn
    optionButtons['fullscreen'].updateText()

    loadScreenOnce = False
    # This will give some time for the screen to change and wait to go through
    # main loop a second time before a fullscreen refresh

    return (newFullscreenOn, optionFile['fullscreen'],
            optionButtons['fullscreen'],
            loadScreenOnce)


def randomGuardKeeperMessage():
    return random.choice(('Good luck with your adventure...',
                          'This world is vast, and it feels like it\'s always expanding!',
                          'Did you hear about the city to the land of the North? They have useful supplies.',
                          'You look prepared, are you going far away? Don\'t fall off the world!',
                          'Thank you for your payment... I don\'t get payed enough...',
                          'It is rumoured that there is a city of gold underground near the core.'
                          ))


def randomGuardSuperiorMessage():
    return random.choice(('If you don\'t make it, let me inherit the rest of your gold!',
                          'There have been countless people like you, good luck.',
                          'I honestly think it is foolish to try and enter a cave for some money... I get paid standing here...',
                          'Wait a moment, you plan on going to the caves? That\'s suicide...',
                          'Now hurry up! You\'re lucky you came here late, I used to charge 20 gold just to leave this place!'
                          ))


def randomGuardSuperiorCaveOpinion(player):
    return ('Ok you\'ve chosen the small cave, only one sane people pick...',
            'You\'ve picked the labyrinth, and why are you going alone?',
            'I know the economy is bad but...')[int(player.caveType) - 1]


GOLDEN_RATIO = (1 + 5 ** 0.5) / 2

CITY_SPEECHES = ('Did you know that the holes in some of the '
                 'caves are caused by explosives used to kill'
                 ' monsters? I\'ve never seen someone'
                 ' actually have explosives though...',

                 'There\'s a story that someone went to buy stocks and'
                 ' realized they ran out of money and couldn\'t leave'
                 ' the city... because they were in the small town...',

                 'Mining can be a profitable business despite how '
                 'expensive those pickaxes are. Just imagine how '
                 'lucky you would be to be given or find one for free...',

                 'Someone once claimed they were killed by a '
                 'dragon in the third cave and woke up in a '
                 'strange place. Of course that is nonsense...',

                 'Rumour has it that people have built an entire '
                 'underground city with advanced technology.'
                 'Imagine the money from selling something from '
                 'that strange place...',

                 'Some people think that the underground city '
                 'exists. That is crazy and the idea of anything'
                 ' being powered by steam is impossible... fire'
                 ' and water working together?',

                 'A day lasts 20 minutes but the time of day '
                 'matters only to those who depend on it... I '
                 'mean what if you are a miner? No point in a watch...',

                 'The world is vast with many cities, but '
                 'invisible force fields seem to be everywhere...',

                 'Here\'s a question that those librarians don\'t'
                 ' want you to ask. How do they know everything'
                 ' we do, are they and how are they watching us?',

                 'I\'ve recently heard that miners have uncovered'
                 ' strange artifacts from aliens or the future, such '
                 'as fast mining pickaxes or flesh slicing swords...',

                 'Someone once said that there must be parallel '
                 'universes. I can\'t imagine other worlds, let alone '
                 'five which are the same world but slightly different...',
                 # Refers to a bug in the old text game in which
                 # stores would not check if item existed
                 'A long time ago, stores tried to sell '
                 'people... they made 0 gold...',

                 'The libraries provide a memory of each cave. '
                 'Although like memory it is full of errors '
                 'no one will ever notice...',

                 'Even though golden ingots don\'t actually do '
                 'anything, you can try buying low and selling '
                 'high like stocks.'
                 )


def createSpeech(player, entity, type=None):
    speechBubble = {}
    if entity.type == 'Villager':
        if type == 'Altruist':
            text = ('Here, have 5 gold. I think you need it more than I do. '
                    'Maybe one day, someone else may need a favour from you...')

        else:
            text = random.choice(CITY_SPEECHES)

        speechBubble['Function'] = 'Click to Close'
        speechBubble['ID'] = 'City Speech'

    elif entity.type == 'Guard':
        text = f'Guard {entity.ID}: '

        if entity.ID == 'Keeper' and not player.canPassGuardKeeper:
            text += ('You need to pay 5 gold to leave the city. '
                     '(Click speech bubble to accept)')
            # TODO: Add support for enter
            #text += 'You need to pay 5 gold to leave the city. (Click or press enter to accept)'
            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Pay Guard'

        elif entity.ID == 'Keeper' and player.canPassGuardKeeper:
            text += randomGuardKeeperMessage()

            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Guard Final Speech'

        elif entity.ID == 'Superior' and entity.showThirdMessage:
            # Placement of elif keeps this running at right time
            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Guard Cave Opinion'

            text = randomGuardSuperiorMessage()

        elif entity.ID == 'Superior' and not player.canPassGuardSuperior:
            text += ('Which of the three caves are you going to? 1, 2, or 3?'
                     ' (Use keyboard or click to select)')
            # Cannot be closed, must select cave type with keyboard
            speechBubble['Function'] = None
            speechBubble['ID'] = 'Choose Cave'

        elif entity.ID == 'Superior' and player.canPassGuardSuperior:
            text += randomGuardSuperiorCaveOpinion(players[PK()])

            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Guard Cave Opinion'

    elif entity.type == 'Cave Guard':
        text = 'Tunnel Manager: '
        if type == 'Not Enough Gold':
            text += ('You do not have enough money to begin an expedition.'
                     ' You need to spend 5 gold to leave the city.')

            speechBubble['Function'] = 'Unclosable'
            speechBubble['Not Enough Gold']

        elif type == 'Initial':
            text += ('I hope you already know that you need'
                     ' to pay to leave so we can keep this place running...'
                     ' How much gold do you want to give us?')

            speechBubble['Function'] = 'Pay Guard'
            speechBubble['ID'] = 'Pay Cave Guard'

        elif type == 'Too Much Gold':
            if goldGiven.quantity > 5:
                text += ('I appreciate your generosity but you don\'t have'
                         ' ' + str(goldGiven.quantity) + ' gold, please give '
                         'a smaller amount.')

            elif goldGiven.quantity == 5:
                text += ('I\'m sorry but you do not have the required 5 gold'
                         ' pass... No exceptions.')

            speechBubble['Function'] = 'Pay Guard'
            speechBubble['ID'] = 'Pay Cave Guard'

        elif type == 'Talk about goldGiven':
            if goldGiven.quantity == 5:
                text += ('I know that\'s the minimum and you\'re allowed to'
                         ' that, but we really need it!')
            elif goldGiven.quantity in range(5, 11):  # 5-10
                text += 'Thank you for the payment it really helps!'
            elif goldGiven.quantity in range(11, 26):  # 11-25
                text += ('Your generosity is really appreciated,'
                         ' it helps maintain our city.')
            elif goldGiven.quantity in range(26, 101):  # 26-100
                text += ('I can tell you\'re probably an experienced rich'
                         ' explorer, or just very generous.')
            elif goldGiven.quantity in range(101, 301):  # 101-300
                text += ('Thank you so much! Next time you come back we'
                         ' might have an upgrade!')
            else:
                text += ('Tell me, where did you find that gold? I won\'t tell anyone.')

            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Gold Given Opinion'

        elif type == 'Leaving Message':
            text += random.choice(('Tunnel Manager: Good luck with your'
                                   ' adventure, beware of the dragon!',

                                   'Tunnel Manager: Remember that the cave is '
                                   'unstable, ceilings fall and floors crumble.',

                                   'Tunnel Manager: Keep on the lookout for '
                                   'ores, some believe the value might increase.',

                                   'Tunnel Manager: It has been rumoured that '
                                   'there is a place where people who don\'t '
                                   'live underground...',

                                   'Tunnel Manager: You should come back '
                                   'again, this place always evolves.',

                                   'Tunnel Manager: People come and go, with '
                                   'our city\'s inventory ever changing...'))

            speechBubble['Function'] = 'Click to Close'
            speechBubble['ID'] = 'Leaving Message'

    # TODO: have the size of bubble vary depending on size of text
    speechBubble['Height'] = 110
    speechBubble['Width'] = round(speechBubble['Height'] * GOLDEN_RATIO)

    speechBubble['Rect'] = pygame.Rect(entity.rect.centerx - speechBubble['Width'] / 2 +
                                       # Center above entity and then shift randomly
                                       random.randint(-30, 30),
                                       # Subtract by height and then additional spacing above villager
                                       entity.rect.top - speechBubble['Height'] - 30,
                                       speechBubble['Width'], speechBubble['Height'])

    speechBubble['Text'] = text

    # Make sure text box doesn't go off screen
    if speechBubble['Rect'].left < 0:
        speechBubble['Rect'].left = 0

    elif speechBubble['Rect'].right > INTERNAL_WIDTH - 1:
        speechBubble['Rect'].right = INTERNAL_WIDTH - 1

    # Points 1 start at top centerx of entity to begin speech bubble
    speechBubble['Triangle'] = [*entity.rect.midtop,
                                speechBubble['Rect'].centerx - 12,
                                speechBubble['Rect'].bottom,
                                speechBubble['Rect'].centerx + 12,
                                speechBubble['Rect'].bottom
                                ]

    speechBubble['Dirty Rects'] = (speechBubble['Rect'],
                                   pygame.Rect(speechBubble['Triangle'][2],  # Farthest left
                                               # Bottom of rect, top of triangle
                                               speechBubble['Rect'].bottom,
                                               # Twice the distance of triangle from center (width of triangle)
                                               12 * 2, entity.rect.top - speechBubble['Rect'].bottom
                                               ))

    return speechBubble

# Refactored http://www.pygame.org/wiki/TextWrap


def drawWrappedText(surface, text, color, rect, font, bgColour=None):
    antialiasing = True
    y = rect.top
    lineSpacing = 0

    # get the height of the font
    fontHeight = font.size("Tg")[1]

    line_count = 0
    while text:
        i = 1

        # determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break

        # determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1

        # if we've wrapped the text, then adjust the wrap to the last word
        if i < len(text):
            i = text.rfind(" ", 0, i) + 1

        blitText = text[:i]
        # render the line and blit it to the surface
        if bgColour:
            image = font.render(blitText, 1, color, bgColour)
            image.set_colorkey(bgColour)
        else:
            image = font.render(blitText, antialiasing, color)

        surface.blit(image, (rect.left, y))
        y += fontHeight + lineSpacing

        # remove the text we just blitted
        text = text[i:]
        line_count += 1

    return line_count


def consoleIntroText(player, single_pl_Info, type):
    output = None
    if type == 'Bank':
        output = ('Welcome to the Bank, you can loan money here to extend '
                  'the duration of your mission.',

                  'You currently have ' + str(single_pl_Info['bankBalance']) + ' gold in '
                  'the bank and ' + str(player.gold) + ' gold on you.',
                  'Type "Deposit, "Withdraw", or "View Balance."')

    elif type == 'Library':
        if len(single_pl_Info['caveAdventures']) == 0:
            output = ('The library is currently closed...',)

        else:
            output = ('Welcome to the Library, here you can view the records'
                      ' of every event you experienced in the cave.',

                      'You have survived, ' +
                      str(len(single_pl_Info['caveAdventures'])) +
                      ' adventures. Type "View History" or "Leave."')

    elif type == 'Market':
        output = ('Welcome to the Market, you can buy and sell things here'
                  ' using your very valuable gold!',

                  'You currently have a ' +
                  cleanInventory(player.inventory)['Str'] +
                  ' and ' + str(player.gold) + ' gold on you.',

                  'Type "Buy/Sell", "View Merchandise".')

    elif type == 'Stock Market':
        output = ('Welcome to the Stock Market!',
                  'Here you can buy stocks and watch their value fluctuate!',
                  'If you\'re lucky you might become rich, just be a little careful.',
                  '',
                  'You currently have ' +
                  str(len(single_pl_Info['stockInv'])) + ' stocks.',
                  'Type "Buy/Sell", or "View Stocks."')

    elif type == 'Warehouse':
        output = ('Welcome to the Warehouse! You can deposit your '
                  'items for safekeeping if you don\'t want it.',

                  'You currently have a ' +
                  cleanInventory(player.inventory)['Len'] + ' items in '
                  'your inventory and ' +
                  cleanInventory(single_pl_Info['warehouseInv'])['Len'] +
                  ' items with me!',

                  'Type "Deposit/Withdraw", "View Inside".')

    # TODO - Make a variable for all new towns or old towns
    elif (type in ('Forge', 'Blacksmith') or
          (type in TOWN_STRINGS + ABANDONED_TOWN and type not in OLD_TOWNS)):
        # These are new areas in the game which did not exist in the text version
        pass

    elif type == SMALL_TOWN:
        output = ('',
                  'You are in a small town, ready to plan your adventure...',

                  'There are 3 buildings here you can enter, the bank,'
                  ' the market, and the library.',

                  'Type "Goto Bank/Library/Market", "Continue Quest."')

    elif type == SECOND_TOWN:
        output = ('',
                  'You are in a large town, ready to continue your adventure...',

                  'There are 5 buildings here you can enter, the bank,'
                  ' the market, and the library.',

                  'Type "Goto Bank/Library/Market/Stock Market/Warehouse",'
                  ' "Continue Quest."')

    elif type == UNDERGROUND_CITY:
        output = ('',
                  'You are in an underground city, ready to continue your'
                  ' adventure...',

                  'There is 1 building here you can enter... the market.',

                  'Type "Goto Market", "View City Information", "Continue Quest."')

    elif type == 'Underground Market':
        output = ('Welcome to the Market, you can buy and sell things here'
                  ' at record prices!',

                  'You currently have a ' +
                  cleanInventory(player.inventory)['Str'] + ' and ' +
                  str(player.gold) + ' gold on you.',

                  'Type "Buy/Sell", "View Merchandise".')

    else:
        raise ValueError

    if output is not None:
        for text in output:
            addLegacyOutput(text)


def removeFile(filePath):
    try:
        os.remove(filePath)

    except FileNotFoundError:
        pass


def resetCaveData(player, mapData):
    player.caveDepth = 'N/A'
    player.caveType = 'N/A'
    player.direction = 'N/A'
    mapData['caveEnvironment'] = None

    return player, mapData


def addLegacyOutput(text):
    consoleText.addOutput(text)
    chatText.addOutput(text)

# Only when completing cave without dying


def finishCave(player, single_pl_Info):
    single_pl_Info['bankBalance'] = round(
        single_pl_Info['bankBalance'] * (1 + player.caveDepth / 100))
    single_pl_Info['oldBankBalance'] = bankGraph.appendData(single_pl_Info['oldBankBalance'],
                                                            single_pl_Info['bankBalance'])
    marketBaseValue = newMarketValue(oldMarketBaseValue)[0]
    newStocks = updateStockValue()

    # TODO: Represent this as a temporary brightening of the screen + chat
    if player.caveType == '1':
        firstMessage = 'After a "short" adventure through the cave, you finally reached the end.'
    elif player.caveType == '2':
        firstMessage = 'After a "long" expedition through the labyrinth, you finally reached the end.'
    elif player.caveType == '3':
        firstMessage = 'Some adventurers gave up, but after your eternal voyage you finally make it through.'

    secondMessage = random.choice(('The feeling of the sun on your back '
                                   'provides renewed strength from the cold cave.',

                                   'The bright blue sky above you welcomes '
                                   'you back home as you see colour once again.',

                                   'You think you hear someone, but '
                                   'perhaps it was only an echo...',

                                   'You find yourself looking back to a cave,'
                                   ' and forward to the vast landscape.',

                                   # TODO: Model cave as parabola with flat grass on other side
                                   'With the pitch black cave behind you, '
                                   'you decide to continue forward.'))

    thirdMessage = random.choice(('You see the small town in the distance and'
                                  ' follow the paved road back...',

                                  'You walk through the forest with the town in '
                                  'sight, getting ready to tell your adventures...',

                                  # TODO Add glow gradient from side of screen opposite of cave
                                  'The lights glow from the town to which you'
                                  ' tiredly stumble forward...',

                                  # In background, put an image of a city with lights
                                  'Now that the town is in sight '
                                  'you walk towards the light...',

                                  'You see the city in the distance and run '
                                  'with all your strength from the darkness'
                                  ' which follows...'))

    for text in (firstMessage, secondMessage, thirdMessage):
        addLegacyOutput(text)

    consoleText.addOutput('')
    addLegacyOutput('You travel back to the ' + player.location.lower() + '.')
    consoleText.addOutput('')

    return (single_pl_Info, marketBaseValue,
            consoleText, newStocks)


def loadSkyImage(fileName):
    path = os.path.join("images", "sky", fileName)
    HALF_HEIGHT = INTERNAL_HEIGHT // 2

    image = pygame.transform.smoothscale(imgLoad(path),
                                         (INTERNAL_WIDTH, HALF_HEIGHT))
    flipped = pygame.transform.flip(image, 0, 1)  # Don't flip x and flip y

    full_surface = pygame.Surface(INTERNAL_SIZE)
    full_surface.blit(image, (0, 0))
    full_surface.blit(flipped, (0, HALF_HEIGHT))

    return full_surface


clearBlueSky = loadSkyImage('clear-blue.png')
duskSunsetSky = loadSkyImage('dusk-sunset.png')
earlySunriseSky = loadSkyImage('early-sunrise.png')
horizonHazeSky = loadSkyImage('horizon-haze.png')
nightBlueSky = loadSkyImage('night-blue.png')
polarizedSky = loadSkyImage('polarized.png')
purpleNightSky = loadSkyImage('purple-night.png')
purpleSunsetSky = loadSkyImage('purple-sunset.png')


def blend_colour(COLOUR_BLEND_MODE, initialColour, finalColour, percentage):
    if COLOUR_BLEND_MODE == 'RGB':
        return (initialColour[0] + (finalColour[0] - initialColour[0]) * percentage,
                initialColour[1] + (finalColour[1] - initialColour[1]) * percentage,
                initialColour[2] + (finalColour[2] - initialColour[2]) * percentage)

    elif COLOUR_BLEND_MODE == 'HSL':
        initial_H, initial_S, initial_V, initial_A = initialColour.hsva
        final_H, final_S, final_V, final_A = finalColour.hsva

        newColour = BLACK  # Arbitrary
        newColour.hsva = (initial_H + (final_H - initial_H) * percentage,
                          initial_S + (final_S - initial_S) * percentage,
                          initial_V + (final_V - initial_V) * percentage,
                          initial_A + (final_A - initial_A) * percentage)

        return newColour

    else:
        assert False

class Sky:
    BOUNDS = {'LeftBounds': 100,
              'RightBounds': INTERNAL_WIDTH - 100}

    BOUNDS['Centre'] = (BOUNDS['LeftBounds'] + BOUNDS['RightBounds']) / 2
    BOUNDS['Diameter'] = BOUNDS['RightBounds'] - BOUNDS['LeftBounds']

    SUN_IMAGE = imgLoad('images/sun.png').convert_alpha()
    MOON_IMAGE = imgLoad('images/moon.png').convert_alpha()

    def __init__(self):
        self.sunRect = Sky.SUN_IMAGE.get_rect()
        self.moonRect = Sky.MOON_IMAGE.get_rect()

    def draw(self, timeTick, timePhase, groundY, windowSurface):
        # Display sky image
        initialSky = Sky._get_image(timeTick)
        finalSky = Sky._get_image(timeTick + SKY_FADE_TIME)

        windowSurface.blit(initialSky, (0, 0))

        assert not timeTick >= DAY_LENGTH
        self.moveSunAndMoon(timeTick, groundY)

        # Don't display sun and moon if below horizon
        dirtyRects = []
        if self.sunRect.top <= groundY:
            windowSurface.blit(Sky.SUN_IMAGE, self.sunRect)
            dirtyRects.append(self.sunRect)

        if self.moonRect.top <= groundY:
            windowSurface.blit(Sky.MOON_IMAGE, self.moonRect)
            dirtyRects.append(self.moonRect)

        return dirtyRects

    @staticmethod
    def _get_image(timeTick):
        while timeTick < 0:
            timeTick += DAY_LENGTH

        while timeTick >= DAY_LENGTH:
            timeTick %= DAY_LENGTH

        if 0 <= timeTick < SUNSET_START:
            sky = clearBlueSky

        elif SUNSET_START <= timeTick < SUNSET_END:
            sky = duskSunsetSky

        elif SUNSET_END <= timeTick < POLARIZED_NIGHT_START:
            sky = nightBlueSky

        elif POLARIZED_NIGHT_START <= timeTick < POLARIZED_NIGHT_END:
            sky = polarizedSky

        elif POLARIZED_NIGHT_END <= timeTick < SUNRISE_START:
            sky = nightBlueSky

        elif SUNRISE_START <= timeTick:
            sky = earlySunriseSky

        return sky

    @classmethod
    def _get_gradient(cls, timeTick, timePhase):  # Calculate the colour of the sky
        # When setting fill colour, first and third colours are being faded out and second is being transitioned to
        if timePhase == 'Sunrise':
            # Early sunrise, dark to orange
            if timeTick <= SUNRISE_START + SUNRISE_LENGTH / 2:
                # Current time subtracted by time when sunrise begins
                timeTickDifference = timeTick - SUNRISE_START

            else:  # Late sunrise, orange to sky
                # Subtract by time when sunrise is half complete (phase 2 begins)
                timeTickDifference = timeTick - SUNRISE_START - SUNRISE_LENGTH / 2

        elif timePhase == 'Sunset':
            if timeTick <= SUNSET_START + SUNRISE_LENGTH / 2:
                timeTickDifference = timeTick - SUNSET_START

            else:
                timeTickDifference = timeTick - SUNSET_START - SUNRISE_LENGTH / 2

    def moveSunAndMoon(self, timeTick, groundY):
        # Value such that time tick can be changed into the height of celestial object
        SCALE_FACTOR = DAY_LENGTH / TAU

        shifted = timeTick + DAY_LENGTH / 2 - SUNRISE_END
        sunMovement = shifted / SCALE_FACTOR
        moonMovement = (shifted + DAY_LENGTH / 2) / SCALE_FACTOR

        self.sunRect.centery = groundY * (1 + math.sin(sunMovement))
        self.moonRect.centery = groundY * (1 + math.sin(moonMovement))

        RADIUS = Sky.BOUNDS['Diameter'] / 2

        self.sunRect.centerx = RADIUS * math.cos(sunMovement) + Sky.BOUNDS['Centre']
        self.moonRect.centerx = RADIUS * math.cos(moonMovement) + Sky.BOUNDS['Centre']


sky = Sky()

# For transitioning between sky images
SUNRISE_END_FADE_START = DAY_LENGTH - SKY_FADE_TIME / 2
SUNRISE_END_FADE_END = SKY_FADE_TIME / 2

SUNSET_START_FADE_START = SUNSET_START - SKY_FADE_TIME / 2
SUNSET_START_FADE_END = SUNSET_START + SKY_FADE_TIME / 2

SUNSET_END_FADE_START = SUNSET_END - SKY_FADE_TIME / 2
SUNSET_END_FADE_END = SUNSET_END + SKY_FADE_TIME / 2

POLARIZED_START_FADE_START = POLARIZED_NIGHT_START - SKY_FADE_TIME / 2
POLARIZED_START_FADE_END = POLARIZED_NIGHT_START + SKY_FADE_TIME / 2

POLARIZED_END_FADE_START = POLARIZED_NIGHT_END - SKY_FADE_TIME / 2
POLARIZED_END_FADE_END = POLARIZED_NIGHT_END + SKY_FADE_TIME / 2

SUNRISE_START_FADE_START = SUNRISE_START - SKY_FADE_TIME / 2
SUNRISE_START_FADE_END = SUNRISE_START + SKY_FADE_TIME / 2


LAVA_DAMAGE = FPS / 40 * 4


def leaveUndergroundCity(player):
    (blockGrid, backgroundBlocks,
     mapData) = undergroundCity['Old Cave Data']

    # ambientSounds = (function to take cave environment and return ambientSound file)

    undergroundCity['Old Cave Data'] = None
    addLegacyOutput('You walk through the tunnel to the other end.')
    entities = []

    player.setLocation('Cave')

    return (blockGrid, backgroundBlocks, ambientSounds, mapData,
            undergroundCity['Old Cave Data'], entities, player)


def updateLibraryCaveInfo(single_pl_Info):
    caveAdventures = single_pl_Info['caveAdventures']

    text = 'Cave Size - ' + str(len(caveAdventures[selectedAdventure - 1]['Compartment']))
    libraryCaveInfoMenu['Cave Size'] = TextRect(font, text, WHITE, DARK_GREY)
    libraryCaveInfoMenu['Cave Size'].rect.top = libraryCaveInfoMenu['Background Rect'].top + 12
    libraryCaveInfoMenu['Cave Size'].rect.x = libraryCaveInfoMenu['Background Rect'].x + 15

    text = 'Cave Type - ' + caveAdventures[selectedAdventure - 1]['Type']
    libraryCaveInfoMenu['Cave Type'] = TextRect(font, text, WHITE, DARK_GREY)
    libraryCaveInfoMenu['Cave Type'].rect.top = libraryCaveInfoMenu['Background Rect'].top + 32
    libraryCaveInfoMenu['Cave Type'].rect.x = libraryCaveInfoMenu['Background Rect'].x + 15

    return libraryCaveInfoMenu


def loadLibrary():
    gamemode = 'Library'
    adventureSelection, dirtyRects = updateAdventureSelection(pl_Info[PK()]['caveAdventures'])
    libraryCaveInfoMenu = updateLibraryCaveInfo(pl_Info[PK()])
    compartmentSelection, cavePreview['Surface'] = updateCompartmentSelection(
        pl_Info[PK()]['caveAdventures'])

    return (gamemode, adventureSelection, libraryCaveInfoMenu,
            compartmentSelection, dirtyRects)


def getUndergroundLightingInfo():
    if undergroundCity['Lighting'] == 'Torches':
        return 'The base is lit up by torches put on the walls and floor.'
    elif undergroundCity['Lighting'] == 'Electric':  # Represents an Arch-Lamp
        return 'The base is lit by a giant tower which shines a brilliant light which commands all lightning.'
    elif undergroundCity['Lighting'] == 'Lava':
        return 'The city is kept in "daylight" with a ceiling of lava and glass to let it shine through.'


def loadUndergroundCityExit(player):
    global mapData
    player.setLocation(UNDERGROUND_CITY_EXIT)

    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()
    mapData['levelDarkness'] = 100

    # Generate map
    for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
        # Ceiling
        for y in range(12):
            blockGrid[x][y]['Type'] = 'Stone'

        for y in range(18, 24):
            blockGrid[x][y]['Type'] = 'Stone'

    mapData['groundY'] = 18 * BLOCK_SIZE

    entities = []
    entities.append(CaveGuard(mapData['groundY']))
    player.canPassCaveGuard = False
    player.payingCaveGuard = False

    goldGiven.update()

    return (player, ambientSounds, blockGrid,
            mapData, backgroundBlocks,
            entities, goldGiven)


def upgradeUndergroundCity(undergroundCity):
    # Attempt to upgrade city
    attemptedUpgrade = random.randint(1, 2)
    if attemptedUpgrade == 1:  # Upgrade lights
        if (undergroundCity['Lighting'] == 'Torches' and
                undergroundCity['Taxes'] >= 300):

            undergroundCity['Lighting'] = 'Electric'
            undergroundCity['Taxes'] -= 300

        elif (undergroundCity['Lighting'] == 'Electric' and
              undergroundCity['Taxes'] >= 1000):

            undergroundCity['Lighting'] = 'Lava'
            undergroundCity['Taxes'] -= 1000

    elif attemptedUpgrade == 2:
        if ('Blacksmith' not in undergroundCity['Buildings'] and
                undergroundCity['Taxes'] >= 1000):

            undergroundCity['Buildings'].append('Blacksmith')
            undergroundCity['Taxes'] -= 1000

    return undergroundCity


def loadUndergroundCity(player, single_pl_Info):
    global mapData
    # Allows spawnEntity to work without requiring groundY to be
    # given as a parameter through multiple scopes

    # This allows oldCaveData to work
    global blockGrid, backgroundBlocks, mapData

    newOldCaveData = oldCaveData
    player.setLocation(UNDERGROUND_CITY)
    player.rect.bottom = mapData['groundY']

    if player.previousLocation == 'Cave':
        newOldCaveData = (blockGrid,
                          backgroundBlocks, mapData)

    (ambientSounds, blockGrid, mapData, backgroundBlocks,
     entities, caveBackground) = generateUndergroundCity()

    # Make number depend on prosperity of city
    entities = []
    entities = spawnEntity(entities, 5, 'Explorer', bottomCoord=mapData['groundY'])
    consoleIntroText(player, single_pl_Info, UNDERGROUND_CITY)
    addLegacyOutput(getUndergroundLightingInfo())

    return (player, ambientSounds, blockGrid,
            mapData, backgroundBlocks,
            entities, newOldCaveData)


def makeClouds(player, entities):
    # TODO:, make clouds stay when moving from town to guard post
    # Only generates new clouds when not coming from outside
    if (player.location in OUTSIDE_LOCATIONS and
            player.location not in ABANDONED_TOWN):
        entities = spawnEntity(entities, random.randint(5, 15), 'Cloud')

    elif (player.location in ABANDONED_TOWN and
          player.location != ABANDONED_TOWN_RIGHT):
        # Make red large clouds in the future
        entities = spawnEntity(entities, random.randint(15, 25), 'Cloud')

    return entities


def enterNewCave(player, single_pl_Info):
    (player,
     newAmbientSounds, blockGrid, mapData,
     backgroundBlocks, entities, consoleText,
     caveBackground, chatText) = enterCave(player)

    addLegacyOutput('Guard Superior: ' +
                    randomGuardSuperiorCaveOpinion(player))
    addLegacyOutput('Guard Superior: ' +
                    randomGuardSuperiorMessage())

    single_pl_Info['caveAdventures'].append({'Type': player.caveType,
                                             'Compartment': []})

    if player.caveType == '1':
        caveSize = random.randint(8, 12)
        addLegacyOutput('You have begun your adventure'
                        ' by entering the small cave.')
    elif player.caveType == '2':
        caveSize = random.randint(15, 25)
        addLegacyOutput('You have begun your adventure'
                        ' in the large cave.')
    elif player.caveType == '3':
        caveSize = 50
        addLegacyOutput('You have begun your adventure'
                        ' through the legendary cave.')

    player.caveDepth = 0

    return (player, single_pl_Info, newAmbientSounds,
            blockGrid, mapData, backgroundBlocks,
            entities, caveBackground, caveSize, consoleText,
            chatText)


def spawnEntity(entities, quantity, type, xCoord=None, bottomCoord=None):
    player = players[PK()]

    for i in range(quantity):
        if type == 'Villager':
            entities.append(Villager(bottomCoord))

        elif type == 'Dragon':
            entities.append(Dragon(player))

        elif type == 'Shadow Dragon':
            entities.append(ShadowDragon(player))

        elif type == 'Explorer':
            entities.append(Explorer(bottomCoord))

        elif type == 'Shadow Explorer':
            entities.append(ShadowExplorer(player))

        elif type == 'Cloud':
            entities.append(Cloud())

        elif type == 'Big Bat':
            entities.append(BigBat(player))

        elif type == 'Small Bat':
            entities.append(SmallBat(player))

        elif type == 'Slime':
            assert bottomCoord is not None
            entities.append(Slime(player, bottomCoord))

    return entities


def randomRound():
    # Adds some randomness by changing how game rounds
    return random.choice((mathFloor, math.ceil,
                          round))  # Default rounding function


def makeCaveFragile(leftBounds, rightBounds, blockGrid):
    '''
    Caves have 8 block of stone at top and bottom
    This function makes it so that caves have a decreasing probability
    of having fragile stone as you move away from the surface
    '''
    # +1 includes blocks at rightBounds
    for x in range(leftBounds, rightBounds + 1):
        for y in range(len(blockGrid)):
            if y <= 7:
                distanceFromAir = 7 - y

            elif y >= 16:
                distanceFromAir = y - 16

            else:
                distanceFromAir = 0

            # Don't influence blocks more than 4 blocks from air
            if distanceFromAir > 4:
                continue

            # Any blocks that are sticking out from where a flat cave would be
            randomChance = 0.45 * math.sqrt(-distanceFromAir + 4)

            # If random chance of making fragile succeeds
            if random.uniform(0, 1) < randomChance:
                if blockGrid[x][y]['Type'] == 'Stone':
                    blockGrid[x][y] = makeFragileStone(x, y)

                elif blockGrid[x][y]['Type'] in oreList:
                    blockGrid[x][y]['Data'].setQuality('Poor')

    return blockGrid


def makeSandCave(leftBounds, rightBounds, blockGrid):
    for x in range(leftBounds, rightBounds + 1):
        if random.randint(0, 1):
            blockGrid[x][16]['Type'] = 'Sandy Stone'

    return blockGrid


def generateOres(player, leftBounds, rightBounds, blockGrid):
    seedType = random.randint(0, 2)

    if player.caveType == '2':
        oreType = random.choice(REGULAR_ORES + ('Iron',))

    elif player.caveType == '3':
        oreType = random.choice(RARE_ORES + ('Iron',))

    oreQuality = random.choice(ORE_QUALITIES)

    if oreType == 'Iron':
        ore = oreType

    else:
        ore = oreQuality + ' ' + oreType

    x = random.randint(leftBounds, rightBounds)
    y = 16  # The floor

    '''
     --Brush ore
     #
    ###
     #
     --Square ore
    ##
    ##
    '''

    if seedType == 0:  # Brush
        for i in range(-1, 2):  # -1 to +1
            #Top, middle, bottom
            if blockGrid[x][y + i]["Type"] == "Stone":
                blockGrid[x][y + i]["Type"] = ore
                blockGrid[x][y + i]["Data"] = Ore(x, y + i, oreType, oreQuality)

        for i in (-1, 1):  # Left and right
            if blockGrid[x + i][y]["Type"] == "Stone":
                blockGrid[x + i][y]["Type"] = ore
                blockGrid[x + i][y]["Data"] = Ore(x + i, y, oreType, oreQuality)

    elif seedType == 1:  # Square
        y += random.randint(0, 1)
        for i in (0, 1):
            for j in (0, 1):
                if blockGrid[x + i][y + j]["Type"] == "Stone":
                    blockGrid[x + i][y + j]["Type"] = ore
                    blockGrid[x + i][y + j]["Data"] = Ore(x + i, y + j, oreType, oreQuality)

    elif seedType == 2:  # Spread over floor
        for i in range(4):
            x = random.randint(0 + 2, INTERNAL_WIDTH / BLOCK_SIZE - 2)
            if blockGrid[x][y]["Type"] == "Stone":
                blockGrid[x][y]["Type"] = ore
                blockGrid[x][y]["Data"] = Ore(x, y, oreType, oreQuality)

    return blockGrid


def generateCraters(leftBounds, rightBounds, blockGrid):  # Similar to generateLake()
    craterSource = (INTERNAL_WIDTH // BLOCK_SIZE) // 2 + random.randint(-3, 3) - 1  # Start point
    craterSeed = craterSource

    round = randomRound()  # Random rounding function (default, floor, ceil)

    for i in range(5):
        craterWidth = random.randint(3, 7)  # Random size

        # This shifts the craterSeed left or right randomly from the
        # last point, giving the appearance of movement of enemy
        craterSeed += random.randint(-10, 10)

        if craterSeed + craterWidth / 2 > rightBounds:
            craterSeed += rightBounds - (craterSeed + craterWidth / 2)

        elif craterSeed - craterWidth / 2 < leftBounds:
            craterSeed -= craterSeed - craterWidth / 2

        # Height of crater by dividing width by random integer
        for height in range(round(craterWidth / random.uniform(3, 5))):
            craterLayerWidth = round(craterWidth / (height + 1))  # Width of this layer

            for width in range(craterLayerWidth):
                x = round(craterSeed + width - round(craterLayerWidth / 2))
                y = round(INTERNAL_HEIGHT / BLOCK_SIZE * 2 / 3) + height
                blockGrid[x][y]['Type'] = 'Air'

    return blockGrid

# Cave environment 7 or underground city


def createTorches(leftBounds, rightBounds, quantity, blockGrid):
    blockGrid = placeBlockOnSolid(leftBounds, rightBounds, quantity,
                                  blockGrid, 'Torch')

    return blockGrid


def createCampfires(leftBounds, rightBounds, quantity, blockGrid):
    blockGrid = placeBlockOnSolid(leftBounds, rightBounds, quantity,
                                  blockGrid, 'Campfire')

    return blockGrid


def placeBlockOnSolid(leftBounds, rightBounds, quantity, blockGrid, block):
    for i in range(quantity):
        for attempt in range(20):  # Keep finding a location until one is found skip if impossible
            x = random.randint(leftBounds, rightBounds)

            # 15 is bottom most layer of air
            if (blockGrid[x][15]['Type'] != block and
                    blockGrid[x][16]['Type'] not in ('Air', 'Water', 'Lava')):

                blockGrid[x][15]['Type'] = block

                if block == 'Torch':
                    blockGrid[x][15]['Data'] = Torch(x, 15)

                elif block == 'Campfire':
                    blockGrid[x][15]['Data'] = CampFire(x, 15)

                break

            else:
                continue

    return blockGrid

# Merge with generatePillar to make a generate tube function or a parameter for horizontal & vertical


def generateHorizontalTube(type, blockGrid, leftBounds, rightBounds, area):
    # Start from 1 block below floor to 1 block above bottom of map (lava tube height is 3)
    yCoord = random.randint(17, 22)

    if area == 'Top':
        yCoord -= 16

    tubeLength = rightBounds - leftBounds + 1
    horizontalCounter = 0

    while horizontalCounter < tubeLength:
        segmentSize = random.randint(1, 4)

        if segmentSize + horizontalCounter > tubeLength:
            segmentSize = horizontalCounter - tubeLength

        yCoord += random.choice((-1, 1))

        if area == 'Bottom':
            if yCoord < 18:
                yCoord = 18

            elif yCoord > 22:
                yCoord = 22

        elif area == 'Top':
            if yCoord < 18 - 16:
                yCoord = 18 - 16

            # Subtract 1 extra because the fluid cannot be the bottom-most block
            # on the ceiling
            elif yCoord > 22 - 17:
                yCoord = 22 - 17

        for x in range(segmentSize):
            for i in range(-1, 2):
                blockGrid[leftBounds + horizontalCounter + x][yCoord + i]['Type'] = type

        horizontalCounter += segmentSize

    return blockGrid


def createPillar():
    # Generate point to make lava pillar. Start near the center of the screen.
    seed = INTERNAL_WIDTH // BLOCK_SIZE // 2 + random.randint(-5, 5)

    return seed


def createWaterFall(blockGrid):
    seed = createPillar()

# Also add support for having the pillar accept a beginning and ending x value for the top and bottom
# Add support for bounds in the future


def generatePillar(type, blockGrid):
    seed = createPillar()

    verticalCounter = 8
    seedOffset = 0

    while verticalCounter > 0:
        segmentSize = random.randint(1, 4)

        if segmentSize > verticalCounter:
            segmentSize = verticalCounter

        seedOffset += random.choice((-1, 1))

        for y in range(segmentSize):
            for x in range(-1, 2):
                blockGrid[seed + x + seedOffset][16 - 1 + verticalCounter - y]['Type'] = type

        verticalCounter -= segmentSize

    return blockGrid


def generateLake(blockType, leftBounds, rightBounds, blockGrid):
    lakeSeed = random.randint(leftBounds, rightBounds)  # Get the seed from the main loop
    lakeWidth = random.uniform(5, 10)
    round = randomRound()  # Random rounding function (default, floor, ceil)
    # This for loop takes the width of the lake and divides by random integer for height
    for i in range(round(lakeWidth / random.uniform(2, 6))):
        # This is the width of the current layer of the lake
        tempLakeWidth = round(lakeWidth / (i + 1))

        for j in range(tempLakeWidth):
            x = round(lakeSeed + j - round(tempLakeWidth / 2))
            y = round(INTERNAL_HEIGHT / BLOCK_SIZE * 2 / 3) + i
            blockGrid[x][y]['Type'] = blockType
            # Fill with water from the center, the X value is the lakeSeed
            # iterated by the width of the layer and centered,
            # Y value is surface + current layer

    return blockGrid


def generate_stalactites(leftBounds, rightBounds, blockGrid):  # Cave environment 5
    round = randomRound()  # Random rounding function (default, floor, ceil)
    for i in range(random.randint(5, 18)):

        rockSeed = random.randint(leftBounds, rightBounds)

        if random.randint(0, 1):  # Generate stalactite
            # If block under stalactite seed is not stone, then continue loop without stalactite, 16 is top of surface
            y = round(INTERNAL_HEIGHT / BLOCK_SIZE * 2 / 3)
            if blockGrid[rockSeed][y]['Type'] != 'Stone':
                continue

            # Generate
            blockGrid[rockSeed][y - 1]['Type'] = 'Stone'

        else:  # Generate stalagmite
            # If block above stalagmite seed is not stone, then continue loop, check bottom of ceiling
            y = round(INTERNAL_HEIGHT / BLOCK_SIZE / 3)
            if blockGrid[rockSeed][y - 1]['Type'] != 'Stone':
                continue

            # Generate
            blockGrid[rockSeed][y]['Type'] = 'Stone'

    return blockGrid


# Placeholder tunnelImage
TUNNEL_SIZE = int(BLOCK_SIZE * 3), int(BLOCK_SIZE * 3)

def get_tunnel_image():
    TUNNEL_RECT = pygame.Rect(0, 0, *TUNNEL_SIZE)
    image = pygame.Surface(TUNNEL_RECT.size, pygame.SRCALPHA, 32)

    FADE_COLOUR = pygame.Color(0, 0, 0)
    ITERATE_COUNT = BLOCK_SIZE

    for i in range(ITERATE_COUNT):
        ratio = i / ITERATE_COUNT
        rect = TUNNEL_RECT.copy()

        DELTA = int(-ratio * BLOCK_SIZE)
        rect.inflate_ip(DELTA * 2, DELTA)
        rect.bottom = TUNNEL_RECT.bottom

        FADE_COLOUR.a = int(255 * ratio)
        image.fill(FADE_COLOUR, rect=rect)


    inner_rect = pygame.Rect(BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE * 2)
    image.fill(BLACK, rect=inner_rect)

    return image

tunnelImage = get_tunnel_image()


def createTunnel(leftBounds, rightBounds, blockGrid, type):
    tunnel = {}
    # Size of entrance is 3x3, - 2 keeps within bounds for x and
    # leaves entrance's bottom at ground level for y

    '''
    The data can be saved as a top left coordinate for where the tunnel begins.
    However it is saved as a rect which does not change block data
    '''
    # Block coordinates
    blockX = random.randint(leftBounds, rightBounds - 2)
    blockY = 15 - 2

    for x in range(3):
        for y in range(3):
            X_Index = blockX + x
            Y_Index = blockY + y

            X_Index = min(X_Index, 31)
            Y_Index = min(Y_Index, 23)

            blockGrid[X_Index][Y_Index]['Type'] = 'Air'

    tunnel['Rect'] = pygame.Rect((blockX * BLOCK_SIZE,
                                  blockY * BLOCK_SIZE),
                                 TUNNEL_SIZE)

    tunnel['Type'] = type

    return tunnel


def generateUndergroundLake(leftBounds, rightBounds, blockGrid,
                            type):  # Cave environment 4
    if leftBounds < 0:
        leftBounds = 0

    elif rightBounds > 31:
        rightBounds = 0

    round = randomRound()  # Random rounding function (default, floor, ceil)
    lavaSeedX = round((leftBounds + rightBounds) / 2)

    if 'fallIntoCave' in gameEvents:
        lavaLakeHeight = 8
        lavaLakeSteepness = random.uniform(0.5, 1.5)

    else:
        # Cave floor is 8 blocks thick, make this change later
        lavaLakeHeight = random.randint(6, 8)
        lavaLakeSteepness = random.uniform(1, 5)

    # Start at bottom and go up
    for height in range(lavaLakeHeight):
        # Round the distance from seed to the bounds subtracted by a quadratic based on height
        # TODO: rewrite this as a quadratic equation and use a function to find the zeros
        tempLeftBounds = leftBounds + round((height / 3) ** lavaLakeSteepness)
        tempRightBounds = rightBounds - round((height / 3) ** lavaLakeSteepness)

        for x in range(tempLeftBounds, tempRightBounds + 1):
            if type == 'Lava':
                y = INTERNAL_HEIGHT // BLOCK_SIZE - 1 - height
                blockGrid[x][y]['Type'] = 'Lava'

            # To elevate cave ceiling, move up by 16 to affect ceiling
            elif type == 'Air Up':
                y = INTERNAL_HEIGHT // BLOCK_SIZE - 1 - height - 16
                blockGrid[x][y]['Type'] = 'Air'

            elif type == 'Air Down':
                y = INTERNAL_HEIGHT // BLOCK_SIZE - 1 - height
                blockGrid[x][y]['Type'] = 'Air'

    # Add basalt or fragile floor
    for x in range(len(blockGrid)):
        # If lava is underneath stone
        if (blockGrid[x][16]['Type'] == 'Stone' and
                blockGrid[x][16 + 1]['Type'] == 'Lava'):

            blockGrid[x][16]['Type'] = 'Obsidian'

        # Air underneath, make fragile stone
        elif (blockGrid[x][16]['Type'] == 'Stone' and
              blockGrid[x][16 + 1]['Type'] == 'Air'):

            blockGrid[x][16] = makeFragileStone(x, 16)

    return blockGrid


def generateCaveChest(caveType, leftBounds, rightBounds, blockGrid):
    Y = round(INTERNAL_HEIGHT / BLOCK_SIZE * 2 / 3) - 1
    for i in range(20):  # Attempt 20 times before giving up
        X = random.randint(leftBounds, rightBounds)

        UNSTABLE_BLOCKS = ('Water', 'Lava', 'Air')
        if blockGrid[X][Y + 1]['Type'] not in UNSTABLE_BLOCKS:
            break

    blockGrid[X][Y]['Type'] = 'Chest'
    blockGrid[X][Y]['Data'] = CaveChest(caveType, X * BLOCK_SIZE, Y * BLOCK_SIZE)

    return blockGrid


def outsideMapGenerator(groundHeight):
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    for i in range(INTERNAL_WIDTH // BLOCK_SIZE):
        # Start right at lower half of screen, 12 from 0 - 23 - Initial depth at new frame
        depth = round(groundHeight / BLOCK_SIZE)

        # Use this to store when ground begins to place player & entities
        mapData['groundY'] = depth * BLOCK_SIZE

        # Grass render
        blockGrid[i][depth]['Type'] = 'Grass'

        for j in range(2):  # Dirt
            depth += 1
            blockGrid[i][depth]['Type'] = 'Dirt'

        while depth < 23:  # Stone, all the way to bottom of screen
            depth += 1
            blockGrid[i][depth]['Type'] = 'Stone'

    entities = makeClouds(players[PK()], entities)

    return (ambientSounds, blockGrid, backgroundBlocks, entities,
            mapData)


def generateAbandonedTown():
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    for i in range(INTERNAL_WIDTH // BLOCK_SIZE):
        # This is unique in that the map starts generating from bottom to top
        height = 0
        for y in range(5):
            height += 1
            blockGrid[i][24 - height]['Type'] = 'Stone'

        for y in range(2):  # Dirt
            height += 1
            blockGrid[i][24 - height]['Type'] = 'Dirt'

        height += 1
        blockGrid[i][24 - height]['Type'] = 'Grass'

        # Use this to store when ground begins to place player & entities
        mapData['groundY'] = (24 - height) * BLOCK_SIZE

    return (ambientSounds, blockGrid, backgroundBlocks, entities,
            mapData)


def generateAbandonedTownRight():
    # Ground
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = generateAbandonedTown()

    # Special features
    blockGrid = makeParabola(blockGrid, 'Stone', mountainParabola,
                             fillDirection='Down')

    # Make tunnel through mountain
    for i in range(2):
        for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
            # 10 + i is used because ground takes up 8 blocks, tunnel starts two blocks higher than this
            blockGrid[x][INTERNAL_HEIGHT // BLOCK_SIZE - (10 + i)]['Type'] = 'Air'

    # Add ladders
    blockGrid = fillBlocks(blockGrid, 'Ladder', pygame.Rect(15, 14, 3, 10))

    return ambientSounds, blockGrid, backgroundBlocks, entities, mapData


def dungeonGenerator():
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
        for y in range(INTERNAL_HEIGHT // BLOCK_SIZE):
            blockGrid[x][y]['Type'] = 'Stone'

    return (ambientSounds, blockGrid, backgroundBlocks, entities,
            mapData)


def generateDungeonTop():
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = dungeonGenerator()

    rect = pygame.Rect(15, 0, 3, INTERNAL_HEIGHT // BLOCK_SIZE)
    blockGrid = fillBlocks(blockGrid, 'Ladder', rect)

    return (ambientSounds, blockGrid, backgroundBlocks, entities,
            mapData)


def generateDungeonBottom():
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = dungeonGenerator()

    rect = pygame.Rect(3, 8, INTERNAL_WIDTH // BLOCK_SIZE - 6,
                       INTERNAL_HEIGHT // BLOCK_SIZE - 3 - 8)
    blockGrid = fillBlocks(blockGrid, 'Air', rect)
    rect = pygame.Rect(15, 0, 3, INTERNAL_HEIGHT // BLOCK_SIZE - 3)
    blockGrid = fillBlocks(blockGrid, 'Ladder', rect)

    return (ambientSounds, blockGrid, backgroundBlocks, entities,
            mapData)


def resetMap():
    # Reset all music
    for sound in ambientSounds:
        sound.fadeout(500)

    newAmbientSounds = []

    blockGrid = []
    backgroundBlocks = []

    entities = []
    mapData = {}
    mapData['levelDarkness'] = 0
    mapData['steamOpacity'] = 0
    mapData['caveTunnels'] = []

    mapData['caveEnvironment'] = None
    mapData['caveEnvData'] = {'Complete': False}
    mapData['caveEvent'] = None  # Default, changed when in cave

    # Creates 32x24 2d array
    for i in range(INTERNAL_WIDTH // BLOCK_SIZE):  # Width, 1024 pixels so 32 blocks
        blockGrid.append([])
        for j in range(INTERNAL_HEIGHT // BLOCK_SIZE):
            blockGrid[i].append({'Type': 'Air'})  # Dictionary containing block info

    return newAmbientSounds, blockGrid, backgroundBlocks, entities, mapData


def playAmbientSounds(ambientSounds):
    for sound in ambientSounds:
        playAmbientSound(sound, -1)


def playAmbientSound(sound, time=0):
    if options['ambience']:
        playSound(sound, time)


def generateUndergroundCity():
    global mapData
    (ambientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()
    mapData['levelDarkness'] = 128

    # Generate map
    for i in range(INTERNAL_WIDTH // BLOCK_SIZE):
        # Ceiling
        depth = 0
        for j in range(3):
            blockGrid[i][depth]['Type'] = 'Stone'
            depth += 1

        # Create the special ceiling if it has the lava ceiling
        if undergroundCity['Lighting'] == 'Lava':
            blockGrid[i][depth]['Type'] = 'Lava'

        else:
            blockGrid[i][depth]['Type'] = 'Stone'

        depth += 1

        if undergroundCity['Lighting'] == 'Lava':
            blockGrid[i][depth]['Type'] = 'Glass'

        else:
            blockGrid[i][depth]['Type'] = 'Stone'

        depth = 16

        mapData['groundY'] = depth * BLOCK_SIZE

        # Repeat 8 times, 16 - 23
        for j in range(round(INTERNAL_HEIGHT / BLOCK_SIZE / 3)):
            blockGrid[i][depth]['Type'] = 'Stone'
            depth += 1

    if undergroundCity['Lighting'] == 'Torches':
        blockGrid = createTorches(2, 30, 6, blockGrid)

    return (ambientSounds, blockGrid, mapData, backgroundBlocks,
            entities, caveBackground)

# TODO: Add in more cave environments


def randomUnimplementedEnvironment():
    implementedEnvironments = (5, 18, 20, 11, 12, 4, 15,
                               16, 13, 19, 10, 14, 23, 24)

    while True:
        randomID = random.randint(1, 33)

        if randomID not in implementedEnvironments:
            return caveEnvironment(randomID)


def caveEnvironments(caveEnvironmentID):
    if caveEnvironmentID == 1:
        caveEnvironment = 'The air is thick and moist, you cannot see very far.'
    elif caveEnvironmentID == 2:
        caveEnvironment = 'The air feels thin and you are having trouble catching your breath.'
    elif caveEnvironmentID == 3:
        caveEnvironment = 'The cold drafts freeze everything, and make the stone walls very cold.'
    elif caveEnvironmentID == 4:
        caveEnvironment = 'The cave air is cold, but you feel the floor to be warm from lava underneath.'
    elif caveEnvironmentID == 5:
        caveEnvironment = 'Large stalactites and stalagmites make the moist cave harder to pass through.'
    elif caveEnvironmentID == 6:
        caveEnvironment = 'A river of lava flows in front of you, you go back and take another route.'
    elif caveEnvironmentID == 7:
        caveEnvironment = 'You see a flickering light in the distance, it must be a torch from another explorer.'
    elif caveEnvironmentID == 8:
        caveEnvironment = 'The cave floor begins to crumble below your feet, you decide to run through and continue your adventure.'
    elif caveEnvironmentID == 9:
        caveEnvironment = 'Streams of water and lava meet and create huge amounts of steam, blocking your vision.'
    elif caveEnvironmentID == 10:
        caveEnvironment = 'In the dark you have trouble seeing, and stumble blindly.'
    elif caveEnvironmentID == 11:
        caveEnvironment = 'The floor is deeply cratered as if someone had set off explosives to kill something.'
    elif caveEnvironmentID == 12:
        caveEnvironment = 'The floor is warm to the touch and made of thick basalt, it would be wise not to dig down...'
    elif caveEnvironmentID == 13:
        caveEnvironment = 'The cave ceiling slopes sharply upward, your footsteps echo hundreds of times in the large room.'
    elif caveEnvironmentID == 14:
        caveEnvironment = 'The rocks in the cave seem to absorb your light, then they slowly fade to nothingness...'
    elif caveEnvironmentID == 15:
        caveEnvironment = 'You try to touch the cave walls and they crumble to your touch, you feel the air and notice its dryness.'
    elif caveEnvironmentID == 16:
        caveEnvironment = 'The air becomes damp and you notice the stone is soft to your fingertips.'
    elif caveEnvironmentID == 17:
        caveEnvironment = 'You reach a clearing only to realize it\'s a large room, you watch the subterrainean waterfall and continue with renewed confidence.'
    elif caveEnvironmentID == 18:
        caveEnvironment = 'The water is up to your waist, you make sure not to get your items wet.'
    elif caveEnvironmentID == 19:
        caveEnvironment = 'You take a step forward and slip, the rocks here are polished smooth and shiny...'
    elif caveEnvironmentID == 20:
        caveEnvironment = 'You see a light and chase it, ahead there is the pool of lava which you use to get comfortable and dry off.'
    elif caveEnvironmentID == 21:
        caveEnvironment = 'You walk and discover a shocking sight, a stream of lava pours off a cliff freezing while falling and hitting the ground as stone.'
    elif caveEnvironmentID == 22:
        caveEnvironment = 'You begin to feel it rain... No! Rocks are falling from the ceiling onto you... The room is weakening!'
    elif caveEnvironmentID == 23:
        caveEnvironment = 'You feel the ground shake and you fall down, a fissure opens on the ground and you see lava flowing.'
    elif caveEnvironmentID == 24:
        caveEnvironment = 'The ground shakes and you notice a hole open up in the wall, you follow through it.'
    elif caveEnvironmentID == 25:
        caveEnvironment = 'You look at the ground and notice sand, there is even a small cactus on the ground, what got a desert down here?'
    elif caveEnvironmentID == 26:
        caveEnvironment = 'The cave seems ordinary but as you look back you realize the exit is gone.'
    elif caveEnvironmentID == 27:
        caveEnvironment = 'The ceiling walls begin to heat up and descend, is it melting?'
    elif caveEnvironmentID == 28:
        caveSection = random.choice(('floor', 'ceiling', 'walls'))
        caveEnvironment = 'The ' + caveSection + \
            ' begins to pulsate and warp, heat radiates and you realize lava is nearby.'
    elif caveEnvironmentID == 29:
        caveEnvironment = 'You see drops of lava and look at yourself to see a dark singe on your clothing.'
    elif caveEnvironmentID == 30:
        caveEnvironment = 'There is a deep lake of lava, it wouldn\'t be a good idea to swim.'
    elif caveEnvironmentID == 31:
        caveEnvironment = 'Behind you the ceiling collapses and lava rushes behind, you run forward.'
    elif caveEnvironmentID == 32:
        # Massive room of lava collapsed into lake
        caveEnvironment = 'You hear a deafening explosion, and steam quickly fills the room.'
    elif caveEnvironmentID == 33:
        caveEnvironment = 'You notice that the floor sounds hollow as you walk through.'

    return caveEnvironment


def generateCave(player):
    global mapData
    # For cave environment 18's riverFunction
    global randomHeightOffset, randomA_Value

    def outputEnvironment(environmentDesc):
        addLegacyOutput(environmentDesc)

    newAmbientSounds = ambientSounds
    newChatText = chatText

    (newAmbientSounds, blockGrid, backgroundBlocks, entities,
     mapData) = resetMap()

    # Generate map
    for i in range(INTERNAL_WIDTH // BLOCK_SIZE):
        # Draw cave ceiling
        depth = 0
        # Repeat 8 times, 0 - 7
        for j in range(round(INTERNAL_HEIGHT / BLOCK_SIZE / 3)):
            blockGrid[i][depth]['Type'] = 'Stone'
            depth += 1

        # Draw bottom cave floor and increase depth counter by 8
        depth += round(INTERNAL_HEIGHT / BLOCK_SIZE / 3)

        mapData['groundY'] = depth * BLOCK_SIZE  # Use this to place player

        # Repeat 8 times, 16 - 23
        for j in range(round(INTERNAL_HEIGHT / BLOCK_SIZE / 3)):
            blockGrid[i][depth]['Type'] = 'Stone'
            depth += 1

    assert player.caveType != 'N/A'

    # Create special features
    caveEnvironment = random.randint(0, 28)

    caveEnvData = {'Complete': False}

    if caveEnvironment == 0:
        blockGrid = generate_stalactites(6, 27, blockGrid)
        newAmbientSounds.append(waterDripSound)
        outputEnvironment(caveEnvironments(5))

    elif caveEnvironment == 1:
        # TODO: Add level in which cave is flooded, partially or half filled
        if random.randint(0, 1):  # Make large river
            randomHeightOffset = random.uniform(1, 5)
            randomA_Value = random.uniform(0.03, 0.1)
            blockGrid = makeParabola(blockGrid, 'Water', riverFunction,
                                     fillDirection='Up')

        else:  # Add a lake
            numberOfLakes = random.randint(1, 3)
            for i in range(numberOfLakes):
                blockGrid = generateLake('Water', 6, 27, blockGrid)

        newAmbientSounds.append(flowingWaterSound)
        outputEnvironment(caveEnvironments(18))

    elif caveEnvironment == 2:
        blockGrid = generateLake('Lava', 6, 27, blockGrid)
        newAmbientSounds.append(lavaSound)
        outputEnvironment(caveEnvironments(20))

    elif caveEnvironment == 3:
        blockGrid = generateCraters(1, 30, blockGrid)
        outputEnvironment(caveEnvironments(11))

    elif caveEnvironment == 4:
        blockGrid = generateUndergroundLake(random.randint(8 - 5, 8 + 5),
                                            random.randint(32 - 15, 32 - 5),
                                            blockGrid, 'Lava')
        newAmbientSounds.append(lavaSound)
        outputEnvironment(caveEnvironments(12))

    elif caveEnvironment == 5:
        type = random.choice(('Lava', 'Air'))
        if type == 'Lava':
            newAmbientSounds.append(lavaSound)
        for i in range(random.randint(1, 4)):
            # Have water and link it to a waterfall?
            blockGrid = generatePillar(type, blockGrid)

    elif caveEnvironment == 6:
        type = random.choice(('Water', 'Air'))
        blockGrid = generateHorizontalTube(type, blockGrid, 0, 31,
                                           random.choice(('Top', 'Bottom')))

    elif caveEnvironment in (7, 17):
        blockGrid = generateUndergroundLake(random.randint(8 - 5,
                                                           8 + 5),
                                            random.randint(32 - 15,
                                                           32 - 5),
                                            blockGrid, 'Air Down')

        if caveEnvironment == 7:
            blockGrid = makeCaveFragile(0, 31, blockGrid)
            caveEnvData['Timer'] = random.uniform(5, 10)
            caveEnvData['Played Sound'] = False

        elif caveEnvironment == 17:
            outputEnvironment(caveEnvironments(33))

    elif caveEnvironment == 8:
        type = 'Lava'
        newAmbientSounds.append(lavaSound)
        blockGrid = generateHorizontalTube(type, blockGrid, 0, 31,
                                           'Bottom')
        outputEnvironment(caveEnvironments(4))

    elif caveEnvironment in (9, 10):
        # Makes stone possible to break by hand
        blockGrid = makeCaveFragile(0, 31, blockGrid)
        for x in range(0, 32):
            for y in (7, 16):
                if blockGrid[x][y]['Type'] == 'Fragile Stone':
                    blockGrid[x][y] = makeSoftStone(x, y)

                elif blockGrid[x][y]['Type'] == 'Stone':
                    blockGrid[x][y] = makeFragileStone(x, y)

        if caveEnvironment == 9:
            outputEnvironment(caveEnvironments(15))

        elif caveEnvironment == 10:
            outputEnvironment(caveEnvironments(16))
            mapData['steamOpacity'] = 120

    elif caveEnvironment == 11:
        outputEnvironment(caveEnvironments(13))
        blockGrid = generateUndergroundLake(random.randint(8 - 5,
                                                           8 + 5),
                                            random.randint(32 - 15,
                                                           32 - 5),
                                            blockGrid, 'Air Up')

    elif caveEnvironment == 12:
        # TODO: Add friction
        outputEnvironment(caveEnvironments(19))

    elif caveEnvironment in (13, 23):
        mapData['levelDarkness'] = 240
        mapData['levelDarkness'] += random.randint(-5, 10)

        if caveEnvironment == 13:  # Stumble blindly
            outputEnvironment(caveEnvironments(10))

        elif caveEnvironment == 23:  # Entrance vanishes
            caveEnvData['Timer'] = random.uniform(3, 10)

    elif caveEnvironment == 14:
        # Rocks absorb light
        outputEnvironment(caveEnvironments(14))

    elif caveEnvironment == 15:
        caveEnvData['Timer'] = random.uniform(1, 2.5)
        caveEnvData['Played Sound'] = False

    elif caveEnvironment == 16:
        caveEnvData['Timer'] = random.uniform(2, 3.5)
        caveEnvData['Played Sound'] = False

    elif caveEnvironment == 18:
        randomHeightOffset = random.uniform(1, 5)
        randomA_Value = random.uniform(0.06, 0.1)
        blockGrid = makeParabola(blockGrid, 'Lava', riverFunction,
                                 fillDirection='Up')
        newAmbientSounds.append(lavaSound)
        outputEnvironment(caveEnvironments(6))

        offsetFromScreen = random.randint(0, 2)
        if player.direction == 'Right':
            mapData['caveTunnels'].append(createTunnel(offsetFromScreen, offsetFromScreen + 2,
                                                       blockGrid, 'Other Cave'))

        elif player.direction == 'Left':
            mapData['caveTunnels'].append(createTunnel(INTERNAL_WIDTH // BLOCK_SIZE - offsetFromScreen - 3,
                                                       INTERNAL_WIDTH // BLOCK_SIZE - offsetFromScreen - 1,
                                                       blockGrid, 'Other Cave'))

    elif mapData['steamOpacity'] > 0:  # Fog
        outputEnvironment(caveEnvironments(1))

    elif caveEnvironment == 20:  # Thin air
        outputEnvironment(caveEnvironments(2))

    elif caveEnvironment in (21, 27):
        newAmbientSounds.append(lavaSound)
        blockGrid = generateHorizontalTube('Lava', blockGrid, 0, 31, 'Top')

        if caveEnvironment == 21:  # Ceiling collapses with lava flowing
            outputEnvironment(caveEnvironments(31))

        elif caveEnvironment == 27:
            outputEnvironment(caveEnvironments(27))

    elif caveEnvironment == 22:
        outputEnvironment(caveEnvironments(22))
        caveEnvData['Falling Rock Rate'] = random.randint(5, 10)

    elif caveEnvironment == 24:
        outputEnvironment(caveEnvironments(9))
        mapData['steamOpacity'] = 190
        randomA_Value = random.uniform(0.03, 0.1)

        blockGrid = makeParabola(blockGrid, 'Water', leftWaterRiver,
                                 fillDirection='Up')
        blockGrid = makeParabola(blockGrid, 'Lava', rightLavaRiver,
                                 fillDirection='Up')

    elif caveEnvironment == 25:
        outputEnvironment(caveEnvironments(25))
        blockGrid = makeSandCave(0, 31, blockGrid)

    elif caveEnvironment == 26:
        caveEnvData['Timer'] = random.uniform(1.5, 5)
        caveEnvData['Played Sound'] = False
        caveEnvData['Finished Fog'] = False
        caveEnvData['Fog Delay'] = random.uniform(1, 3)
        caveEnvData['Fog Opacity'] = random.randint(170, 230)

    # Environment 28 in caveEnvironments function
    if caveEnvironment in (28, 29, 30):
        caveSection = {28: 'floor',
                       29: 'ceiling',
                       30: 'walls'}[caveEnvironment]

        outputEnvironment('The ' + caveSection + ' begins to pulsate and warp, '
                          'heat radiates and you realize lava is nearby.')

    if player.caveType == '1':
        maxEvent = 6

    elif player.caveType == '2':
        maxEvent = 7

    elif player.caveType == '3':
        maxEvent = 8

    caveEvent = random.randint(0, maxEvent)

    if caveEvent == 1:
        pass  # Uneventful

    elif caveEvent == 2:
        # Multiple paths
        if player.caveType == '1':
            numberOfPaths = random.randint(2, 3)

        elif player.caveType == '2':
            numberOfPaths = random.randint(3, 5)

        elif player.caveType == '3':
            numberOfPaths = random.randint(2, 4)

        for i in range(numberOfPaths):
            # TODO: make sure tunnels are separate
            mapData['caveTunnels'].append(createTunnel(5, 28, blockGrid, 'Other Cave'))

    elif caveEvent == 3:
        blockGrid = generateCaveChest(player.caveType, 5, 28, blockGrid)

    elif caveEvent == 4:
        # Shadow moves by
        if random.randint(0, 1):
            entities = spawnEntity(entities, 1, 'Shadow Dragon')

        else:
            entities = spawnEntity(entities, 1, 'Shadow Explorer')

    if caveEvent == 1:
        entities = spawnEntity(entities, 1, 'Dragon')

    elif caveEvent == 2:
        entities = spawnEntity(entities, random.randint(1, 3), 'Small Bat')
        entities = spawnEntity(entities, random.randint(1, 2), 'Big Bat')

    elif caveEvent == 4:
        entities = spawnEntity(entities, random.randint(
            2, 3), 'Slime', bottomCoord=mapData['groundY'])

    if caveEvent in (5, 6):
        entities = spawnEntity(entities, 1, 'Explorer', bottomCoord=mapData['groundY'])

    elif caveEvent == 7:
        blockGrid = generateOres(player, 5, 28, blockGrid)

    elif caveEvent == 8:  # Encampment
        blockGrid = createTorches(5, 28, 5, blockGrid)
        blockGrid = createCampfires(10, 20, 1, blockGrid)

        if random.randint(0, 1):  # Temporary 50% chance of any entity
            entities = spawnEntity(entities, 1, 'Dragon')

        else:
            entities = spawnEntity(entities, 3, 'Explorer', bottomCoord=mapData['groundY'])

    # Separate
    if random.randint(0, 1) and caveEnvironment not in (9, 10, 7, 17):
        blockGrid = makeCaveFragile(0, 31, blockGrid)

    # Maybe make this darker TODO: or make first level lighter
    # Cave environment 10
    # TODO: join this with the cave environment code when these environments have enough features
    # Only create random steam or darkness if cave environment has not set anything

    if mapData['levelDarkness'] == 0 and mapData['steamOpacity'] == 0:
        if random.randint(0, 1):
            mapData['levelDarkness'] = random.randint(50, 160)

        else:
            mapData['steamOpacity'] = random.randint(25, 80)

    if mapData['levelDarkness'] == 0:
        mapData['levelDarkness'] = 50

    if random.randint(1, 7) == 7 and player.caveType == '3':
        caveTunnels['caveTunnels'].append(createTunnel(5, 28, blockGrid, UNDERGROUND_CITY))

    if 'fallIntoCave' in gameEvents:
        centerBlockX = player.rect.centerx // BLOCK_SIZE
        blockGrid = generateUndergroundLake(centerBlockX - random.randint(5, 7),
                                            centerBlockX + random.randint(5, 7),
                                            blockGrid, 'Air Up')

    playAmbientSounds(newAmbientSounds)
    mapData['caveEnvironment'] = caveEnvironment
    mapData['caveEvent'] = caveEvent
    mapData['caveEnvData'] = caveEnvData

    return (newAmbientSounds, blockGrid, mapData, backgroundBlocks,
            entities, caveBackground, newChatText)

# TODO: Merge player death with reducePlayerHealth and store death cause and goldLoss


def playerDeath(player, goldLoss, consoleText):
    if goldLoss is None:
        goldLoss = 20

    player.gold -= goldLoss
    player.health = player.maxHealth  # Reset health after death

    if player.gold < 0:
        player.gold = 0  # Reset

        # Death results in leaving caves
        if player.direction == 'Left':
            leaveCave = 'Right'

        elif player.direction == 'Right':
            leaveCave = 'Left'

        for text in ('You have run out of gold, and died.',
                     'In the bank you had ' + str(pl_Info[PK()]['bankBalance']) + ' gold left.'):

            addLegacyOutput(text)

    else:
        leaveCave = None

    return player, leaveCave, consoleText


def reducePlayerHealth(damage, textParticles):
    player = players[PK()]

    (player.health,
     textParticles) = reduceHealth(player.health, player.invincible, damage,
                                   player.rect.center, 'Defense', textParticles)

    return player, textParticles

# Record damage events and only sum and show once a second


def reduceHealth(health, invincibleMode, damage, entityRectCenter, damageType,
                 textParticles):
    # This function can be used to simulate special effects such as potions
    if invincibleMode:
        multiplier = 0

    else:
        multiplier = 1

    damageDealt = damage * multiplier
    health -= damageDealt

    damage * multiplier

    if damageType == 'Attack':
        textType = AttackText

    elif damageType == 'Defense':
        textType = DefenseText

    textParticles.append(textType(round(damageDealt, 1), entityRectCenter))

    return health, textParticles


abandonedTownBuildingLabels = {}

for buildingName in ('Bank', 'Market'):
    abandonedTownBuildingLabels[buildingName] = TextRect(touchScreenFont, buildingName,
                                                         BLACK)

abandonedTownBuildingLabels['Bank'].rect.center = INTERNAL_WIDTH / 4, INTERNAL_HEIGHT / 5
abandonedTownBuildingLabels['Market'].rect.center = INTERNAL_WIDTH * 3 / 4, INTERNAL_HEIGHT / 4


class PhysicalBuilding:
    # Accepts left, right, top, bottom or rect
    def __init__(self, hasDoors,
                 left=None, right=None, top=None, bottom=None,
                 rect=None):
        if rect is None:
            assert (left is not None and
                    right is not None and
                    top is not None and
                    bottom is not None)

            width = right - left
            height = bottom - top

            self.rect = pygame.Rect(left, top, width, height)

        else:
            self.rect = rect

        self.hasDoors = hasDoors

        self.backImage = None
        self.displayRect = pygame.Rect(self.rect.left * BLOCK_SIZE,
                                       self.rect.top * BLOCK_SIZE,
                                       (self.rect.width + 1) * BLOCK_SIZE,
                                       (self.rect.height + 1) * BLOCK_SIZE)

    def draw(self):
        # Draw inside of building (dark wood) not edges which are physica blocks
        # +1 in for loop is to make the background of building include behind physical wall/floor/ceiling blocks
        if not self.backImage:
            self.backImage = pygame.Surface(self.displayRect.size)

            for x in range(self.rect.width + 1):
                for y in range(self.rect.height + 1):
                    self.backImage.blit(woodPlankBackImage, (x * BLOCK_SIZE,
                                                             y * BLOCK_SIZE))

        windowSurface.blit(self.backImage, self.displayRect.topleft)

    def makeBuilding(self, blockGrid):
        # Walls do not include corners
        # TODO: Replace this gap with a real door

        for y in range(self.rect.top, self.rect.bottom + 1):
            # Skip doors
            if (self.hasDoors and
                    y in range(self.rect.bottom - 2, self.rect.bottom)):

                continue

            blockGrid[self.rect.left][y]['Type'] = 'Plank'
            blockGrid[self.rect.right][y]['Type'] = 'Plank'

        # +1 is to make the for loop include the corners
        for x in range(self.rect.left, self.rect.right + 1):
            blockGrid[x][self.rect.top]['Type'] = 'Plank'
            blockGrid[x][self.rect.bottom]['Type'] = 'Plank'

        return blockGrid


# 32 - 6 is the width of map subtracted by the left of building
guardBuilding = PhysicalBuilding(left=6, right=32 - 6,
                                 top=6, bottom=12, hasDoors=True)

ABANDONED_TOWN_LEFT_MIDSPACING = 4

abandonedBankBuilding = {'Bottom Floor': PhysicalBuilding(left=2,
                                                          right=16 - ABANDONED_TOWN_LEFT_MIDSPACING // 2,
                                                          top=11, bottom=16,
                                                          hasDoors=True)}

rect = abandonedBankBuilding['Bottom Floor'].rect.copy()
rect.inflate_ip(-2, -2)
rect.y -= 5
abandonedBankBuilding['Top Floor'] = PhysicalBuilding(rect=rect,
                                                      hasDoors=False)

abandonedMarketBuilding = {'Bottom Floor': PhysicalBuilding(left=16 + ABANDONED_TOWN_LEFT_MIDSPACING // 2,
                                                            right=32 - 2,
                                                            top=12, bottom=16,
                                                            hasDoors=True)}

rect = abandonedMarketBuilding['Bottom Floor'].rect.copy()
rect.inflate_ip(-3, -3)
rect.y -= 4
hasDoors = False
abandonedMarketBuilding['Top Floor'] = PhysicalBuilding(rect=rect,
                                                        hasDoors=False)

# Initial value
mousePos = pygame.mouse.get_pos()

entireTimer = Timer()
lightRegionTimer = Timer()
mainLightTimer = Timer()

# Main loop
gameEvents = []
while True:
    clipboard = pygame.scrap.get(pygame.SCRAP_TEXT)

    entireTimer.reset()
    lightRegionTimer.reset()
    mainLightTimer.reset()

    for timer in lighting.segments:
        timer.reset()

    if not android:
        mousePos = pygame.mouse.get_pos()

    # Screen update checking code is needed for all gamemodes
    if not loadScreenOnce:
        loadScreenOnce = True
        loadFrameOnce = False
        # Append a fullscreen
        dirtyRects.append(pygame.Rect(0, 0, *INTERNAL_SIZE))

    # Store events so they can be checked multiple times
    pygameEvents = pygame.event.get()

    for event in pygameEvents:
        if event.type == pygame.QUIT:
            killThread = True
            quitGame()

        elif event.type == pygame.KEYUP:
            if (event.key == pygame.K_F8 and
                gamemode in ('Play', 'Warehouse', 'Bank', 'Market',
                             'Stock Market', 'Library')):

                if gamemode == 'Bank':
                    bankMode = 'Main'

                elif gamemode == 'Library':
                    libraryMode = 'Main'

                elif gamemode == 'Market':
                    marketMode = 'Main'

                elif gamemode == 'Stock Market':
                    stockMarketMode = 'Main'

                elif gamemode == 'Warehouse':
                    warehouseMode = 'Main'

                elif gamemode == 'Play' and players[PK()].location == GUARD_POST:
                    if players[PK()].canPassGuardKeeper:
                        players[PK()].rect.centerx = INTERNAL_WIDTH // 2

                if not console:
                    players[PK()], heldKey = resetInput(players[PK()])

                console = not console
                loadScreenOnce = False

            elif event.key == pygame.K_F6:
                useNumpy = not useNumpy
                DEVELOPER_MODE = not DEVELOPER_MODE

            elif event.key in (pygame.K_F2, pygame.K_PRINT):
                take_screenshot(windowSurface)

            elif event.key == pygame.K_F3:
                debugMode = not debugMode

            elif event.key == pygame.K_F11:
                optionFile = shelve.open('options')

                (options['fullscreen'], optionFile['fullscreen'],
                 optionButtons['fullscreen'],
                 loadScreenOnce) = toggleFullscreen()

                optionFile.close()

        # Used to delay console output and simulate the time.sleep function
        elif event.type == CONSOLE_TIMER and sleepTime > 0:
            sleepTime -= 1

            if console:
                if gamemode == 'Play' and players[PK()].location == GUARD_POST:
                    if guardPostPause:
                        addLegacyOutput('Guard Superior: Which of the three '
                                        'caves are you going to? (1, 2, or 3?)')
                        consoleText.addOutput('')

                        guardPostPause = False
                        guardPostAskCaveType = True

                    elif (players[PK()].canPassGuardKeeper and
                          not players[PK()].canPassGuardSuperior and
                          not guardPostAskCaveType):
                        addLegacyOutput('You walk through the building '
                                        'to the other end.')

                        guardPostPause = True

                        sleepTime = 2

        elif (((not android and event.type == MUSIC_END) or

               (android and not soundMixer.music.get_busy()))

              and options['music'] and gamemode not in MENUS):

            currentMusic = pickMusic(players[PK()])
            soundMixer.music.load(currentMusic)
            soundMixer.music.play()

        elif event.type == pygame.MOUSEMOTION:
            if gamemode in INVENTORY_MENU_GAMEMODES:
                if mouseover(inventoryMenu.mainRect) and inventoryMenu.maximized:
                    currentMenu = 'Player Inventory'

                else:
                    currentMenu = None

            if gamemode == 'Play' and debugMode:
                newXValue, newYValue = clickedBlock()['x'], clickedBlock()['y']
                newBlockValue = blockGrid[newXValue][newYValue]['Type']

                debugInfo['xCoord'].updateValue(newXValue)
                debugInfo['yCoord'].updateValue(newYValue)
                debugInfo['blockType'].updateValue(newBlockValue)

        elif ((scrollUp(event) or scrollDown(event)) and
              gamemode in INVENTORY_MENU_GAMEMODES):

            dirtyRects.append(pl_InventoryGUI.slots[players[PK()].selectedInvSlot])

            if scrollUp(event):
                players[PK()].selectedInvSlot -= 1

            elif scrollDown(event):
                players[PK()].selectedInvSlot += 1

            # Restrict to first row
            players[PK()].selectedInvSlot %= 9

            dirtyRects.append(pl_InventoryGUI.slots[players[PK()].selectedInvSlot])

        elif not console and displayChat != 'Display All':
            mousePos = list(pygame.mouse.get_pos())

            if android:
                mousePos[0] -= offsetX
                mousePos[1] -= offsetY

            if shake.is_active():
                mousePos[0] -= round(shake.x)
                mousePos[1] -= round(shake.y)

            mousePos = tuple(mousePos)

            if leftClick(event):
                mouseDown = True
                mouseDownTimer = FPS / 2  # Reset

                # If mouse clicked inventory menu tab
                if mouseover(inventoryMenu.titleRect):
                    inventoryMenu.toggleVisibility()

                if gamemode == 'Play':
                    for tunnel in mapData['caveTunnels']:
                        if (mouseover(tunnel['Rect']) and
                                not players[PK()].fightingMob):
                            loadScreenOnce = False
                            if tunnel['Type'] == UNDERGROUND_CITY:
                                (players[PK()], ambientSounds, blockGrid,
                                 mapData, backgroundBlocks,
                                 tunnel, entities,
                                 undergroundCity['Old Cave Data']) = loadUndergroundCity(players[PK()],
                                                                                         pl_Info[PK()])
                                undergroundCity = upgradeUndergroundCity(undergroundCity)

                            elif tunnel['Type'] == 'Other Cave':
                                gameEvents.append('incrementCave')

            if gamemode in INVENTORY_MENU_GAMEMODES:
                # Allow clicking on inventory slots by checking if mouse is over slot
                if (currentMenu == 'Player Inventory' and
                    mouseoverSlot is not None
                        and not buyingItem):
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT and leftClick(event):  # Shift click to inventory
                        if gamemode == 'Warehouse':
                            (pl_Info[PK()]['warehouseInv'],
                             dirtyRects) = appendWarehouseInventory(players[PK()].inventory[mouseoverSlot],
                                                                    pl_Info[PK()]['warehouseInv'],
                                                                    returnDirtyRects=True)

                            players[PK()].inventory[mouseoverSlot] = None
                            # Update search
                            warehouseSearchResults = updateWarehouseResults(
                                pl_Info[PK()]['warehouseInv'])

                        elif (gamemode == 'Market' and
                              players[PK()].inventory[mouseoverSlot] is not None):
                            (players[PK()].inventory[mouseoverSlot],
                             players[PK()].gold) = marketSellItem(players[PK()],
                                                                  players[PK()].inventory[mouseoverSlot])

                    else:
                        if leftClick(event):
                            (players[PK()].mouseInventory,
                             players[PK()].inventory[mouseoverSlot]) = (players[PK()].inventory[mouseoverSlot],
                                                                        players[PK()].mouseInventory)

                        elif rightClick(event):
                            # Attempt to use item
                            if isinstance(players[PK()].inventory[mouseoverSlot], HealthPotion):
                                playSound(potionDrinkSound)

                                players[PK()].health += players[PK()
                                                                ].inventory[mouseoverSlot].strength
                                if players[PK()].health > players[PK()].maxHealth:
                                    players[PK()].health = players[PK()].maxHealth

                                # Remove item
                                players[PK()].inventory[mouseoverSlot] = None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouseDown = False
            holdMouseDown = False

    # Debug info
    newFPS = round(mainClock.get_fps())
    debugInfo['FPS'].updateValue(newFPS)

    # Manage mousedown code every frame
    if mouseDown:
        # Hold mouse down for initial click and holding after half a second
        if mouseDownTimer in (0, FPS // 2):
            holdMouseDown = True

        else:
            holdMouseDown = False

        if mouseDownTimer != 0:
            mouseDownTimer -= 1

    if serverOn or gamemode in ('Play',) + BUILDING_GAMEMODES:
        # Client can temporarily run these on its own
        timeTick += 100 / FPS  # Increment time if game is not paused
        while timeTick >= DAY_LENGTH:  # Reset because an entire day is DAY_LENGTH ticks
            timeTick %= DAY_LENGTH

        #Smelt in forge
        for i in range(FORGE_INVENTORY_NUMBER):
            if (pl_Info[PK()]['forgeInv']['Output'][i] is None and
                pl_Info[PK()]['forgeInv']['Input'][i] is not None and
                    pl_Info[PK()]['forgeInv']['Started'][i]):
                # Finish operation after 30 seconds
                pl_Info[PK()]['forgeInv']['Progress'][i] += 1 / FPS / FORGE_OPERATION_TIME

                if pl_Info[PK()]['forgeInv']['Progress'][i] > 1:
                    pl_Info[PK()]['forgeInv']['Progress'][i] = 0
                    pl_Info[PK()]['forgeInv']['Output'][i] = pl_Info[PK()]['forgeInv']['Input'][i]
                    pl_Info[PK()]['forgeInv']['Input'][i] = None

                    newItem = pl_Info[PK()]['forgeInv']['Output'][i].id
                    if newItem in SMELTABLE_ITEMS:
                        pl_Info[PK()]['forgeInv']['Output'][i] = Item(SMELTABLE_ITEMS[newItem])

            else:
                # Reset to 0 if slot is empty or output filled with another item
                pl_Info[PK()]['forgeInv']['Progress'][i] = 0
                pl_Info[PK()]['forgeInv']['Started'][i] = False

    # Internal server
    # In game, make time progress
    if (serverOn or gamemode in ('Play',) + BUILDING_GAMEMODES) and not isClient:
        # Weather
        weatherDuration -= 1 / FPS

        if weatherDuration == 0:
            # Random weather
            weather = random.randint(0, 3)
            if weather in (0, 1):
                weather = 'Sun'

            elif weather == 2:
                weather = 'Rain'

            elif weather == 3:
                weather = 'Snow'

            weatherDuration = random.uniform(60, 360)

        if serverOn:
            TCP_ServerBufferLock.acquire()
            for i in TCP_ServerBuffer:
                # Send weather update to all clients
                TCP_ServerBuffer[i].append({'Type': 'Weather',
                                            'Weather': (weather,
                                                        weatherDuration)})

                TCP_ServerBuffer[i].append({'Type': 'timeTick',
                                            'timeTick': timeTick})
            TCP_ServerBufferLock.release()

        for event in pygameEvents:
            if event.type == AUTOSAVE_TIMER:
                if not isClient:
                    saveGame(librarySave=False)

    # Code that should run every frame regardless of whether in console mode
    if gamemode == 'Play':
        # This variable gets reset every frame and is made true when changing location
        changingLocation = False
        tryLoadingCache = False

    if (gamemode in ('Main Menu', 'Multiplayer Menu',
                     'Multiplayer Menu - Add Server',
                     'Multiplayer Error',
                     'Multiplayer Menu - Edit') + INGAME_MENUS and not inGame):
        # Draw background
        windowSurface.blit(stoneBackground, (0, 0))

    elif gamemode in ('Paused',) + INGAME_MENUS and inGame:
        # If the user presses resume, the variable is set to None
        windowSurface.blit(pauseBackground, (0, 0))

        BLACK_SCREEN.set_alpha(160)
        windowSurface.blit(BLACK_SCREEN, (0, 0))

    if console:
        for event in pygameEvents:
            if event.type == pygame.KEYDOWN:
                if event.key in ENTER_KEYS and sleepTime == 0:
                    # Can be checked while consoleText changes
                    consoleInput = consoleText.field.value
                    consoleText.addInput()

                    if cheatMode is not None:
                        if cheatMode == 'Main':
                            if consoleInput == 'Gold':
                                consoleText.addOutput('Enter the amount of gold you want.')
                                cheatMode = 'Gold'

                            elif consoleInput == 'Inventory':
                                consoleText.addOutput('Do you want to "Add" or "Remove" an item?')
                                cheatMode = 'Main Inventory'

                            elif consoleInput == 'Stock Inventory':
                                consoleText.addOutput('What stock do you want?')
                                cheatMode = 'Stocks'

                            elif consoleInput == 'Change Location':
                                cheatMode = 'Location'
                                consoleText.addOutput(PROMPT_CITY_STRING)

                            elif consoleInput == 'Console':
                                consoleText.addOutput('To exit console type "Exit."')
                                cheatMode = 'Console'

                            else:
                                consoleText.addOutput('Input not recognized.')

                        elif cheatMode == 'Gold':
                            # TODO: Use integer input function

                            try:
                                players[PK()].gold = int(consoleInput)

                            except ValueError:
                                consoleText.addOutput('Please type an integer!')

                            else:
                                consoleText.addOutput('Changed gold quantity to '
                                                      + str(players[PK()].gold) + '.')
                                cheatMode = None

                        elif cheatMode == 'Main Inventory':
                            if consoleInput not in ('Add', 'Remove'):
                                consoleText.addOutput('Please select "Add" or "Remove."')

                            elif consoleInput == 'Add':
                                consoleText.addOutput('What item do you want?')
                                cheatMode = 'Inventory Add'

                            elif consoleInput == 'Remove':
                                for text in ('What item do you want to remove?',
                                             cleanInventory(players[PK()].inventory)['Str']):

                                    consoleText.addOutput(text)

                                cheatMode = 'Inventory Remove'

                        elif cheatMode == 'Inventory Add' and len(consoleInput) > 0:
                            if None in players[PK()].inventory:
                                players[PK()] = appendPlayerInventory(Item(consoleInput),
                                                                      player=players[PK()],
                                                                      returnDirtyRects=False)

                                consoleText.addOutput(consoleInput +
                                                      ' was added to your inventory.')
                            cheatMode = None

                        # Make sure you can't remove if nothing is in inventory
                        elif (cheatMode == 'Inventory Remove' and
                              int(cleanInventory(players[PK()].inventory)['Len']) > 0):

                            # Check for None prevents crashes
                            if (consoleInput not in players[PK()].inventory or
                                    consoleInput is None):
                                consoleText.addOutput('Item not found. Please select'
                                                      ' an item you want to remove.')

                            else:
                                # Remove item by finding it and replacing with None
                                for i in range(len(players[PK()].inventory)):
                                    if players[PK()].inventory[i] == consoleInput:
                                        players[PK()].inventory[i] = None
                                        break  # Prevent from removing more than one item

                                consoleText.addOutput(consoleInput + ' was removed.')

                                cheatMode = None

                        elif cheatMode == 'Stocks':
                            pl_Info[PK()]['stockInv'].append(consoleInput)

                            consoleText.addOutput(consoleInput +
                                                  ' was added to your inventory.')
                            cheatMode = None

                        elif cheatMode == 'Location':
                            if consoleInput not in TOWN_STRINGS + ABANDONED_TOWN + (UNDERGROUND_CITY,):
                                consoleText.addOutput(PROMPT_CITY_STRING)

                            else:
                                if consoleInput in TOWN_STRINGS + ABANDONED_TOWN:
                                    (players[PK()], ambientSounds,
                                     blockGrid, mapData, backgroundBlocks,
                                     entities, consoleText,
                                     caveBackground) = loadTown(consoleInput, players[PK()],
                                                                pl_Info[PK()])

                                elif consoleInput == UNDERGROUND_CITY:
                                    (players[PK()], ambientSounds, blockGrid,
                                     mapData, backgroundBlocks,
                                     tunnel, entities,
                                     undergroundCity['Old Cave Data']) = loadUndergroundCity(players[PK()],
                                                                                             pl_Info[PK()])
                                    undergroundCity = upgradeUndergroundCity(undergroundCity)

                                else:
                                    assert False

                                (speechBubbles, NPC_Trading['Visible'],
                                 loadScreenOnce, players[PK()],
                                 changingLocation) = enterNewLocation(players[PK()])
                                cheatMode = None
                                consoleText.addOutput('Changed location to ' +
                                                      players[PK()].location + '.')

                        elif cheatMode == 'Console':
                            if consoleInput == 'Exit':
                                cheatMode = None

                            else:
                                try:
                                    exec(consoleInput)

                                except Exception as e:
                                    # Print exception message
                                    consoleText.addOutput(repr(e))
                                    consoleText.addOutput('The command could not be'
                                                          ' run. Check the syntax.')

                    else:
                        if consoleInput == 'Gold':
                            consoleText.addOutput(str(players[PK()].gold))

                        elif consoleInput == 'Cheat':
                            for text in ('Enter cheat code.',
                                         '"Gold", "Inventory", "Stock Inventory",'
                                         ' "Change Location", "Console"'):

                                consoleText.addOutput(text)

                                cheatMode = 'Main'

                        elif consoleInput == 'View Inventory':
                            consoleText.addOutput('You currently have ' +
                                                  cleanInventory(players[PK()].inventory)['Str'] +
                                                  ' in your inventory.')

                        # Update into a function which returns the number
                        # of each stock and make this apply to inventory
                        elif consoleInput == 'View Stock Inventory':
                            consoleText.addOutput('You currently have ' +
                                                  str(pl_Info[PK()]['stockInv']) +
                                                  ' in your inventory.')

                        elif gamemode == 'Play':  # Handle input for towns
                            if (players[PK()].location in TOWNS and
                                consoleInput in ('Goto Bank', 'Goto Library'
                                                 'Goto Market')):

                                if consoleInput == 'Goto Bank':
                                    gamemode = 'Bank'
                                    bankMode = 'Main'

                                elif consoleInput == 'Goto Library':
                                    (gamemode, adventureSelection, libraryCaveInfoMenu,
                                     compartmentSelection, dirtyRects) = loadLibrary()

                                elif consoleInput == 'Goto Market':
                                    gamemode = 'Market'

                            elif players[PK()].location == SECOND_TOWN:
                                if consoleInput == 'Goto Stock Market':
                                    gamemode = 'Stock Market'

                                elif consoleInput == 'Goto Warehouse':
                                    gamemode = 'Warehouse'

                            # Display message for entering buildings
                            if (players[PK()].location in TOWNS and
                                consoleInput in ('Goto Bank', 'Goto Library', 'Goto Market') or

                                players[PK()].location == SECOND_TOWN and
                                    consoleInput in ('Goto Stock Market', 'Goto Warehouse')):
                                consoleIntroText(players[PK()], pl_Info[PK()],
                                                 gamemode)

                                if (gamemode == 'Library' and
                                        len(pl_Info[PK()]['caveAdventures']) == 0):

                                    gamemode = 'Play'
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     players[PK()].location)

                            if (players[PK()].location in TOWNS and
                                    consoleInput == 'Continue Quest'):
                                consoleText.addOutput('')

                                # TODO Make this create a speech bubble
                                if players[PK()].gold < 5:
                                    consoleText.addOutput('You do not have enough '
                                                          'money to begin an expedition.')
                                    consoleText.addOutput('You need to spend 5 '
                                                          'gold to leave the city.')

                                else:
                                    if players[PK()].location == SMALL_TOWN:
                                        players[PK()].direction = 'Right'

                                    elif players[PK()].location == SECOND_TOWN:
                                        players[PK()].direction = 'Left'

                                    gameEvents.append('Load Guard Post')

                                    players[PK()].gold -= 5
                                    addLegacyOutput('You pay the guard, 5 gold to pass...')
                                    addLegacyOutput('Guard Keeper: ' +
                                                    randomGuardKeeperMessage())

                                    players[PK()].canPassGuardKeeper = True
                                    sleepTime = 2

                            elif (players[PK()].location == GUARD_POST and
                                  guardPostAskCaveType):
                                caveType = consoleInput

                                if caveType in ('1', '2', '3'):
                                    gameEvents.append('pickCave')
                                    gameEvents.append('Enter New Cave')

                                else:
                                    addLegacyOutput('Please select 1, 2, or 3.')

                            elif players[PK()].location == 'Cave':
                                if consoleInput == '':
                                    consoleText.addOutput('')
                                    gameEvents.append('incrementCave')

                                elif consoleInput == 'Leave':
                                    consoleText.addOutput('')
                                    addLegacyOutput('You leave the cave...')
                                    consoleText.addOutput('')

                                    if players[PK()].direction == 'Left':
                                        leaveCave = 'Right'

                                    elif players[PK()].direction == 'Right':
                                        leaveCave = 'Left'

                                elif consoleInput == 'View Progress':
                                    consoleText.addOutput('You are currently ' + str(players[PK()].caveDepth) +
                                                          ' compartments inside the cave.')

                                else:
                                    for text in ('Type "Gold" to see current amount of gold',
                                                 'Type "Leave" to leave the cave."',
                                                 'Type "View Progress" to see how deep you are in the cave."',
                                                 'Type "View Inventory" to view your inventory.',
                                                 'Just press enter to continue through the cave.'):

                                        consoleText.addOutput(text)

                            elif players[PK()].location == UNDERGROUND_CITY:
                                if consoleInput == 'Goto Market':
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     'Underground Market')

                                elif consoleInput == 'View City Information':
                                    consoleText.addOutput('There are ' + str(len(undergroundCity['Compartments'])) +
                                                          ' compartment(s) in the base.')

                                    consoleText.addOutput(getUndergroundLightingInfo())

                                elif consoleInput == 'Continue Quest':
                                    gameEvents.append('leaveUndergroundCity')

                                else:
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     UNDERGROUND_CITY)

                        elif gamemode == 'Bank':
                            if bankMode == 'Main':
                                if consoleInput == 'Leave':
                                    (bankDeposit.value, bankWithdraw.value, gamemode,
                                     loadScreenOnce) = leaveBank()

                                elif consoleInput == 'Deposit':
                                    consoleText.addOutput('Please type the amount of'
                                                          ' gold you want to deposit.')
                                    bankMode = 'Deposit'

                                elif consoleInput == 'Withdraw':
                                    consoleText.addOutput('Please type the amount of'
                                                          ' gold you want to withdraw.')
                                    bankMode = 'Withdraw'

                                elif consoleInput == 'View Balance':
                                    consoleText.addOutput('You currently have ' +
                                                          str(bankBalance) + ' gold in the bank.')
                                    consoleText.addOutput('You are currently holding ' +
                                                          str(players[PK()].gold) + ' gold with you.')

                            elif bankMode == 'Deposit':
                                try:
                                    bankDeposit.value = int(consoleInput)

                                except ValueError:
                                    consoleText.addOutput('Please type an integer!')

                                else:
                                    if bankDeposit.value > players[PK()].gold:
                                        consoleText.addOutput('You do not have that much money.'
                                                              ' Depositing all your gold instead.'
                                                              ' (' + str(players[PK()].gold) + ')')
                                        bankDeposit.value = players[PK()].gold

                                    elif bankDeposit.value < 0:
                                        consoleText.addOutput('Why don\'t you just ask'
                                                              ' for a loan instead?')

                                    # Use if to allow changing depositValue in above if/elif statements
                                    if 0 < bankDeposit.value <= players[PK()].gold:
                                        players[PK()].gold -= bankDeposit.value
                                        pl_Info[PK()]['bankBalance'] += bankDeposit.value
                                        consoleText.addOutput(
                                            'Thank you for your transaction, anything else?')

                                        bankMode = 'Main'

                            elif bankMode == 'Withdraw':
                                try:
                                    bankWithdraw.value = int(consoleInput)

                                except ValueError:
                                    consoleText.addOutput('Please type an integer!')

                                else:
                                    if bankWithdraw.value > bankBalance:
                                        consoleText.addOutput('Sorry, you do not have '
                                                              'that much money in the bank.')

                                    elif bankWithdraw.value < 0:
                                        consoleText.addOutput('Why not just make a deposit?')

                                    elif 0 < bankWithdraw.value <= bankBalance:
                                        players[PK()].gold += bankWithdraw.value
                                        pl_Info[PK()]['bankBalance'] -= bankWithdraw.value
                                        consoleText.addOutput('Thank you for your '
                                                              'transaction, anything else?')

                                        bankMode = 'Main'

                        elif gamemode == 'Market':
                            if marketMode == 'Main':
                                if consoleInput == 'Leave':
                                    (gamemode, loadScreenOnce, buyingItem, buyingItemID,
                                     players[PK()]) = leaveMarket(players[PK()],
                                                                  buyingItem)

                                elif consoleInput.startswith('Buy'):
                                    if consoleInput.count(' '):  # If the player used a space in input
                                        # then don't ask for input and define requestItem
                                        # Define requestItem as input without "Buy"
                                        requestItem = consoleInput[4:]
                                        marketMode = 'Buy 1'

                                    else:
                                        consoleText.addOutput('What do you want to buy?')
                                        marketMode = 'Buy 0'

                                elif consoleInput.startswith('Sell'):
                                    if consoleInput.count(' '):
                                        requestItem = consoleInput[5:]
                                        marketMode = 'Sell 1'

                                    else:
                                        consoleText.addOutput('What do you want to sell?')
                                        marketMode = 'Sell 0'

                                elif consoleInput == 'View Merchandise':
                                    consoleText.addOutput('We have these items in stock...')
                                    consoleText.addOutput(cleanInventory(merchandise)['Str'])
                                    consoleText.addOutput(
                                        'Name the item and we can tell you the price!')
                                    marketMode = 'View Merchandise'

                            elif marketMode in ('Buy 0', 'Sell 0'):  # Choose item
                                requestItem = consoleInput

                                if marketMode == 'Buy 0':
                                    marketMode = 'Buy 1'

                                elif marketMode == 'Sell 0':
                                    marketMode = 'Sell 1'

                            elif marketMode == 'Buy 2':
                                if consoleInput.lower() == 'yes':
                                    if None in players[PK()].inventory:
                                        players[PK()] = appendPlayerInventory(requestItem,
                                                                              player=players[PK()],
                                                                              returnDirtyRects=False)
                                        players[PK()].gold -= itemValue

                                        consoleText.addOutput('Thank you! Have a nice day, you currently'
                                                              ' have ' + str(players[PK()].gold) + ' gold left.')

                                    else:
                                        consoleText.addOutput('You do not have enough '
                                                              'space in your inventory.')

                                elif consoleInput.lower() == 'no':
                                    consoleText.addOutput(
                                        'Sorry then, maybe one day we\'ll have discounts...')

                                if consoleInput.lower() in ('yes', 'no'):
                                    marketMode = 'Main'

                            elif marketMode == 'Sell 2':
                                if consoleInput.lower() == 'yes':
                                    numberOfItems = players[PK()].inventory.count(requestItem)

                                    if numberOfItems > 1:
                                        consoleText.addOutput('You can sell 1 - ' + str(numberOfItems) +
                                                              '. How much do you want to sell?')
                                        marketMode = 'Sell 3'  # Ask quantity

                                    else:
                                        marketMode = 'Sell 4'  # Sell right away

                                elif consoleInput.lower() == 'no':
                                    consoleText.addOutput(
                                        'Sorry, come back we might have a better deal! Really!')
                                    marketMode = 'Main'

                            elif marketMode == 'Sell 3':
                                consoleTextAndInput = integer_input(consoleInput,
                                                                    consoleText)

                                if len(consoleTextAndInput) == 2:
                                    consoleText, numberOfItemSold = consoleTextAndInput

                                    if numberOfItemSold <= numberOfItems:
                                        consoleText.addOutput('You sold ' + str(numberOfItems) +
                                                              ' for ' + str(itemValue * numberOfItemSold) + ' gold.')
                                        marketMode = 'Sell 4'

                                elif len(consoleTextAndInput) == 1:
                                    consoleText = consoleTextAndInput[0]

                            elif marketMode == 'View Merchandise':
                                if consoleInput in merchandise:
                                    itemValue = round(consoleInput.getValue() * marketBaseValue)
                                    consoleText.addOutput(
                                        'The cost of the ' + consoleInput + ' is...')

                                    consoleQueue = {'Timer': [1],
                                                    'Text': ((str(itemValue) + ' gold!',
                                                              'That\'s a great value!'))
                                                    }

                                    sleepTime = consoleQueue['Timer'][0]

                                else:
                                    consoleText.addOutput("We don't have that...")

                                marketMode = 'Main'

                            # Making this an if statement allows it to run right after
                            if marketMode == 'Sell 4':
                                for i in range(numberOfItems):
                                    players[PK()] = removeInventory(players[PK()], requestItem)

                                players[PK()].gold += itemValue * numberOfItems
                                consoleText.addOutput('That was a good deal, you now have ' +
                                                      str(players[PK()].gold) + ' gold.')

                                marketMode = 'Main'

                            if marketMode == 'Buy 1':
                                if requestItem not in merchandise:
                                    # Check if cheat code was inputted
                                    if requestItem == 'Kevin':
                                        for item in merchandise:
                                            if None in players[PK()].inventory:
                                                break

                                            players[PK()] = appendPlayerInventory(item, player=players[PK()],
                                                                                  returnDirtyRects=False)

                                        for item in REGULAR_ORES:
                                            if None in players[PK()].inventory:
                                                break

                                            players[PK()] = appendPlayerInventory(OreItem('Good', item),
                                                                                  player=players[PK(
                                                                                  )],
                                                                                  returnDirtyRects=False)

                                        players[PK()].gold = round(players[PK()].gold * math.pi)
                                        consoleText.addOutput('Here you go...')

                                    else:
                                        consoleText.addOutput(
                                            'We don\'t have that in stock, maybe next time...')

                                    marketMode = 'Main'

                                else:
                                    # Calculate the value beforehand to check if you have enough gold
                                    itemValue = round(requestItem.getValue() * marketBaseValue)

                                    # Check if player has enough gold
                                    if itemValue <= players[PK()].gold:
                                        consoleText.addOutput('That will cost about ' + str(itemValue) +
                                                              ' gold, is that acceptable?')
                                        marketMode = 'Buy 2'

                                    else:
                                        consoleText.addOutput('The item you want costs ' + str(itemValue) +
                                                              ' gold but you only have ' + str(players[PK()].gold) +
                                                              '. Buy it next time.')
                                        marketMode = 'Main'

                            # If statement functions same as above ('Buy 1')
                            if marketMode == 'Sell 1':
                                if requestItem in players[PK()].inventory:
                                    itemValue = round(requestItem.getValue() * marketBaseValue)
                                    consoleText.addOutput('We will give you ' + str(itemValue) +
                                                          ' gold for the ' + requestItem + ', is that good?')
                                    marketMode = 'Sell 2'

                                else:
                                    consoleText.addOutput('You don\'t actually have it...')
                                    marketMode = 'Main'

                        elif gamemode == 'Library':
                            if libraryMode == 'Main':
                                if consoleInput == 'Leave':
                                    gamemode = 'Play'
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     players[PK()].location)

                                elif consoleInput == 'View History':
                                    consoleText.addOutput(
                                        'Please type which adventure you want to hear about.')
                                    consoleText.addOutput('1 - ' +
                                                          str(len(pl_Info[PK()]['caveAdventures'])))
                                    libraryMode = 'Input 0'

                            elif libraryMode == 'Input 0':
                                try:
                                    consoleInput = int(consoleInput)

                                except ValueError:
                                    consoleText.addOutput('Please type an integer!')

                                else:
                                    # Move 1 ahead because of range, but remember array is 1 back
                                    caveAdv = pl_Info[PK()]['caveAdventures']
                                    if consoleInput in range(1, len(caveAdvs) + 1):
                                        adventureRequest = consoleInput

                                        consoleText.addOutput(
                                            'Please tell me what compartment you want me to tell you about.')
                                        # Find amount of lists inside specific adventure
                                        consoleText.addOutput(
                                            '1 - ' + str(len(caveAdvs[adventureRequest - 1]['Compartment']) + 1))

                                        libraryMode = 'Input 1'

                            elif libraryMode == 'Input 1':
                                try:
                                    consoleInput = int(consoleInput)

                                except ValueError:
                                    consoleText.addOutput('Please type an integer!')

                                else:
                                    # Add 1 for starting at 0, and another for range
                                    if consoleInput in range(1, len(pl_Info[PK()]['caveAdventures'][adventureRequest - 1]) + 2):
                                        levelRequest = consoleInput

                                        consoleText.addOutput('Ok, I got it...')

                                        consoleQueue = {'Timer': [3],
                                                        'Text': ['']  # Temporary fix later
                                                        }

                                        sleepTime = consoleQueue['Timer'][0]

                                        ''' In development, caves are different #TODO: make cave environments
                                        cave_environments(caveAdventures[adventureRequest - 1][levelRequest - 1][0])
                                        #Prints caveEnvironment by giving caveID and having it printed inside function
                                        print(caveAdventures[adventureRequest - 1][levelRequest - 1][1]) #Print the caveEvent
                                        '''

                                        libraryMode = 'Main'

                        elif gamemode == 'Stock Market':
                            if stockMarketMode == 'Main':
                                #requestItem = ''

                                if consoleInput == 'Leave':
                                    gamemode = 'Play'
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     players[PK()].location)

                                elif consoleInput.startswith('Buy'):
                                    if consoleInput.count(' '):
                                        requestItem = consoleInput[4:]
                                        stockMarketMode = 'Buy 1'

                                    else:
                                        consoleText.addOutput('What do you want to buy?')
                                        stockMarketMode = 'Buy 0'

                                elif consoleInput.startswith('Sell'):
                                    if consoleInput.count(' '):
                                        requestItem = consoleInput[5:]
                                        stockMarketMode = 'Sell 1'

                                    else:
                                        consoleText.addOutput('What do you want to sell?')
                                        stockMarketMode = 'Sell 0'

                                elif consoleInput == 'View Stocks':
                                    consoleText.addOutput('We have these stocks available.')

                                    # Iterate through available stocks and find their value using function
                                    for stock in availableStocks:
                                        consoleText.addOutput(
                                            stock + ' - ' + str(stocks[stock].int))

                                    for text in ('The previous to current values of all the stocks are...',
                                                 str(stocks['Miner Co.'].int),
                                                 str(stocks['Exploration Inc'].int),
                                                 str(stocks['Blocks and Crafts'].int),
                                                 'Name the company and we can tell you more information!'):

                                        consoleText.addOutput(text)

                                    stockMarketMode = 'View Stocks'

                            elif stockMarketMode in ('Buy 0', 'Sell 0'):
                                requestItem = consoleInput

                                if stockMarketMode == 'Buy 0':
                                    stockMarketMode = 'Buy 1'

                                elif stockMarketMode == 'Sell 0':
                                    stockMarketMode = 'Sell 1'

                            elif stockMarketMode == 'Buy 2':
                                try:
                                    stockMarketBuy.value = int(consoleInput)

                                except ValueError:
                                    consoleText.addOutput('Please type an integer!')

                                else:
                                    # Check if player has enough gold
                                    if itemValue * stockMarketBuy.value <= players[PK()].gold:
                                        consoleText.addOutput('That will cost about ' +
                                                              str(itemValue * stockMarketBuy.value) +
                                                              ' gold, is that acceptable?')
                                        stockMarketMode = 'Buy 3'

                                    else:
                                        consoleText.addOutput('You don\'t have enough money to buy ' +
                                                              str(stockMarketBuy.value) + ' stocks.')
                                        consoleText.addOutput('That would require ' +
                                                              str(itemValue * stockMarketBuy.value) +
                                                              ' gold and you only have ' + str(players[PK()].gold))

                            elif stockMarketMode == 'Buy 3':
                                if consoleInput.lower() == 'yes':
                                    # Append requestedQuantity number of times
                                    for i in range(stockMarketBuy.value):
                                        pl_Info[PK()]['stockInv'].append(requestItem)

                                    # Subtract gold value by item value and quantity
                                    players[PK()].gold -= round(itemValue * stockMarketBuy.value)
                                    consoleText.addOutput('Thank you! Have a nice day, you currently have ' +
                                                          str(players[PK()].gold) + ' gold left.')

                                elif consoleInput.lower() == 'no':
                                    consoleText.addOutput(
                                        'Sorry then, maybe one day it\'s value will decrease...')

                                if consoleInput.lower() in ('yes', 'no'):
                                    stockMarketMode = 'Main'

                            elif stockMarketMode == 'Sell 2':
                                if consoleInput.lower() == 'yes':
                                    pl_Info[PK()]['stockInv'].remove(requestItem)
                                    players[PK()].gold += itemValue
                                    consoleText.addOutput('That was a good deal, you have ' +
                                                          str(players[PK()].gold) + ' gold left.')

                                elif consoleInput.lower() == 'no':
                                    consoleText.addOutput('Sorry, maybe you just need to wait. ' +
                                                          'May the odds be ever in your favor.')

                                if consoleInput.lower() in ('yes', 'no'):
                                    stockMarketMode = 'Main'

                            elif stockMarketMode == 'View Stocks':
                                requestItem = consoleInput

                                if requestItem not in availableStocks:
                                    consoleText.addOutput('That company never existed...')
                                    consoleText.addOutput('The stocks are, ' + str(availableStocks))

                                else:
                                    # Comparison stock manager begins, 5 is newest and 1 is oldest stock value
                                    for text in stockCritic(stocks[selectedStock].oldFloatValue)[-5:]:
                                        consoleText.addOutput(text)
                                        stockMarketMode = 'Main'

                            if stockMarketMode == 'Buy 1':  # Read the comment about if statements at end of elifs near end of marketMode code
                                requestItem = consoleInput
                                if requestItem not in availableStocks:  # Check if stock is non existent
                                    consoleText.addOutput('That stock doesn\'t exist, why don\'t you '
                                                          'look for information before you invest...')
                                    consoleText.addOutput(
                                        'Try again, here are the stocks. ' + str(availableStocks))

                                else:
                                    itemValue = stocks[requestItem].int
                                    consoleText.addOutput('How much stocks do you want to buy? The cost '
                                                          'of one stock is ' + str(round(itemValue)) + '.')
                                    consoleText.addOutput('The maximum amount of stocks you can buy is ' +
                                                          str(mathFloor(players[PK()].gold / itemValue)) + ' stocks.')

                                    stockMarketMode = 'Buy 2'

                            if stockMarketMode == 'Sell 1':
                                if requestItem in pl_Info[PK()]['stockInv']:
                                    itemValue = stocks[requestItem].float
                                    consoleText.addOutput('We will give you ' + str(round(itemValue)) + ' gold for'
                                                          ' the ' + requestItem + '\'s stock, is that good?')
                                    stockMarketMode = 'Sell 2'

                                else:
                                    consoleText.addOutput(
                                        'You don\'t have that company\'s stock...')
                                    stockMarketMode = 'Sell 0'

                        elif gamemode == 'Warehouse':
                            if warehouseMode == 'Main':
                                if consoleInput == 'Leave':
                                    gamemode = 'Play'
                                    consoleIntroText(players[PK()], pl_Info[PK()],
                                                     players[PK()].location)

                                elif consoleInput.startswith('Deposit'):
                                    if consoleInput.count(' '):
                                        requestItem = consoleInput[len('Deposit '):]
                                        warehouseMode = 'Deposit 1'

                                    else:
                                        consoleText.addOutput('What do you want to deposit?')
                                        warehouseMode = 'Deposit 0'

                                elif consoleInput.startswith('Withdraw'):
                                    if consoleInput.startswith('Withdraw '):
                                        requestItem = consoleInput[len('Withdraw '):]
                                        warehouseMode = 'Withdraw 1'

                                    else:
                                        consoleText.addOutput('What do you want to withdraw?')
                                        warehouseMode = 'Withdraw 0'

                                elif consoleInput == 'View Inside':
                                    if len(pl_Info[PK()]['warehouseInv']) == 0:
                                        consoleText.addOutput('You have nothing inside!')

                                    else:
                                        consoleText.addOutput('You put these items inside...')
                                        consoleText.addOutput(cleanInventory(
                                            pl_Info[PK()]['warehouseInv'])['Str'])

                            elif warehouseMode in ('Deposit 0', 'Withdraw 0'):
                                requestItem = consoleInput

                                if stockMarketMode == 'Deposit 0':
                                    stockMarketMode = 'Deposit 1'

                                elif stockMarketMode == 'Withdraw 0':
                                    stockMarketMode = 'Withdraw 1'

                            if warehouseMode == 'Deposit 1':  # Read the comment about if statements at end of elifs near end of marketMode code
                                requestItem = consoleInput

                                if requestItem in players[PK()].inventory:
                                    pl_Info[PK()]['warehouseInv'].append(requestItem)
                                    players[PK()] = removeInventory(players[PK()],
                                                                    requestItem)

                                    string = random.choice(("Thank you, my warehouse gets more and more full!",
                                                            "Thank you! I'm going to need to move out, and get a new warehouse!",
                                                            "Oh that'sssssss a very nice item you deposited...",
                                                            "I'll keep it safe! Do not worry!",
                                                            "You can count on us! I mean me!"
                                                            ))
                                    consoleText.addOutput(string)

                                    warehouseMode = 'Main'

                                else:
                                    consoleText.addOutput('I don\'t understand what you mean, ',
                                                          'please repeat what you want to deposit.')

                            if warehouseMode == 'Withdraw 1':
                                requestItem = consoleInput

                                if (requestItem in pl_Info[PK()]['warehouseInv'] and
                                        None in players[PK()].inventory):
                                    players[PK()] = appendPlayerInventory(requestItem,
                                                                          player=players[PK()],
                                                                          returnDirtyRects=False)
                                    pl_Info[PK()]['warehouseInv'].remove(requestItem)

                                    string = random.choice(('The item I gave you is not someone else\'s, same but different.',
                                                            'You don\'t have to remove things because of our theft problem...',
                                                            'Despite some scratches and holes, your item was not underneath more than 50 objects.',
                                                            'We lost it... but we took a replica and added each scratch and fingerprint back on.',
                                                            'Some parts have been chipped away, so we put some new material. '
                                                            'We may have accidentally chipped away and replaced everything...'
                                                            ))
                                    consoleText.addOutput(string)

                                    warehouseMode = 'Main'

                                elif (requestItem in pl_Info[PK()]['warehouseInv'] and
                                      None not in players[PK()].inventory):
                                    consoleText.addOutput(
                                        'You do not have enough space in your inventory.')

                                elif requestItem not in pl_Info[PK()]['warehouseInv']:
                                    consoleText.addOutput('We don\'t have that with us, '
                                                          'but we didn\'t lose anything!')

                else:
                    consoleText.keydown()

        windowSurface.fill(BLACK)
        consoleText.draw()

    else:  # Not in console mode
        if gamemode == 'Paused':
            for event in pygameEvents:
                if leftClick(event):
                    # Check if clicked on any buttons to play sound
                    for i in pauseButtons:
                        if mouseover(pauseButtons[i].rect):
                            playSound(menuButtonSound)

                    if mouseover(pauseButtons['Resume'].rect):
                        gamemode = 'Play'
                        loadScreenOnce = False
                        pauseBackground = None
                        BLACK_SCREEN.set_alpha(255)

                    elif mouseover(pauseButtons['Toggle Server'].rect):
                        if isClient:
                            chatText.addOutput('You cannot start a server while'
                                               'still connected as a client.')

                        else:
                            dirtyRects.append(pauseButtons['Toggle Server'].rect.copy())
                            serverOn = not serverOn

                            if serverOn:
                                pauseButtons['Toggle Server'].changeText('Stop Server',
                                                                         menuFont)

                                # Start server
                                TCP_STREAM, UDP_STREAM = createNetworkingStreams()
                                TCP_STREAM.bind((HOST_IP, MAIN_PORT))
                                UDP_STREAM.bind((HOST_IP, MAIN_PORT))
                                SEND_BROADCAST_STREAM.bind((HOST_IP, BROADCAST_PORT))

                                TCP_STREAM.listen(5)

                                killThread = False
                                disconnectServer = {}
                                threading.Thread(target=TCP_server).start()

                            else:
                                pauseButtons['Toggle Server'].changeText('Start Server',
                                                                         menuFont)
                                # Stop
                                killThread = True
                                TCP_STREAM, UDP_STREAM = killSocket(TCP_STREAM, UDP_STREAM)

                            dirtyRects.append(pauseButtons['Toggle Server'].rect)

                    elif mouseover(pauseButtons['Options'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Options')

                    elif mouseover(pauseButtons['Quit Game'].rect):
                        if isClient:
                            (pauseButtons['Quit Game'], gamemode, disconnectClient,
                             TCP_STREAM, UDP_STREAM) = tryDisconnectClient()

                        else:
                            saveGame(librarySave=False)
                            (gamemode,
                             mainMenuScreenshots) = loadMainMenu()

                        loadScreenOnce = False
                        worldID = None  # No world loaded
                        inGame = False
                        soundMixer.music.stop()

                if pressEscape(event):
                    gamemode = 'Play'
                    loadScreenOnce = False

            for i in pauseButtons:
                pauseButtons[i].draw()

        elif gamemode == 'Main Menu':
            for event in pygameEvents:
                if leftClick(event):
                    if mouseover(mainMenuButtons['Single Player'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Singleplayer Menu')

                    elif mouseover(mainMenuButtons['Multiplayer'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Multiplayer Menu')

                    elif mouseover(mainMenuButtons['Options'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Options')

                    elif mouseover(mainMenuButtons['Quit'].rect):
                        quitGame()

                    # Toggling between phone mode and tablet mode
                    elif android and mouseover(changeAndroidMode[options['phoneMode']].rect):
                        options['phoneMode'] = not options['phoneMode']
                        playSound(menuButtonSound)

                    # Play sound if player clicked on any button
                    for i in mainMenuButtons:
                        if mouseover(mainMenuButtons[i].rect):
                            playSound(menuButtonSound)
                            break

                elif event.type == pygame.KEYDOWN:
                    optionFile = shelve.open('options')
                    dirtyRects = changeName.typeText()
                    options['playerName'] = changeName.value

                    optionFile['Player Name'] = options['playerName']
                    optionFile.close()

                elif event.type == AUTOSAVE_TIMER and autoShuffle:
                    if gamemode == 'Main Menu':
                        mainMenuScreenshots = shuffleScreenshots()

            windowSurface.blit(logoImage, logoRect)

            for i in mainMenuScreenshotOrder:
                pygame.draw.rect(windowSurface, DARKER_GREY, mainMenuScreenshots['Outline'][i])

                # If screenshot not found
                if mainMenuScreenshots['Image'][i] is not None:
                    windowSurface.blit(mainMenuScreenshots['Image'][i],
                                       mainMenuScreenshotSize[i])

                    mainMenuScreenshots['TextRect'][i].draw()

                    drawRightTriangles(GREY, mainMenuScreenshots['TextRect'][i].rect)

            for i in mainMenuButtons:
                mainMenuButtons[i].draw()

            # Show ability to switch between phone (small) GUI and tablet GUI
            if android:
                changeAndroidMode[options['phoneMode']].draw()

            changeName.draw()

        elif gamemode == 'Options':
            for event in pygameEvents:
                if leftClick(event):
                    optionFile = shelve.open('options')
                    for i in optionButtons:
                        if mouseover(optionButtons[i].rect):
                            dirtyRects.append(optionButtons[i].rect.copy())
                            break

                    if mouseover(optionButtons['Sound'].rect):  # Sound Options
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Sound Options')

                    elif mouseover(optionButtons['fullscreen'].rect):
                        (options['fullscreen'], optionFile['fullscreen'],
                         optionButtons['fullscreen'],
                         loadScreenOnce) = toggleFullscreen()

                    elif mouseover(optionButtons['Dirty Rect'].rect):
                        options['dirtyRect'] = not options['dirtyRect']

                        if options['dirtyRect']:
                            dirtyRectEnabledString = 'Optimized'

                        else:
                            dirtyRectEnabledString = 'Fail-safe'

                        optionFile['Dirty Rect'] = options['dirtyRect']
                        optionButtons['Dirty Rect'].changeText(dirtyRectEnabledString,
                                                               menuFont)

                        # Auto disable Lighting when dirty rect system is used
                        if options['dirtyRect'] and options['lighting'] != 'Off':
                            (options['lighting'], optionFile['Lighting'],
                             optionButtons['Lighting']) = toggleLightingMode('Off')

                    elif mouseover(optionButtons['Controls'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Controls')

                    elif (mouseover(optionButtons['Lighting'].rect) and
                          not options['dirtyRect']):
                        newLightingMode = {'Off': 'B & W',
                                           'B & W': 'Colour',
                                           'Colour': 'Off'}[options['lighting']]
                        (options['lighting'], optionFile['Lighting'],
                         optionButtons['Lighting']) = toggleLightingMode(newLightingMode)

                    elif mouseover(optionButtons['Advanced Options'].rect):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Advanced Options')

                    elif mouseover(backButton.rect):
                        (loadScreenOnce, gamemode,
                         previousGamemode) = clickBackButton()

                    for i in ('tooltips', 'touchScreen', 'autoCombat'):
                        if mouseover(optionButtons[i].rect):
                            (dirtyRects, options[i],
                             optionFile) = optionButtons[i].checkClick(optionFile)
                            break

                    optionFile.close()

                    for i in optionButtons:
                        # These buttons already manage the below
                        if i in ('tooltips', 'touchScreen', 'autoCombat'):
                            continue

                        if mouseover(optionButtons[i].rect):
                            playSound(menuButtonSound)
                            dirtyRects.append(optionButtons[i].rect)
                            break

            for i in optionButtons:
                optionButtons[i].draw()

            # If mousing over dirty rects, display info
            if mouseover(optionButtons['Dirty Rect'].rect):
                dirtyRectInfo.rect.topleft = mousePos
                dirtyRects.append(dirtyRectInfo.draw())

            backButton.draw()

        elif gamemode == 'Advanced Options':
            for event in pygameEvents:
                if leftClick(event):
                    if mouseover(backButton.rect):
                        (loadScreenOnce, gamemode,
                         previousGamemode) = clickBackButton()

                    else:
                        for i in advancedOptionButtons:
                            if mouseover(advancedOptionButtons[i].rect):
                                optionFile = shelve.open('options')
                                (dirtyRects, options[i],
                                 optionFile) = advancedOptionButtons[i].checkClick(optionFile)
                                optionFile.close()
                                break

            for i in advancedOptionButtons:
                advancedOptionButtons[i].draw()

            backButton.draw()

        elif gamemode == 'Controls':
            for event in pygameEvents:
                if leftClick(event):
                    for i in controlButtons:
                        if mouseover(controlButtons[i].rect):
                            playSound(menuButtonSound)
                            selectedControlButton = i
                            dirtyRects.append(controlButtons[i].rect)
                            break

                    else:
                        if selectedControlButton is not None:
                            selectedControlButton = None
                            dirtyRects.append(controlButtons[i].rect)

                        if mouseover(backButton.rect):
                            (loadScreenOnce, gamemode,
                             previousGamemode) = clickBackButton()

                elif event.type == pygame.KEYDOWN:
                    if selectedControlButton is not None:
                        i = selectedControlButton
                        controls = controlButtons[i].keyDown(event.key, controls)

            # Display menu buttons
            for i in controlButtons:
                controlButtons[i].draw()

            backButton.draw()

        elif gamemode == 'Sound Options':
            for event in pygameEvents:
                if leftClick(event):
                    optionFile = shelve.open('options')
                    # Generic, toggle option code
                    for i in soundOptionButtons:
                        if mouseover(soundOptionButtons[i].rect):
                            print('clicked', i)
                            (dirtyRects, options[i],
                             optionFile) = soundOptionButtons[i].checkClick(optionFile)
                            print('Options', i, options[i])
                            break

                    # Each button's actions are below
                    if mouseover(soundOptionButtons['sound'].rect):
                        if not options['sound']:
                            for sound in ambientSounds:
                                sound.stop()

                    elif mouseover(soundOptionButtons['music'].rect):
                        if options['music']:
                            if previousGamemode[-2] in ('Play', 'Paused'):
                                currentMusic = pickMusic(players[PK()])
                                soundMixer.music.load(currentMusic)
                                soundMixer.music.play()

                        else:
                            soundMixer.music.stop()

                    elif mouseover(soundOptionButtons['ambience'].rect):
                        if options['ambience']:
                            for sound in ambientSounds:
                                playSound(sound, -1)

                        else:
                            for sound in ambientSounds:  # Same as turning sound off
                                sound.stop()

                    elif mouseover(backButton.rect):
                        (loadScreenOnce, gamemode,
                         previousGamemode) = clickBackButton()

                    optionFile.close()

            for i in soundOptionButtons:
                soundOptionButtons[i].draw()

            backButton.draw()

        elif gamemode == 'Singleplayer Menu':
            for event in pygameEvents:
                if leftClick(event):
                    # Check if clicked on any buttons to play sound
                    worldButtons.mouseover()

                    for i in singlePlayMenuButtons:
                        if mouseover(singlePlayMenuButtons[i].rect):
                            playSound(menuButtonSound)


                    worldID = worldButtons.get_mouseover()
                    if worldID is not None:
                        # Don't create saves folder yet if it doesn't exist
                        saveFolder = checkSaveDirectory(worldID, False)

                        if not deleteMode:
                            gamemode = 'Play'
                            loadScreenOnce = False

                            # Create saves folder if non-existant
                            saveFolder = checkSaveDirectory(worldID, True)

                            path = getSaveFile(saveFolder)
                            if os.path.isfile(path):  # Load world
                                saveFile = shelve.open(path, writeback=True)
                                marketBaseValue, oldMarketBaseValue = saveFile['marketBaseValue']
                                timeTick = saveFile['timeTick']
                                weather, weatherDuration = saveFile['weather']
                                oldCaveData = saveFile['oldCaveData']
                                entities = saveFile['entities']
                                players = saveFile['players']
                                (pl_Info, consoleText, chatText, blockGrid,
                                 backgroundBlocks,
                                 mapData) = saveFile['pl_Info']

                                stocks = saveFile['stocks']

                                caveSize = saveFile['Cave Info']

                                undergroundCity = saveFile['undergroundCity']
                                abandonedTown = saveFile['abandonedTown']

                                speechBubbles = saveFile['Speech Bubbles']

                                saveFile.close()

                                if players[PK()].location == UNDERGROUND_CITY_EXIT:
                                    goldGiven.update()

                            else:  # Clicked create world
                                # Generate world
                                timeTick = 50

                                weatherDuration = random.uniform(180, 360)
                                weather = 'Sun'

                                # Player information, map generator needs this
                                players = {PK(): Player(INTERNAL_HEIGHT / 2)}

                                oldMarketBaseValue = []
                                (marketBaseValue,
                                 oldMarketBaseValue) = newMarketValue(oldMarketBaseValue)
                                caveSize = 'N/A'

                                (pl_Info[PK()], consoleText,
                                 chatText) = createPlayerData()

                                # Stock Information
                                stocks = {'Miner Co.': Stock(25, 0.1),
                                          'Exploration Inc': Stock(75, 0.25),
                                          'Blocks and Crafts': Stock(250, 0.05)}

                                # Underground City Information, expand this later to include more variables
                                undergroundCity = {'Taxes': 0,  # Counts amount of money given by player
                                                   'Buildings': [],
                                                   'Compartments': ['Centre'],
                                                   'Lighting': 'Torches',
                                                   'Old Cave Data': None}  # Upgrades to experimental electricity and then glass-lava ceiling
                                oldCaveData = None

                                abandonedTown = {}
                                for i in ('Left', 'Centre', 'Right'):
                                    abandonedTown[i] = {}
                                    abandonedTown[i]['Map'] = None

                                for i in range(longTermStockGraph.linesOfHeight):
                                    stocks = updateStockValue()

                                for i in range(marketGraph.linesOfHeight):  # 15
                                    (marketBaseValue,
                                     oldMarketBaseValue) = newMarketValue(oldMarketBaseValue)

                                entities = []  # Setup blank list
                                speechBubbles = []

                                (players[PK()], ambientSounds,
                                 blockGrid, mapData, backgroundBlocks,
                                 entities, consoleText,
                                 caveBackground) = loadTown(players[PK()].location, players[PK()],
                                                            pl_Info[PK()])

                                players[PK()].rect.bottom = mapData['groundY']
                                # End create world

                                saveFolder = checkSaveDirectory(worldID, True)
                                createNewSave(saveFolder)

                            currentMusic, playerInfo = initializeWorld()

                        # Click existing world in delete mode
                        elif deleteMode and os.path.isfile(getSaveFile(saveFolder)):
                            shutil.rmtree(saveFolder)
                            path = os.path.join("saves", "thumbnails", str(worldID) + '.png')
                            removeFile(path)

                            dirtyRects.append(worldButtons.buttons[worldID].rect)
                            worldButtons.buttons[worldID].changeText('Create World',
                                                                     menuFont)
                            dirtyRects.append(worldButtons.buttons[worldID].rect)

                    else:
                        if singlePlayMenuButtons['Delete World'].mouseover():
                            (deleteMode,
                             dirtyRects) = singlePlayMenuButtons['Delete World'].toggleDeleteButton()

                        elif singlePlayMenuButtons['World Type'].mouseover():
                            options['testWorld'] = not options['testWorld']

                            if options['testWorld']:
                                testWorldString = 'Test World'

                            else:
                                testWorldString = 'Normal World'

                            dirtyRects.append(singlePlayMenuButtons['World Type'].rect.copy())
                            singlePlayMenuButtons['World Type'].changeText(testWorldString,
                                                                           menuFont)
                            dirtyRects.append(singlePlayMenuButtons['World Type'].rect)

                            optionFile = shelve.open('options')
                            optionFile['Test World'] = options['testWorld']
                            optionFile.close()

                        # Player has not clicked on any buttons, check Back
                        elif mouseover(backButton.rect):
                            lastHighlightedWorld['ID'] = None
                            lastHighlightedWorld['Preview'] = None

                            (loadScreenOnce, gamemode,
                             previousGamemode) = clickBackButton()
                            # Duplicate statements which set main menu
                            gamemode, mainMenuScreenshots = loadMainMenu()

                elif event.type == pygame.MOUSEMOTION:
                    # Check if player's mouse went over any worlds
                    # Last two buttons are not worlds
                    worldID = worldButtons.get_mouseover()
                    if worldID is not None:
                        # Don't update background if same world
                        if worldID != lastHighlightedWorld['ID']:
                            # TODO: move this into the world directory
                            lastHighlightedWorld['ID'] = worldID
                            saveFolder = checkSaveDirectory(lastHighlightedWorld['ID'], False)

                            if lastHighlightedWorld['Date'] is not None:
                                dirtyRects.append(lastHighlightedWorld['Date'].rect)

                            path = os.path.join('saves', 'thumbnails',
                                                str(lastHighlightedWorld['ID']) + '.png')
                            if os.path.isfile(path):
                                lastHighlightedWorld['Preview'] = imgLoad(path)

                            else:
                                # If thumbnail was deleted just leave it blank
                                lastHighlightedWorld['Preview'] = None

                            path = getSaveFile(saveFolder)
                            if os.path.isfile(path):
                                saveFile = shelve.open(path, writeback=True)

                                try:
                                    dateText = saveFile['Time Last Played']

                                except KeyError:
                                    dateText = 'Time last played data corrupted.'

                                saveFile.close()

                                lastHighlightedWorld['Date'] = TextRect(font, dateText, GREY)
                                lastHighlightedWorld['Date'].rect.topleft = 0, 0

                            dirtyRects.append(SCREEN_RECT)

                            if lastHighlightedWorld['Date'] is not None:
                                dirtyRects.append(lastHighlightedWorld['Date'].rect)

                elif pressEscape(event):
                    gamemode, mainMenuScreenshots = loadMainMenu()
                    loadScreenOnce = False

            # Display background
            if lastHighlightedWorld['Preview'] is not None:
                # Similar to pause screen with faded image of world
                windowSurface.blit(lastHighlightedWorld['Preview'], (0, 0))

                if lastHighlightedWorld['Date'] is not None:
                    lastHighlightedWorld['Date'].draw()

            else:
                windowSurface.blit(stoneBackground, (0, 0))

            for i in singlePlayMenuButtons:
                singlePlayMenuButtons[i].draw()

            worldButtons.draw()
            backButton.draw()

        elif gamemode == 'Multiplayer Menu':
            for event in pygameEvents:
                if leftClick(event):
                    if (mouseover(multiPlayMenuButtons['Connect'].rect) and
                        selectedServerID is not None and
                            serverList[selectedServerID] is not None):

                        serverIP = serverList[selectedServerID]['IP']
                        TCP_STREAM, UDP_STREAM = createNetworkingStreams()

                        # Start connection
                        killThread = False
                        threading.Thread(target=TCP_client).start()
                        isClient = True
                        loadScreenOnce = False

                        pauseButtons['Quit Game'].changeText('Disconnect', menuFont)

                    elif (mouseover(multiPlayMenuButtons['Refresh'].rect) and
                          # Clicked refresh and not scanning for servers
                          not scanningServers):
                        # Search for LAN servers
                        timeScanningServers = 0
                        threading.Thread(target=UDP_Broadcast).start()

                        LAN_ServerListLock.acquire()
                        LAN_ServerList = {}
                        LAN_ServerListLock.release()

                    elif mouseover(multiPlayMenuButtons['Add Server'].rect):
                        for i in serverList:
                            if i is None:
                                # Only switch gamemode if player has a spare slot
                                (loadScreenOnce, previousGamemode,
                                 gamemode) = setGamemode('Multiplayer Menu - Add Server')
                                addServerName.setValue('')
                                addIP.setValue('')
                                break

                        else:
                            playSound(errorSound)

                    elif (mouseover(multiPlayMenuButtons['Edit'].rect) and
                          selectedServerID is not None):
                        (loadScreenOnce, previousGamemode,
                         gamemode) = setGamemode('Multiplayer Menu - Edit')
                        addServerName.setValue(serverList[selectedServerID]['Name'])
                        addIP.setValue(serverList[selectedServerID]['IP'])

                    elif mouseover(multiPlayMenuButtons['Delete'].rect):
                        (deleteMode,
                         dirtyRects) = multiPlayMenuButtons['Delete'].toggleDeleteButton()

                    elif mouseover(backButton.rect):
                        (loadScreenOnce, gamemode,
                         previousGamemode) = clickBackButton()

                        selectedServerID = None

                    else:
                        for i, rect in zip(range(len(serverList)), multiPlayMenuList):
                            if mouseover(rect) and serverList[i] is not None:
                                selectedServerID = i

                                if deleteMode:
                                    serverList[selectedServerID] = None
                                    selectedServerID = None

                                break

                        else:
                            selectedServerID = None

                    # Play sound if player clicked on any button
                    for i in multiPlayMenuButtons:
                        if mouseover(multiPlayMenuButtons[i].rect):
                            playSound(menuButtonSound)
                            break

                elif pressEscape(event):
                    gamemode, mainMenuScreenshots = loadMainMenu()
                    loadScreenOnce = False

                elif event.type == SECOND_TIMER and scanningServers:
                    if timeScanningServers < scanServerTimeout:
                        timeScanningServers += 1

                        if timeScanningServers >= scanServerTimeout:
                            scanningServers = False
                            RECV_BROADCAST_STREAM.shutdown(socket.SHUT_RDWR)

            pygame.draw.rect(windowSurface, DARK_GREY,
                             pygame.Rect(0, INTERNAL_HEIGHT - 150,
                                         INTERNAL_WIDTH, 150))

            # Display buttons
            for i in multiPlayMenuButtons:
                multiPlayMenuButtons[i].draw()

            backButton.draw()

            for i, rect in zip(range(len(serverList)), multiPlayMenuList):
                if mouseover(rect) or i == selectedServerID:
                    color = GREY

                else:
                    color = DARK_GREY

                pygame.draw.rect(windowSurface, color, rect)

                if serverList[i] is not None:
                    serverList[i]['Name TR'].draw()
                    serverList[i]['IP TR'].draw()

            if disconnectMessage['Text'] is not None:
                (loadScreenOnce, previousGamemode,
                 gamemode) = setGamemode('Multiplayer Error')

                disconnectMessage['TextRect'] = TextRect(
                    font, disconnectMessage['Text'], WHITE, GREY)
                disconnectMessage['TextRect'].rect.center = (INTERNAL_WIDTH // 2,
                                                             INTERNAL_HEIGHT // 2)

        elif gamemode in ('Multiplayer Menu - Add Server',
                          'Multiplayer Menu - Edit'):
            for event in pygameEvents:
                if leftClick(event):
                    addServerName.toggleChangingField()
                    addIP.toggleChangingField()

                    if mouseover(backButton.rect):
                        (loadScreenOnce, gamemode,
                         previousGamemode) = clickBackButton()

                    elif mouseover(addServerMenuButtons['Continue'].rect):
                        validIP = False
                        if addIP.value == 'localhost':
                            validIP = True

                        else:
                            try:  # Check if valid IP address
                                socket.inet_aton(addIP.value)

                            except OSError:
                                pass  # TODO: Alert user

                            else:
                                validIP = True

                        if validIP:
                            if gamemode == 'Multiplayer Menu - Add Server':
                                serverList = addServer(addServerName.value, addIP.value)

                            elif gamemode == 'Multiplayer Menu - Edit':
                                serverList = setServer(addServerName.value, addIP.value,
                                                       selectedServerID)

                            else:
                                assert False

                            # Go back to multiplayer menu
                            (loadScreenOnce, gamemode,
                             previousGamemode) = clickBackButton()

                    # Play sound if player clicked on any button
                    for i in addServerMenuButtons:
                        if mouseover(addServerMenuButtons[i].rect):
                            playSound(menuButtonSound)
                            break

                elif event.type == pygame.KEYDOWN:
                    if addIP.changingField:
                        dirtyRects = addIP.typeText()

                    elif addServerName.changingField:
                        dirtyRects = addServerName.typeText()

            # Display buttons
            for i in addServerMenuButtons:
                addServerMenuButtons[i].draw()

            backButton.draw()

            addServerName.draw()
            addIP.draw()

        elif gamemode == 'Multiplayer Error':
            for event in pygameEvents:
                if leftClick(event):
                    (loadScreenOnce, gamemode,
                     previousGamemode) = clickBackButton()
                    disconnectMessage['Text'] = None
                    del disconnectMessage['TextRect']

            # Should only be None if player clicked to exit gamemode
            if disconnectMessage['Text'] is not None:
                disconnectMessage['TextRect'].draw()

            backButton.draw()

        elif gamemode == 'Bank':
            if holdMouseDown:
                if clickRectList(bankDeposit.allButtons):
                    bankDeposit.changeValue(bounds=players[PK()].gold)

                elif clickRectList(bankWithdraw.allButtons):
                    bankWithdraw.changeValue(bounds=pl_Info[PK()]['bankBalance'])

            for event in pygameEvents:
                if leftClick(event):
                    if mouseover(bankDeposit.finalizeButton):
                        players[PK()].gold -= bankDeposit.value
                        pl_Info[PK()]['bankBalance'] += bankDeposit.value

                    elif mouseover(bankWithdraw.finalizeButton):
                        players[PK()].gold += bankWithdraw.value
                        pl_Info[PK()]['bankBalance'] -= bankWithdraw.value

                    elif mouseover(bankText['Bank'].rect):
                        (bankDeposit.value, bankWithdraw.value, gamemode,
                         loadScreenOnce) = leaveBank()

                    if clickRectList((bankDeposit.finalizeButton,
                                      bankWithdraw.finalizeButton)):

                        pl_Info[PK()]['oldBankBalance'] = bankGraph.appendData(pl_Info[PK()]['oldBankBalance'],
                                                                               pl_Info[PK()]['bankBalance'])

                        playSound(adjustValueSound)

                if pressEscape(event):
                    (bankDeposit.value, bankWithdraw.value, gamemode,
                     loadScreenOnce) = leaveBank()

            windowSurface.fill(BLACK)

            bankDeposit.draw(players[PK()].gold)
            bankWithdraw.draw(pl_Info[PK()]['bankBalance'])

            # Autoupdate texts as needed
            bankText['Inventory'].updateSurface(players[PK()].gold)
            bankText['Current Balance'].updateSurface(pl_Info[PK()]['bankBalance'])

            for i in bankText:
                bankText[i].draw()

            bankGraph.draw(pl_Info[PK()]['oldBankBalance'])

        elif gamemode == 'Library':
            updateCavePreview = False
            libraryScroll = None

            for event in pygameEvents:
                if (pressEscape(event) or leftClick(event)
                        and mouseover(library.text['Library'].rect)):

                    gamemode, loadScreenOnce = leaveBuilding()

                elif scrollUp(event):
                    libraryScroll = 'Left'

                elif scrollDown(event):
                    libraryScroll = 'Right'

                elif leftClick(event):
                    for i, rect in enumerate(adventureSelection['Back Rect']):
                        adventureID = i + adventureSelection['Offset']

                        if mouseover(rect):
                            adventure_count = len(pl_Info[PK()]['caveAdventures']) - 1
                            adventureID = min(adventureID, adventure_count)

                            selectedAdventure = adventureID + 1
                            selectedCompartment = 0
                            compartmentSelection['Offset'] = 0

                            libraryCaveInfoMenu = updateLibraryCaveInfo(pl_Info[PK()])
                            (compartmentSelection,
                             cavePreview['Surface']) = updateCompartmentSelection(pl_Info[PK()]['caveAdventures'])

                    for i, backRect in enumerate(compartmentSelection['Back Rect']):
                        if mouseover(backRect):
                            selectedCompartment = i + compartmentSelection['Offset']
                            updateCavePreview = True
                            break

                    if mouseover(compartmentSelection['Left Arrow Rect']):
                        libraryScroll = 'Left'

                    elif mouseover(compartmentSelection['Right Arrow Rect']):
                        libraryScroll = 'Right'

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_w, pygame.K_UP):
                        if selectedAdventure > 1:
                            selectedAdventure -= 1
                            selectedCompartment = 0
                            compartmentSelection['Offset'] = 0

                            if selectedAdventure <= adventureSelection['Offset']:
                                adventureSelection['Offset'] -= 1

                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        if selectedAdventure <= len(pl_Info[PK()]['caveAdventures']) - 1:
                            selectedAdventure += 1
                            selectedCompartment = 0
                            compartmentSelection['Offset'] = 0

                            if (selectedAdventure + 1) - adventureSelection['Offset'] == 9:
                                adventureSelection['Offset'] += 1

                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN):
                        adventureSelection, dirtyRects = updateAdventureSelection(
                            pl_Info[PK()]['caveAdventures'])

            if libraryScroll == 'Left':
                updateCavePreview = True
                selectedCompartment -= 1

                if compartmentSelection['Offset'] > 0:
                    compartmentSelection['Offset'] -= 1
                    compartmentSelection, cavePreview['Surface'] = updateCompartmentSelection(
                        pl_Info[PK()]['caveAdventures'])

                if selectedCompartment < 0:
                    selectedCompartment = 0

            elif libraryScroll == 'Right':
                updateCavePreview = True
                selectedCompartment += 1
                compartments = len(pl_Info[PK()]['caveAdventures'][selectedAdventure - 1]['Compartment'])

                if (compartmentSelection['Offset'] +
                    len(compartmentSelection['Back Rect']) < compartments):

                    compartmentSelection['Offset'] += 1
                    compartmentSelection, cavePreview['Surface'] = updateCompartmentSelection(
                        pl_Info[PK()]['caveAdventures'])

                selectedCompartment = min(selectedCompartment, compartments - 1)

            if updateCavePreview:
                saveFolder = os.path.join(checkSaveDirectory(worldID, True),
                                          "caves", str(selectedAdventure),
                                          str(selectedCompartment))

                thumbnail_path = os.path.join(saveFolder, "thumbnail.png")
                if os.path.isfile(thumbnail_path):
                    image = imgLoad(thumbnail_path)
                    cavePreview['Surface'] = pygame.transform.smoothscale(
                        image, cavePreview['Rect'].size)

                else:
                    cavePreview['Surface'] = pygame.Surface(cavePreview['Rect'].size)
                    cavePreview['Surface'].fill(BLACK)

            library.draw()

        elif gamemode == 'Market':
            # Holding store item and can afford
            canBuy = (players[PK()].mouseInventory is not None
                      and players[PK()].gold >= round(players[PK()].mouseInventory.getValue() *
                                                      marketBaseValue)
                      and buyingItem)
            canSell = (players[PK()].mouseInventory is not None
                       and not buyingItem)

            for event in pygameEvents:
                if pressEscape(event):
                    (gamemode, loadScreenOnce, buyingItem, buyingItemID,
                     players[PK()]) = leaveMarket(players[PK()], buyingItem)

                elif leftClick(event):
                    if mouseover(marketSellMenu['Finish Rect']):
                        if canSell:
                            (players[PK()].mouseInventory,
                             players[PK()].gold) = marketSellItem(players[PK()],
                                                                  players[PK()].mouseInventory)

                        else:
                            playSound(errorSound)

                    elif mouseover(marketBuyMenu['Finish Rect']):
                        if canBuy:
                            dirtyRects.append(marketBuyMenu['Inventory Rect'][buyingItemID])

                            buyingItem = False
                            buyingItemID = None

                            players[PK()].gold -= round(players[PK()].mouseInventory.getValue() *
                                                        marketBaseValue)

                            players[PK()], dirtyRects = appendPlayerInventory(players[PK()].mouseInventory,
                                                                              player=players[PK()],
                                                                              returnDirtyRects=True)

                            playSound(pickUpItemSound)
                            players[PK()].mouseInventory = None

                        else:
                            playSound(errorSound)

                    elif clickRectList(marketBuyMenu['Inventory Rect']):
                        if (players[PK()].mouseInventory is None and
                                not buyingItem):

                            buyingItem = True

                            for rect in marketBuyMenu['Inventory Rect']:
                                if mouseover(rect):
                                    buyingItemID = marketBuyMenu['Inventory Rect'].index(rect)

                            players[PK()].mouseInventory = merchandise[buyingItemID]

                        elif players[PK()].mouseInventory is not None and buyingItem:
                            buyingItem = False
                            buyingItemID = None

                            players[PK()].mouseInventory = None

                    elif mouseover(marketText['Market'].rect):
                        (gamemode, loadScreenOnce, buyingItem, buyingItemID,
                         players[PK()]) = leaveMarket(players[PK()], buyingItem)

            # Player is holding an item but it hasn't been processed to diplay info (marketSellMenu)
            if players[PK()].mouseInventory is not None:
                lastItemHighlighted = players[PK()].mouseInventory

                marketSellMenu['Item Name'].visible = True
                marketSellMenu['Item Value'].visible = True

                marketSellMenu['Item Name'].updateSurface(lastItemHighlighted.name)
                marketSellMenu['Item Value'].updateSurface(
                    round(lastItemHighlighted.getValue() * marketBaseValue))

                # Don't change the values
                oldItemValue = []
                for baseValue in oldMarketBaseValue:
                    oldItemValue.append(lastItemHighlighted.getValue() * baseValue)

            elif (players[PK()].mouseInventory is None and
                  marketSellMenu['Item Name'].visible):
                dirtyRects.append(marketSellMenu['Item Name'].rect)
                dirtyRects.append(marketSellMenu['Item Value'].rect)

                marketSellMenu['Item Name'].visible = False
                marketSellMenu['Item Value'].visible = False

                # Reset | This allows graph to still be displayed but with no graphed lines
                for i in range(len(oldItemValue)):
                    oldItemValue[i] = 0

            windowSurface.fill(BLACK)

            # Begin displaying buying area
            pygame.draw.rect(windowSurface, DARK_GREY,
                             marketBuyMenu['Background Rect'])

            for item, rect in zip(marketBuyMenu['Inventory Item'],
                                  marketBuyMenu['Inventory Rect']):

                if buyingItemID is not None and merchandise[buyingItemID] == item:
                    # Don't display item if being held by player
                    windowSurface.blit(inventorySpaceImage, rect)

                else:
                    dirtyRects, itemTooltip = displayItemSlot(itemTooltip,
                                                              item, rect)

            if canBuy:
                invImage = selectedInventorySpaceImage
            else:
                invImage = inventorySpaceImage

            windowSurface.blit(invImage, marketBuyMenu['Finish Rect'])

            if mouseover(marketBuyMenu['Finish Rect']):
                dirtyRects.append(marketBuyMenu['Finish Rect'])
                windowSurface.blit(highlightInventoryImage,
                                   marketBuyMenu['Finish Rect'])

            # Begin displaying selling area
            pygame.draw.rect(windowSurface, DARK_GREY,
                             marketSellMenu['Background Rect'])

            marketSellMenu['Item Name'].draw()
            marketSellMenu['Item Value'].draw()

            if canSell:
                invImage = selectedInventorySpaceImage
            else:
                invImage = inventorySpaceImage

            windowSurface.blit(invImage, marketSellMenu['Finish Rect'])

            if mouseover(marketSellMenu['Finish Rect']):
                dirtyRects.append(marketSellMenu['Finish Rect'])
                windowSurface.blit(highlightInventoryImage,
                                   marketSellMenu['Finish Rect'])

            # Scan for updates
            marketText['Inventory'].updateSurface(players[PK()].gold)

            # Draw text for market
            for i in marketText:
                marketText[i].draw()

            marketGraph.draw(oldItemValue)

        elif gamemode == 'Stock Market':
            if holdMouseDown:
                if clickRectList(stockMarketBuy.allButtons):
                    stockMarketBuy.changeValue(bounds=players[PK()].gold)

                elif clickRectList(stockMarketSell.allButtons):
                    stockMarketSell.changeValue(bounds=pl_Info[PK()]['stockInv'])

            for event in pygameEvents:
                if (pressEscape(event) or leftClick(event)
                        and mouseover(stockMarketText['Stock Market'].rect)):

                    gamemode, loadScreenOnce = leaveBuilding()

                elif leftClick(event):
                    if selectStock.visible:
                        for stock in selectStock.text:
                            if mouseover(selectStock.selectRect[stock]):
                                selectedStock = stock
                                break

                    if mouseover(stockMarketBuy.finalizeButton):
                        (players[PK()], pl_Info[PK()],
                         stockMarketBuy) = buyStock(players[PK()],
                                                    pl_Info[PK()])

                    elif mouseover(stockMarketSell.finalizeButton):
                        (players[PK()], pl_Info[PK()],
                         stockMarketSell) = sellStock(players[PK()], pl_Info[PK()])

                    if clickRectList((stockMarketBuy.finalizeButton,
                                      stockMarketSell.finalizeButton)):
                        playSound(adjustValueSound)

                    for key in STOCK_MARKET_TABS:
                        if mouseover(stockMarketText[key].rect):
                            # Update dirty rects for old tab
                            dirtyRects.append(
                                stockMarketText[stockMarketSelectedTab].getDirtyRect())
                            stockMarketSelectedTab = key

                            # Update dirty rects for new tab
                            dirtyRects.append(stockMarketText[key].getDirtyRect())
                            break

                elif event.type == STOCK_TIMER:
                    stocks = updateStockValue()

                elif event.type == pygame.MOUSEMOTION:
                    dirtyRects = selectStock.checkMouseOver(dirtyRects)

            windowSurface.fill(BLACK)

            stockMarketBuy.draw(bounds=players[PK()].gold)
            stockMarketSell.draw(bounds=pl_Info[PK()]['stockInv'])

            # Scan for updates
            stockMarketText['Own Number of Stocks'].updateSurface(
                (pl_Info[PK()]['stockInv'].count(selectedStock)))
            stockMarketText['Gold Equivalent'].updateSurface(round(stocks[selectedStock].float * stockMarketBuy.value),
                                                             round(stocks[selectedStock].float * stockMarketSell.value))
            stockMarketText['Inventory'].updateSurface(players[PK()].gold)

            for i in stockMarketText:
                stockMarketText[i].draw()

            if stockMarketSelectedTab == 'Past Values':
                floatValues = stocks[selectedStock].oldFloatValue
                stockGraph.draw(floatValues[-stockGraph.linesOfHeight:])

            elif stockMarketSelectedTab == 'Historic Value':
                longTermStockGraph.draw(stocks[selectedStock].oldFloatValue)

            elif stockMarketSelectedTab == 'Own Quantity':
                # TODO: replace second argument with past stockInv
                ownQuantityStockGraph.draw(stocks[selectedStock].oldFloatValue)

            if selectedStock == 'Miner Co.':
                windowSurface.blit(stockMarketLogo['Logo Image'][selectedStock],
                                   stockMarketLogo['Logo Rect'][selectedStock])

                windowSurface.blit(selectStock.text[selectedStock],
                                   stockMarketLogo['Text Rect'][selectedStock])

            dirtyRects = selectStock.draw(dirtyRects)

        elif gamemode == 'Warehouse':
            for event in pygameEvents:
                if (pressEscape(event) or
                        leftClick(event) and mouseover(warehouseText[0].rect)):

                    gamemode, loadScreenOnce = leaveBuilding()

                # TODO: Make this into a class and have the forge inventory use a similar system
                elif leftClick(event):
                    # Similar code to inventory in the play gamemode
                    # Allow clicking on inventory slots by checking if mouse is over slot
                    if currentMenu == 'Warehouse Inventory' and mouseoverSlot is not None:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # Shift click to inventory
                            emptySlot = players[PK()].inventory.index(None)
                            players[PK()].inventory[emptySlot] = pl_Info[PK()
                                                                         ]['warehouseInv'][mouseoverSlot]
                            pl_Info[PK()]['warehouseInv'][mouseoverSlot] = None

                        else:
                            (players[PK()].mouseInventory,
                             pl_Info[PK()]['warehouseInv'][mouseoverSlot]) = (pl_Info[PK()]['warehouseInv'][mouseoverSlot],
                                                                              players[PK()].mouseInventory)

                        # Update results upon changing inventory
                        warehouseSearchResults = updateWarehouseResults(
                            pl_Info[PK()]['warehouseInv'])

                elif event.type == pygame.MOUSEMOTION:
                    if clickRectList((warehouseInvGUI.backRect,
                                      warehouseSearchResultsBackground)):

                        currentMenu = 'Warehouse Inventory'

                elif event.type == pygame.KEYDOWN:
                    dirtyRects = warehouseSearchBox.typeText()
                    warehouseSearchResults = updateWarehouseResults(pl_Info[PK()]['warehouseInv'])

            windowSurface.fill(BLACK)

            for surf in warehouseText:
                surf.draw()

            warehouseInvGUI.draw()

            for i, inventorySlot in enumerate(warehouseInvGUI.slots):
                # Check if mouse over any of the boxes
                if mouseover(inventorySlot):
                    mouseoverSlot = i

                (dirtyRects,
                 itemTooltip) = displayBigItemSlot(itemTooltip,
                                                   pl_Info[PK()]['warehouseInv'][i],
                                                   inventorySlot)

            # Should the column of items or the text describing them be shaded differently?
            pygame.draw.rect(windowSurface, DARK_GREY, warehouseSearchResultsBackground)

            for result, selectRect in zip(warehouseSearchResults,
                                          warehouseSearchResultSelectRect):

                # Highlight item
                if mouseover(selectRect):
                    # the color is brighter than other search results and darker than the search box
                    pygame.draw.rect(windowSurface, DARKER_GREY, selectRect)
                    mouseoverSlot = result['Index']

                drawItem(result['Item'], pygame.Rect(selectRect.topleft, ITEM_SIZE))

                windowSurface.blit(result['Text Surface'], (selectRect.x + 32,  # 32 is size of item area
                                                            # 8 is an arbitrary shift to center text
                                                            selectRect.y + 8))

            # Draw the search area
            pygame.draw.rect(windowSurface, GREY, warehouseSearchBoxBackRect)
            warehouseSearchBox.draw()

        elif gamemode == 'Forge':
            for event in pygameEvents:
                if leftClick(event):
                    if mouseover(forgeText['Forge'].rect):
                        gamemode = 'Play'
                        fireplaceSound.fadeout(3000)

                    # Similar code to inventory in the play gamemode and blacksmith
                    # Allow clicking on inventory slots by checking if mouse is over slot
                    elif (currentMenu in ('Forge Inventory Input',
                                          'Forge Inventory Output') and
                          mouseoverSlot is not None):
                        if currentMenu == 'Forge Inventory Input':
                            i = 'Input'

                        elif currentMenu == 'Forge Inventory Output':
                            i = 'Output'

                        else:
                            assert False

                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # Shift click to inventory
                            emptySlot = players[PK()].inventory.index(None)
                            players[PK()].inventory[emptySlot] = pl_Info[PK()
                                                                         ]['forgeInv'][i][mouseoverSlot]
                            pl_Info[PK()]['forgeInv'][i][mouseoverSlot] = None

                        else:
                            (players[PK()].mouseInventory,
                             pl_Info[PK()]['forgeInv'][i][mouseoverSlot]) = (pl_Info[PK()]['forgeInv'][i][mouseoverSlot],
                                                                             players[PK()].mouseInventory)

                    else:
                        if players[PK()].gold >= FORGE_OPERATION_COST:
                            for i in range(FORGE_INVENTORY_NUMBER):
                                if (mouseover(forgeInvRect['Start Rect'][i]) and
                                    not pl_Info[PK()]['forgeInv']['Started'][i] and
                                    pl_Info[PK()]['forgeInv']['Input'][i] is not None and
                                        pl_Info[PK()]['forgeInv']['Output'][i] is None):

                                    pl_Info[PK()]['forgeInv']['Started'][i] = True
                                    players[PK()].gold -= FORGE_OPERATION_COST

                elif event.type == pygame.MOUSEMOTION:
                    if clickRectList(forgeInvRect['Input']):
                        currentMenu = 'Forge Inventory Input'

                    elif clickRectList(forgeInvRect['Output']):
                        currentMenu = 'Forge Inventory Output'

                elif pressEscape(event):
                    gamemode = 'Play'
                    fireplaceSound.fadeout(3000)

            windowSurface.fill(BLACK)
            windowSurface.blit(forgeFireImage, forgeFireRect)

            forgeInvSelection.draw()

            # Draw boxes for forge inventory
            for j in range(FORGE_INVENTORY_NUMBER):
                for i in ('Input', 'Output'):
                    # Check if mouse over any of the boxes
                    if mouseover(forgeInvRect[i][j]):
                        mouseoverSlot = j

                    (dirtyRects,
                     itemTooltip) = displayBigItemSlot(itemTooltip, pl_Info[PK()]['forgeInv'][i][j],
                                                       forgeInvRect[i][j])

                if pl_Info[PK()]['forgeInv']['Started'][j]:
                    textRect = forgeStartText['Orange']

                elif ((pl_Info[PK()]['forgeInv']['Input'][j] is not None and
                       pl_Info[PK()]['forgeInv']['Input'][j].id not in SMELTABLE_ITEMS) or
                      pl_Info[PK()]['forgeInv']['Output'][j] is not None):
                    textRect = forgeStartText['Red']

                elif (pl_Info[PK()]['forgeInv']['Input'][j] is not None and
                      pl_Info[PK()]['forgeInv']['Input'][j].id in SMELTABLE_ITEMS):
                    textRect = forgeStartText['Green']

                elif (pl_Info[PK()]['forgeInv']['Input'][j] is None and
                      pl_Info[PK()]['forgeInv']['Output'][j] is None):
                    textRect = forgeStartText['White']

                else:
                    assert False

                windowSurface.blit(textRect.surface, forgeInvRect['Start Rect'][j])

            # Display progress of smelting
            for progress, outerRect, innerRect in zip(pl_Info[PK()]['forgeInv']['Progress'],
                                                      forgeInvRect['Progress']['Outer'],
                                                      forgeInvRect['Progress']['Inner']):
                pygame.draw.rect(windowSurface, GREY, outerRect)

                filledInnerRect = innerRect.copy()
                filledInnerRect.height = innerRect.height * progress
                filledInnerRect.bottom = innerRect.bottom

                pygame.draw.rect(windowSurface, DARK_GREY, innerRect)
                pygame.draw.rect(windowSurface, ORANGE, filledInnerRect)

            for i in forgeText:
                forgeText[i].draw()

        elif gamemode == 'Blacksmith':
            for event in pygameEvents:
                if leftClick(event):
                    if mouseover(blacksmithText['Blacksmith'].rect):
                        (gamemode, loadScreenOnce,
                         players[PK()]) = leaveBlacksmith(players[PK()])

                    elif selectBlueprint.visible:
                        for item in selectBlueprint.text:
                            if mouseover(selectBlueprint.selectRect[item]):
                                selectedBlueprint = item
                                # Put items back in inventory before changing blueprint
                                players[PK()], dirtyRects = emptyBlacksmithInventory(players[PK()])
                                (dirtyRects,
                                 requiredItemSlots) = updateBlacksmithInfo(True)
                                break

                    elif mouseover(blacksmithDesiredItem['Rect']):
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # Shift click to inventory
                            emptySlot = players[PK()].inventory.index(None)
                            players[PK()].inventory[emptySlot] = blacksmithDesiredItem['Inventory']
                            blacksmithDesiredItem['Inventory'] = None

                        elif players[PK()].mouseInventory is None:
                            players[PK()].mouseInventory = blacksmithDesiredItem['Inventory']
                            blacksmithDesiredItem['Inventory'] = None

                    elif (currentMenu == 'Blacksmith - Required Items' and
                          mouseoverSlot is not None):
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # Shift click to inventory
                            emptySlot = players[PK()].inventory.index(None)
                            players[PK()].inventory[emptySlot] = requiredItemSlots[mouseoverSlot]['Inventory']
                            requiredItemSlots[mouseoverSlot]['Inventory'] = None

                        elif (players[PK()].mouseInventory == requiredItemSlots[mouseoverSlot]['Desired Item'] or
                              players[PK()].mouseInventory is None):
                            (players[PK()].mouseInventory,
                             requiredItemSlots[mouseoverSlot]['Inventory']) = (requiredItemSlots[mouseoverSlot]['Inventory'],
                                                                               players[PK()].mouseInventory)

                            for slot in requiredItemSlots:
                                if slot['Desired Item'] != slot['Inventory']:
                                    break

                            else:  # All boxes have been filled with ingredients
                                for slot in requiredItemSlots:
                                    slot['Inventory'] = None

                                blacksmithDesiredItem['Inventory'] = selectedBlueprint
                                playSound(pickUpGoldSound)

                elif pressEscape(event):
                    (gamemode, loadScreenOnce,
                     players[PK()]) = leaveBlacksmith(players[PK()])

                elif event.type == pygame.MOUSEMOTION:
                    dirtyRects = selectBlueprint.checkMouseOver(dirtyRects)

                    if mouseover(blacksmithRequiredItemsSection.rect):
                        currentMenu = 'Blacksmith - Required Items'

            windowSurface.fill(BLACK)

            blacksmithInvestSection.draw()
            blacksmithUnlockInfoSection.draw()
            blacksmithRequiredItemsSection.draw()

            for i, slot in enumerate(requiredItemSlots):
                if mouseover(slot['Rect']):
                    mouseoverSlot = i

                if slot['Inventory'] is None:
                    displayedItem = slot['Desired Item']
                    alpha = 128

                else:
                    displayedItem = slot['Inventory']
                    alpha = 255

                (dirtyRects,
                 itemTooltip) = displayBigItemSlot(itemTooltip, displayedItem,
                                                   slot['Rect'], alpha)

            dirtyRects = selectBlueprint.draw(dirtyRects)

            # GUI for creating new items
            if blacksmithDesiredItem['Inventory'] is None:
                displayedItem = selectedBlueprint
                alpha = 64

            else:
                displayedItem = blacksmithDesiredItem['Inventory']
                alpha = 255

            dirtyRects, itemTooltip = displayBigItemSlot(itemTooltip, Item(displayedItem),
                                                         blacksmithDesiredItem['Rect'])

            # Update texts
            blacksmithText['Desired Item'].updateSurface(selectedBlueprint)

            itemCost = BLUEPRINT[selectedBlueprint]['Cost']
            blacksmithText['Operation Cost'].updateSurface(itemCost)

            for i in blacksmithText:
                blacksmithText[i].draw()

        elif gamemode == 'Dying':
            windowSurface.blit(deathScreen, (0, 0))

            # Display death at end to effect entire screen including menus
            deathDisplayCounter += 120 / FPS

            if deathDisplayCounter >= 255:
                deathDisplay = 'Fade Out'

                # Kill player
                (players[PK()], leaveCave,
                 consoleText) = playerDeath(players[PK()], goldLoss, consoleText)

                # TODO: Replace with variable to keep track of cause of death
                try:
                    entities.remove(removeEntity)

                except ValueError:
                    pass

                goldLoss = None
                removeEntity = None

                gamemode = 'Play'

        elif gamemode == 'Play':
            entireTimer.start()
            # Local draw
            timePhase = get_time_phase(timeTick)

            if players[PK()].location in OUTSIDE_LOCATIONS:
                mapData['levelDarkness'] = get_level_brightness(timeTick, timePhase)
            # End local draw

            # GUI logic
            if options['touchScreen'] and not displayChat:
                touchScreenButtons.check_buttons(holdMouseDown)

            chooseCave = False
            for sb in speechBubbles:
                # Set a boolean as to whether key movements should be checked
                if not chooseCave and sb['ID'] == 'Choose Cave':
                    chooseCave = True

                    if not selectCaveButtons['Aligned']:
                        for i, buttonRect in enumerate(selectCaveButtons['Rect']):
                            buttonRect.centerx = sb['Rect'].x + sb['Rect'].width * (i + 1) / 4
                            buttonRect.bottom = sb['Rect'].bottom

                        selectCaveButtons['Aligned'] = True

                # Find dirty rects
                for rect in sb['Dirty Rects']:
                    dirtyRects.append(rect.copy())

            # Now known that player is not choosing a cave
            if not chooseCave:
                selectCaveButtons['Aligned'] = False

            # Touchscreen
            if options['touchScreen'] and not displayChat:
                heldKey = touchScreenButtons.get_held(heldKey)

            for event in pygameEvents:
                if event.type == pygame.KEYDOWN:
                    if displayChat == 'Display All':
                        if event.key in ENTER_KEYS and len(chatText.field.value) > 0:
                            # Run command
                            if chatText.field.value.startswith('/'):
                                # In future, splitCommand needs to be able to
                                # support brackets for arguments with spaces
                                arguments, command = splitCommand(chatText.field.value)

                                # Display input
                                chatText.addInput()

                                if not isClient:
                                    if chatText.field.value.startswith('/tpto'):
                                        output, players[PK()] = tpto(arguments, players[PK()])

                                if command == 'help':
                                    output = ('--- Help Menu ---',
                                              '/tpto (player name) - Teleports you to the given player.',
                                              '/tp (player name 1) (player name 2) - Teleports player 1 to player 2.',
                                              '/help - Displays this help menu.',
                                              '/helpop - Displays help menu for commands only available for the server owner.')

                                elif command == 'helpop':
                                    output = ('--- Advanced Help Menu ---',
                                              '/playsound (sound) (client) - Plays a sound for the desired player.',
                                              '/playsound (sound) - Plays a sound for yourself.')

                                elif command == 'tp':
                                    if len(arguments) != 2:
                                        output = ('Invalid number of arguments. 2 were expected.',)

                                    elif (arguments[0] in players and
                                          arguments[1] in players):

                                        players[arguments[0]] = teleportToPlayer(players[arguments[0]],
                                                                                 players[arguments[1]])

                                        output = ('Teleported ' + arguments[0] +
                                                  ' to ' + arguments[1] + '.',)

                                    else:
                                        output = ('One of the players were not found.'
                                                  ' Did you spell the names correctly?',)

                                elif command in ('i', 'item'):
                                    (output, players[PK()],
                                     dirtyRects) = itemCommand.call(arguments, players[PK()])

                                elif command == 'playsound':
                                    if len(arguments) == 0:
                                        output = ('Invalid number of arguments. 1 - 2 were expected.',
                                                  'Possible arguments include "pickUpGold" and "pickUpItem".',
                                                  'e.g. /playsound pickUpGold')

                                    elif len(arguments) == 1:
                                        pass

                                    elif len(arguments) == 2:
                                        if serverOn:
                                            pass

                                        else:
                                            output = ('Sounds cannot be sent to another player'
                                                      ' if you are not running a server.',)

                                    else:
                                        output = (
                                            'Invalid number of arguments. 1 - 2 were expected.',)

                                elif command == 'god':
                                    if len(arguments) == 0:
                                        players[PK()].invincible = not players[PK()].invincible
                                        output = ('God Mode - ' +
                                                  onOffString[players[PK()].invincible],)

                                    elif len(arguments) == 1:
                                        if serverOn:
                                            pass  # Enable god mode for player

                                        else:
                                            output = (
                                                'You must be running a server to give/remove god mode.',)

                                else:
                                    output = ('Command not recognized. Type /help for more info.',)

                                # Show output
                                if not isClient and not serverOn:
                                    for text in output:
                                        chatText.addOutput(text)

                            elif not isClient:
                                # Display input if not a client connected to a server
                                # If connected to a server, then the server will provide the message
                                chatText.addOutput(options['playerName'] +
                                                   ': ' + chatText.field.value)

                            if isClient:
                                message = chatText.field.value

                            elif serverOn:
                                message = options['playerName'] + ': ' + chatText.field.value

                            if isClient:  # Send message to server
                                TCP_ClientBufferLock.acquire()
                                TCP_ClientBuffer.append({'Type': 'Chat',
                                                         'Text': message})
                                TCP_ClientBufferLock.release()

                            if serverOn and not chatText.field.value.startswith('/'):
                                chatText.broadcast(message)

                            # Reset field
                            chatText.field.setValue('')

                        else:
                            chatText.keydown()

                    else:
                        heldKey = get_key_held_down(event, controls, heldKey)

                        if chooseCave:
                            caveType = None
                            if event.key in (pygame.K_1, pygame.K_KP1):
                                caveType = '1'

                            elif event.key in (pygame.K_2, pygame.K_KP2):
                                caveType = '2'

                            elif event.key in (pygame.K_3, pygame.K_KP3):
                                caveType = '3'

                            if caveType is not None:
                                gameEvents.append('pickCave')

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        if displayChat == 'Display All':
                            displayChat = False

                        elif inGameMenu is not None:
                            inGameMenu = None

                        else:
                            (gamemode, loadScreenOnce, pauseBackground, inGame,
                             players[PK()], heldKey) = pauseGame(players[PK()])

                    elif event.key == controls['Open Chat']:
                        displayChat = 'Display All'

                    elif event.key == controls['Open Map'] and displayChat != 'Display All':
                        if inGameMenu is None:
                            inGameMenu = 'Map'

                    elif event.key == controls['Open Inventory'] and displayChat != 'Display All':
                        if inGameMenu is None:
                            inGameMenu = 'Inventory'

                    if not options['touchScreen']:
                        heldKey = get_key_held_up(event, controls, heldKey)

                elif leftClick(event) and not console:
                    if mouseover(playerInfoMenu.titleRect):  # click on Player Info tab
                        playerInfoMenu.toggleVisibility()

                    elif (mouseover(NPC_TradingMenu.titleRect) and
                          NPC_Trading['Visible']):  # Click NPC Trading tab
                        NPC_TradingMenu.toggleVisibility()

                    elif chooseCave:
                        for i, rect in enumerate(selectCaveButtons['Rect']):
                            if mouseover(rect):
                                caveType = str(i + 1)
                                gameEvents.append('caveType')
                                break

                    elif (options['touchScreen'] and
                          mouseover(touchScreenButtons.buttons['Rect']['Menu'])):
                        (gamemode, loadScreenOnce, pauseBackground,
                         inGame, players[PK()], heldKey) = pauseGame(players[PK()])

                    elif inGameMenu is not None:
                        for i in inGameMenuButtons:
                            if mouseover(inGameMenuButtons[i].backRect):
                                inGameMenu = i
                                break

                    elif (isinstance(players[PK()].getHeldItem(), Bow) and
                          not clickGUI()):
                        playSound(bowShotSound)

                        # Player has arrow
                        if getItemIndex('Arrow', players[PK()].inventory) is not None:
                            entities.append(Arrow(players[PK()].rect.centerx,
                                                  players[PK()].rect.centery,
                                                  mousePos[0], mousePos[1],
                                                  players[PK()].getHeldItem().bowType))
                            players[PK()] = removeInventory(players[PK()], 'Arrow')

                    else:
                        clickedBlockData = clickedBlock()

                        if (clickedBlockData['Type'] in TRANSPARENT_BLOCKS and
                            players[PK()].mouseInventory is not None and
                            # Disable dropping any item when clicking on a menu
                            # TODO: add support for NPC_Trading Menu
                                not clickGUI()):

                            if isClient:
                                TCP_ClientBufferLock.acquire()
                                TCP_ClientBuffer.append({'Type': 'Drop Item',
                                                         'Item': players[PK()].mouseInventory,
                                                         'Position': mousePos})
                                TCP_ClientBufferLock.release()

                                players[PK()].mouseInventory = None

                            else:
                                (entities,
                                 players[PK()].mouseInventory) = dropItem(players[PK()].mouseInventory,
                                                                          mousePos)

                        elif clickedBlockData['Type'] in minableBlocks:
                            x, y = clickedBlockData['x'], clickedBlockData['y']
                            blockGrid[x][y]['Data'].attemptMining(players[PK()])

                    for entity in entities:
                        # Provoke dragon by clicking on it
                        if entity.type in HOSTILE_MOBS and mouseover(entity.rect):
                            if not entity.aggressive:
                                entity.aggressive = True

                            if players[PK()].fightingMob and not options['autoCombat']:
                                '''Damage dragon if player clicks on dragon
                                Multiplication helps player deal more damage
                                since clicking is slower than automatic combat

                                Players click about 5.5 times a second which is found
                                using FPS / 5.5 times slower than the automatic combat
                                '''

                                # Generate attack data if it hasn't been created yet
                                if entity.playerAttack is None and entity.mobAttack is None:
                                    entity.battleCalculation(players[PK()])

                                # Random chance of successful attack
                                if random.randint(0, 2) == 2:
                                    entity.health -= entity.playerAttack * FPS / 5
                                    textParticles.append(AttackText(entity.playerAttack,
                                                                    mousePos))

                                else:
                                    textParticles.append(AttackText(0, mousePos))

                        elif entity.type == 'Explorer' and entity.stopped:
                            (NPC_Trading, players[PK()],
                             dirtyRects) = entity.clickMenu(NPC_Trading, players[PK()], dirtyRects)

                            NPC_Trading = entity.clickTrade(NPC_Trading, players[PK()])

                        # If player clicked on villager to start a conversation
                        # Check if clicking on villager and close to player
                        elif (abs(players[PK()].rect.centerx - entity.rect.centerx) < 100
                              and mouseover(entity.rect)):

                            if entity.type == 'Villager':
                                entity.talk(players[PK()])

                            elif entity.type == 'Explorer':
                                dirtyRects.append(entity.talk(consoleText))

                            break

                    for sb in speechBubbles:
                        if mouseover(sb['Rect']):
                            if sb['Function'] == 'Click to Close':
                                speechBubbles.remove(sb)

                            if sb['ID'] == 'Pay Guard' and players[PK()].gold >= 5:
                                players[PK()].gold -= 5
                                players[PK()].canPassGuardKeeper = True

                            elif (sb['ID'] == 'Pay Cave Guard' and
                                  not clickRectList((goldGiven.leftArrowRect,
                                                     goldGiven.rightArrowRect))):
                                # Remove that now it is known that player is not
                                # clicking on arrows
                                speechBubbles.remove(sb)

                                for guard in entities:
                                    if guard.type != 'Cave Guard':
                                        continue

                                    if players[PK()].gold >= goldGiven.quantity:
                                        players[PK()].gold -= goldGiven.quantity
                                        players[PK()].canPassCaveGuard = True
                                        players[PK()].payingCaveGuard = False

                                        undergroundCity['Taxes'] += goldGiven.quantity

                                        speechBubbles.append(createSpeech(players[PK()], guard,
                                                                          'Talk about goldGiven'))

                                    else:
                                        speechBubbles.append(createSpeech(players[PK()], guard,
                                                                          'Too Much Gold'))

                    clickedBuilding = None
                    townBuildings = None

                    if players[PK()].location in TOWNS:
                        townBuildings = TOWNS[players[PK()].location].townBuildings

                    if townBuildings is not None:
                        for i in townBuildings.translucentText:
                            if mouseover(townBuildings.translucentText[i].backTextRect):
                                clickedBuilding = i
                                break  # If the player clicked on a building, no need to check others

                    # Enter clicked building
                    if clickedBuilding in ('Bank', 'Market', 'Stock Market',
                                           'Warehouse', 'Forge', 'Blacksmith'):
                        gamemode = clickedBuilding

                    if clickedBuilding == 'Library':
                        if len(pl_Info[PK()]['caveAdventures']) > 0:
                            (gamemode, adventureSelection, libraryCaveInfoMenu,
                             compartmentSelection, dirtyRects) = loadLibrary()

                        else:
                            consoleIntroText(players[PK()], pl_Info[PK()],
                                             'Library')

                    elif clickedBuilding == 'Forge':
                        playAmbientSound(fireplaceSound, -1)

                    elif clickedBuilding == 'Blacksmith':
                        selectBlueprint = SideMenu(pl_Info[PK()]['availableBlueprints'], 220)
                        requiredItemSlots = updateBlacksmithInfo(False)
                    elif clickedBuilding == 'Locked House':
                        pass

                    # TODO: Enable locked house
                    if (clickedBuilding is not None and clickedBuilding != 'Locked House' and
                        # Don't run if player couldn't enter closed library
                            not (clickedBuilding == 'Library' and len(pl_Info[PK()]['caveAdventures']) == 0)):
                        # Gamemode needs to be set for clickBuilding method to work
                        (loadScreenOnce, players[PK()],
                         heldKey) = townBuildings.clickBuilding(players[PK()],
                                                                pl_Info[PK()])

                elif event.type == AUTOSAVE_TIMER:
                    '''
                    Refresh entire screen so that weather can be seen
                    on optimized mode
                    Also provides infrequent updates for sunrises and sunsets
                    to change the sky's colour
                    '''
                    if (weather != 'Sun' or
                        (timePhase not in ('Sunrise', 'Sunset') and
                         players[PK()].location in OUTSIDE_LOCATIONS)):
                        loadFrameOnce = True

            # Manage input from touchscreen or key press
            players[PK()].jumping = 'Up' in heldKey

            if 'Left' in heldKey:
                players[PK()].horizontalControls = 'Left'

            if 'Right' in heldKey:
                players[PK()].horizontalControls = 'Right'

            if not 'Left' in heldKey and not 'Right' in heldKey:
                players[PK()].horizontalControls = None

            # Refresh screen
            if players[PK()].location in OUTSIDE_LOCATIONS:
                dirtyRects += sky.draw(timeTick, timePhase, mapData["groundY"],
                                       windowSurface)

                if playerNearTown(players[PK()], VOLCANIC_TOWN):
                    weatherManager.draw(windowSurface, "Ash")

                else:
                    weatherManager.draw(windowSurface, weather)

            elif players[PK()].location in ('Cave', UNDERGROUND_CITY,
                                            UNDERGROUND_CITY_EXIT) + DUNGEONS:
                windowSurface.blit(caveBackground, (0, 0))

            # Display clouds
            for entity in entities:
                if entity.type == 'Cloud':
                    entity.draw()

            # Display buildings
            if players[PK()].location in TOWNS:
                TOWNS[players[PK()].location].draw()

            elif players[PK()].location == GUARD_POST:
                guardBuilding.draw()

            elif players[PK()].location == ABANDONED_TOWN_LEFT:
                for label in abandonedTownBuildingLabels:
                    # Building labels
                    abandonedTownBuildingLabels[label].draw()

                for building in (abandonedBankBuilding, abandonedMarketBuilding):
                    for floor in building:
                        building[floor].draw()

            # Display regular blocks
            for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
                for y in range(INTERNAL_HEIGHT // BLOCK_SIZE):
                    coords = (x * BLOCK_SIZE, y * BLOCK_SIZE)

                    if blockGrid[x][y]['Type'] == 'Air':
                        continue

                    elif blockGrid[x][y]['Type'] in ('Torch', 'Campfire'):
                        blockGrid[x][y]['Data'].draw(lighting)

                    elif blockGrid[x][y]['Type'] in (oreList + ('Chest',)):
                        blockGrid[x][y]['Data'].draw()

                    else:
                        windowSurface.blit(typeToSurface[blockGrid[x][y]['Type']],
                                           coords)

                    if blockGrid[x][y]['Type'] == 'Lava':
                        lighting.light(coords[0] + BLOCK_SIZE // 2,
                                       coords[1] + BLOCK_SIZE // 2,
                                       7, 0.8, ORANGE)

            for tunnel in mapData['caveTunnels']:
                windowSurface.blit(tunnelImage, tunnel['Rect'])

            # Display speech bubbles
            for sb in speechBubbles:
                # Draw the rect that the text is placed upon
                pygame.draw.rect(windowSurface, GREY, sb['Rect'])
                # The triangle which connects the speech bubble to entity
                pygame.gfxdraw.filled_trigon(windowSurface, *sb['Triangle'],
                                             GREY)
                drawWrappedText(windowSurface, sb['Text'], BLACK,
                                sb['Rect'], submenuFont, GREY)

            if players[PK()].payingCaveGuard:
                goldGiven.draw()

            if players[PK()].payingCaveGuard and holdMouseDown:
                if (mouseover(goldGiven.leftArrowRect)
                        and goldGiven.quantity > 5):
                    goldGiven.quantity -= 1
                    goldGiven.update()

                elif mouseover(goldGiven.rightArrowRect):
                    goldGiven.quantity += 1
                    goldGiven.update()

            # This runs if player is moving, this also makes sure that the player
            # is inside the bounds of the game when getBlockInfo is used
            # (this comment was written before getBlockInfo supported entities outside of bounds)
            if players[PK()].horizontalControls is not None or leaveCave is not None:
                # Blocked at guard gate
                if players[PK()].location == GUARD_POST:
                    for guard in entities:
                        if guard.type != 'Guard':  # Only guard interactions are used
                            continue

                        # Player collides with guard and not allowed to pass
                        if (players[PK()].rect.colliderect(guard.rect) and not
                            (players[PK()].canPassGuardSuperior and guard.ID == 'Superior' or
                             players[PK()].canPassGuardKeeper and guard.ID == 'Keeper')):

                            if (players[PK()].direction == 'Right' and
                                    players[PK()].rect.right > guard.rect.left):
                                players[PK()].rect.right = guard.rect.left

                            elif (players[PK()].direction == 'Left' and
                                  players[PK()].rect.left < guard.rect.right):
                                players[PK()].rect.left = guard.rect.right

                            # First message on contact not displayed
                            if not guard.showFirstMessage:
                                if guard.ID == 'Superior':
                                    speechBubbles.append(guard.speechBubbles['First'])

                                elif guard.ID == 'Keeper':
                                    speechBubbles.append(guard.speechBubbles['First'])

                                guard.showFirstMessage = True

                        # Check if player went 100 pixels past guard
                        if ((players[PK()].direction == 'Right' and
                             players[PK()].rect.left - guard.rect.right > 100) or
                            (players[PK()].direction == 'Left' and
                             guard.rect.left - players[PK()].rect.right > 100)):

                            if guard.ID == 'Superior' and not guard.showThirdMessage:
                                print('Superior Show opinion')
                                # Remove old message
                                for sb in speechBubbles:
                                    if sb['ID'] == 'Guard Cave Opinion':
                                        speechBubbles.remove(sb)
                                        break

                                guard.showThirdMessage = True
                                guard.speechBubbles['Third'] = createSpeech(
                                    players[PK()], guard)  # Cave opinion
                                speechBubbles.append(guard.speechBubbles['Third'])

                            elif guard.ID == 'Keeper' and not guard.showSecondMessage:
                                print('Keeper Show opinion')
                                guard.showSecondMessage = True
                                guard.speechBubbles['Second'] = createSpeech(players[PK()], guard)
                                speechBubbles.append(guard.speechBubbles['Second'])

                elif players[PK()].location == UNDERGROUND_CITY_EXIT:
                    for guard in entities:
                        if guard.type != 'Cave Guard':  # Only guard interactions are used
                            continue

                        # Making giving gold to guard another menu
                        if (players[PK()].rect.colliderect(guard.rect) and
                                not players[PK()].canPassCaveGuard):

                            players[PK()].rect.right = guard.rect.left

                            if not guard.showInitialMessage:
                                speechBubbles.append(createSpeech(players[PK()], guard, 'Initial'))
                                guard.showInitialMessage = True
                                players[PK()].payingCaveGuard = True

                                goldGiven.update()

                        elif (players[PK()].rect.centerx > INTERNAL_WIDTH * 3 // 5
                              and not guard.showLastMessage):

                            guard.showLastMessage = True
                            for sb in speechBubbles:
                                if sb['ID'] == 'Gold Given Opinion':
                                    speechBubbles.remove(sb)

                            speechBubbles.append(createSpeech(players[PK()], guard,
                                                              'Leaving Message'))

                # No longer checking guards

                # Right side
                if players[PK()].rect.centerx > INTERNAL_WIDTH or leaveCave == 'Right':
                    if (players[PK()].location == QUIET_TOWN  # Prevent from going right
                        or (players[PK()].location == 'Cave'
                            and players[PK()].direction == 'Left'
                            and leaveCave is None)):

                        players[PK()].rect.centerx = INTERNAL_WIDTH - 1

                    elif players[PK()].location == 'Cave':
                        gameEvents.append('incrementCave')

                    elif (players[PK()].location in TOWNS or
                          players[PK()].location == ABANDONED_TOWN_RIGHT):
                        players[PK()].direction = 'Right'
                        gameEvents.append('Load Guard Post')

                    elif players[PK()].location == GUARD_POST:
                        if players[PK()].direction == 'Right':
                            gameEvents.append('Enter New Cave')

                        elif players[PK()].direction == 'Left':
                            gameEvents.append('Load Previous Town')

                    elif players[PK()].location == UNDERGROUND_CITY:
                        gameEvents.append('loadUndergroundCityExit')

                    elif players[PK()].location == SMALL_TOWN_HILLS:
                        (players[PK()], ambientSounds,
                         blockGrid, mapData, backgroundBlocks,
                         entities, consoleText,
                         caveBackground) = loadTown(SMALL_TOWN, players[PK()],
                                                    pl_Info[PK()])

                    elif players[PK()].location == UNDERGROUND_CITY_EXIT:
                        gameEvents.append('leaveUndergroundCity')

                    elif players[PK()].location == ABANDONED_TOWN_LEFT:
                        gameEvents.append(ABANDONED_TOWN_CENTRE)

                    elif players[PK()].location == ABANDONED_TOWN_CENTRE:
                        gameEvents.append(ABANDONED_TOWN_RIGHT)

                elif players[PK()].rect.centerx < 0 or leaveCave == 'Left':  # Left side
                    if (players[PK()].location == SMALL_TOWN_HILLS or  # At left-most map
                        (players[PK()].location == 'Cave' and
                         players[PK()].direction == 'Right'
                         and leaveCave is None)):

                        players[PK()].rect.centerx = 0

                    elif players[PK()].location == 'Cave':
                        gameEvents.append('incrementCave')

                    elif players[PK()].location == GUARD_POST:
                        if players[PK()].direction == 'Left':
                            gameEvents.append('Enter New Cave')

                        elif players[PK()].direction == 'Right':
                            gameEvents.append('Load Previous Town')

                    elif players[PK()].location in (SECOND_TOWN, INDUSTRIAL_TOWN,
                                                    ABANDONED_TOWN_LEFT, OUTPOST_TOWN,
                                                    CAPITAL_CITY, MINING_TOWN, VOLCANIC_TOWN,
                                                    QUIET_TOWN, BEACH_TOWN):
                        players[PK()].direction = 'Left'
                        gameEvents.append('Load Guard Post')

                    elif players[PK()].location == SMALL_TOWN:
                        (players[PK()], ambientSounds,
                         blockGrid, backgroundBlocks, entities,
                         mapData) = loadSmallTownHills(players[PK()])

                    elif players[PK()].location == ABANDONED_TOWN_CENTRE:
                        gameEvents.append(ABANDONED_TOWN_LEFT)

                    elif players[PK()].location == ABANDONED_TOWN_RIGHT:
                        gameEvents.append(ABANDONED_TOWN_CENTRE)

                    elif players[PK()].location == UNDERGROUND_CITY:
                        # Maybe block this off in the future with stone blocks
                        # and have an upgrade remove them
                        players[PK()].rect.centerx = 0

                    elif players[PK()].location == UNDERGROUND_CITY_EXIT:
                        (players[PK()], ambientSounds, blockGrid,
                         mapData, backgroundBlocks, entities,
                         undergroundCity['Old Cave Data']) = loadUndergroundCity(players[PK()],
                                                                                 pl_Info[PK()])
                        loadScreenOnce = False

                # Check if player moves off screen to another level,
                # the previous location is checked since current location changed
                # Make this work for any level change in the future
                if (players[PK()].rect.centerx > INTERNAL_WIDTH and
                    players[PK()].previousLocation in (GUARD_POST, SMALL_TOWN_HILLS,
                                                       'Cave',
                                                       UNDERGROUND_CITY,
                                                       UNDERGROUND_CITY_EXIT
                                                       ) + TOWN_STRINGS + ABANDONED_TOWN and
                    players[PK()].previousLocation != QUIET_TOWN

                    or players[PK()].rect.centerx < 0 and
                    players[PK()].previousLocation in ('Cave', GUARD_POST,
                                                       UNDERGROUND_CITY_EXIT
                                                       ) + TOWN_STRINGS + ABANDONED_TOWN and
                    players[PK()].previousLocation != SMALL_TOWN_HILLS

                        or leaveCave is not None):

                    (speechBubbles, NPC_Trading['Visible'],
                     loadScreenOnce, players[PK()],
                     changingLocation) = enterNewLocation(players[PK()])

                    # TODO: merge into the increment cave function with world generation
                    if players[PK()].location == 'Cave':
                        saveGame(librarySave=True)

                        # Kludge, replace with appending console text of cave environment
                        pl_Info[PK()]['caveAdventures'][-1]['Compartment'].append([])

                    # Leaving underground city by moving right
                    if players[PK()].previousLocation == UNDERGROUND_CITY_EXIT:
                        if players[PK()].rect.centerx > INTERNAL_WIDTH:
                            for tunnel in mapData['caveTunnels']:
                                if tunnel['Type'] == UNDERGROUND_CITY:
                                    players[PK()].rect.centerx = tunnel['Rect'].centerx

                        elif players[PK()].rect.centerx < 0:
                            players[PK()].rect.right = INTERNAL_WIDTH

                        players[PK()].payingCaveGuard = False

                    else:  # Regular movement off screen
                        if players[PK()].rect.centerx > INTERNAL_WIDTH:  # Move right
                            players[PK()].rect.left = 0
                        elif players[PK()].rect.centerx < 0:
                            players[PK()].rect.right = INTERNAL_WIDTH

                if leaveCave in ('Left', 'Right'):
                    leaveCave = None  # Variable no longer needed after it's used to enter if statements

                    # Create someone to give player a little gold
                    if players[PK()].gold + pl_Info[PK()]['bankBalance'] < 5:
                        entity = Villager()
                        entity.rect.right = players[PK()].rect.left
                        entity.stay = True
                        speechBubbles.append(createSpeech(players[PK()], entity,
                                                          type='Altruist'))
                        entities = dropGold(5, entity.rect.center)

                        entities.append(entity)

            if players[PK()].rect.top > INTERNAL_HEIGHT or players[PK()].rect.top < -5:
                verticalMapChange = True

            else:
                verticalMapChange = False

            if players[PK()].rect.top > INTERNAL_HEIGHT:
                players[PK()].rect.y -= INTERNAL_HEIGHT - BLOCK_SIZE
                if players[PK()].location == 'Cave':
                    # Create cave with hole on top
                    gameEvents.append('fallIntoCave')

                elif players[PK()].location == ABANDONED_TOWN_RIGHT:
                    players[PK()].location = DUNGEON_TOP
                    gameEvents.append(DUNGEON_TOP)

                elif players[PK()].location == DUNGEON_TOP:
                    players[PK()].location = DUNGEON_BOTTOM
                    (ambientSounds, blockGrid, backgroundBlocks, entities,
                     mapData) = generateDungeonBottom()

                else:
                    assert False

            elif players[PK()].rect.top < -5:
                if players[PK()].location in (DUNGEON_TOP, DUNGEON_BOTTOM):
                    players[PK()].rect.y += INTERNAL_HEIGHT

                if players[PK()].location == DUNGEON_TOP:
                    gameEvents.append(ABANDONED_TOWN_RIGHT)

                elif players[PK()].location == DUNGEON_BOTTOM:
                    players[PK()].location = DUNGEON_TOP
                    gameEvents.append(DUNGEON_TOP)

            if verticalMapChange:
                verticalMapChange = not verticalMapChange
                playerYCoord = players[PK()].rect.y
                (speechBubbles, NPC_Trading['Visible'],
                 loadScreenOnce, players[PK()],
                 changingLocation) = enterNewLocation(players[PK()])
                # By default, enterNewLocation sets player's rect.bottom to groundY
                players[PK()].rect.y = playerYCoord

            if players[PK()].inLavaCheck():
                # Lose 10 HP per second
                (players[PK()], textParticles
                 ) = reducePlayerHealth(LAVA_DAMAGE, textParticles)

            if isinstance(players[PK()].getHeldItem(), Bow):
                # Update degrees
                relativeX = mousePos[0] - players[PK()].rect.centerx
                relativeY = mousePos[1] - players[PK()].rect.centery

                # Draw player's bow trajectory
                if getItemIndex('Arrow', players[PK()].inventory) is None:
                    colour = RED

                else:
                    colour = GREEN

                players[PK()].getHeldItem().drawTrajectory(players[PK()].rect.center, mousePos)

            for coords in players[PK()].getBlockInfo()['Coords']:
                x, y = coords

                if blockGrid[x][y]['Type'] == 'Chest':
                    blockGrid[x][y]['Data'].adjacentPlayer()

            # Cave environments
            if mapData['caveEnvironment'] == 22:  # Raining rocks
                if random.randint(0, mapData['caveEnvData']['Falling Rock Rate']) == 0:
                    x = random.randint(0, INTERNAL_WIDTH - smallStoneImage.get_width())
                    y = 8 * BLOCK_SIZE
                    entities.append(SmallFallingBlock(x, y))

            elif (mapData['caveEnvironment'] == 26 and mapData['caveEnvData']['Complete'] and
                  not mapData['caveEnvData']['Finished Fog']):  # Explosion happened but fog not finished

                if mapData['caveEnvData']['Fog Delay'] > 0:
                    mapData['caveEnvData']['Fog Delay'] -= 1 / 40

                if mapData['caveEnvData']['Fog Delay'] <= 0:
                    mapData['steamOpacity'] += (mapData['caveEnvData']
                                                ['Fog Opacity'] - mapData['steamOpacity']) / 10

                    if round(mapData['steamOpacity']) >= mapData['caveEnvData']['Fog Opacity']:
                        mapData['caveEnvData']['Finished Fog'] = True

            if not mapData['caveEnvData']['Complete']:
                if mapData['caveEnvironment'] in (7, 15, 16, 23, 26):
                    if mapData['caveEnvData']['Timer'] > 0:
                        mapData['caveEnvData']['Timer'] -= 1 / FPS

                if mapData['caveEnvironment'] in (7, 15, 16, 26):  # Shake cave
                    # Start earthquake sound 2 seconds before earthquake
                    if (mapData['caveEnvData']['Timer'] == 2 and
                            not mapData['caveEnvData']['Played Sound']):
                        playAmbientSound(earthquakeSound, 0)

                    # Event is only forced early in cave environment 15 (fissure in earth)
                    if (playerPastDistance(players[PK()], INTERNAL_WIDTH - 200)
                            and mapData['caveEnvironment'] == 15):
                        mapData['caveEnvData']['Timer'] = 0

                        if not mapData['caveEnvData']['Played Sound']:
                            playAmbientSound(earthquakeSound, 0)

                    if mapData['caveEnvData']['Timer'] <= 0:
                        mapData['caveEnvData']['Complete'] = True
                        shake.start(40)

                        if mapData['caveEnvironment'] in (7, 15):
                            initialLeftBounds = 10
                            leftBounds, rightBounds = getCentralBounds(initialLeftBounds)

                            entities, blockGrid = collapseArea(leftBounds,
                                                               rightBounds, 16,
                                                               INTERNAL_HEIGHT // BLOCK_SIZE - 1)

                        if mapData['caveEnvironment'] == 7:
                            chatText.addOutput(caveEnvironments(8))

                        # Make cave collapse
                        elif mapData['caveEnvironment'] == 15:
                            chatText.addOutput(caveEnvironments(23))

                            for x in range(leftBounds, rightBounds):
                                blockGrid[x][-1]['Type'] = 'Lava'

                        # Add new tunnel
                        elif mapData['caveEnvironment'] == 16:
                            chatText.addOutput(caveEnvironments(24))
                            mapData['caveTunnels'].append(
                                createTunnel(2, 29, blockGrid, 'Other Cave'))

                        elif mapData['caveEnvironment'] == 26:
                            chatText.addOutput(caveEnvironments(32))

                elif mapData['caveEnvironment'] == 21:  # Ceiling collapses with lava
                    if playerPastDistance(players[PK()], INTERNAL_WIDTH - 200):
                        mapData['caveEnvData']['Complete'] = True

                        topBounds = 2
                        bottomBounds = 8

                        middle = INTERNAL_WIDTH // BLOCK_SIZE // 2
                        offset = random.randint(1, 3)
                        if players[PK()].direction == 'Left':
                            rightBounds = INTERNAL_WIDTH // BLOCK_SIZE - offset
                            leftBounds = middle

                        elif players[PK()].direction == 'Right':
                            leftBounds = offset
                            rightBounds = middle

                        entities, blockGrid = collapseArea(leftBounds, rightBounds,
                                                           topBounds, bottomBounds)

                elif mapData['caveEnvironment'] == 23:  # Entrance disappears
                    if playerPastDistance(players[PK()], INTERNAL_WIDTH / 2):  # Halfway across screen
                        mapData['caveEnvData']['Timer'] = 0

                    if mapData['caveEnvData']['Timer'] <= 0:
                        mapData['caveEnvData']['Complete'] = True
                        chatText.addOutput(caveEnvironments(26))

                        if players[PK()].direction == 'Left':
                            x = 31

                        elif players[PK()].direction == 'Right':
                            x = 0

                        # Replace entrance with stone
                        for y in range(8, 16):
                            blockGrid[x][y]['Type'] = 'Stone'

            for particle in textParticles:
                dirtyRects.append(particle.draw())

            # Entity code
            for entity in entities:
                dirtyRects.append(entity.rect.copy())

                # Display entities
                if entity.type in ('Big Bat', 'Small Bat', 'Slime', 'Dragon',
                                   'Shadow Dragon', 'Villager', 'Explorer',
                                   'Shadow Explorer'):
                    entity.animate()

                elif entity.type == 'Item':
                    playersLock.acquire()
                    for i in players:
                        (players[i],
                         entities, dirtyRects) = entity.update(players[i],
                                                               entities, dirtyRects)

                    playersLock.release()

                elif entity.type in ('Falling Block', 'Arrow', 'Cloud'):
                    entity.update()

                elif entity.type == 'Small Falling Block':
                    (players[PK()], textParticles, dirtyRects,
                     goldLoss, removeEntity) = entity.update(removeEntity, players[PK()])

                if entity.type in ('Villager', 'Explorer', 'Guard', 'Arrow',
                                   'Dragon', 'Item', 'Cave Guard', 'Shadow Dragon',
                                   'Shadow Explorer', 'Falling Block', 'Small Falling Block',
                                   'Slime') + BATS:
                    entity.draw()

                # AI
                # serverName in players checks if client shares location with server
                if ((not isClient or
                     (isClient and (serverName not in players or
                                    players[PK()].location == GUARD_POST)))

                    and entity.type not in ('Item', 'Guard', 'Cloud',
                                            'Cave Guard', 'Falling Block',
                                            'Small Falling Block', 'Arrow')):
                    entity.updateRect()

                    if entity.type in HOSTILE_MOBS:
                        (players[PK()], goldLoss, removeEntity, combatRect, combatSurfaces,
                         loadFrameOnce,
                         dirtyRects) = entity.update(players[PK()], goldLoss, removeEntity,
                                                     combatRect, combatSurfaces,
                                                     loadFrameOnce)

                    elif entity.type == 'Explorer':
                        if entity.stopped:  # Draw menu when talking to explorer
                            entity.drawMenu()
                            if entity.menu in ('Trade', 'Request Item', 'Sell'):
                                itemTooltip = entity.drawInventory(itemTooltip)

                        else:
                            # Only make explorer walk is not stopped
                            entity.update()

                    else:
                        entity.update()

                if entity.type != 'Cloud' and not entity.rect.colliderect(SCREEN_RECT):
                    # If entity falls off screen, delete it.
                    # Clouds manage this on their own
                    entities.remove(entity)

            if players[PK()].health <= 0 and gamemode != 'Dying':  # Only runs once per death
                deathDisplay = 'Fade In'  # This triggers a function for player death
                # If set to 0, the level will appear to brighten up before fading
                deathDisplayCounter = mapData['levelDarkness']
                deathScreen = windowSurface.copy()

                # Prevents unintentional movement after dying
                players[PK()], heldKey = resetInput(players[PK()])

                gamemode = 'Dying'

            # TODO - separate physics and graphics
            playersLock.acquire()
            for i in players:
                if players[i].fightingMob:
                    for entity in entities:
                        if (entity.type in HOSTILE_MOBS and
                                entity.rect.colliderect(players[i].rect)):
                            break

                    else:
                        # Allow movement when no longer in contact with dragon
                        players[i].fightingMob = False

                players[i].physicsUpdate()

                # TODO make movement use proper physics, friction, forces, dx, etc
                players[i].move()
                players[i].animate()

                if sameLocation(players[PK()], players[i]):
                    if i != PK():
                        if i not in playerNames:  # Name above head
                            playerNames[i] = TextRect(submenuFont, i, WHITE)

                        playerNames[i].rect = drawPlayerLabel(players[i],
                                                              playerNames[i].rect)

                    # Displays animation of moving player
                    dirtyRects.append(players[i].draw())

                    if players[i].health != players[i].maxHealth:
                        dirtyRects.append(players[i].drawHealthBar())

                    if i != PK():
                        dirtyRects.append(playerNames[i].draw())

                if DEVELOPER_MODE:
                    lighting.light(*players[i].rect.center,
                                   players[i].getLightRadius(mapData['caveEnvironment']),
                                   0.5, BLUE)

                players[i].incrementPastCoords()
                if mapData['caveEnvironment'] == 14 and options['lighting'] != 'Off':
                    # Check if cave absorbs light
                    for j, coord in enumerate(players[i].pastCoords):
                        lighting.light(*players[i].pastCoords[j],
                                       round(8 * 0.9 ** j),
                                       0.5 - 0.025 * j)

            playersLock.release()

            # Level darkness darkens level but not menu
            if deathDisplay == 'Fade Out':
                deathDisplayCounter -= 120 / FPS

            if mapData['steamOpacity'] > 0:
                WHITE_SCREEN.set_alpha(mapData['steamOpacity'])
                windowSurface.blit(WHITE_SCREEN, (0, 0))

            entireTimer.stop()
            mainLightTimer.start()

            # Consider allowing colour lighting for all levelDarknesses
            # Consider using levelDarkness as a lightgrid minimum, and removing baseShade
            if options['lighting'] != 'Off' and mapData['levelDarkness'] > 0:
                lighting.draw(mapData['levelDarkness'], options['lighting'])

            else:  # No special lighting - uniform level of grey
                if mapData['levelDarkness'] > 0:
                    BLACK_SCREEN.set_alpha(mapData['levelDarkness'])
                    windowSurface.blit(BLACK_SCREEN, (0, 0))

            mainLightTimer.stop()
            entireTimer.start()

            if players[PK()].fightingMob and options['highlightCombat']:
                for i in combatSurfaces:
                    windowSurface.blit(combatSurfaces[i], combatRect[i])

            playerInfoMenu.draw()

            if playerInfoMenu.maximized:
                for i in playerInfo:
                    playerInfo[i].updateSurface()

                    windowSurface.blit(playerInfo[i].surface,
                                       (playerInfoMenu.mainRect.x + 10,
                                        playerInfoMenu.mainRect.y + 15 +
                                        PLAYER_INFO_ORDER.index(i) * 14))

            if NPC_Trading['Visible']:
                NPC_TradingMenu.draw()

                if NPC_TradingMenu.maximized:
                    # Display item offer
                    NPC_Trading['Item Offer Label'].draw()

                    dirtyRects, itemTooltip = displayItemSlot(itemTooltip,
                                                              NPC_Trading['Item Offer'],
                                                              NPC_Trading['Item Offer Rect'])
                    # Display counter offer
                    NPC_Trading['Counter Offer Label'].draw()

                    for item, rect in zip(NPC_Trading['Counter Offer'],
                                          NPC_Trading['Counter Offer Rect']):
                        dirtyRects, itemTooltip = displayItemSlot(itemTooltip,
                                                                  item, rect)

                    # Gold counter offer
                    if NPC_Trading['Gold Offer'] is not None:
                        image = 'Gold'

                    else:
                        image = None

                    # Display the quantity of gold after item slot is shown
                    if NPC_Trading['Gold Offer'] is not None:
                        # Display requested amount of gold
                        dirtyRects, itemTooltip = displayItemSlot(itemTooltip, image,
                                                                  NPC_Trading['Gold Offer Label'].rect)

                        NPC_Trading['Gold Offer Label'].draw()

            # Highlights any ore
            # Make this only work for blocks near player
            # If holding a pickaxe of any type
            if (players[PK()].mouseInventory is not None and
                    isinstance(players[PK()].getHeldItem(), Pickaxe)):
                for x in range(INTERNAL_WIDTH // BLOCK_SIZE):
                    for y in range(INTERNAL_HEIGHT // BLOCK_SIZE):
                        if (blockGrid[x][y]['Type'] in minableBlocks and
                            mouseover(pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE,
                                                  BLOCK_SIZE, BLOCK_SIZE))):

                            # Store this value and run the highlight function
                            # later so displaying blocks doesn't cover it
                            highlightedBlock = x, y
                            break

            if mapData['caveEnvironment'] == 20:  # Thin air
                # TODO: Add motion blur by blitting previous frames of entities when air is thin
                BLACK_SCREEN.set_alpha(200)
                windowSurface.blit(BLACK_SCREEN, (0, 0))

        # Outside of gamemode == 'Play'
        if gamemode in ('Play', 'Dying'):
            if deathDisplay in ('Fade In', 'Fade Out'):
                BLACK_SCREEN.set_alpha(deathDisplayCounter)
                windowSurface.blit(BLACK_SCREEN, (0, 0))

        if deathDisplay == 'Fade Out' and deathDisplayCounter <= 0:
            deathDisplay = None
            deathDisplayCounter = None
            deathScreen = None

        if gamemode in INVENTORY_MENU_GAMEMODES:
            inventoryMenu.draw()
            # Render the normal inventory
            if inventoryMenu.maximized:
                for i, inventorySlot in enumerate(pl_InventoryGUI.slots):
                    if i == players[PK()].selectedInvSlot:
                        (dirtyRects,
                         itemTooltip) = displayItemSlot(itemTooltip, players[PK()].inventory[i],
                                                        inventorySlot,
                                                        invSpaceImage=selectedInventorySpaceImage)
                    else:
                        (dirtyRects,
                         itemTooltip) = displayItemSlot(itemTooltip, players[PK()].inventory[i],
                                                        inventorySlot)

                    if mouseover(inventorySlot):  # Check if mouse over any of the boxes
                        mouseoverSlot = i

        if gamemode == 'Play':
            currentTime = time.time()

            if currentTime - chatText.getTimeLastMessage() >= 3 and displayChat == 'Preview':
                displayChat = False

            elif currentTime - chatText.getTimeLastMessage() < 3 and not displayChat:
                displayChat = 'Preview'

            # Display after menus
            if displayChat == 'Display All':
                BLACK_SCREEN.set_alpha(92)
                windowSurface.blit(BLACK_SCREEN, (0, 0))

                chatText.draw()

            elif displayChat == 'Preview':
                drawWrappedText(windowSurface, chatText.lines[-1]['Text'], WHITE,
                                pygame.Rect(0, 0, *INTERNAL_SIZE),
                                chatFont)

            if displayChat != 'Display All':
                # High priority to be displayed
                if options['touchScreen']:
                    touchScreenButtons.draw()

                if chooseCave:
                    for surface, rect in zip(selectCaveButtons['Surface'],
                                             selectCaveButtons['Rect']):
                        windowSurface.blit(surface, rect)

            if inGameMenu is not None:
                # Darken existing screen to create background
                BLACK_SCREEN.set_alpha(200)
                windowSurface.blit(BLACK_SCREEN, (0, 0))

                for i in inGameMenuButtons:
                    inGameMenuButtons[i].draw()

                if inGameMenu == 'Map':
                    map.draw(windowSurface)

        # Mouse has item held by it
        if gamemode in INVENTORY_MENU_GAMEMODES:
            if players[PK()].mouseInventory is not None:
                '''Display item at mouse coordinates
                Function needs a rect so a temporary rect is made.
                Width and height not needed'''
                rect = pygame.Rect(mousePos, (0, 0))
                dirtyRect = drawItem(players[PK()].mouseInventory, rect)

                dirtyRects.append(dirtyRect)

            itemTooltip.draw(mousePos)

        # Display highlighted block after all other things have been displayed
        if highlightedBlock is not None:
            dirtyRects.append(highlightBlock(highlightedBlock[0],
                                             highlightedBlock[1], GREY))
            # Reset for next frame
            highlightedBlock = None

        if debugMode:
            debugInfo['useNumpy'].updateValue(usingNumpy())
            for i in range(len(lighting.segments)):
                debugInfo[i].updateValue(lighting.segments[i].percentage())

            debugInfo['mainLoopLightTimer'].updateValue(mainLightTimer.percentage())
            debugInfo['lightRegionTimer'].updateValue(lightRegionTimer.percentage())

            for column, key in enumerate(DEBUG_ORDER):
                dirtyRects = debugInfo[key].draw(column)

            # Show highlighted block
            if debugInfo['xCoord'].value is not None:
                assert debugInfo['yCoord'].value is not None

                dirtyRects.append(highlightBlock(debugInfo['xCoord'].value,
                                                 debugInfo['yCoord'].value,
                                                 GREY))

    if 'incrementCave' in gameEvents or 'fallIntoCave' in gameEvents:
        (players[PK()], ambientSounds,
         blockGrid, mapData, backgroundBlocks, entities,
         consoleText, caveBackground, chatText,
         pl_Info[PK()], marketBaseValue, stocks
         ) = incrementCave(players[PK()], pl_Info[PK()], mapData)

        while 'incrementCave' in gameEvents:
            gameEvents.remove('incrementCave')

        while 'fallIntoCave' in gameEvents:
            gameEvents.remove('fallIntoCave')

    if 'loadUndergroundCityExit' in gameEvents:
        (players[PK()], ambientSounds, blockGrid,
         mapData, backgroundBlocks, entities,
         goldGiven) = loadUndergroundCityExit(players[PK()])

        gameEvents.remove('loadUndergroundCityExit')

    if 'leaveUndergroundCity' in gameEvents:
        (blockGrid, backgroundBlocks, ambientSounds,
         mapData, undergroundCity['Old Cave Data'],
         entities, player) = leaveUndergroundCity(players[PK()])

        gameEvents.remove('leaveUndergroundCity')

    if 'Load Guard Post' in gameEvents:
        (players[PK()], ambientSounds, blockGrid,
         mapData, backgroundBlocks, entities,
         consoleText) = loadGuardPost(players[PK()])

        if playerNearTown(players[PK()], VOLCANIC_TOWN):
            blockGrid = makeAshenEarth(blockGrid)

        gameEvents.remove('Load Guard Post')

    if 'pickCave' in gameEvents:
        for sb in speechBubbles:  # Remove bubble
            if sb['ID'] == 'Choose Cave':
                speechBubbles.remove(sb)
                break
        else:
            raise RuntimeError

        players[PK()].caveType = caveType
        players[PK()].canPassGuardSuperior = True

        for i in range(len(entities)):  # Set guard to let player through and change message
            if entities[i].type == 'Guard' and entities[i].ID == 'Superior':
                entities[i].speechBubbles['Second'] = createSpeech(players[PK()], entities[i])
                speechBubbles.append(entities[i].speechBubbles['Second'])

        gameEvents.remove('pickCave')

    if 'Enter New Cave' in gameEvents:
        (players[PK()], pl_Info[PK()],
         ambientSounds, blockGrid, mapData,
         backgroundBlocks, entities, caveBackground,
         caveSize, consoleText, chatText) = enterNewCave(players[PK()],
                                                         pl_Info[PK()])

        gameEvents.remove('Enter New Cave')

    if 'Load Previous Town' in gameEvents:
        (players[PK()], ambientSounds,
         blockGrid, mapData, backgroundBlocks,
         entities, consoleText,
         caveBackground) = loadTown(players[PK()].previousTown, players[PK()],
                                    pl_Info[PK()])

        gameEvents.remove('Load Previous Town')

    if ABANDONED_TOWN_LEFT in gameEvents:
        (players[PK()], ambientSounds, blockGrid,
         mapData, backgroundBlocks,
         entities, consoleText,
         caveBackground) = loadAbandonedTownLeft(players[PK()])

        gameEvents.remove(ABANDONED_TOWN_LEFT)

    if ABANDONED_TOWN_CENTRE in gameEvents:
        (players[PK()], newAmbientSounds, blockGrid,
         mapData, backgroundBlocks,
         entities, consoleText,
         caveBackground) = loadAbandonedTownCentre(players[PK()])

        gameEvents.remove(ABANDONED_TOWN_CENTRE)

    if ABANDONED_TOWN_RIGHT in gameEvents:
        (players[PK()], newAmbientSounds, blockGrid,
         mapData, backgroundBlocks, entities,
         consoleText, caveBackground) = loadAbandonedTownRight(players[PK()])

        gameEvents.remove(ABANDONED_TOWN_RIGHT)

    if DUNGEON_TOP in gameEvents:
        (ambientSounds, blockGrid, backgroundBlocks, entities,
         mapData) = generateDungeonTop()

        gameEvents.remove(DUNGEON_TOP)

    if gameEvents:  # Should be empty
        raise Exception(gameEvents)

    # Other TCP Networking
    # Look into only loading and sending maps when in cave
    if changingLocation:
        mapLoadTime = time.time()
        if serverOn:
            # Try checking map cache to see if there's a map to load
            serverMapCacheLock.acquire()

            for i in serverMapCache:
                if sameMapLocation(serverMapCache[i]):
                    blockGrid, mapData = loadCachedMap(serverMapCache[i])
                    entitiesLock.acquire()
                    otherPlayerEntitiesLock.acquire()
                    entities = otherPlayerEntities[i]
                    otherPlayerEntitiesLock.release()
                    entitiesLock.release()

            serverMapCacheLock.release()

        if isClient and not disconnectClient:
            # Try checking map cache to see if there's a map to load
            clientMapCacheLock.acquire()

            for map in clientMapCache:
                if sameMapLocation(map):
                    blockGrid, mapData = loadCachedMap(map)

            clientMapCacheLock.release()

    if isClient and changingLocation:
        # Send map cache
        TCP_ClientBufferLock.acquire()
        print('Send cache!')
        TCP_ClientBuffer.append({'Type': 'Map Cache',
                                 'Map': sendCachedMap()})
        TCP_ClientBufferLock.release()

    if serverOn:
        TCP_ServerBufferLock.acquire()
        for otherPlayerName in TCP_ServerBuffer:
            if otherPlayerName == LPK:
                continue

            # Temporarily make the server send all map caches
            # In future, limit the map cache to maps adjacent to client
            # Send map cache
            serverMapCacheLock.acquire()

            # Check if player is in process of disconnecting
            if otherPlayerName in TCP_ServerBuffer:
                # Kludge - client buffer will have all the same data as server buffer

                mapCacheData = list(serverMapCache.values())
                mapCacheData.append(sendCachedMap())

                TCP_ServerBuffer[otherPlayerName].append({'Type': 'Map Cache',
                                                          'Map': tuple(mapCacheData)})

            serverMapCacheLock.release()

        TCP_ServerBufferLock.release()

    # End TCP Networking

    # UDP Networking
    if isClient and not disconnectClient:
        # Fails if the client has begun to connect but still hasn't received "player" variable
        try:
            # TODO - have client broadcast if android client
            pythonTwoClient = True
            UDP_STREAM.sendto(serialize({'Player': players[PK()], 'Entities': entities}, pythonTwoClient),
                              (serverIP, MAIN_PORT))
        except NameError:
            pass

    elif serverOn:
        # Broadcast server
        queuedData = (LAN_IP,)
        SEND_BROADCAST_STREAM.sendto(serialize(queuedData, True),
                                     ('255.255.255.255', BROADCAST_PORT))

        # Manage individual clients
        playersLock.acquire()
        for otherPlayerName in players:
            if otherPlayerName == LPK:
                continue

            queuedData = {}
            # Send information on players in addition to self
            queuedData['Players'] = createOtherPlayerFile(otherPlayerName)
            #queuedData['Inventory'] = players[otherPlayerName]['Inventory']

            # Only run once player is inside list
            if sameLocation(players[PK()], players[otherPlayerName]):
                queuedData['Entities'] = copy.deepcopy(entities)

                for cloud in queuedData['Entities']:
                    if cloud.type == 'Cloud':
                        queuedData['Entities'].remove(cloud)

            # Send UDP data to client
            pythonTwoClient = True
            UDP_STREAM.sendto(serialize(queuedData, pythonTwoClient), playerToIP[otherPlayerName])

        playersLock.release()

    if shake.is_active():
        shake.animate(windowSurface)
        loadFrameOnce = False  # Reload entire screen

    if flash.is_active():
        flash.animate(windowSurface)
        loadFrameOnce = False  # Reload entire screen

    if android:
        displaySurface.fill(BLACK)
        displaySurface.blit(windowSurface, offsetX, offsetY)

    # This code must run at end for every gamemode
    if options['dirtyRect'] and deathDisplay is None and not console:
        if loadFrameOnce:
            if optimize_dirty_rects is not None:
                optimize = optimize_dirty_rects.optimize_dirty_rects
                dirtyRects = optimize(copy.deepcopy(dirtyRects))
            pygame.display.update(dirtyRects + oldDirtyRects)

        else:
            pygame.display.update()
            loadFrameOnce = True

    else:
        pygame.display.update()

    oldDirtyRects = []

    for rect in dirtyRects:
        # The rect must be copied
        if rect is not None:
            oldDirtyRects.append(rect.copy())

    dirtyRects = []  # Refresh every frame
    if gamemode == 'Play':
        try:
            entireTimer.stop()
        except AttributeError:
            pass

    mainClock.tick(FPS)
