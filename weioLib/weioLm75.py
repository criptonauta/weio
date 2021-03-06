# LM75B thermometer driver

###
#
# WEIO Web Of Things Platform
# Copyright (C) 2013 Nodesign.net, Uros PETREVSKI, Drasko DRASKOVIC
# All rights reserved
#
#               ##      ## ######## ####  #######
#               ##  ##  ## ##        ##  ##     ##
#               ##  ##  ## ##        ##  ##     ##
#               ##  ##  ## ######    ##  ##     ##
#               ##  ##  ## ##        ##  ##     ##
#               ##  ##  ## ##        ##  ##     ##
#                ###  ###  ######## ####  #######
#
#                    Web Of Things Platform
#
# This file is part of WEIO
# WEIO is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WEIO is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors :
# Uros PETREVSKI <uros@nodesign.net>
# Drasko DRASKOVIC <drasko.draskovic@gmail.com>
#
###

from fcntl import ioctl
import struct
import platform
import time

class WeioLm75:

    # Kernel driver definition
    # SDA GPIO18
    # SCL GPIO19

    def __init__(self):

        if (platform.machine() == 'mips') :

            # file path
            filePath = "/dev/i2c-0"

            # from i2c-dev.h
            I2C_SLAVE = 0x0703

            # open file
            self.f = open(filePath, "r+")

            # LM75 addreess on weio board
            lm75addr = 0x48

            # set device address
            ioctl(self.f, I2C_SLAVE, lm75addr)

            # i2c device address
            self.deviceAddress = lm75addr
            # set instruction to get temperature - 0x0 to get temperature
            self.inst = struct.pack('B', 0x0)

    def getTemperature(self, unit="C"):
        if (platform.machine() == 'mips') :
            # ask for a temperature
            self.f.write(self.inst)

            # get two bytes as result
            rcv = self.f.read(2)

            # do data conversion see LM75B datasheet
            temp  = struct.unpack('B', rcv[0])[0] << 8
            temp |= struct.unpack('B', rcv[1])[0]

            temp >>= 5
            c = float(temp)*0.125
            if (unit is "C"):
                return c
            elif (unit is "K"):
                return c + 273.15
            elif (unit is "F"):
                return 1.8*c+32
            else:
                print "Bad unit. You can choose between C,K or F"
        else :
            print "This is fake temperature 25.123, testing purposes"
            return 25.123
# Example
# t = WeioLm75()
# while True :
#     print t.getTemperature()
#     time.sleep(0.1)

