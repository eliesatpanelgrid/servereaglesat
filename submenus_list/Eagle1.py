# -*- coding: utf-8 -*-
import os
from enigma import getDesktop

# Import direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import standalone network helpers
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet
from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console

from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ConfigList import ConfigListScreen
from Components.config import (
    ConfigText,
    ConfigSelection,
    ConfigInteger,
    getConfigListEntry
)

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel

PANEL_DIRS = [
    "/media/hdd/ServerEagleSat",
    "/media/usb/ServerEagleSat",
    "/media/mmc/ServerEagleSat"
]

class Eagle1(Screen, ConfigListScreen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Read layout template file exactly like your original setup
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle1-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Add Reader"))
        self.panel_dir = self.detect_panel_dir()
        
        # Safe storage path initialization
        if not os.path.exists(self.panel_dir):
            try:
                os.makedirs(self.panel_dir)
            except:
                pass
        
        sub_file = os.path.join(self.panel_dir, "subscription.txt")
        if not os.path.exists(sub_file):
            try:
                with open(sub_file, "w") as f:
                    f.write("")
            except:
                pass

        self.system_info = SystemInfo()

        # CONFIG ENGINE CORE FIELD DEFINITIONS
        self.label_choice = ConfigSelection(default="ServerEagle", choices=[("ServerEagle", "ServerEagle"), ("ElieSat", "ElieSat"), ("Custom", "Custom")])
        self.label_custom = ConfigText(default="server_name", fixed_size=False)
        self.label_custom.useKeyboard = False
        
        self.status = ConfigSelection(default="enabled", choices=[("enabled", "Enabled"), ("disabled", "Disabled")])
        self.protocol = ConfigSelection(default="cccam", choices=[("cccam", "CCcam"), ("newcamd", "NewCamd"), ("mgcamd", "MgCamd")])
        self.host = ConfigText(default="tv8k.cc", fixed_size=False)
        self.port = ConfigInteger(default=22222, limits=(1, 99999))
        self.user = ConfigText(default="User", fixed_size=False)
        self.passw = ConfigText(default="Pass", fixed_size=False)
        self.inactivitytimeout = ConfigInteger(default=30, limits=(1, 99))
        self.group = ConfigInteger(default=1, limits=(0, 99))
        
        # CCcam Specific Fields
        self.disablecrccws = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.cccamversion = ConfigSelection(default="2.0.11", choices=[(v, v) for v in ["2.0.11", "2.1.1", "2.1.2", "2.1.3", "2.1.4", "2.2.0", "2.2.1", "2.3.0", "2.3.1", "2.3.2"]])
        self.cccwantemu = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.ccckeepalive = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.audisabled = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        
        # Newcamd/Mgcamd Specific Fields
        self.key = ConfigText(default="0102030405060708091011121314", fixed_size=False)
        self.disableserverfilter = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.connectoninit = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])

        for element in [self.host, self.user, self.passw, self.cccamversion, self.key, self.label_custom]:
            element.useKeyboard = False

        # Load historical settings safely prior to population
        self.load_last_reader_to_config()

        # Initialize ConfigListScreen with an empty list base
        ConfigListScreen.__init__(self, [], session=session)
        
        # Build initial components list entries
        self.update_fields()

        # Field Notifiers for adaptive visibility shifts
        self.label_choice.addNotifier(self.on_config_change, initial_call=False)
        self.protocol.addNotifier(self.on_config_change, initial_call=False)

        # ACTIONS MAP DATA - Fully integrated ConfigListScreen behavior
        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.keyOK,               # Interact with individual fields
                "cancel": self.exit,
                "back": self.exit,
                "green": self.keyGreenSave,     # GREEN button saves changes
                "red": self.sharing,            # RED button runs target file check
                "yellow": self.grid,            # YELLOW shows last backup reader
                "blue": self.scriptslist,       # BLUE restores last reader backup to systems
                "info": self.infoKey,
            }
        )

        # UI SIDE BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # INITIALIZE SYSTEM METRIC CONFIG LABELS
        labels = ["MemoryLabel", "SwapLabel", "FlashLabel", "gstreamerLabel",
                  "pythonLabel", "CPULabel", "ipLabel", "macLabel",
                  "HardwareLabel", "ImageLabel", "KernelLabel",
                  "EnigmaVersionLabel", "driverLabel", "internetLabel"]
        text = [_("Ram:"), _("Swap:"), _("Flash:"), _("Gst:"), _("Py:"), _("Prc:"),
                _("IP address:"), _("Mac Address:"), _("Hdw:"), _("Img:"), _("Krn:"), _("Upd:"), _("Drv:"), _("Internet:")]
        for l, t in zip(labels, text):
            self[l] = StaticText(t)

        # INITIALIZE SYSTEM METRIC VALUES CONTAINERS
        values = ["memTotal", "swapTotal", "flashTotal", "device", "gstreamer", "python",
                  "Hardware", "Image", "CPU", "Kernel", "ipInfo", "macInfo",
                  "EnigmaVersion", "driver", "internet"]
        for v in values:
            self[v] = StaticText()

        self["Version"] = Label(_("V" + Version))
        self["Panel"] = Label(_(Panel))
        self["boxicon"] = Pixmap()

        self.onLayoutFinish.append(self.loadScreenData)

    def parse_subscription_file(self):
        """Helper to safely read subscription.txt and return a list of reader dictionaries."""
        file_path = os.path.join(self.panel_dir, "subscription.txt")
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r") as f:
                content = f.read()
            blocks = content.split("[reader]")
            readers = []
            for b in blocks:
                if not b.strip():
                    continue
                info = {}
                for line in b.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
                readers.append(info)
            return readers
        except Exception as e:
            print("[ServerEagleSat] Error parsing subscription historical logs:", e)
            return []

    def load_last_reader_to_config(self):
        """Reads local subscription configuration text history cleanly into state variables."""
        readers = self.parse_subscription_file()
        if not readers:
            return
        try:
            last = readers[-1]
            if "protocol" in last:
                p_val = last["protocol"].lower()
                if p_val in ["cccam", "newcamd", "mgcamd"]:
                    self.protocol.value = p_val
            if "device" in last and "," in last["device"]:
                h_val, p_val = last["device"].split(",", 1)
                self.host.value = h_val.strip()
                try:
                    self.port.value = int(p_val.strip())
                except:
                    pass
            if "user" in last:
                self.user.value = last["user"]
            if "password" in last:
                self.passw.value = last["password"]
            if "enable" in last:
                self.status.value = "enabled" if last["enable"] == "1" else "disabled"
            if "group" in last:
                try:
                    self.group.value = int(last["group"])
                except:
                    pass
            if "disablecrccws" in last and last["disablecrccws"] in ["0", "1"]:
                self.disablecrccws.value = last["disablecrccws"]
            if "inactivitytimeout" in last:
                try:
                    self.inactivitytimeout.value = int(last["inactivitytimeout"])
                except:
                    pass
            if "cccversion" in last:
                self.cccamversion.value = last["cccversion"]
            if "cccwantemu" in last and last["cccwantemu"] in ["0", "1"]:
                self.cccwantemu.value = last["cccwantemu"]
            if "ccckeepalive" in last and last["ccckeepalive"] in ["0", "1"]:
                self.ccckeepalive.value = last["ccckeepalive"]
            if "audisabled" in last and last["audisabled"] in ["0", "1"]:
                self.audisabled.value = last["audisabled"]
            if "key" in last:
                self.key.value = last["key"]
            if "disableserverfilter" in last and last["disableserverfilter"] in ["0", "1"]:
                self.disableserverfilter.value = last["disableserverfilter"]
            if "connectoninit" in last and last["connectoninit"] in ["0", "1"]:
                self.connectoninit.value = last["connectoninit"]
            if "label" in last:
                lbl = last["label"]
                if lbl in ["ServerEagle", "ElieSat"]:
                    self.label_choice.value = lbl
                else:
                    self.label_choice.value = "Custom"
                    self.label_custom.value = lbl
        except Exception as e:
            print("[ServerEagleSat] Error Restoring History Configuration Setup:", e)

    def update_fields(self):
        """Constructs configuration lists using standard components API."""
        cfg_list = [
            getConfigListEntry("Label:", self.label_choice),
        ]
        if self.label_choice.value == "Custom":
            cfg_list.append(getConfigListEntry("Custom Name:", self.label_custom))

        cfg_list += [
            getConfigListEntry("Status:", self.status),
            getConfigListEntry("Protocol:", self.protocol),
            getConfigListEntry("Host:", self.host),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.user),
            getConfigListEntry("Password:", self.passw),
            getConfigListEntry("Inactivity Timeout:", self.inactivitytimeout),
            getConfigListEntry("Group:", self.group),
        ]

        proto = self.protocol.value.lower()
        if proto == "cccam":
            cfg_list += [
                getConfigListEntry("Disable CRC/CWS:", self.disablecrccws),
                getConfigListEntry("CCcam Version:", self.cccamversion),
                getConfigListEntry("Want Emu:", self.cccwantemu),
                getConfigListEntry("Keep Alive:", self.ccckeepalive),
                getConfigListEntry("Audio Disabled:", self.audisabled),
            ]
        elif proto in ["newcamd", "mgcamd"]:
            cfg_list += [
                getConfigListEntry("Key:", self.key),
                getConfigListEntry("Disable Server Filter:", self.disableserverfilter),
                getConfigListEntry("Connect on Init:", self.connectoninit),
            ]

        # Feeds the correct config structures directly back to the system config key handler
        self["config"].l.setList(cfg_list)

    def on_config_change(self, cfg=None):
        """Handles screen adjustments transparently without losing selection index tracking."""
        self.update_fields()

    def keyGreenSave(self):
        """Executes the data save routine and performs softcam system restarts."""
        self.add_reader()
        self.restartSoftcam()

    def sharing(self):
        """Triggered by the RED button shortcut: Check available target paths."""
        self.checkAvailableSharingConfigs()

    def checkAvailableSharingConfigs(self):
        """Scans filesystem locations and prints active/missing configuration targets to the screen."""
        targets = [
            os.path.join(self.panel_dir, "subscription.txt"),
            "/etc/tuxbox/config/ncam.server",
            "/etc/tuxbox/config/ncam-icam/ncam.server",
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/oscam/oscam.server",
            "/etc/tuxbox/config/oscam-emu/oscam.server",
            "/etc/tuxbox/config/oscam-master/oscam.server",
            "/etc/tuxbox/config/oscam-smod/oscam.server",
            "/etc/tuxbox/config/oscamicamnew/oscam.server",
            "/etc/tuxbox/config/oscamicamall/oscam.server",
            "/etc/tuxbox/config/oscam-icam/oscam.server"
        ]

        found_files = []
        missing_files = []

        for path in targets:
            if os.path.exists(path):
                found_files.append(path)
            else:
                missing_files.append(path)

        # Construct diagnostic readout presentation text
        message = _("--- Active Sharing Config Files Found ---\n")
        if found_files:
            message += "\n".join([f"✔ {p}" for p in found_files])
        else:
            message += _("No active reader profiles discovered.\n")

        message += _("\n\n--- Missing Config Locations ---\n")
        if missing_files:
            message += "\n".join([f"❌ {p}" for p in missing_files])
        else:
            message += _("None.")

        # Fire standard scrolling information overlay alert cleanly
        self.session.open(MessageBox, message, MessageBox.TYPE_INFO)

    def build_entry_string(self, label, enable, protocol, host, port, user, password, extra_dict=None):
        """Unified string template writer for generation optimization."""
        entry = (
            "[reader]\n"
            f"label = {label}\n"
            f"enable = {enable}\n"
            f"protocol = {protocol}\n"
            f"device = {host},{port}\n"
            f"user = {user}\n"
            f"password = {password}\n"
        )
        if extra_dict:
            for k, v in extra_dict.items():
                if k not in ["label", "enable", "protocol", "device", "user", "password"]:
                    entry += f"{k} = {v}\n"
        entry = entry.strip() + "\n\n"
        return entry

    def add_reader(self):
        """Appends the formatted screen configuration entry across your active server file paths."""
        proto = self.protocol.value.lower()
        lbl_val = self.label_custom.value if self.label_choice.value == "Custom" else self.label_choice.value
        enable_val = "1" if self.status.value == "enabled" else "0"

        extra = {}
        if proto == "cccam":
            extra = {
                "inactivitytimeout": self.inactivitytimeout.value,
                "group": self.group.value,
                "disablecrccws": self.disablecrccws.value,
                "cccversion": self.cccamversion.value,
                "cccwantemu": self.cccwantemu.value,
                "ccckeepalive": self.ccckeepalive.value,
                "audisabled": self.audisabled.value
            }
        else:
            extra = {
                "key": self.key.value,
                "disableserverfilter": self.disableserverfilter.value,
                "connectoninit": self.connectoninit.value,
                "group": self.group.value,
                "disablecrccws": self.disablecrccws.value
            }

        entry = self.build_entry_string(lbl_val, enable_val, proto, self.host.value, self.port.value, self.user.value, self.passw.value, extra)
        self.write_to_targets(entry, self.host.value, self.port.value, self.user.value, self.passw.value)

    def write_to_targets(self, entry_str, host, port, user, password):
        """Appends built blocks into config destinations dynamically, validating duplicates."""
        targets = [
            os.path.join(self.panel_dir, "subscription.txt"),
            "/etc/tuxbox/config/ncam.server",
            "/etc/tuxbox/config/ncam-icam/ncam.server",
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/oscam/oscam.server",
            "/etc/tuxbox/config/oscam-emu/oscam.server",
            "/etc/tuxbox/config/oscam-master/oscam.server",
            "/etc/tuxbox/config/oscam-smod/oscam.server",
            "/etc/tuxbox/config/oscamicamnew/oscam.server",
            "/etc/tuxbox/config/oscamicamall/oscam.server",
            "/etc/tuxbox/config/oscam-icam/oscam.server"
        ]

        summary = ""
        for path in targets:
            if "subscription.txt" in path and not os.path.exists(self.panel_dir):
                try:
                    os.makedirs(self.panel_dir)
                except:
                    continue

            if not os.path.exists(path):
                continue

            duplicated = False
            try:
                with open(path, "r") as fr:
                    content = fr.read()
                blocks = content.split("[reader]")
                match_str = f"{host},{port}"
                for b in blocks:
                    if match_str in b and user in b and password in b:
                        duplicated = True
                        break
            except:
                pass

            if duplicated:
                summary += f"Already exists in: {path}\n"
            else:
                try:
                    with open(path, "a") as fw:
                        with open(path, "r") as fr:
                            curr = fr.read()
                        if not curr.endswith("\n\n") and len(curr.strip()) > 0:
                            fw.write("\n")
                        fw.write(entry_str)
                    summary += f"Successfully written: {path}\n"
                except Exception as ex:
                    summary += f"Write failure {path}: {str(ex)}\n"

        if not summary:
            summary = "No eligible active softcam config files discovered."
        self.session.open(MessageBox, summary, MessageBox.TYPE_INFO, timeout=6)

    def restartSoftcam(self):
        """Terminates and restarts running card sharing emulation components smoothly."""
        import subprocess
        try:
            init_atv = "/etc/init.d/softcam"
            init_pli = "/usr/script/softcam.sh"

            use_systemd = False
            use_atv = False
            use_pli = False

            if os.path.exists(init_atv):
                use_atv = True
            elif os.path.exists(init_pli):
                use_pli = True
            else:
                use_systemd = True

            subprocess.call("killall -15 oscam ncam CCcam 2>/dev/null", shell=True)
            subprocess.call("sleep 2", shell=True)

            if use_atv:
                subprocess.call("/etc/init.d/softcam stop", shell=True)
            elif use_pli:
                subprocess.call("/usr/script/softcam.sh stop", shell=True)
            elif use_systemd:
                subprocess.call("systemctl stop softcam 2>/dev/null", shell=True)

            subprocess.call("sleep 2", shell=True)

            if use_atv:
                subprocess.call("/etc/init.d/softcam start", shell=True)
            elif use_pli:
                subprocess.call("/usr/script/softcam.sh start", shell=True)
            elif use_systemd:
                subprocess.call("systemctl start softcam 2>/dev/null", shell=True)

            self.session.open(MessageBox, "Softcam service configuration updated successfully.", MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            self.session.open(MessageBox, f"Softcam control request failed:\n{str(e)}", MessageBox.TYPE_ERROR, timeout=4)

    def loadScreenData(self):
        """Fires safely after layout finishes rendering to paint all fields simultaneously."""
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

    def detect_panel_dir(self):
        for folder in PANEL_DIRS:
            if os.path.exists(folder) or os.path.exists(os.path.join(folder, "panel_dir.cfg")):
                return folder
        if os.path.exists("/media/hdd"):
            return "/media/hdd/ServerEagleSat"
        elif os.path.exists("/media/usb"):
            return "/media/usb/ServerEagleSat"
        elif os.path.exists("/media/mmc"):
            return "/media/mmc/ServerEagleSat"
        return "/media/hdd/ServerEagleSat"

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def grid(self):
        """YELLOW button: Show information about the last backup reader entry inside subscription.txt."""
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("No backup readers found in history file."), MessageBox.TYPE_INFO, timeout=5)
            return

        last = readers[-1]
        msg = _("--- Last Saved Reader Backup Data ---\n\n")
        for key, value in last.items():
            msg += f"• {key.capitalize()}: {value}\n"
        
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def scriptslist(self):
        """BLUE button: Restore the last backup reader from subscription.txt directly back to live config setups."""
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("Restoration canceled: No backup dataset available."), MessageBox.TYPE_ERROR, timeout=5)
            return

        last = readers[-1]
        
        lbl_val = last.get("label", "Backup_Reader")
        enable_val = last.get("enable", "1")
        proto = last.get("protocol", "cccam").lower()
        
        device_str = last.get("device", "localhost,22222")
        if "," in device_str:
            host_val, port_val = device_str.split(",", 1)
        else:
            host_val, port_val = device_str, "22222"
            
        user_val = last.get("user", "User")
        pass_val = last.get("password", "Pass")

        # Build entry text containing all original extra keys loaded directly from data block
        entry = self.build_entry_string(lbl_val, enable_val, proto, host_val.strip(), port_val.strip(), user_val, pass_val, last)
        
        # Write to all configurations safely and trigger emulator system reload sequences
        self.write_to_targets(entry, host_val.strip(), port_val.strip(), user_val, pass_val)
        self.restartSoftcam()

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])
