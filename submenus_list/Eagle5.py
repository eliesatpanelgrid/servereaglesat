# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from enigma import getDesktop

# Import your direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import your standalone network helpers
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet
from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console

import os
from threading import Timer

from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel


class Eagle5(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Read layout template safely
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle5-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Add Reader"))
        self.indexpos = None
        
        # Initialize your core info manager for hardware specifications
        self.system_info = SystemInfo()

        # ACTIONS
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.keyOK,
                "cancel": self.exit,
                "back": self.exit,
                "red": self.iptv,
                "info": self.infoKey,
                "green": self.cccam,  # Maps to the green execution command
                "yellow": self.grid,
                "blue": self.scriptslist,
            }
        )

        # UI BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # COLOR KEYS LABELS
        self["key_red"] = Label("Iptv Adder")
        self["key_green"] = Label("Install Emu")
        self["key_yellow"] = Label("News")
        self["key_blue"] = Label("Scripts")

        # MENU INITIALIZATION
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

        # HOOKS NATIVE DELIVERY SYSTEM
        self.onLayoutFinish.append(self.loadScreenData)

    def loadScreenData(self):
        """Fires safely after layout finishes rendering to paint all fields simultaneously."""
        self.loadBoxIcon()
        self.mList()

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

    def mList(self):
        """Populates menu list items with specific icons based on their names"""
        self.list = []
        items = [
            ("Ncam", 1, _("Fairbird تنزيل و تثبيت ايميو")),
            ("Oscam", 2, _("Levi45 تنزيل و تثبيت ايميو")),
            ("Oscam", 3, _("Mohamed_os تنزيل و تثبيت ايميو")),
            ("Gosatplus-oscam", 4, _("Mohamed_os تنزيل و تثبيت ايميو")),
            ("Powercam-oscam", 5, _("Mohamed_os تنزيل و تثبيت ايميو")),
            ("Supcam-oscam", 6, _("Mohamed_os تنزيل و تثبيت ايميو")),
            ("Ultracam-oscam", 7, _("Mohamed_os تنزيل و تثبيت ايميو"))
        ]
        
        base_path = "Extensions/ServerEagleSat/icons_list/menu/"
        
        for name, idx, desc in items:
            if name == "Ncam":
                img_name = "ncam.png"
            else:
                img_name = "oscam.png"
                
            full_path = resolveFilename(SCOPE_PLUGINS, base_path + img_name)
            
            if not fileExists(full_path):
                print(f"[ServerEagleSat] Warning: Icon file missing at {full_path}")
            
            img = LoadPixmap(cached=True, path=full_path)
            self.list.append((_(name), idx, desc, img))
        
        self["menu"].setList(self.list)

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

    def runScript(self):
        """Dynamic router targeting user-chosen emu installer files"""
        current = self["menu"].getCurrent()
        if not current:
            return

        item_id = current[1]
        emu_name = current[0]
        script_url = ""

        # Map index IDs cleanly to target remote script elements
        if item_id == 1:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/fairbird/ncam.sh"
        elif item_id == 2:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/levi45/oscam.sh"
        elif item_id == 3:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/mohamed_os/oscam.sh"
        elif item_id == 4:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/mohamed_os/gosatplus-oscam.sh"
        elif item_id == 5:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/mohamed_os/powercam-oscam.sh"
        elif item_id == 6:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/mohamed_os/supcam-oscam.sh"
        elif item_id == 7:
            script_url = "https://raw.githubusercontent.com/eliesatpanelgrid/oe2.0/main/softcams/mohamed_os/ultracam-oscam.sh"

        if script_url:
            cmd = f"wget --no-check-certificate {script_url} -qO - | /bin/sh"
            title = _(f"Installing {emu_name}...")
            self.session.open(Console, title, [cmd])

    def keyOK(self):
        self.runScript()

    def cccam(self):
        # Green button triggers the script installation too
        self.runScript()

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def iptv(self): pass
    def grid(self): pass
    def scriptslist(self): pass

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])