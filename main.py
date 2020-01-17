#!/usr/bin/env python3

import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

import os
import time
import select
import socket
import struct
import numpy as np
from SbusParser import SbusParser, Flight_Mode
from Bot_State import Bot_State
from FollowBot import FollowBot

MOAB_COMPUTER = "192.168.8.20" # Office use "192.168.11.20"  GLinet use 192.168.8.20
MOAB_PORT = 12346

sbus = SbusParser()
followBot = FollowBot()

# This is the bounding-box data udp port from "collision-detector":
DATA_PORT = 3101
data_socks = [
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
]

# We also have three camera version, but for this project we use only one on the middle.
#data_socks[0].bind(("127.0.0.1", DATA_PORT))
data_socks[1].bind(("127.0.0.1", DATA_PORT))
#data_socks[2].bind(("127.0.0.1", DATA_PORT + 2))


# This is the scanline data udp port from "collision-detector":
# a distance from camera in a horizontal line of the image
SCAN_PORT = 3125  #3301
scan_socks = [
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
]
# Similarly, we use only one middle camera for this project
#scan_socks[0].bind(("127.0.0.1", SCAN_PORT))
scan_socks[1].bind(("127.0.0.1", SCAN_PORT))
#scan_socks[2].bind(("127.0.0.1", SCAN_PORT + 2))

# This is the sbus udp port.
SBUS_PORT = 31338  #31338
sbus_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sbus_sock.bind(("0.0.0.0", SBUS_PORT))

############
# These are the bounding boxes (and distances) from "collision-detector"
###
rx_bbox_data = [
    {
        'remote_id': 0,
        'nboxes': 0,
        'closestIdx': None,
        'distances': np.zeros(16, np.float),
        'bboxes': np.zeros((16, 4), np.int32),
        'ts': time.time()
    },
    {
        'remote_id': 0,
        'nboxes': 0,
        'closestIdx': None,
        'distances': np.zeros(16, np.float),
        'bboxes': np.zeros((16, 4), np.int32),
        'ts': time.time()
    },
    {
        'remote_id': 0,
        'nboxes': 0,
        'closestIdx': None,
        'distances': np.zeros(16, np.float),
        'bboxes': np.zeros((16, 4), np.int32),
        'ts': time.time()
    },
]

## find the closest camera and distance
def parse_bbox_data(camNum, data, addr):
    rx_bbox_data[camNum]['remote_id'] = data[2]
    rx_bbox_data[camNum]['nboxes'] = data[3]
    rx_bbox_data[camNum]['ts'] = time.time()
    nboxes = min(16, data[3])
    for i in range(nboxes):
        iStart = i*20 + 4
        iStop = iStart + 20
        #distances[i], bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3] = \
        a, b, c, d, e = struct.unpack('fiiii', data[iStart:iStop])
        rx_bbox_data[camNum]['distances'][i] = a
        rx_bbox_data[camNum]['bboxes'][i][0] = b
        rx_bbox_data[camNum]['bboxes'][i][1] = c
        rx_bbox_data[camNum]['bboxes'][i][2] = d
        rx_bbox_data[camNum]['bboxes'][i][3] = e
    if nboxes:
        closestIdx = np.argmin(rx_bbox_data[camNum]['distances'][:nboxes])
        rx_bbox_data[camNum]['closestIdx'] = closestIdx
    else:
        rx_bbox_data[camNum]['closestIdx'] = None


def get_last_packet(sock, bufsize=65536):
    '''Empty out the UDP recv buffer and return only the final packet
    (in case the GUI is slower than the data flow)
    '''
    sock.setblocking(0)
    data = None
    addr = None
    cont=True
    while cont:
        try:
            tmpData, addr = sock.recvfrom(bufsize)
        except Exception as ee:
            #print(ee)
            cont=False
        else:
            if tmpData:
                if data is not None:
                    pass
                    #print('throwing away a packet (GUI is too slow)')
                data = tmpData 
            else:
                cont=False
    sock.setblocking(1)
    return data, addr

depth_scale = 0.001

coords = np.zeros((3, 848, 2), np.float64)

'''
D435 Camera Intrinsics:
-----------------------
Left:  848 480  424.856293 235.481308 616.874939 616.795410
Mid:   848 480  423.163788 241.534744 613.706116 613.494080
Right: 848 480  436.346313 233.982529 613.315552 613.175415
'''

#x_range = (np.arange(848) - rgb0_intrinsics.ppx) / rgb0_intrinsics.fx  # this doesn't change

x_ranges = np.empty((3, 848))
x_ranges[0] = (np.arange(848) - 424.856293) / 616.874939
x_ranges[1] = (np.arange(848) - 423.163788) / 613.706116
x_ranges[2] = (np.arange(848) - 436.346313) / 613.315552

theta = np.radians(60.0)
rotate_left = np.array([
    [np.cos(theta), -np.sin(theta)],
    [np.sin(theta), np.cos(theta)]])

