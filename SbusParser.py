#!/usr/bin/env python3
  
import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

import time
import struct
from enum import Enum

class Flight_Mode(Enum):
    STOP = 1
    MANUAL = 2
    AUTO = 3



class SbusParser:
    def __init__(self):
        self.prev_ch1 = 0
        self.prev_ch2 = 0
        self.prev_ch3 = 0
        self.prev_ch4 = 0
        self.prev_ch5 = 0
        self.prev_ch6 = 0
        self.prev_ch7 = 0
        self.prev_ch8 = 0
        self.tButton = time.time()
        self.flight_mode = Flight_Mode.STOP

    def parse_packet(self, pkt):
        assert len(pkt) == 34
        ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8, \
        ch9, ch10, ch11, ch12, ch13, ch14, ch15, ch16, \
        failsafe, frame_lost = struct.unpack("HHHHHHHHHHHHHHHH??", pkt[:34])
        stop_trig = False
        if ch7 < 1050 and ch7 > 950 and ch8 < 1050 and ch8 > 950 and ch6 < 1500:
            # MANUAL
            return 2
        elif ch7 > 1050 and ch7 < 1100 and ch8 > 1050 and ch8 < 1100 and ch6 < 1500:
            # AUTO (FOLLOW)
            return 1
        else:
            # NONE (STOP)
            return 0
        '''
        do_something = False
        if self.prev_ch1 != ch1:
            self.prev_ch1 = ch1
            do_something = True
        if self.prev_ch3 != ch3:
            self.prev_ch3 = ch3
            do_something = True
        if self.prev_ch5 != ch5:
            self.prev_ch5 = ch5
            do_something = True
        if self.prev_ch6 != ch6:
            self.prev_ch6 = ch6
            do_something = True
        if self.prev_ch7 != ch7:
            self.prev_ch7 = ch7
            do_something = True
        if self.prev_ch8 != ch8:
            self.prev_ch8 = ch8
            do_something = True
        if do_something:
            return self.do_something()
        '''

    def do_something(self):
        if self.prev_ch7 < 1050 and self.prev_ch7 > 950 and self.prev_ch6 < 1500:
            self.flight_mode = Flight_Mode.MANUAL
        elif self.prev_ch7 > 1050 and self.prev_ch8 > 1050 and self.prev_ch6 < 1500:
            self.flight_mode = Flight_Mode.AUTO
        else:
            self.flight_mode = Flight_Mode.STOP

        print(self.prev_ch3, self.prev_ch2, self.prev_ch5, self.prev_ch6, self.prev_ch7, self.prev_ch8)
        if self.prev_ch5 > 1500 and ((time.time() - self.tButton) > 0.7):
            if self.flight_mode == Flight_Mode.MANUAL:
                return 2
            elif self.flight_mode == Flight_Mode.AUTO:
                return 1
            else:
                return 0
        


