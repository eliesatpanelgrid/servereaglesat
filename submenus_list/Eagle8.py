# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox  # Cleanly imported at top level
from enigma import getDesktop, gFont

# Import your direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import your standalone network helpers and softcam control helper
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet, restart_softcam_services
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


class Eagle8(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Track the path of the currently loaded config file
        self.current_file_path = None

        # Read layout template
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle8-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Server Config Editor"))
        self.indexpos = None
        
        # Initialize your core info manager for hardware specifications
        self.system_info = SystemInfo()

        # ACTIONS
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.keyOK,                   # OK button edits the line
                "cancel": self.exit,
                "back": self.exit,
                "red": self.removeSelectedLine,     # Red button removes line from screen
                "info": self.infoKey,
                "green": self.saveChanges,          # Green button saves modifications to file
                "yellow": self.loadOscamContent,    # Yellow button loads oscam.server
                "blue": self.loadNcamContent,       # Blue button loads ncam.server
            }
        )

        # UI BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # COLOR KEYS LABELS
        self["key_red"] = Label("Remove Line")
        self["key_green"] = Label("Save & Restart")
        self["key_yellow"] = Label("OSCam Server")
        self["key_blue"] = Label("NCam Server")

        # MENU / FILE CONTENT LIST
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

        # POPULATE HARDWARE METRICS
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

        # DIRECT COLD EXECUTION FOR NETWORK VALUES
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

        # DEFAULT INITIAL LOAD: oscam.server
        self.loadOscamContent()

    def readServerFile(self, filename):
        """Scans /etc/tuxbox/config/ and subfolders for the given file name and loads its text content."""
        search_root = "/etc/tuxbox/config"
        self.current_file_path = None
        
        if os.path.exists(search_root):
            for root, dirs, files in os.walk(search_root):
                if filename in files:
                    self.current_file_path = os.path.join(root, filename)
                    break

        file_lines = []
        if self.current_file_path and os.path.exists(self.current_file_path):
            try:
                with open(self.current_file_path, "r") as f:
                    for line in f:
                        clean_line = line.rstrip("\r\n")
                        file_lines.append((clean_line,))
            except Exception as e:
                file_lines.append((_("Error reading %s: %s" % (filename, str(e))),))
        else:
            file_lines.append((_("%s file not found in /etc/tuxbox/config/ hierarchy" % filename),))

        self.list = file_lines
        self["menu"].setList(self.list)

    def loadOscamContent(self):
        """Bound to Yellow button. Displays oscam.server content and updates key labels."""
        self.setTitle(_("ServerEagleSat - OSCam Server Editor"))
        self["key_yellow"].setText("[ active ] OSCam")
        self["key_blue"].setText("NCam Server")
        self.readServerFile("oscam.server")

    def loadNcamContent(self):
        """Bound to Blue button. Displays ncam.server content and updates key labels."""
        self.setTitle(_("ServerEagleSat - NCam Server Editor"))
        self["key_yellow"].setText("OSCam Server")
        self["key_blue"].setText("[ active ] NCam")
        self.readServerFile("ncam.server")

    def keyOK(self):
        """Opens VirtualKeyBoard with the selected line's text for inline modifications."""
        if not self.list:
            return

        current_index = self["menu"].getIndex()
        selected_item = self.list[current_index]
        current_text = selected_item[0]

        if "file not found" in current_text or "Error reading" in current_text:
            return

        self.session.openWithCallback(self.virtualKeyBoardCallback, VirtualKeyBoard, title=_("Edit Line Content:"), text=current_text)

    def virtualKeyBoardCallback(self, callback_string):
        """Applies configuration string edits only onto screen without touching the actual file yet."""
        if callback_string is not None:
            current_index = self["menu"].getIndex()
            self.list[current_index] = (callback_string,)
            self["menu"].setList(self.list)

    def removeSelectedLine(self):
        """Bound to Red button. Removes line from UI list and refreshes screen without file operations."""
        if not self.list:
            return

        current_index = self["menu"].getIndex()
        selected_item = self.list[current_index]
        current_text = selected_item[0]

        if "file not found" in current_text or "Error reading" in current_text:
            return

        del self.list[current_index]
        self["menu"].setList(self.list)

        if current_index >= len(self.list):
            self["menu"].setIndex(max(0, len(self.list) - 1))

    def saveChanges(self):
        """Bound to Green button. Writes active list changes systematically back into the config file and restarts services."""
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            return

        try:
            output_content = ""
            for item in self.list:
                output_content += item[0] + "\n"

            with open(self.current_file_path, "w") as f:
                f.write(output_content)

            # Trigger automated service ecosystem softcam restart sequence cleanly
            success, message = restart_softcam_services()
            
            filename_base = os.path.basename(self.current_file_path)
            if success:
                self.session.open(MessageBox, _("Changes saved to %s!\nSoftcam restarted successfully." % filename_base), MessageBox.TYPE_INFO, timeout=4)
            else:
                self.session.open(MessageBox, _("Changes saved to %s!\nSoftcam restart notice:\n%s" % (filename_base, message)), MessageBox.TYPE_INFO)
                
        except Exception as e:
            self.session.open(MessageBox, _("Failed to save changes:\n%s" % str(e)), MessageBox.TYPE_ERROR)

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

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def iptv(self): pass

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])