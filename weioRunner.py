#!/usr/bin/python -u
from tornado import web, ioloop, options, websocket

import sys,os,logging, platform, json, signal, datetime

import multiprocessing
import threading

import functools
import subprocess

from weioLib import weioUserApi
from weioLib import weioIO

# JS to PYTHON handler
from handlers.weioJSPYHandler import WeioHandler

# IMPORT BASIC CONFIGURATION FILE ALL PATHS ARE DEFINED INSIDE
from weioLib import weio_config

# IMPORT WEIO FILE SUPPORT
from weioLib import weioFiles

from sockjs.tornado import SockJSRouter, SockJSConnection

# Import globals for user Tornado
from weioLib import weioRunnerGlobals

# Global list of user processes
userProcessList = []

from weioLib import weioGpio
from weioLib import weioIO

import time

###
# HTTP SERVER HANDLER
###
# This is user project index.html
class WeioIndexHandler(web.RequestHandler):
    def get(self):
        firstTimeSwitch = confFile['first_time_run']
        #print firstTimeSwitch

        if (firstTimeSwitch=="YES") :
           path = "www/firstTime.html"
        else :
           if (weioFiles.checkIfFileExists(confFile['user_projects_path'] + confFile['last_opened_project'] + "index.html")):
              path = "www/userIndex.html"
           else :
              path = "www/error404.html"
        path = "www/userIndex.html"
        self.render(path, error="")


###
# WeIO User Even Handler
###
class UserControl():
    def __init__(self):
        self.errLine = 0
        self.errObject = []
        self.errReason = ""
        self.lastCalledProjectPath = None

        # Variable to store SockJSConnection calss instance
        # in order to call it's send() method from MainProgram thread
        CONSOLE = None

        self.connection = None

        # Ask this variable is player is playing at this moment
        self.playing = False

        # User Project main module (main.py)
        self.userMain = None

        # List of user processes
        self.userProcessList = []

    def setConnectionObject(self, connection):
        # captures only the last connection
        self.connection = connection

    def send(self, data):
        # if no connection object (editor is not opened) than data for editor is lost
        if not(self.connection is None):
            self.connection.send(data)

    def start(self, rq={'request':'play'}):
        print "STARTING USER PROCESSES"

        if (len(self.userProcessList)!=0):
            self.stop()

        if (weioIO.gpio != None):
            if (weioRunnerGlobals.WEIO_SERIAL_LINKED == False):
                try :
                    weioIO.gpio = weioGpio.WeioGpio()

                    # Initialize globals for the user Tornado
                    weioRunnerGlobals.DECLARED_PINS = weioIO.gpio.declaredPins
                except :
                    print "LPC coprocessor is not present"
                    weioIO.gpio = None

            # Launching threads
            for key in weioUserApi.attach.procs :
                print key
                p = multiprocessing.Process(target=weioUserApi.attach.procs[key].procFnc)
                p.daemon = True
                # Add it to the global list of user processes
                self.userProcessList.append(p)
                # Start it
                p.start()
                print "STARTING PROCESS PID", p.pid

    def stop(self):
        print "STOPPING USER PROCESSES"

        for p in self.userProcessList:
            print "KILLING PROCESS PID", p.pid
            p.terminate()
            p.join(0.5)
            try :
                # If job is not properly done than kill it with bazooka
                os.kill(p.pid, 9) # very violent
            except:
                pass
            self.userProcessList.remove(p)

        if (weioIO.gpio != None):
            if (weioRunnerGlobals.WEIO_SERIAL_LINKED == True):
                weioIO.gpio.stopReader()
                weioIO.gpio.reset()

        # Reset user attached elements
        weioUserApi.attach.procs = {}
        weioUserApi.attach.events = {}
        weioUserApi.attach.ins = {}

    def userPlayer(self, fd, events):
        print "Inside userControl()"

        if (fd is not None):
            cmd = os.read(fd,128)
            print "Received: " + cmd
        else:
            return

        if (cmd == "*START*"):
            # Re-load user main (in case it changed)
            self.userMain = self.loadUserProjectMain()

            # Calling user setup() if present
            if "setup" in vars(self.userMain):
                self.userMain.setup()

            # Then start processes from it
            self.start()
        elif (cmd == "*STOP*"):
            self.stop()

    def loadUserProjectMain(self):
        confFile = weio_config.getConfiguration()

        # Get the last name of project and run it
        #projectModule = confFile["user_projects_path"].replace('/', '.') + \
        #                    confFile["last_opened_project"].replace('/', '.') + "main"


        projectModule = confFile["last_opened_project"].replace('/', '.') + "main"
        print projectModule
        
        if (self.lastCalledProjectPath == projectModule):
            print "RELOADING"
            self.userMain = reload(self.userMain)
        else:
            print "NEW IMPORT"
            # Import userMain from local module
            try :
                self.userMain = __import__(projectModule, fromlist=[''])
            except :
                print "MODULE CAN'T BE LOADED"
                
        self.lastCalledProjectPath = projectModule
        
