# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from enigma import getDesktop, iServiceInformation

# Import your direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import your standalone network helpers
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet
from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console

import os
from datetime import datetime
from threading import Timer

from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

# Helper imports with direct fallbacks
try:
    from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import restart_oscam, get_translation
except ImportError:
    def restart_oscam(): pass
    def get_translation(text): return text

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel


class Eagle4(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Read layout template
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle4-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - SoftCam Manager"))
        self.indexpos = None
        
        # Initialize your core info manager for hardware specifications
        self.system_info = SystemInfo()

        # ACTIONS (Directions handle custom list index changes)
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions", "DirectionActions"],
            {
                "ok": self.keyOK,
                "cancel": self.exit,
                "back": self.exit,
                "red": self.iptv,
                "info": self.infoKey,
                "green": self.cccam,
                "yellow": self.grid,
                "blue": self.addBissKey,
                "up": self.moveUp,
                "down": self.moveDown
            }
        )

        # UI BARS (Text transformation matches skin's vertical layout orientation)
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # SKIN MENU SOURCE ATTACHMENT
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

        # Gather dynamic live transponder variables
        self.current_service = self.session.nav.getCurrentlyPlayingServiceReference()
        self.sid = self.getSID()
        self.vpid = self.getVPID()
        self.channel_name = self.getChannelName()

        # Cache key graphic indicators for row compilation
        self.key_icon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/key_blue1.png"))

        # HOOKS NATIVE DELIVERY SYSTEM
        self.onLayoutFinish.append(self.loadScreenData)

    def loadScreenData(self):
        """Fires safely after layout finishes rendering to paint all fields simultaneously."""
        self.loadBoxIcon()

        # 1. POPULATE HARDWARE METRICS
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

        # 2. DIRECT COLD EXECUTION FOR NETWORK VALUES
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

        # 3. CONVERT SOFTCAM TO MULTICONTENT TEMPLATE SCHEME
        self.loadFile()

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

    # --- SKIN DATA CONNECTIONS ---

    def loadFile(self):
        """Converts raw SoftCam text records cleanly into skin layout structure positions."""
        try:
            base_config_path = "/etc/tuxbox/config/"
            try:
                import Components.config
                if hasattr(Components.config.config.plugins, 'CiefpOscamEditor'):
                    base_config_path = os.path.dirname(Components.config.config.plugins.CiefpOscamEditor.dvbapi_path.value)
            except:
                pass

            self.softcam_path = os.path.join(base_config_path, "SoftCam.Key")
            self.raw_lines = []
            self.list = []

            if os.path.exists(self.softcam_path):
                with open(self.softcam_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line and not clean_line.startswith("#"):
                            self.raw_lines.append(clean_line)
                            
                            # Split key instruction from channel text comment safely
                            parts = clean_line.split(";", 1)
                            key_part = parts[0].strip()
                            comment_part = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Maps explicitly into your TemplatedMultiContent parameters:
                            # pos 0: Text (Left), pos 2: Text (Right), pos 3: Pixmap (Icon)
                            self.list.append((key_part, "", comment_part, self.key_icon))
            else:
                self.list.append((get_translation("file_not_exist"), "", "", None))
            
            self["menu"].setList(self.list)
        except Exception as e:
            print("[Eagle4] SoftCam parsing stream skin connection failure:", e)
            self["menu"].setList([(get_translation("file_read_error").format(str(e)), "", "", None)])

    def addBissKey(self):
        """Spawns system Virtual Keyboard frame screen."""
        title = f"Enter BISS Key for {self.channel_name} (SID:{self.sid}, VPID:{self.vpid})"
        self.session.openWithCallback(
            self.bissKeyCallback,
            VirtualKeyBoard,
            title=title,
            text=""
        )

    def bissKeyCallback(self, biss_key):
        if not biss_key:
            return

        formatted_key = biss_key.replace(" ", "").upper()
        if len(formatted_key) not in [8, 16]:
            self.session.open(MessageBox, get_translation("invalid_key_length"), MessageBox.TYPE_ERROR, timeout=3)
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sid_vpid = f"{self.sid}{self.vpid}"
        line = f"F {sid_vpid} 00 {formatted_key} ; {self.channel_name} - {current_time}\n"

        try:
            base_dir = os.path.dirname(self.softcam_path)
            for filename in ["SoftCam.Key", "softcam.key"]:
                target_path = os.path.join(base_dir, filename)
                self._writeToFile(target_path, line, f"F {sid_vpid} 00")

            # Force live list conversion recalculation update loop
            restart_oscam()
            self.loadFile()

            self.session.open(MessageBox, get_translation("biss_key_added").format(self.channel_name), MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            print(f"Error handling file execution template update stack: {e}")
            self.session.open(MessageBox, f"Error: {str(e)}", MessageBox.TYPE_ERROR, timeout=3)

    def _writeToFile(self, file_path, new_line, search_pattern):
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line for line in f if search_pattern not in line]
        else:
            lines = []

        lines.append(new_line)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # --- DVB SYSTEM IDENTIFICATION MODULES ---

    def getSID(self):
        if self.current_service:
            try:
                service_string = self.current_service.toString()
                parts = service_string.split(':')
                if len(parts) >= 4:
                    sid_hex = parts[3]
                    return f"{int(sid_hex, 16):04X}"
            except:
                pass
        return "0001"

    def getVPID(self):
        try:
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                if info:
                    vpid = info.getInfo(iServiceInformation.sVideoPID)
                    if vpid > 0:
                        return f"{vpid:04X}"
        except:
            pass
        return "0021"

    def getChannelName(self):
        try:
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                if info:
                    name = info.getName()
                    if name:
                        return name
        except:
            pass
        return "Current Channel"

    # --- ENGINE CONTROLS INTERFACES ---

    def keyOK(self):
        pass

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def moveUp(self):
        self["menu"].up()

    def moveDown(self):
        self["menu"].down()

    def iptv(self): pass
    def cccam(self): pass
    def grid(self): pass

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])
