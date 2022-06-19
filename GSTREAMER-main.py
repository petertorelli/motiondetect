#!/usr/bin/env python3

import time
from datetime import datetime
import signal
import multiprocessing
from queue import Empty
from threading import Thread
import RPi.GPIO as GPIO
import os
import subprocess
import signal

# Motion detector on GPIO 18
# Floodlight on GPIO 23

DELAY_UPLOAD_S = 60
DELAY_TIMEOUT_S = 60

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
		self._filename = ""
		self._cmd_q = None
		self._startTimestamp = "timestamp"
		self._lastStopTime = time.time()
		self._todoQueue = []

		self._ffmpeg = None

	def _startVideo(self, name):
		self._filename = name

		args = ['/usr/bin/gst-launch-1.0']
		args.append('-e')
		#args.append('-v')
		args.append('v4l2src')
		args.append('!')
		args.append('videoconvert')
		args.append('!')
		args.append('videoscale')
		args.append('!')
		args.append('video/x-raw,format=I420,width=640,height=480,framerate=15/1')
		args.append('!')
		args.append('timeoverlay')
		args.append('!')
		args.append('x264enc')
		args.append('!')
		args.append('mp4mux')
		args.append('!')
		args.append('filesink')
		args.append('location=/tmp/%s' % name)

		print("Staring GStreamer subprocess:")
		print(' '.join(str(x) for x in args))
		self._ffpmeg = subprocess.Popen(args)

	def _stopVideo(self):
		#self._ffpmeg.terminate()
		self._ffpmeg.send_signal(signal.SIGINT)
		self._ffpmeg = None
		cmd = "/home/peter/motiondetect/pushvideo.sh /tmp/%s" % self._filename
		print("... Done. Stored '%s' until upload timeout" % cmd)
		self._todoQueue.append(cmd)
		self._lastStopTime = time.time()

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
					self._startTimestamp = dt.strftime('%Y-%m-%d_%H-%M-%S')
					self._startVideo(("%s.mp4" % self._startTimestamp))
					self._lightsOn()
					self._startTime = time.time()
				else:
					print("... captured motion, resetting timeout")
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
				if deltaSec >= DELAY_TIMEOUT_S:
					self._changeState('stop')
			else:
				# Don't try to run FFMPEG and OpenCV2 video.read() together!
				# Wait 60 seconds since last time and then contact uploader
				if len(self._todoQueue) > 0:
					if time.time() - self._lastStopTime > DELAY_UPLOAD_S:
						print("60 seconds elapsed, sending %d commands..." % len(self._todoQueue))
						for cmd in self._todoQueue:
							cmd_q.put(cmd)
						self._todoQueue = []
			time.sleep(0.500)

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

commandQueue = multiprocessing.Queue(30)
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

