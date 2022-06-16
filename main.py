#!/usr/bin/env python3

import time
from datetime import datetime
import signal
import cv2
import multiprocessing
from queue import Empty
from threading import Thread
import RPi.GPIO as GPIO
import os

# Motion detector on GPIO 18
# Floodlight on GPIO 23

class Uploader:
	def __init__(self):
		pass

	def run(self, in_q):
		print("Starting upload thread")
		while True:
			cmd = in_q.get()
			print("Issuing command from queue...", cmd)
			print(os.system(cmd))

class Recorder:
	def __init__(self):
		self._state = "idle"
		self._recording = False
		self._startTime = 0
		self._videos = 0
		self._filename = ""
		self._cmd_q = None

	def _startVideo(self, name):
		self._vidCapture = cv2.VideoCapture(0)
		self._vidCodec = cv2.VideoWriter_fourcc(*'avc1')
		self._videos = self._videos + 1
		self._filename = name
		self._output = cv2.VideoWriter(name, self._vidCodec, 20.0, (640, 480))

	def _stopVideo(self):
		self._vidCapture.release()
		self._output.release()
		cmd = "./pushvideo.sh %s" % self._filename
		print("Sending command to queue...", cmd)
		self._cmd_q.put(cmd)	

	def _lightsOn(self):
		GPIO.output(23, 1)

	def _lightsOff(self):
		GPIO.output(23, 0)

	def _changeState(self, state):
		print("Change from %s to %s" % (self._state, state))
		# This function just validates the state
		if (state == 'run'):
			self._state = 'run'
		elif state == 'stop':
			self._state = 'stop'
		elif state == 'start':
			self._state = 'start'
		elif state == 'idle':
			self._state = 'idle'
		else:
			raise Exception("Unknown state %s" % state)

	def run(self, in_q, cmd_q):
		self._cmd_q = cmd_q
		print("Starting recorder thread")
		while True:
			try:
				data = in_q.get(False)
				if data is not None:
					self._changeState(data)
			except Empty:
				pass

			if self._state == 'start':
				if self._recording is False:
					self._recording = True
					dt = datetime.now()
					self._startVideo(dt.strftime('%Y-%m-%d_%H-%M-%S.mp4'))
					self._lightsOn()
					self._startTime = time.time()
				else:
					self._startTime = time.time()
				self._changeState('run')
			elif self._state == 'run':
				pass
			elif self._state == 'stop':
				if self._recording is True:
					self._recording = False
					self._lightsOff()
					self._stopVideo()
				self._changeState('idle')
			elif self._state == 'idle':
				pass

			if self._recording is True:
				deltaSec = time.time() - self._startTime	
				if deltaSec >= 30:
					self._changeState('stop')
				else:
					ret, frame = self._vidCapture.read()
					self._output.write(frame)
			else:
				time.sleep(0.100)
		

def handler(signum, frame):
	print("SIGINT")
	GPIO.cleanup()
	exit(-1)

def motionHandler(channel):
	global messageQueue
	detect = GPIO.input(18)
	print("edge", time.time(), channel, detect)
	if detect == 1:
		messageQueue.put("start")

commandQueue = multiprocessing.Queue()
messageQueue = multiprocessing.Queue()
uploader = Uploader();
recorder = Recorder();
t0 = Thread(target=uploader.run, args=(commandQueue, ), daemon=True)
t1 = Thread(target=recorder.run, args=(messageQueue, commandQueue, ), daemon=True)
t0.start()
t1.start()
print("Importing done, threads started...")

signal.signal(signal.SIGINT, handler)

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN);
GPIO.setup(23, GPIO.OUT)
GPIO.add_event_detect(18, GPIO.BOTH, callback=motionHandler)

print("Looping in main thread")
while 1:
	time.sleep(30)
	pass

print("Cleaning up main thread")
GPIO.cleanup()

