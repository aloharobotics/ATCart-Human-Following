#!/usr/bin/env python3

import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

import socket
import struct
import time
import math as m
import numpy as np
#import matplotlib.pyplot as plt


MOAB_COMPUTER = "192.168.8.20"
MOAB_PORT = 12346

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', 0))



def testSendInt(int1, int2):
    udpPacket = struct.pack('HH', int1, int2)
    s.sendto(udpPacket, (MOAB_COMPUTER, MOAB_PORT))

def testSendFloat(float1, float2):
    udpPacket = struct.pack('ff', float1, float2)
    s.sendto(udpPacket, (MOAB_COMPUTER, MOAB_PORT))


#print(sendOut)
while True:

	testSendFloat(102.5,130.5)
	time.sleep(0.1)




 
