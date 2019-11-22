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



def testSendInt(steering_sbus_value, throttle_sbus_value):
    udpPacket = struct.pack('HH', steering_sbus_value, throttle_sbus_value)
    s.sendto(udpPacket, (MOAB_COMPUTER, MOAB_PORT))

def FloatToInt(rpm):
	
	rpm = round(rpm,2)  # round the rpm float number to 0.00 
	
	# Positive number
	if rpm >= 0.0:
		intValue = int(rpm*100) 
	# Negative number
	else:
		intValue = int(65536 + rpm*100)    # ex. 65536 + -14400

	return intValue

L = 50.0
R = L
#%changed 1 2 4 6 10 0

rpmR = FloatToInt(R)
rpmL = FloatToInt(L)
#print(sendOut)
while True:
	# UDP sends an inter, not float.
	# MOAB will receive this value and / by 100.0 to make a float point

	testSendInt(rpmR,rpmL)
	time.sleep(0.1)




 