rotate_right = np.array([
    [np.cos(-theta), -np.sin(-theta)],
    [np.sin(-theta), np.cos(-theta)]])

last_scanlines = [
    np.zeros(848, np.uint16),
    np.zeros(848, np.uint16),
    np.zeros(848, np.uint16),
]

raw_coords = [
    np.empty((848, 2)),
    np.empty((848, 2)),
    np.empty((848, 2)),
]
coords = np.empty((848*3, 2))

## scanline of realsense, we use only middle camera, (1)
def rx_scanline_packet(cam_number, data, addr):
    if len(data) == 848*2:
        last_scanlines[cam_number] = np.frombuffer(data, dtype='<u2')
        if cam_number == 0:  # left camera
            raw_coords[0][:, 1] = last_scanlines[0] * depth_scale
            raw_coords[0][:, 0] = x_ranges[0] * raw_coords[0][:, 1]
            coords[:848] = np.dot(rotate_left, raw_coords[0].T).T + np.array((-0.1, -0.06))

        elif cam_number == 1:  # middle
            raw_coords[1][:, 1] = last_scanlines[1] * depth_scale
            raw_coords[1][:, 0] = x_ranges[1] * raw_coords[1][:, 1]

            coords[848:848*2] = raw_coords[1]

        elif cam_number == 2:  # right
            raw_coords[2][:, 1] = last_scanlines[2] * depth_scale
            raw_coords[2][:, 0] = x_ranges[2] * raw_coords[2][:, 1]

            coords[848*2:848*3] = np.dot(rotate_right, raw_coords[2].T).T + np.array((0.1, -0.06))

    else:
        print('packet is wrong size: %d bytes\n' % (len(data)))

bot_mode = Bot_State.NONE
allSockets = data_socks + scan_socks + [sbus_sock]

# main loop start
while True:
    ###################################################################################
    #################### Get Human Distance / ScanLine / SBUS data ####################
    ################################################################################### 
    inputs, outputs, errors = select.select(allSockets, [], [])

    for oneInput in inputs:
    	# we only have a middle camera, [1] is a middle one
        if oneInput == data_socks[1]:
            #print("recv data_sock")
            data, addr = data_socks[1].recvfrom(1024)		# get bbox data
            try:
                parse_bbox_data(1, data, addr)				# parse bbox data
            except Exception as ee:
                print('failed to process bbox data #1:', ee)
            else:
                followBot.find_closest(rx_bbox_data)		# find the closest human

        # we only have a middle camera, [1] is a middle one
        elif oneInput == scan_socks[1]:
            data, addr = get_last_packet(scan_socks[1])		# get scanline data
            rx_scanline_packet(1, data, addr)				# parse scanline data

        elif oneInput == sbus_sock:  
            data, addr = get_last_packet(sbus_sock, 64)		# get sbus data
            try:
                req_mode_change = sbus.parse_packet(data)	# parse sbus data
            except Exception as ee:
                print('failed to parse S.Bus packet:', ee)
            else:
                if req_mode_change is not None:
                    #print('Requested Mode Change:', req_mode_change)
                    if req_mode_change == 0:
                        bot_mode = Bot_State.NONE 			# None mode will start first
                    elif req_mode_change == 1:
                        bot_mode = Bot_State.FOLLOW 		# after push a confirm button, we always use this mode 
                    elif req_mode_change == 2:
                    	bot_mode = Bot_State.MANUAL
                    else:
                        print("error, unknown modechange from Sbus parser")

    ###################################################################################
    ################ Select bot_mode according to chosen SBUS channel #################
    ################################################################################### 
    
    ## None Mode ##
    if bot_mode == Bot_State.NONE:
        #print("NONE Mode")
        rpmR = 0 
        rpmL = 0     
        udpPacket = struct.pack('ff', rpmR, rpmL)
        sbus_sock.sendto(udpPacket, (MOAB_COMPUTER, MOAB_PORT))
    
    ## Follow Mode ##
    elif bot_mode == Bot_State.FOLLOW:
        #print("FOLLOW MODE")
        col_stop = followBot.load_middle_scanline(raw_coords[1][:, 1]) #raw_coords[1][:, 1]
        
        # If there is something closer than minimum skidding distance, so consider as collision
        if col_stop:
            print(' ------------ HIT SCANLINE --------------')
            rpmR = 0.0  # Stop
            rpmL = 0.0 
        else:
            rpmR, rpmL = followBot.do_something()
            #print("rpmR",rpmR)
            #print("rpmL",rpmL)
        
        udpPacket = struct.pack('ff', rpmR, rpmL)
        sbus_sock.sendto(udpPacket, (MOAB_COMPUTER, MOAB_PORT))
    
    elif bot_mode == Bot_State.MANUAL:
        print("MANUAL MODE")

    else:
        print(" ------- a BUG...  missing step in Bot_State enum!!")
    sys.stdout.flush()
    
    # max period for reading for loop is around 0.03s
    # max period in this while loop is around 0.033s



