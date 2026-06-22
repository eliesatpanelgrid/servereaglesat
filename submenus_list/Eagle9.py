# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from enigma import getDesktop

# Import your direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import your standalone network helpers
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet
from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console

import os

# Components
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel 

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel
from enigma import eTimer 


class Eagle9(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Read layout template
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle9-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Cam Live Logs"))
        self.indexpos = None
        
        self.system_info = SystemInfo()
        self.last_log_content = ""

        # CLEANED ACTIONS: Removed color mappings entirely so they act purely as visual decoration
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "HotkeyActions", "DirectionActions"],
            {
                "ok": self.keyOK,
                "cancel": self.exit,
                "back": self.exit,
                "info": self.infoKey,
                
                # Manual Scrolling Key-Binds for Logs
                "up": self.logUp,
                "down": self.logDown,
                "left": self.logUp,
                "right": self.logDown,
            }
        )

        # UI BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # DECORATIVE ONLY: Static placeholders on the screen
        self["key_red"] = Label("- - - -")
        self["key_green"] = Label("- - - -")
        self["key_yellow"] = Label("- - - -")
        self["key_blue"] = Label("- - - -")

        # MENU PLACEHOLDER
        self.list = []
        self["menu"] = List(self.list)

        # INITIALIZE LABELS
        labels = ["MemoryLabel", "SwapLabel", "FlashLabel", "gstreamerLabel",
                  "pythonLabel", "CPULabel", "ipLabel", "macLabel",
                  "HardwareLabel", "ImageLabel", "KernelLabel",
                  "EnigmaVersionLabel", "driverLabel", "internetLabel"]
        text = [_("Ram:"), _("Swap:"), _("Flash:"), _("Gst:"), _("Py:"), _("Prc:"),
                _("IP address:"), _("Mac Address:"), _("Hdw:"), _("Img:"), _("Krn:"), _("Upd:"), _("Drv:"), _("Internet:")]
        for l, t in zip(labels, text):
            self[l] = StaticText(t)

        # INITIALIZE VALUES
        values = ["memTotal", "swapTotal", "flashTotal", "device", "gstreamer", "python",
                  "Hardware", "Image", "CPU", "Kernel", "ipInfo", "macInfo",
                  "EnigmaVersion", "driver", "internet"]
        for v in values:
            self[v] = StaticText()

        self["Version"] = Label(_("V" + Version))
        self["Panel"] = Label(_(Panel))
        self["boxicon"] = Pixmap()

        # The Log component
        self["cam_logs"] = ScrollLabel(_("Loading live log streams..."))

        self.log_timer = eTimer()
        self.log_timer.callback.append(self.updateCamLogs)

        self.onLayoutFinish.append(self.loadScreenData)
        self.onClose.append(self.cleanupScreen)

    def loadScreenData(self):
        self.loadBoxIcon()

        try:
            self.system_info.memInfo(self)
            self.system_info.FlashMem(self)
            self.system_info.devices(self)
            self.system_info.mainInfo(self)
            self.system_info.cpuinfo(self)
            self.system_info.getPythonVersionString(self)
            self.system_info.getGStreamerVersionString(self)
        except Exception as e:
            print("[ServerEagleSat Submenu] Hardware Specifications Load Failure:", e)

        try:
            local_ip = get_local_ip()
            self["ipInfo"].setText(str(local_ip))

            net_status = check_internet()
            if net_status == "Online":
                self["internet"].setText(_("Connected"))
            else:
                self["internet"].setText(_("Disconnected"))
        except Exception as e:
            print("[ServerEagleSat Submenu] Network Target Mapping Failure:", e)

        self.log_timer.start(2000, False)

    def updateCamLogs(self):
        possible_paths = [
            "/tmp/oscam.log",
            "/tmp/ncam.log",
            "/var/log/oscam.log",
            "/var/log/ncam.log",
            "/tmp/smartcard.log"
        ]
        
        current_log_data = _("No active OSCam or NCam log detected on filesystem.")
        
        for log_path in possible_paths:
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", errors="ignore") as f:
                        lines = f.readlines()
                        latest_lines = lines[-100:]
                        current_log_data = "".join(latest_lines)
                    break
                except Exception as e:
                    current_log_data = "Log Read Error: %s" % str(e)

        if current_log_data != self.last_log_content:
            self.last_log_content = current_log_data
            if "cam_logs" in self:
                self["cam_logs"].setText(current_log_data)
                self["cam_logs"].pageDown()

    def logUp(self):
        if "cam_logs" in self:
            self["cam_logs"].pageUp()

    def logDown(self):
        if "cam_logs" in self:
            self["cam_logs"].pageDown()

    def cleanupScreen(self):
        if self.log_timer:
            self.log_timer.stop()

    def loadBoxIcon(self):
        try:
            box = "default"
            if os.path.exists("/etc/hostname"):
                with open("/etc/hostname", "r") as f:
                    box = f.read().strip().lower()
            folder = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/boxicons/")
            icon = os.path.join(folder, "%s.png" % box)
            if not fileExists(icon):
                icon = os.path.join(folder, "default.png")
            if fileExists(icon):
                pix = LoadPixmap(cached=True, path=icon)
                if pix and self["boxicon"].instance:
                    self["boxicon"].instance.setPixmap(pix)
                    self["boxicon"].show()
        except Exception as e:
            print("SUBMENU ICON ERROR:", e)

    def keyOK(self): pass
    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])
    def exit(self): self.close()
    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])