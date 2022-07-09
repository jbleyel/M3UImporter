"""
M3UImporter Plugin by jbleyel 2022

Some of the code is from other plugins:
all credits to the coders :-)

M3UImporter Plugin is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

M3UImporter Plugin is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
"""


import json
from enigma import eServiceReference, eServiceCenter, eDVBDB

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config
from Components.ProgressBar import ProgressBar
from Components.Sources.StaticText import StaticText
import Components.Task
from Plugins.Plugin import PluginDescriptor
from Screens.ChannelSelection import MODE_TV  #,service_types_tv, MODE_RADIO
from Screens.Screen import Screen
from Tools.Directories import fileExists

VERSION = "1.0"

class M3UImporterScreen(Screen):

	skin = """
	<screen name="Setup" position="center,center" size="980,570" resolution="1280,720">
		<widget name="Title" position="10,10" size="e-20,50" font="Regular;25"/>
		<widget name="lab2" position="10,e-160" size="e-20,100" font="Regular;20" valign="center" />
		<widget name="progress" position="10,e-50" size="e-20,20" foregroundColor="#1A27408B" borderWidth="2" transparent="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):

		self.skin = M3UImporterScreen.skin
		Screen.__init__(self, session)
		self.setTitle("M3UImporter v%s (c) JB" % VERSION)

		self.bouquet_rootstr = ""
		self.boxchannels = {}

		self["lab2"] = Label()
		
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)
		
		self["key_green"] = StaticText(_("Start"))
		self["key_red"] = StaticText(_("Close"))
		
		self["actions"] = ActionMap(["ColorActions"],
		{
			"red": self.keyCancel,
			"green": self.keyStart,
		}, -2)

		self.callback = None
		self.propertys = {}
		
		if not fileExists('/etc/enigma2/M3UImporter.conf'):
			self["lab2"].setText("/etc/enigma2/M3UImporter.conf not found")
		else:
			self["lab2"].setText("error in M3UImporter.conf")
			try:
				with open('/etc/enigma2/M3UImporter.conf') as json_file:
					self.propertys = json.load(json_file)
				self["lab2"].setText("")
			except (IOError, ValueError):
				pass


	def keyCancel(self):
		self.close()

	def progress(self, current, total):
		p = int(100*current/float(total))
		self["progress"].setValue(p)

	
	def keyStart(self):

		if "m3ufile" not in self.propertys:
			self["lab2"].setText("m3u file not defnined .. see /etc/enigma2/M3UImporter.conf")
			return

		m3ufile = self.propertys["m3ufile"]
		if not fileExists(m3ufile):
			self["lab2"].setText("m3u file not found .. see /etc/enigma2/M3UImporter.conf")
			return

		boxepgimport = []
		
		if "boxepgimport" in self.propertys:
			boxepgimport = self.propertys["boxepgimport"]

#		self.JobImport()

		Components.Task.job_manager.AddJob(self.creatImportJob())

	def creatImportJob(self):
		job = Components.Task.Job("M3UImporter")
		task = Components.Task.PythonTask(job,"Getting M3U...")
		task.work = self.JobImport
		task.weighting = 1
		return job

	def JobImport(self):
		lines = []
		m3ufile = self.propertys["m3ufile"]
		self["lab2"].setText("Read M3U")

		try:
			import codecs
			text_file = codecs.open(m3ufile, encoding='utf-8')   
			for line in text_file:
				lines.append(line)
			text_file.close()
		except IOError:
			pass

		if len(lines) == 0:
			self["lab2"].setText("m3u file not found .. see /etc/enigma2/M3UImporter.conf")
			return

		self["lab2"].setText("Get Bouquets")
		
		boxepgimport = []
		
		if "boxepgimport" in self.propertys:
			boxepgimport = self.propertys["boxepgimport"]

		self.GetAllServices(boxepgimport)
	
		self["lab2"].setText("Start Import")

		max = len(lines)
		pos = 1

		series = []
		live2 = []
		bqs = {}
		mbqs = {}
		mbqns = {}
		
		groupmappings = {}
		
		if "groupmappings" in self.propertys:
			groupmappings = self.propertys["groupmappings"]


		moviegroupmappings = {}
		if "moviegroupmappings" in self.propertys:
			moviegroupmappings = self.propertys["moviegroupmappings"]
		
		bqns = []
		for k,v in groupmappings.items():
			if v not in bqns:
				bqns.append(v)
				bqs[v] = []
				bqs[v].append("#NAME %s" % v)

		othermoviesbqname = ""
		if "othermoviesbqname" in self.propertys:
			othermoviesbqname = self.propertys["othermoviesbqname"]
		
		bqns = []
		for k,v in moviegroupmappings.items():
			if v not in bqns:
				bqns.append(v)
				mbqs[v] = []
				mbqs[v].append("#NAME %s" % v)
				mbqns[v] = []

		if othermoviesbqname != "":
			mbqs[othermoviesbqname] = []
			mbqs[othermoviesbqname].append("#NAME %s" % othermoviesbqname)
			mbqns[othermoviesbqname] = []

		exclude = {}
		
		if "exclude" in self.propertys:
			exclude = self.propertys["exclude"]

		seriesbqname = ""
		othersbqname = ""
		
		if "othermoviesbqname" in self.propertys:
			othermoviesbqname = self.propertys["othermoviesbqname"]

		if "seriesbqname" in self.propertys:
			seriesbqname = self.propertys["seriesbqname"]
		
		if "othersbqname" in self.propertys:
			othersbqname = self.propertys["othersbqname"]
			
		importepgmappings = {}
		if "importepgmappings" in self.propertys:
			importepgmappings = self.propertys["importepgmappings"]

		series.append("#NAME %s" % seriesbqname)
		live2.append("#NAME %s" % othersbqname)

		epgrefs = {}

		while pos < max:
			self.progress(pos , max)

			t = lines[pos]
			ln = lines[pos+1]
			ln = ln.replace('\n', "")
			ln = ln.replace('\r', "")
			t = t.replace('\n', "")
			t = t.replace('\r', "")

			gt = t.split(' group-title="')
			gt = gt[1].split('"')
			g = gt[0]

			na= t.split(',')
			n = na[-1]
			nn = n

			if n.endswith(' DE'):
				nn = n[:-3]
			if n.endswith(' UK'):
				nn = n[:-3]
			if n.endswith(' US'):
				nn = n[:-3]
			if n.endswith(' AT'):
				nn = n[:-3]
			if n.endswith(' CH'):
				nn = n[:-3]

			nn = nn.replace(' FHD',' HD')

			l = "#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s" % ln.replace(':','%3a')

			self["lab2"].setText(nn)

			if "/series/" in l:
				if "####" in t:
					series.append("#SERVICE 1:64:0:0:0:0:0:0:0:0::%s" % n)
					series.append("#DESCRIPTION: %s" % n)
				else:
					series.append(l)
					series.append("#DESCRIPTION: %s" % n)
			elif "/movie/" in l:

				ll = l
				if "####" in t:
					ll = "#SERVICE 1:64:0:0:0:0:0:0:0:0::%s" % n
				nnn = "#DESCRIPTION: %s" % n

				md = {
					"l" : ll,
					"n" : nnn
				}
				if g in moviegroupmappings:
					gk = moviegroupmappings[g]
					mbqns[gk].append(md)
				elif othermoviesbqname != "":
					mbqns[othermoviesbqname].append(md)
			elif g in groupmappings:
				if g in exclude:
					for exx in exclude[g]:
						ll = len(exx) - 1 
						if exx == n:
							n = ""
							continue
						elif exx.endswith("*") and len(n) >= ll:
							if exx[:-1] == n[:ll]:
								n = ""
								continue
						
				if "All" in exclude:
					for exx in exclude["All"]:
						if exx == n:
							n = ""
							continue

				if n == "":
					pos = pos + 2
					continue

				l = "#SERVICE 4097:0:1:%s:0:0:0:0:0:0:%s" % (str(pos), ln.replace(':','%3a'))
				if g in importepgmappings:
					ne = "%s.%s" % (nn.replace(" HD","").replace(" ",""), importepgmappings[g])
					ll = "4097:0:1:%s:0:0:0:0:0:0:%s" % (str(pos), ln.replace(':','%3a'))
					epgrefs[ll] = ne
				else:
					ref = self.getRef(nn)
					if ref != "":
						l = "#SERVICE %s%s" % (ref,ln.replace(':','%3a'))
					
				if "####" in t:
					ll = "#SERVICE 1:64:0:0:0:0:0:0:0:0::%s" % n
				else:
					ll = l
				nnn = "#DESCRIPTION: %s" % n
				gk = groupmappings[g]
				bqs[gk].append(ll)
				bqs[gk].append(nnn)
			else:
				if "####" in t:
					live2.append("#SERVICE 1:64:0:0:0:0:0:0:0:0::%s" % n)
					live2.append("#DESCRIPTION: %s" % n)
				else:
					live2.append(l)
					live2.append("#DESCRIPTION: %s" % n)
			pos = pos + 2

		self["lab2"].setText("End Import")

		for k,v in mbqns.items():
			for mmm in sorted(v, key=lambda i: i["n"]):
				mbqs[k].append(mmm["l"])
				mbqs[k].append(mmm["n"])

		for k,v in bqs.items():
			bn = self.addBouquet(str(k), MODE_TV, None)
			if bn != "":
				filename = "/etc/enigma2/userbouquet.%s.tv" % bn
				with codecs.open(filename, 'w', 'utf-8') as outfile:
					for line in v:
						outfile.write(line)
						outfile.write('\n')

		for k,v in mbqs.items():
			bn = self.addBouquet(str(k), MODE_TV, None)
			if bn != "":
				filename = "/etc/enigma2/userbouquet.%s.tv" % bn
				with codecs.open(filename, 'w', 'utf-8') as outfile:
					for line in v:
						outfile.write(line)
						outfile.write('\n')

		if othersbqname != "":
			bn = self.addBouquet(str(othersbqname), MODE_TV, None)
			if bn != "":
				filename = "/etc/enigma2/userbouquet.%s.tv" % bn
				with codecs.open(filename, 'w', 'utf-8') as outfile:
					for line in live2:
						outfile.write(line)
						outfile.write('\n')

		if seriesbqname != "":
			bn = self.addBouquet(str(seriesbqname), MODE_TV, None)
			if bn != "":
				filename = "/etc/enigma2/userbouquet.%s.tv" % bn
				with codecs.open(filename, 'w', 'utf-8') as outfile:
					for line in series:
						outfile.write(line)
						outfile.write('\n')

		eDVBDB.getInstance().reloadBouquets()

		if fileExists("/etc/epgimport/"):
			import xml.etree.cElementTree as ET
			
			root = ET.Element("channels")
			for k,v in epgrefs.items():
				ET.SubElement(root, "channel", id=v).text = k
			
			tree = ET.ElementTree(root)
			tree.write("/etc/epgimport/custom.channels.xml")

		self["lab2"].setText("DONE")
		#self.close()


	def getMutableBouquetList(self, mode):
		if mode == MODE_TV:
			self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
		else:
			self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
		return self.getMutableList(eServiceReference(self.bouquet_rootstr))

	def getMutableList(self, ref):
		serviceHandler = eServiceCenter.getInstance()
		return serviceHandler.list(ref).startEdit()

	def buildBouquetID(self, str, prefix, mode):
		tmp = str.lower()
		name = ''
		for c in tmp:
			if (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9'):
				name += c
			else:
				name += '_'
		# check if file is unique
		suffix = ""
		if mode == MODE_TV:
			suffix = ".tv"
		else:
			suffix = ".radio"
		filename = '/etc/enigma2/' + prefix + name + suffix
		return name

	def addBouquet(self, bName, mode, services):
		if config.usage.multibouquet.value:
			mutableBouquetList = self.getMutableBouquetList(mode)
			if mutableBouquetList:
				bb = self.buildBouquetID(bName, "userbouquet.", mode)
				#print bb
				if mode == MODE_TV:
					#bName += " (TV)"
					sref = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.%s.tv\" ORDER BY bouquet' % bb
				else:
					#bName += " (Radio)"
					sref = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.%s.radio\" ORDER BY bouquet' % bb
				new_bouquet_ref = eServiceReference(str(sref))
				if not mutableBouquetList.addService(new_bouquet_ref):
					mutableBouquetList.flushChanges()
					eDVBDB.getInstance().reloadBouquets()
					mutableBouquet = self.getMutableList(new_bouquet_ref)
					if mutableBouquet:
						mutableBouquet.setListName(bName)
						if services is not None:
							for service in services:
								if mutableBouquet.addService(service):
									print("add % to new bouquet failed" % service.toString())
						mutableBouquet.flushChanges()
						#self.setRoot(self.bouquet_rootstr)
						print("Bouquet %s created." % bName)
						return bb
					else:
						print("Get mutable list for new created bouquet failed!")
						return ""
				else:
					print("Bouquet %s already exists." % bName)
					return bb
			else:
				print("Bouquetlist is not editable!")
		else:
			print("Multi-Bouquet is not enabled!")
		return ""

	def GetAllServices(self, boxepgimport):
		try:
			from Plugins.Extensions.OpenWebif.controllers.models.services import getServices
			_bouquets = getServices(sRef = "")
			for b in _bouquets["services"]:
				if b["servicename"] in boxepgimport:
					_services = getServices( sRef = b["servicereference"])
					for s in _services['services']:
						if "%" not in s["servicereference"]:
							sn = s["servicename"]
							if sn not in self.boxchannels:
								self.boxchannels[sn] = s["servicereference"]
		except ImportError:
			print("OpenWebif Plugin not found")
			return
		
	def getRef(self, name):
		if name in self.boxchannels:
			return self.boxchannels[name]
		return ""


def main(session, **kwargs):
	session.open(M3UImporterScreen)

def Plugins(**kwargs):
	return PluginDescriptor(
		name="M3UImporter",
		description="M3UImporter",
		where = PluginDescriptor.WHERE_PLUGINMENU,
		fnc=main)
