

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import json



AllowedActions = ['both', 'publish', 'subscribe']

host = "a1wjytbxze00ry-ats.iot.us-east-2.amazonaws.com"
rootCAPath = "/Users/tneier/awspi/AmazonRootCA1.pem"
certificatePath = "/Users/tneier/awspi/cec0dfd6f8-certificate.pem.crt"
privateKeyPath = "/Users/tneier/awspi/cec0dfd6f8-private.pem.key"
port = ''
useWebsocket = ''
clientId = ''
topic = 'sdk/test/Python'
mode = "both"
message = "Hello World!"

if mode not in AllowedActions:
    # parser.error("Unknown --mode option %s. Must be one of %s" % (mode, str(AllowedActions)))
    exit(2)

if useWebsocket and certificatePath and privateKeyPath:
    # parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not useWebsocket and (not certificatePath or not privateKeyPath):
    # parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if useWebsocket and not port:  # When no port override for WebSocket, default to 443
    port = 443
if not useWebsocket and not port:  # When no port override for non-WebSocket, default to 8883
	port = 8883

def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: {message.topic} ----\n\n".format(**locals()))
	# print("--------------\n\n")

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath)
else:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
if mode == 'both' or mode == 'subscribe':
    myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)
time.sleep(2)


loopCount = 0
while True:
    if mode == 'both' or mode == 'publish':
        outmessage = {}
        outmessage['message'] = message
        outmessage['sequence'] = loopCount
        messageJson = json.dumps(outmessage)
        myAWSIoTMQTTClient.publish(topic, messageJson, 1)
        if mode == 'publish':
            print('Published topic %s: %s\n' % (topic, messageJson))
        loopCount += 1
time.sleep(1)