# User Tornado signal handler
def signalHandler(userControl, sig, frame):
        #logging.warning('Caught signal: %s', sig)
        print "CALLING STOP IF PRESENT"
        if "stop" in vars(userControl.userMain):
            logging.warning('Calling user defined stop function')
            userControl.userMain.stop()
        sys.exit(0)



###
# Shared variables between all the processes
###
class WeioShared():
    def __init__(self):
        # Create parent-child message queues
        self.qin = multiprocessing.Queue()
        self.qout = multiprocessing.Queue()

        # Create shared variable and array
        self.val = multiprocessing.Value('d', 15)
        self.arr = multiprocessing.Array('i', 256)

        # Arrays of UIDs for connections
        self.uids = multiprocessing.Array('I', 256)
        self.uidNb = multiprocessing.Value('I', 0)

    def setVal(self, idx, val):
        self.arr[idx] = val

    def getVal(self, idx):
        return self.arr[idx]

    def addClient(self, uid):
        """ N.B.
            This function is to be called by the weioRunner ONLY
            i.e. NOT from the user processes """
        self.uids[self.uidNb.value] = uid
        self.uidNb.value = self.uidNb.value + 1


def userListener():
    """thread worker function"""
    print "*************** USER LISTENER STARTED"
    qin = weioRunnerGlobals.WEIO_SHARED.qout
    while True:
        print "UL: Try to get message"
        msg = qin.get()
        print "UL: Got message"
        print "UID = " + str(msg.uid)
        print "MESSAGE = " + msg.msg
        weioRunnerGlobals.WEIO_SHARED.setVal(0, 10)
        print msg
    return



if __name__ == '__main__':
    confFile = weio_config.getConfiguration()
    # set python working directory
    #os.chdir("userFiles/"+sys.argv[1])
    myPort = confFile["userAppPort"]
    options.define("port", default=myPort, type=int)

    apiRouter = SockJSRouter(WeioHandler, '/api')

    # Instantiate all handlers for user Tornado
    app = web.Application(apiRouter.urls + [
    ('/', WeioIndexHandler),
    (r"/(.*)", web.StaticFileHandler, {"path": "www/"})
    ])
    app.listen(options.options.port, "0.0.0.0")

    logging.info(" [*] Listening on 0.0.0.0:" + str(options.options.port))
    print "*SYSOUT* User API Websocket is created at localhost:" + str(options.options.port) + "/api"

    ###
    # Construct global gpio object
    # Must be constructed here and nowhere else, because it creates UNIQUE UPER object
    ###

    try :
        weioIO.gpio = weioGpio.WeioGpio()

        # Initialize globals for the user Tornado
        weioRunnerGlobals.DECLARED_PINS = weioIO.gpio.declaredPins
    except :
        print "LPC coprocessor is not present"
        weioIO.gpio = None

    # Create a weioShared object
    weioRunnerGlobals.WEIO_SHARED = WeioShared()

    # Fire up a message listener thread
    t = threading.Thread(target=userListener)
    t.setDaemon(True)
    t.start()

    # Create a userControl object
    userControl = UserControl()

    # Install signal handlers
    signalCallback = functools.partial(signalHandler, userControl)
    signal.signal(signal.SIGTERM, signalCallback)
    signal.signal(signal.SIGINT, signalCallback)

    # Create ioloop
    ioloop = ioloop.IOLoop.instance()

    # Add user control via stdin pipe
    ioloop.add_handler(sys.stdin.fileno(), userControl.userPlayer, ioloop.READ)

    ###
    # Initialize global USER API instances
    ###
    weioUserApi.attach =  weioUserApi.WeioAttach()
    weioUserApi.console =  weioUserApi.WeioPrint()
    weioUserApi.weioShared = weioRunnerGlobals.WEIO_SHARED
    ###

    userMain = userControl.loadUserProjectMain()
    userControl.userMain.setup()
    userControl.start()



    # Before starting ioloop, stop led blinking,
    # which will light up correct LED and give information to the user
    # that all is ready
    if (platform.machine() == 'mips'):
        subprocess.call(["/etc/init.d/led_blink", "stop"])

    ioloop.start()
