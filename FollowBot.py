#!/usr/bin/env python3

import sys
if sys.version_info[0] < 3:
	raise Exception("Must be using Python 3")

import os
import struct
import time
import numpy as np
import math as m

from miscMath import get_line_coefficients

def print_position(distance, throttle, pos):
	'''pos should be between 0 and the number of columns in your terminal'''
	style = 0
	fg = 37  # 30..38
	bg = 40  # 40..48
	ansi_format = ';'.join([str(style), str(fg), str(bg)])
	s1 = '\x1b[' + ansi_format + 'm'
	s3 = '\x1b[0m'
	spaces = ' ' * pos
	print("%.01f %d" % (distance, throttle),spaces + s1 + '  ' + s3)

MAX_SKID_SPEED = 10.0       # RPM

MIN_CHASE_DISTANCE = 2.0  #2.0
MAX_CHASE_DISTANCE = 7.0   #5.0

MIN_SKID_DISTANCE = 0.5
MAX_SKID_DISTANCE = MIN_CHASE_DISTANCE

MIN_CHASE_SPEED = 25.0      # unit in RPM
MAX_CHASE_SPEED = 100.0     # unit in RPM

deg2rad = m.pi/180.0
rad2deg = 180.0/m.pi

R_wheel = 15.34/100.0		# radius of the wheel, meters
L_cart = 47.0/100.0			# length between two wheels, meters

# We will follow the form of:  y = m*x + b
_chase_m, _chase_b = get_line_coefficients(
				MIN_CHASE_DISTANCE, MAX_CHASE_DISTANCE, 
				MIN_CHASE_SPEED, MAX_CHASE_SPEED)

class FollowBot:
	def __init__(self):
		self._closestCam = None
		self._closestDistance = None
		self._bbox = None
		self._collision_stop = False
		self.x_avg = 424.0      # RealSense is 424.0  /  Mynteyed is 640.0        
		self.leds_angle = 0.0

	def map(self, val, in_min, in_max, out_min, out_max):

		return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

	def load_middle_scanline(self, scanline):
		if scanline[100:-100].min() < MIN_SKID_DISTANCE: #2.0
			self._collision_stop = True
			#print(scanline[100:-100].min())
			#print("  ------------------------------ ")
		else:
			self._collision_stop = False
			#print()
		return self._collision_stop

	def find_closest(self, bbox_data):
		self._closestDistance = 20.0
		self._closestCam = None
		self._bbox = np.zeros(4, np.int32)
		for camNum, rxDat in enumerate(bbox_data):
			idx = rxDat['closestIdx']
			if idx is not None:
				dist = rxDat['distances'][idx]
				if dist < self._closestDistance:
					self._closestDistance = dist
					self._closestCam = camNum
					self._bbox = rxDat['bboxes'][idx]

		if self._closestCam is not None:
			self.x_avg = (self._bbox[0] + self._bbox[1]) / 2.0

			if self._closestCam == 0:
				self.leds_angle = 34.5 * (self.x_avg - 424) / 424.0 - 60.0
			elif self._closestCam == 1:
				self.leds_angle = 34.5 * (self.x_avg - 424) / 424.0
			elif self._closestCam == 2:
				self.leds_angle = 34.5 * (self.x_avg - 424) / 424.0 + 60.0
			else:
				print("  **** A BUG IN FOLLOW-BOT.  UNKNOWN Camera number! ****")
				self.leds_angle = 100.0
		else:
			self.leds_angle = 100.0


	def do_something(self):
		if self._closestCam is not None:
			pos = 1.0 * (self.x_avg - 424) / 424.0  # pos is mapped value of the x_avg from -1 to 1
			#print("x_avg",self.x_avg)
			#print("pos",pos)

			print("_closestDistance", self._closestDistance)
			if self._closestDistance > MAX_CHASE_DISTANCE:
				print("Over than MAX_CHASE_DISTANCE")
				rpmR = 0.0  # stop chasing
				rpmL = 0.0
				#print("if__1")
			elif self._closestDistance <= MIN_SKID_DISTANCE:
				print("Less than MIN_CHASE_DISTANCE")
				rpmR = 0.0  # stop chasing
				rpmL = 0.0
				#print("if__2")
			elif (self._closestDistance >= MIN_SKID_DISTANCE) and (self._closestDistance < MAX_SKID_DISTANCE):
				rpmR = -MAX_SKID_SPEED*pos           # 
				rpmL = -rpmR
				print("SKIDDING..." + "____________" + "rpmR: "+ str(rpmR) + "   " + "rpmL: " + str(rpmL))
			else:
				# Adjust the speed according to the distance
				#print("CHASING...")
				humanDepth = self._closestDistance
				frameDist = 2.0*(humanDepth)*(m.tan(55.0*deg2rad))		# this is a formula to calculate horizontal distance of the human plan
				x_dist = self.map(pos, -1.0, 1.0, -frameDist/2.0, frameDist/2.0) # map a pos value to real distance same unit as humanDepth
				chord_dist = m.sqrt(x_dist**2 + humanDepth**2)		# a hypotenuse length of right triangle, and also a chord distance of ICC circle
				humanAng = m.atan(x_dist/humanDepth)				# an angle from center of camera to detected human on the frame
				ICCAng = m.pi/2.0 - humanAng						# an angle between two radiuses in ICC circle
				ICC_R = (chord_dist/2.0)/m.sin(ICCAng/2.0)			# a radius of ICC circle

				chase_rpm = _chase_m*humanDepth + _chase_b		# this is an easy map from human distance to wheel's chasing rpm

				# human on the right
				if pos > 0.1:
					VL = (chase_rpm*6.0*deg2rad)*R_wheel					# wheel's linear velocity, VL is faster than VR
					VR = VL*(2*ICC_R/L_cart - 1.0)/(2*ICC_R/L_cart + 1.0)	# we know ICC_R and faster wheel speed, then slower wheel can be found
					rpmL = VL/(6*(np.pi/180.0)*R_wheel)
					rpmR = VR/(6*(np.pi/180.0)*R_wheel)

				
					print("Follow RIGHT" + "____________" + "rpmR: "+ str(rpmR) + "   " + "rpmL: " + str(rpmL))

				# human on the left
				elif pos < -0.1:
					
					VR = (chase_rpm*6.0*deg2rad)*R_wheel					# wheel's linear velocity, VR is faster than VL
					VL = VR*(2*ICC_R/L_cart - 1.0)/(2*ICC_R/L_cart + 1.0)	# we know ICC_R and faster wheel speed, then slower wheel can be found
					rpmL = VL/(6*(np.pi/180.0)*R_wheel)
					rpmR = VR/(6*(np.pi/180.0)*R_wheel)
					print("Follow LEFT" + "____________" + "rpmR: "+ str(rpmR) + "   " + "rpmL: " + str(rpmL))

				# human almost at the center
				else:
					rpmR = chase_rpm		# both wheels have same rpm speed
					rpmL = chase_rpm
					print("Follow STRAIGHT" + "____________" + "rpmR: "+ str(rpmR) + "   " + "rpmL: " + str(rpmL))

					#print("else")

				posPercent = int(round((pos / 6 + 0.5) * 100))
				#print_position(self._closestDistance, sbus_throttle_value, posPercent)

			return  rpmR, rpmL 

		else:
			# Stop
			print("NO HUMAN DETECTED")
			rpmR = 0  
			rpmL = 0
			self.leds_angle = 0.0
			# XDrive throttle comes first then steering 
			return rpmR, rpmL 



