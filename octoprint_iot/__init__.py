# coding=utf-8
from __future__ import absolute_import
from octoprint.events import eventManager, Events
import octoprint.plugin
import requests
import json

class IotPlugin(octoprint.plugin.SettingsPlugin,
				octoprint.plugin.StartupPlugin,
                octoprint.plugin.AssetPlugin,
				octoprint.plugin.EventHandlerPlugin,
                octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self.iot = None
		self.print_key = None

	def on_after_startup(self):
		self._logger.info("instantiating AWS object, yo")
		from octoprint_iot.aws import AWS
		self.iot = AWS(self._logger, self.message_handler, self._settings)
		self._logger.info("instantiated AWS object, yo")


	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			iot_host="some-key.iot.us-east-2.amazonaws.com",
			iot_rootCAPath="/path/to/cert.pem",
			iot_certificatePath="/path/to/certificate.pem.crt",
			iot_privateKeyPath="/path/to/private.pem.key"
		)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]
	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/iot.js"],
			css=["css/iot.css"],
			less=["less/iot.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			iot=dict(
				displayName="Iot Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="gerfderp",
				repo="OctoPrint-Iot",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/gerfderp/OctoPrint-Iot/archive/{target_version}.zip"
			)
		)

	def message_handler(self, message):
		retvar = json.loads(message.payload)
		filename = retvar['File']
		url = retvar['Url']
		self._logger.info("Uploading file {filename} with {url}".format(**locals()))

		with open(filename, 'rb') as image:
			response = requests.put(url, headers={}, data=image)
		self._logger.info(response)

	# ~~ EventHandlerPlugin mixin
	def on_event(self, event, payload):
		data = {}
		data.update({"print_key": self.print_key})
		data.update({"payload": payload})
		job = self._printer.get_current_job()
		if job:
			data.update({"job": job})
		if event == Events.CAPTURE_DONE:
			self._logger.info("capture_done with payload: {payload}".format(**locals()))
		# 	self.recent_capture = payload['file']
		# elif event == Events.CAPTURE_START:
		# 	self._logger.info("capture_start with payload: {payload}".format(**locals()))
			filename = payload['file'].split('/')[-1]
			last = len(filename.split('-')[-1])+1
			folder = filename[:-last]
			self.print_key = folder
			key = folder + '/' + filename
			# '/Users/tneier/Library/Application Support/OctoPrint/timelapse/tmp/AmazonBasics_PETG_0.4_logitech_mount_20181025162827-0.jpg'
			# {
			# 	"operation": "putObject",
			# 	"bucket": "octoprint-frames",
			# 	"key": "test.zip",
			# 	"replyTo": "print/image/url/response"
			# }
			data = {}
			data.update({"operation": "putObject"})
			data.update({"bucket": "octoprint-frames"})
			data.update({"key": key})
			data.update({"filename": payload['file']})
			data.update({"replyTo": "print/image/url/response"})
			self._logger.info("about to call url/request with data: {data}".format(**locals()))
			self.iot.pub('print/image/url/request', data)
		elif event == Events.MOVIE_DONE:
			self._logger.info("movie_done with payload: {payload}".format(**locals()))
			filename = payload['movie_basename']
			folder = self.print_key
			key = folder + '/' + filename
			data = {}
			data.update({"operation": "putObject"})
			data.update({"bucket": "octoprint-frames"})
			data.update({"key": key})
			data.update({"filename": payload['movie']})
			data.update({"replyTo": "print/image/url/response"})
			self._logger.info("about to call url/request with data: {data}".format(**locals()))
			self.iot.pub('print/image/url/request', data)
		elif event == Events.PRINT_STARTED:
			data.update({"event": "START"})
			self.iot.pub('print/events', data)
		elif event == Events.PRINT_DONE:
			data.update({"event": "DONE"})
			self.iot.pub('print/events', data)
		elif event == Events.PRINT_CANCELLED:
			data.update({"event": "CANCELLED"})
			self.iot.pub('print/events', data)
		elif event == Events.PRINT_FAILED:
			data.update({"event": "FAILED"})
			self.iot.pub('print/events', data)
		elif event == Events.POSITION_UPDATE:
			if self._plugin_manager.plugin_implementations['monitor']:
				envdata = self._plugin_manager.plugin_implementations['monitor'].update_data()
				data.update({"env": envdata})
				data.update({"nozzle": self._printer._temp})
				data.update({"bed": self._printer._bedTemp})
				data.update({"current_z": self._printer._stateMonitor._current_z})
				# {'message': {'job': {'averagePrintTime': 1169.9760892391205, 'lastPrintTime': 1340.1732590198517,
				# 					 'user': 'dummy',
				# 					 'file': {'origin': 'local', 'name': u'AmazonBasics_PETG_0.4_logitech_mount.gcode',
				# 							  'date': 1537496950, 'path': u'AmazonBasics_PETG_0.4_logitech_mount.gcode',
				# 							  'display': u'AmazonBasics PETG_0.4_logitech_mount.gcode',
				# 							  'size': 2733978}, 'estimatedPrintTime': 8426.296109180143, 'filament': {
				# 		u'tool0': {u'volume': 21.90765380203784, u'length': 9108.144049999091}}},
				# 			 'payload': {'reason': None, 'e': 0.0, 't': 0, 'f': 10320.0, 'y': 100.0, 'x': 100.0,
				# 						 'z': 1.4},
				# 			 'env': {'humidity': '19.1', 'temp_internal': 71.9, 'temp_external': '71.2',
				# 					 'light_state': 'off'}}, 'sequence': 19}
			self.iot.pub('print/layer', data)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Iot Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = IotPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

