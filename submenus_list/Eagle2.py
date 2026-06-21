# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import getDesktop, gFont, eTimer, RT_HALIGN_LEFT
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

# Import hardware, network, and softcam control helpers explicitly from menus_list.Helpers
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet, restart_softcam_services
from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console

import os
import re
import base64
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel


# =========================================================================
#                 AUTONOMOUS OSCAM CONFIG PARSERS
# =========================================================================
def find_oscam_dir():
    """Scans all known Enigma2 image default directories for OSCam files."""
    possible_paths = [
        "/etc/tuxbox/config/",
        "/etc/tuxbox/config/oscam/",
        "/var/tuxbox/config/",
        "/usr/keys/",
        "/etc/"
    ]
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "oscam.server")):
            return path
    return "/etc/tuxbox/config/"

def read_oscam_conf():
    """Parses oscam.conf to extract WebIF port and credentials."""
    conf = {"ip": "127.0.0.1", "port": "8888", "user": "", "pwd": ""}
    conf_path = os.path.join(find_oscam_dir(), "oscam.conf")
    if not os.path.exists(conf_path):
        return conf
    
    try:
        with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
            in_webif = False
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    in_webif = (line.lower() == "[webif]")
                    continue
                if in_webif and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip().lower()
                    val = val.split(";")[0].split("#")[0].strip() # Strip comments
                    if key == "httpport":
                        conf["port"] = val
                    elif key == "httpuser":
                        conf["user"] = val
                    elif key == "httppwd":
                        conf["pwd"] = val
    except Exception as e:
        print("[ServerEagleSat] Error parsing oscam.conf:", e)
    return conf

def get_all_readers_from_config():
    """Parses local oscam.server file to pull all defined readers names."""
    readers = []
    server_path = os.path.join(find_oscam_dir(), "oscam.server")
    if not os.path.exists(server_path):
        return readers
        
    try:
        with open(server_path, "r", encoding="utf-8", errors="ignore") as f:
            current_label = None
            for line in f:
                line = line.strip()
                if line.lower() == "[reader]":
                    current_label = None
                elif "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip().lower() == "label":
                        current_label = val.split(";")[0].split("#")[0].strip()
                        if current_label and current_label not in readers:
                            readers.append(current_label)
    except Exception as e:
        print("[ServerEagleSat] Error parsing oscam.server:", e)
    return readers

