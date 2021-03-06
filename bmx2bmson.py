#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import re
import sys
import json
import traceback

__author__ = "xert*"
__version__ = 0.1
__bmsonversion__ = "1.0.0"


class bms2bmson:

	def ToXX(self, str, shift):

		a = ord(str[0])
		b = ord(str[1])
		c = 0

		c += a - ord('A') + 10 if (a >= ord('A') and a <= ord('Z')) else a - ord('0')
		c *= shift
		c += b - ord('A') + 10 if (b >= ord('A') and b <= ord('Z')) else b - ord('0')

		return c

	def LoadBMS(self, bmsfile):

		bmsfilename = bmsfile

		ext_formats = [".bms", ".bme", ".bml", ".pms"]
		
		ext = os.path.splitext(os.path.basename(bmsfile))[1]
		
		for ptr, format in enumerate(ext_formats):
			
			if ext == format:
				
				self.bmstype = ptr

				with open(bmsfile, "rb") as bmsdata:
					return bmsdata.read()
		
		print "[!] is not bms type file"
		return None

	def SaveBmson(self, jsondata):

		try:
			with open("result.bmson", "wb") as jf:
				jf.write(jsondata)
			return True

		except Exception:
			traceback.print_exc()
			return False

	def ExportToJson(self):

		bmson = {}

		lines = self.lines
		bpmnotes = self.bpmnotes
		stopnotes = self.stopnotes

		bmson["version"] 	 = __bmsonversion__
		bmson["info"] 		 = self.BMSInfo
		bmson["lines"] 		 = self.lines
		bmson["bpm_events"]  = self.bpmnotes
		bmson["stop_events"] = self.stopnotes

		cnotes = {}
		bmson["sound_channels"] = []

		wavslen = len(self.wavHeader)
		for i in range(wavslen):
			cnotes[self.wavHeader[i]["ID"]] = []
				
		for wn in self.notes:

			if wn["id"] not in cnotes:
				continue
			
			n = {}
			n["c"] = wn["channel"] > 30
			
			if wn["channel"] is 1:
				n["x"] = 0
			else:
				n["x"] = (wn["channel"]-10) % 20

			n["y"] = wn["locate"]
			n["l"] = wn["length"]

			cnotes[wn["id"]].append(n)
		
		for i in range(wavslen):

			tempdict = {}
			tempdict["name"] = self.wavHeader[i]["name"]
			tempdict["notes"] = cnotes[self.wavHeader[i]["ID"]]
			bmson["sound_channels"].append(tempdict)

		bga = {}
		bga["bga_header"] = self.bgaHeader
		bga["bga_events"] = self.bbnotes
		bga["layer_events"] = self.blnotes
		bga["poor_events"] = self.bpnotes

		bmson["bga"] = bga

		bmson = json.dumps(bmson, ensure_ascii=False, sort_keys=True, indent=4)

		self.SaveBmson(bmson)

	def GetMetadata(self, bmsdata):
		"""
		return -> self.BMSInfo
		"""

		self.BMSInfo = { "title" 			: None,
						 "subtitle" 		: None,
					     "artist" 			: None,
					     "subartists" 		: None,
					     "genre" 			: None,
					     "mode_hint" 		: "beat-7k",
					     "chart_name" 		: None,
					     "level" 			: 0,
					     "init_bpm" 		: 0.0,
					     "total" 			: 100.0,
					     "back_image" 		: None,
					     "eyecatch_image"	: None,
					     "banner_image" 	: None,
					     "preview_music" 	: None,
					     "resolation" 		: 240 }

		self.wavHeader = []
		self.bgaHeader = []
		self.stopnum = []
		self.bpmnum = []

		tags = [ "ARTIST", "GENRE", "TITLE", "BPM", "TOTAL", "PLAYLEVEL" ]
		extags = [ "WAV", "BMP", "BPM", "STOP" ]

		for tag in tags:

			value = re.search(r"#" + tag + "\s(.+)\r", bmsdata)

			if value is not None:
				value = value.group(1)
			
			if tag is "PLAYLEVEL" and value is not None:
				self.BMSInfo["level"] = int(value)

			elif tag is "BPM" and value is not None:
				self.BMSInfo["init_bpm"] = float(value)
				
			elif tag is "TOTAL" and value is not None:
				self.BMSInfo["total"] = float(value)

			elif (tag is "TITLE") or (tag is "GENRE") or (tag is "ARTIST"):
				self.BMSInfo[tag.lower()] = str(value)

			else:
				pass

		for tag in extags:

			value = re.findall(r"#" + tag + "([0-9A-Z]{2})\s(.+)\r", bmsdata)
			
			if value is not None:

				for v, parameter in value:
					
					if tag is "WAV":
						self.wavHeader.append({ "ID" : self.ToXX(v, 36), "name" : parameter })

					elif tag is "BMP":
						self.bgaHeader.append({ "ID" : self.ToXX(v, 36), "name" : parameter })

					elif tag is "BPM":
						self.bpmnum.append({ self.ToXX(v, 36) : float(parameter) })

					elif tag is "STOP":
						self.stopnum.append({ self.ToXX(v, 36) : int(parameter) })

		return self.BMSInfo

	def ReadBMSLines(self, bmsdata):

		self.lineh	= { i : 960 for i in range(1000) }
		self.isln 	= { i : False for i in range(4096) }
		self.lines = []
		self.NotePre = []
		self.linemax = 0

		self.tempcount = 0

		bmslines = re.findall(r"#([0-9]{3})([0-9]{2}):(.+)\r", bmsdata)

		for measure, channel, parameter in bmslines:
			
			ch = int(channel)
			ms = int(measure)

			if ch >= 10 and ch < 70:
				c = ch % 10
				m = ch / 10
				if c == 6:   c = 8
				elif c == 7: c = 9
				elif c == 8: c = 6
				elif c == 9: c = 7
				ch = m * 10 + c

			if ch == 2:
				self.lineh[ms] = int(960 * float(parameter))

			else:
				paramlen = len(parameter) / 2

				for j in range(paramlen):

					paramsub = parameter[j*2:j*2+2]
					nn = self.ToXX(paramsub, 16) if ch == 3 else self.ToXX(paramsub, 36)

					if nn is not 0:

						self.tempcount = self.tempcount + 1
						self.linemax = max([self.linemax, ms + 1])
						self.NotePre.append({ "x" : ch, 
											  "y" : 0, 
											  "n" : nn, 
											  "ms" : ms, 
											  "mm" : paramlen, 
											  "mc" : j })

		y = 0
		for i in range(self.linemax + 1):

			self.lines.append({"y" : y})
			y += self.lineh[i]

		for i in range(len(self.NotePre)):

			ms = self.NotePre[i]["ms"]
			seq_y = (self.lines[ms+1]["y"] - self.lines[ms]["y"]) * self.NotePre[i]["mc"] / self.NotePre[i]["mm"]
			
			self.NotePre[i]["y"] = self.lines[ms]["y"] + seq_y

		self.NotePre = sorted(self.NotePre, key=lambda k: k['y'])

		t1 = 0
		t2 = 0

		for i in range(len(self.NotePre)):
			
			ch = self.NotePre[i]['x']
			if (ch > 10 and ch < 50) and self.isln[self.NotePre[i]['n']]:

				t1 = t1 + 1
			
				pln = i
				while True:	

					pln = pln - 1
					ch2 = self.NotePre[pln]['x']

					if ch == ch2:
						self.NotePre.append({ "x" : self.NotePre[pln]['x'], 
											  "y" : self.NotePre[pln]['y'], 
											  "n" : self.NotePre[pln]['n'],
											  "ms" : 0, 
											  "mm" : 0,
											  "mc" : 0 })

						self.NotePre[pln]['x'] = 0
						self.NotePre[i]['x'] = 0					
						break

			if (ch > 50 and ch < 70):

				t2 = t2 + 1

				pln = i
				while True:
					pln = pln + 1
					ch2 = self.NotePre[pln]['x']

					if ch == ch2:
						self.NotePre.append({ "x" : self.NotePre[pln]['x'] - 40, 
											  "y" : self.NotePre[pln]['y'], 
											  "n" : self.NotePre[pln]['n'],
											  "ms" : 0, 
											  "mm" : 0,
											  "mc" : 0 })

						self.NotePre[pln]['x'] = 0
						self.NotePre[i]['x'] = 0
						break

		for idx, r in enumerate(self.NotePre):
			if r['x'] == 0:
				del self.NotePre[idx]

		self.SetNotes()


	def SetNotes(self):

		self.notes = []
		self.bbnotes = []
		self.blnotes = []
		self.bpnotes = []
		self.bpmnotes = []
		self.stopnotes = []

		for i in range(len(self.NotePre)):

			np = self.NotePre[i]

			if (np['x'] is 4) or (np['x'] is 6) or (np['x'] is 7):

				bn = { 'y'  : np['y'],
					   'id' : np['n'] }

				if np['x'] == 4:
					self.bbnotes.append(bn)

				elif np['x'] == 6:
					self.bpnotes.append(bn)

				elif np['x'] == 7:
					self.blnotes.append(bn)

			elif (np['x'] == 1) or (np['x'] / 10 >= 1) or (np['x'] / 10 <= 4):
				
				n = { "channel" : np['x'],
					  "id"		: np['n'],
					  "locate"	: np['y'],
					  "length"	: 0 }

				self.notes.append(n)

			else:
				en = { "y" : np['y'] }

				if np['x'] == 3:
					en['v'] = float(np['n'])
					self.bpmnotes.append(en)

				elif np['x'] == 8:
					en['v'] = self.bpmnum[np['n']]
					self.bpmnotes.append(en)

				elif np['x'] == 9:
					en['v'] = self.stopnum[np['n']]
					self.stopnotes.append(en)

	def Convert(self, file):

		bmsdata = self.LoadBMS(file)

		self.GetMetadata(bmsdata)
		self.ReadBMSLines(bmsdata)
		self.ExportToJson()

		print "wav defined : {}\nwav notes : {}\nbga defines : {}".format(len(self.wavHeader), len(self.notes), len(self.bgaHeader))
		print "bb : {} bl : {} bp : {}".format(len(self.bbnotes), len(self.blnotes), len(self.bpnotes))

		print "[all done]"


if __name__ == "__main__":

	uinput = sys.argv[1]
	bms = bms2bmson()

	formats = [".bms", ".bme", ".bml", ".pms"]

	if os.path.isdir(uinput):
	
		for root, dirs, files in os.walk(uinput):
			
			for file in files:
				
				if file.endswith(tuple(formats)):
					
						targetbms = os.path.join(root, file)
						try:
							#print targetbms
							meta = bms.Convert(targetbms)
							
						#print meta
						except:
							pass
	else:
		
		meta = bms.Convert(uinput)
