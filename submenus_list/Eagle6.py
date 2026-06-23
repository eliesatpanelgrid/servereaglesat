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


class Eagle6(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Consolidated list of all standard and variant softcam directories
        self.target_dirs = [
            "/etc/tuxbox/config",
            "/etc/tuxbox/config/ncam",
            "/etc/tuxbox/config/ncam-icam",
            "/etc/tuxbox/config/oscam",
            "/etc/tuxbox/config/oscam-emu",
            "/etc/tuxbox/config/oscam-master",
            "/etc/tuxbox/config/oscam-smod",
            "/etc/tuxbox/config/oscam-icam",
            "/etc/tuxbox/config/oscamicamnew",
            "/etc/tuxbox/config/oscamicamall",
            "/usr/keys"
        ]

        # Read layout template safely
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle6-fhd.xml")
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
                "green": self.cccam,
                "yellow": self.grid,
                "blue": self.scriptslist,
            }
        )

        # UI BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # COLOR KEYS LABELS
        self["key_red"] = Label("Remove Keys")
        self["key_green"] = Label("Install Keys")
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
        """Populates menu list items in standard direct flat layout tuple form"""
        self.list = []
        items = [
            ("Enigma1969", 1, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Novaler4k", 2, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Mohamed_Nasr", 3, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Mohamed_os", 4, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Serjoga", 5, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Softcam.org", 6, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس")),
            ("Smcam", 7, _(" تنزيل و تثبيت ملف الشفرات و مفاتيح البيسس"))
        ]
        
        img_path = "Extensions/ServerEagleSat/icons_list/menu/biss.png"
        img = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, img_path))
        
        for name, idx, desc in items:
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

    def keyOK(self):
        current = self["menu"].getCurrent()
        if current:
            item_id = current[1]
            print("[ServerEagleSat Eagle6] Selected item ID:", item_id)
            
            # Helper to generate multi-directory installation commands dynamically
            def get_download_cmd(url):
                cmds = []
                cmds.append("wget --no-check-certificate \"{}\" -O /tmp/SoftCam.Key".format(url))
                for path in self.target_dirs:
                    cmds.append("if [ -d {0} ]; then cp /tmp/SoftCam.Key {0}/SoftCam.Key; chmod 644 {0}/SoftCam.Key; fi".format(path))
                cmds.append("rm -f /tmp/SoftCam.Key")
                cmds.append("echo '====================================='")
                cmds.append("echo '  SoftCam.Key Updated Successfully! '")
                cmds.append("echo '====================================='")
                return cmds

            # WIRING TARGET WGET LINKS TO SELECTION INDEXES
            if item_id == 1:
                url = "https://docs.google.com/uc?export=download&id=1aujij43w7qAyPHhfBLAN9sE-BZp8_AwI"
                self.session.open(Console, _("Updating Enigma1969 Keys..."), get_download_cmd(url))
                
            elif item_id == 2:
                url = "http://novaler.homelinux.com/SoftCam.Key"
                self.session.open(Console, _("Updating Novaler4k Keys..."), get_download_cmd(url))
                
            elif item_id == 3:
                url = "https://raw.githubusercontent.com/popking159/softcam/master/SoftCam.Key"
                self.session.open(Console, _("Updating Mohamed Nasr Keys..."), get_download_cmd(url))
                
            elif item_id == 4:
                url = "https://raw.githubusercontent.com/MOHAMED19OS/SoftCam_Emu/main/SoftCam.Key"
                self.session.open(Console, _("Updating Mohamed_os Keys..."), get_download_cmd(url))
                
            elif item_id == 5:
                url = "http://raw.githubusercontent.com/audi06/SoftCam.Key_Serjoga/master/SoftCam.Key"
                self.session.open(Console, _("Updating Serjoga Keys..."), get_download_cmd(url))
                
            elif item_id == 6:
                url = "http://www.softcam.org/deneme6.php?file=SoftCam.Key"
                self.session.open(Console, _("Updating Softcam.org Keys..."), get_download_cmd(url))
                
            elif item_id == 7:
                url = "https://raw.githubusercontent.com/smcam/s/main/SoftCam.Key"
                self.session.open(Console, _("Updating Smcam Keys..."), get_download_cmd(url))

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def iptv(self):
        """Red Button - Removes SoftCam.Key from all designated locations safely."""
        cmds = []
        cmds.append("rm -f /tmp/SoftCam.Key")
        for path in self.target_dirs:
            cmds.append("if [ -f {0}/SoftCam.Key ]; then rm -f {0}/SoftCam.Key; echo 'Removed from: {0}'; fi".format(path))
        cmds.append("echo '====================================='")
        cmds.append("echo '  SoftCam.Key Cleanup Finished!     '")
        cmds.append("echo '====================================='")
        
        self.session.open(Console, _("Removing SoftCam files..."), cmds)

    def cccam(self):
        """Green Button - Acts exactly like the OK button."""
        self.keyOK()

    def grid(self): pass
    def scriptslist(self): pass

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])