def get_reader_credentials(label_name):
    """Parses local oscam.server configuration block to extract connection specs."""
    creds = {
        "file": "-",
        "label": label_name,
        "url": "-",
        "port": "-",
        "user": "-",
        "pass": "-"
    }
    
    server_dir = find_oscam_dir()
    server_file_path = os.path.join(server_dir, "oscam.server")
    creds["file"] = server_file_path
    
    if not os.path.exists(server_file_path):
        return creds
        
    try:
        with open(server_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Case-insensitive configuration block regex parser matching reader arrays
        pattern = r"(?i)\[reader\][\s\S]*?label\s*=\s*" + re.escape(label_name) + r"\b[\s\S]*?(?=\[reader\]|$)"
        match = re.search(pattern, content)
        
        if match:
            block_text = match.group(0)
            for line in block_text.splitlines():
                line = line.strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip().lower()
                    val = val.split(";")[0].split("#")[0].strip() # Clean out inline comment structures
                    
                    if key == "device":
                        if "," in val:
                            url_part, port_part = val.split(",", 1)
                            creds["url"] = url_part.strip()
                            creds["port"] = port_part.strip()
                        else:
                            creds["url"] = val
                    elif key == "user":
                        creds["user"] = val
                    elif key == "password":
                        creds["pass"] = val
    except Exception as e:
        print("[ServerEagleSat] Error isolating config credentials parsing arrays:", e)
        
    return creds

def get_oscam_readers(ip, port, user, pwd):
    """
    Fetches real-time runtime readers states from the active OSCam WebIF.
    Uses a clean XML parse layout matching the pattern structure of your reference sample.
    """
    active_readers = []
    
    auth_header = None
    if user and pwd:
        credentials = f"{user}:{pwd}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8").strip()
        auth_header = "Basic " + encoded

    url_xml = f"http://{ip}:{port}/oscamapi.html?part=status"
    try:
        req_xml = urllib.request.Request(url_xml, method="GET")
        if auth_header:
            req_xml.add_header("Authorization", auth_header)
            
        with urllib.request.urlopen(req_xml, timeout=5) as resp:
            xml_data = resp.read().decode("utf-8", errors="ignore")
            root = ET.fromstring(xml_data)
            
            # Fetch both physical local readers (r) and proxy network readers (p)
            for client in root.findall(".//client[@type='r']") + root.findall(".//client[@type='p']"):
                name = client.get("name", "Unknown").strip()
                protocol = client.get("protocol", "-").strip()
                au = client.get("au", "-").strip()
                
                connection = client.find("connection")
                status = connection.text.strip() if connection is not None and connection.text else "Unknown"
                
                times = client.find("times")
                idle = times.get("idle", "-") if times is not None else "-"
                
                # Strip web display suffixes safely like "MyReader (p)" -> "MyReader"
                clean_name = name.split(" (")[0].strip()
                
                active_readers.append({
                    "name": clean_name,
                    "protocol": protocol,
                    "au": au,
                    "idle": idle,
                    "status": status
                })
            if active_readers:
                return active_readers
    except Exception as e:
        print("[ServerEagleSat] XML Engine Error, using regex fallbacks:", e)

    # -----------------------------------------------------------------
    # REGEX FALLBACK: Runs if ElementTree parsing fails completely
    # -----------------------------------------------------------------
    try:
        url_html = f"http://{ip}:{port}/status.html"
        req_html = urllib.request.Request(url_html, method="GET")
        if auth_header:
            req_html.add_header("Authorization", auth_header)
            
        with urllib.request.urlopen(req_html, timeout=4) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            rows = re.findall(r'<tr[^>]*class=["\'](?:r|p|readers)["\'][^>]*>.*?</tr>', html, re.DOTALL | re.IGNORECASE)
            
            for row in rows:
                columns = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if not columns or len(columns) < 5:
                    continue
                
                name_match = re.search(r'label=[^>]*>([^<]+)</a>', columns[0], re.IGNORECASE)
                if not name_match:
                    name_match = re.search(r'>([^<]+)</a>', columns[0], re.IGNORECASE)
                
                name = name_match.group(1).strip() if name_match else re.sub(r'<[^>]*>', '', columns[0]).strip()
                clean_name = name.split(" (")[0].strip()
                
                if not clean_name or any(x in clean_name.lower() for x in ("emulator", "anonymous", "all readers", "totals")):
                    continue
                    
                protocol = re.sub(r'<[^>]*>', '', columns[1]).strip()
                au = re.sub(r'<[^>]*>', '', columns[2]).strip()
                idle = re.sub(r'<[^>]*>', '', columns[3]).strip()
                status = re.sub(r'<[^>]*>', '', columns[4]).strip()
                
                if "<a" in columns[4]:
                    status_link = re.search(r'>([^<]+)</a>', columns[4], re.IGNORECASE)
                    if status_link:
                        status = status_link.group(1).strip()

                active_readers.append({
                    "name": clean_name, "protocol": protocol, "au": au, "idle": idle, "status": status
                })
    except Exception as e:
        print("[ServerEagleSat] Local parsing block error fallback stack:", e)

    return active_readers


