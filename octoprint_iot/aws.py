from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
from datetime import datetime
import os, pwd


class AWS():
	home_dir = pwd.getpwuid(os.getuid()).pw_dir
	myAWSIoTMQTTClient = None
	AllowedActions = ['both', 'publish', 'subscribe']
	host = None
	rootCAPath = None
	certificatePath = None
	privateKeyPath = None
	port = ''
	useWebsocket = ''
	clientId = ''
	topic = 'print/image/url/response'
	mode = "both"
	message = "Hello World!"
	logger = None
	handler = None
	_settings = None

	def __init__(self, logger, handler, settings):
		self.logger = logger
		self.handler = handler
		self._settings = settings
		logger.info("init!")
		self.host = self._settings.get(["iot_host"])
		self.rootCAPath = self._settings.get(["iot_rootCAPath"])
		self.certificatePath = self._settings.get(["iot_certificatePath"])
		self.privateKeyPath = self._settings.get(["iot_privateKeyPath"])
		if self.mode not in self.AllowedActions:
			# parser.error("Unknown --mode option %s. Must be one of %s" % (mode, str(AllowedActions)))
			exit(2)

		if self.useWebsocket and self.certificatePath and self.privateKeyPath:
			# parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
			exit(2)

		if not self.useWebsocket and (not self.certificatePath or not self.privateKeyPath):
			# parser.error("Missing credentials for authentication.")
			exit(2)

		# Port defaults
		if self.useWebsocket and not self.port:  # When no port override for WebSocket, default to 443
			port = 443
		if not self.useWebsocket and not self.port:  # When no port override for non-WebSocket, default to 8883
			port = 8883


		# Init AWSIoTMQTTClient
		self.myAWSIoTMQTTClient = None
		if self.useWebsocket:
			self.myAWSIoTMQTTClient = AWSIoTMQTTClient(self.clientId, useWebsocket=True)
			self.myAWSIoTMQTTClient.configureEndpoint(self.host, port)
			self.myAWSIoTMQTTClient.configureCredentials(self.rootCAPath)
		else:
			self.myAWSIoTMQTTClient = AWSIoTMQTTClient(self.clientId)
			self.myAWSIoTMQTTClient.configureEndpoint(self.host, port)
			self.myAWSIoTMQTTClient.configureCredentials(self.rootCAPath, self.privateKeyPath, self.certificatePath)

		# AWSIoTMQTTClient connection configuration
		self.myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 128, 20)
		self.myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
		self.myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
		self.myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
		self.myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

		# Connect and subscribe to AWS IoT
		self.myAWSIoTMQTTClient.connect()
		if self.mode == 'both' or self.mode == 'subscribe':
			# self.myAWSIoTMQTTClient.subscribe(self.topic, 1, self.handler)
			self.myAWSIoTMQTTClient.subscribe(self.topic, 1, self.customCallback)
		# time.sleep(2)

	def customCallback(self, client, userdata, message):
		self.logger.info("Received a new message: ")
		self.logger.info(message.payload)
		self.logger.info("from topic: {message.topic} ----\n\n".format(**locals()))
		self.handler(message)

	def pub(self, topic, message):
		outmessage = dict()
		outmessage['message'] = message
		outmessage['sequence'] = datetime.now().microsecond / 10000
		messageJson = json.dumps(outmessage)
		self.myAWSIoTMQTTClient.publish(topic, messageJson, 1)
		self.logger.info("Just published to {topic} this message: {outmessage}".format(**locals()))