# =========================================================================
#                         MAIN EAGLE2 SCREEN CLASS
# =========================================================================
class Eagle2(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle2-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - OSCam Status Panel"))
        self.indexpos = None
        
        self.system_info = SystemInfo()

        # REMOTE SHORTCUT HANDLERS MAPPINGS
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.toggleReaderAction,
                "cancel": self.exit,
                "back": self.exit,
                "info": self.infoKey,
                "red": self.deleteReaderConfirm,
                "green": self.restartSoftcamAction,
                "yellow": self.showReaderCredentialsAction,
                "blue": self.toggleReaderAction,
            }
        )

        # DECORATIVE FRAME LABELS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))
        self["key_red"] = Label("Delete Reader")     
        self["key_green"] = Label("Restart Softcam")
        self["key_yellow"] = Label("Show Credentials")
        self["key_blue"] = Label("Toggle Reader")

        # RENDER LIST MANAGEMENT COMPONENT
        self.list = []
        self["menu"] = List(self.list)

        # TEXT BOX SPECIFICATIONS LABELS MAPPINGS
        labels = ["MemoryLabel", "SwapLabel", "FlashLabel", "gstreamerLabel",
                  "pythonLabel", "CPULabel", "ipLabel", "macLabel",
                  "HardwareLabel", "ImageLabel", "KernelLabel",
                  "EnigmaVersionLabel", "driverLabel", "internetLabel"]
        text = [_("Ram:"), _("Swap:"), _("Flash:"), _("Gst:"), _("Py:"), _("Prc:"),
                _("IP address:"), _("Mac Address:"), _("Hdw:"), _("Img:"), _("Krn:"), _("Upd:"), _("Drv:"), _("Internet:")]
        for l, t in zip(labels, text):
            self[l] = StaticText(t)

        # VALUES DYNAMIC STORAGE DEFINITIONS
        values = ["memTotal", "swapTotal", "flashTotal", "device", "gstreamer", "python",
                  "Hardware", "Image", "CPU", "Kernel", "ipInfo", "macInfo",
                  "EnigmaVersion", "driver", "internet"]
        for v in values:
            self[v] = StaticText()

        self["Version"] = Label(_("V" + Version))
        self["Panel"] = Label(_(Panel))
        self["boxicon"] = Pixmap()

        # Automated Background loop (Runs every 10 seconds)
        self.refresh_timer = eTimer()
        self.refresh_timer.callback.append(self.refreshOscamStatus)

        # Separate single-shot instance container to avoid execution lifecycle crashes
        self.post_restart_timer = None
        self.post_restart_conn = None

        self.onLayoutFinish.append(self.loadScreenData)

    def loadScreenData(self):
        """Pre-populates basic infrastructure telemetry strings."""
        self.loadBoxIcon()

        # Update Hardware Information Fields
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

        # Update Network Information Fields
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

        # Fire initial read cycle data populate and enable loops
        self.refreshOscamStatus()
        self.refresh_timer.start(10000, False)

    def refreshOscamStatus(self):
        """Assembles data arrays to populate the target visual content template rows."""
        self.list = []
        unsorted_readers = []
        try:
            conf = read_oscam_conf()
            active_readers = get_oscam_readers(
                ip=conf["ip"],
                port=conf["port"],
                user=conf["user"],
                pwd=conf["pwd"]
            )
            
            # Map using lower-case normalized keys to avoid string match dropouts
            active_map = {r['name'].lower(): r for r in active_readers}
            all_readers = get_all_readers_from_config()

            if not all_readers:
                self.list.append((_("No Readers Found"), "", _("Please check local config files inside /etc/tuxbox/"), None))
            else:
                for rname in all_readers:
                    rname_lower = rname.lower()
                    if rname_lower in active_map:
                        reader = active_map[rname_lower]
                        status = reader.get('status', 'OFF')
                        au = reader.get('au', '-')
                        idle = reader.get('idle', '-')
                        protocol = reader.get('protocol', '-')
                    else:
                        status = "OFF"
                        au = idle = protocol = "-"

                    status_lower = status.lower().strip()
                    
                    # ---------------------------------------------------------
                    # BULLETPROOF SUBSTRING STATUS MATCHING & PRIORITY ENGINE
                    # ---------------------------------------------------------
                    if not status_lower or any(x in status_lower for x in ("off", "disable", "down", "stopped")):
                        icon_name = "red.png"
                        priority = 3
                    elif any(x in status_lower for x in ("connected", "cardok", "ok", "active")) or (":" in status_lower and ("ok" in status_lower or "connected" in status_lower or len(status_lower) > 7)):
                        icon_name = "green.png"
                        priority = 1
                    elif any(x in status_lower for x in ("needinit", "unknown", "init", "error")):
                        icon_name = "yellow.png"
                        priority = 2
                    else:
                        if ":" in status_lower:
                            icon_name = "green.png"
                            priority = 1
                        else:
                            icon_name = "red.png"
                            priority = 3
                    
                    icon_path = os.path.join(resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/"), icon_name)
                    pixmap = LoadPixmap(path=icon_path) if fileExists(icon_path) else None

                    details_text = f"Status: {status} | AU: {au} | Idle: {idle} | Prot: {protocol}"
                    
                    # Stash them into a temporary structure along with their weight priority
                    unsorted_readers.append({
                        "priority": priority,
                        "row_data": (rname, "", details_text, pixmap)
                    })

                # Sort logic based on priority key (1 comes first, then 2, then 3)
                unsorted_readers.sort(key=lambda item: item["priority"])
                
                # Rebuild the final interface display list
                for item in unsorted_readers:
                    self.list.append(item["row_data"])

        except Exception as e:
            print("[ServerEagleSat] OSCam Core Parsing Error Interception:", e)
            self.list.append((_("Connection Error"), "", str(e), None))

        self["menu"].setList(self.list)

    def toggleReaderAction(self):
        """Fires the toggle command for the selected list row."""
        current_selection = self["menu"].getCurrent()
        if not current_selection or len(current_selection) < 3:
            self.session.open(MessageBox, _("No reader selected!"), MessageBox.TYPE_ERROR, timeout=5)
            return

        clean_name = current_selection[0]
        if clean_name in [_("No Readers Found"), _("Connection Error")]:
            return

        details_str = current_selection[2]
        current_status = "off"
        if "Status: " in details_str:
            current_status = details_str.split("Status: ")[1].split(" |")[0].strip().lower()

        # Engine mapping logic checks text patterns to toggle target values safely
        should_enable = any(x in current_status for x in ("off", "error", "disable", "down", "stop", "unknown", "needinit", "init"))
        action = "enable" if should_enable else "disable"

        try:
            conf = read_oscam_conf()
            encoded_reader_name = urllib.parse.quote(clean_name)
            url = f"http://{conf['ip']}:{conf['port']}/readers.html?label={encoded_reader_name}&action={action}"

            req = urllib.request.Request(url, method="GET")

            if conf.get("user") and conf.get("pwd"):
                credentials = f"{conf['user']}:{conf['pwd']}"
                encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8").strip()
                req.add_header("Authorization", "Basic " + encoded)

            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.getcode() == 200:
                    msg = _("Reader '%s' set successfully to %s.") % (clean_name, "ON" if action == "enable" else "OFF")
                    self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=3)
                    self.refreshOscamStatus() 
                else:
                    raise Exception(f"HTTP {resp.getcode()}")

        except Exception as e:
            self.session.open(MessageBox, _("Error changing reader state:\n%s") % str(e), MessageBox.TYPE_ERROR, timeout=5)

    # -----------------------------------------------------------------
    #                    RED BUTTON REMOVE FUNCTIONALITY
    # -----------------------------------------------------------------
    def deleteReaderConfirm(self):
        """Asks for confirmation before wiping out the chosen reader profile."""
        current_selection = self["menu"].getCurrent()
        if not current_selection or len(current_selection) < 3:
            return

        self.selected_reader_name = current_selection[0]
        if self.selected_reader_name in [_("No Readers Found"), _("Connection Error")]:
            return

        msg = _("Are you sure you want to permanently delete reader:\n'%s'?") % self.selected_reader_name
        self.session.openWithCallback(self.deleteReaderAction, MessageBox, msg, MessageBox.TYPE_YESNO)

    def deleteReaderAction(self, answer):
        """Processes the actual delete script upon prompt approval."""
        if not answer:
            return

        clean_name = self.selected_reader_name
        try:
            conf = read_oscam_conf()
            encoded_reader_name = urllib.parse.quote(clean_name)
            
            # 1. Dispatch Delete Call directly into OSCam Web Interface Engine
            url = f"http://{conf['ip']}:{conf['port']}/readers.html?label={encoded_reader_name}&action=delete"
            req = urllib.request.Request(url, method="GET")

            if conf.get("user") and conf.get("pwd"):
                credentials = f"{conf['user']}:{conf['pwd']}"
                encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8").strip()
                req.add_header("Authorization", "Basic " + encoded)

            # Fire HTTP Web Request
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    pass
            except Exception as http_err:
                print("[ServerEagleSat] WebIF deletion call status warning:", http_err)

            # 2. Local fallback / direct block removal inside physical oscam.server file
            server_file_path = os.path.join(find_oscam_dir(), "oscam.server")
            if os.path.exists(server_file_path):
                with open(server_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Regex pattern isolates the targeted reader configuration block precisely
                pattern = r"(?i)\[reader\][\s\S]*?label\s*=\s*" + re.escape(clean_name) + r"\b[\s\S]*?(?=\[reader\]|$)"
                modified_content = re.sub(pattern, "", content)
                
                # Write back the polished data stream clean of dead configs
                with open(server_file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content.strip() + "\n")

            self.session.open(MessageBox, _("Reader '%s' removed successfully.") % clean_name, MessageBox.TYPE_INFO, timeout=3)
            self.refreshOscamStatus()

        except Exception as e:
            self.session.open(MessageBox, _("Error trying to drop reader:\n%s") % str(e), MessageBox.TYPE_ERROR, timeout=5)

    # -----------------------------------------------------------------
    #               YELLOW BUTTON CREDENTIALS FUNCTIONALITY
    # -----------------------------------------------------------------
    def showReaderCredentialsAction(self):
        """Retrieves and pops up localized physical config attributes from oscam.server."""
        current_selection = self["menu"].getCurrent()
        if not current_selection or len(current_selection) < 3:
            return

        label_name = current_selection[0]
        if label_name in [_("No Readers Found"), _("Connection Error")]:
            return

        # Query parsing block to extract local data parameters 
        creds = get_reader_credentials(label_name)

        # Build message container layout properties exactly matching screen style specifications
        msg = (
            _("File path: %s\n") % creds["file"] +
            _("Label: %s\n") % creds["label"] +
            _("Url: %s\n") % creds["url"] +
            _("Port: %s\n") % creds["port"] +
            _("User: %s\n") % creds["user"] +
            _("Pass: %s") % creds["pass"]
        )
        
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    # -----------------------------------------------------------------
    #                 GREEN BUTTON SOFTCAM RESTART ACTION
    # -----------------------------------------------------------------
    def restartSoftcamAction(self):
        """Invokes the multi-image fallback restart mechanism from Helpers.py."""
        success, message = restart_softcam_services()
        if success:
            self.session.open(MessageBox, _(message), MessageBox.TYPE_INFO, timeout=4)
            
            # Stop any existing single-shot instance safely
            if self.post_restart_timer is not None:
                try:
                    self.post_restart_timer.stop()
                except Exception:
                    pass
            
            # Instantiate a clean dedicated timer instance
            self.post_restart_timer = eTimer()
            
            # Universal connection strategy wrapper with strict exception fallbacks
            connected = False
            if hasattr(self.post_restart_timer, "timeout"):
                try:
                    self.post_restart_conn = self.post_restart_timer.timeout.connect(self.refreshOscamStatus)
                    connected = True
                except Exception:
                    connected = False

            if not connected:
                try:
                    self.post_restart_timer.callback.append(self.refreshOscamStatus)
                except Exception as e:
                    print("[ServerEagleSat] Failed to bind background recovery timer:", e)

            # Fire execution window safely. Passing True enforces single-shot execution rules.
            try:
                self.post_restart_timer.start(2000, True)
            except Exception as e:
                print("[ServerEagleSat] Error starting timer instance execution loop:", e)
        else:
            self.session.open(MessageBox, _(message), MessageBox.TYPE_ERROR, timeout=6)

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
        pass

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.refresh_timer.stop() 
        if self.post_restart_timer is not None:
            self.post_restart_timer.stop()
        self.close()

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])