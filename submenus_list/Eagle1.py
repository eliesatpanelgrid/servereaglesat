# -*- coding: utf-8 -*-
import os
from enigma import getDesktop
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet, restart_softcam_services
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

        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/skins_list/eagle1-fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1800,980' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Add Reader"))
        self.panel_dir = self.detect_panel_dir()
        
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

        self.label_choice = ConfigSelection(default="ServerEagle", choices=[("ServerEagle", "ServerEagle"), ("ElieSat", "ElieSat"), ("Custom", "Custom")])
        self.label_custom = ConfigText(default="server_name", fixed_size=False)
        self.label_custom.useKeyboard = True
        
        self.status = ConfigSelection(default="enabled", choices=[("enabled", "Enabled"), ("disabled", "Disabled")])
        self.protocol = ConfigSelection(default="cccam", choices=[("cccam", "CCcam"), ("newcamd", "NewCamd"), ("mgcamd", "MgCamd")])
        self.host = ConfigText(default="tv8k.cc", fixed_size=False)
        self.host.useKeyboard = True
        self.port = ConfigInteger(default=22222, limits=(1, 99999))
        self.user = ConfigText(default="User", fixed_size=False)
        self.user.useKeyboard = True
        self.passw = ConfigText(default="Pass", fixed_size=False)
        self.passw.useKeyboard = True
        self.inactivitytimeout = ConfigInteger(default=30, limits=(1, 99))
        self.group = ConfigInteger(default=1, limits=(0, 99))
        
        self.disablecrccws = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.cccamversion = ConfigSelection(default="2.0.11", choices=[(v, v) for v in ["2.0.11", "2.1.1", "2.1.2", "2.1.3", "2.1.4", "2.2.0", "2.2.1", "2.3.0", "2.3.1", "2.3.2"]])
        self.cccwantemu = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.ccckeepalive = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.audisabled = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        
        self.key = ConfigText(default="0102030405060708091011121314", fixed_size=False)
        self.key.useKeyboard = True
        self.disableserverfilter = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.connectoninit = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])

        self.load_last_reader_to_config()

        ConfigListScreen.__init__(self, [], session=session)
        
        self.update_fields()

        self.label_choice.addNotifier(self.on_config_change, initial_call=False)
        self.protocol.addNotifier(self.on_config_change, initial_call=False)

        self["NumberActions"] = NumberActionMap(["NumberActions"], {'0': self.keyNumberGlobal})
        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.keyOK,
                "cancel": self.exit,
                "back": self.exit,
                "green": self.keyGreenSave,
                "red": self.sharing,
                "yellow": self.grid,
                "blue": self.scriptslist,
                "info": self.infoKey,
            }
        )

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        labels = ["MemoryLabel", "SwapLabel", "FlashLabel", "gstreamerLabel",
                  "pythonLabel", "CPULabel", "ipLabel", "macLabel",
                  "HardwareLabel", "ImageLabel", "KernelLabel",
                  "EnigmaVersionLabel", "driverLabel", "internetLabel"]
        text = [_("Ram:"), _("Swap:"), _("Flash:"), _("Gst:"), _("Py:"), _("Prc:"),
                _("IP address:"), _("Mac Address:"), _("Hdw:"), _("Img:"), _("Krn:"), _("Upd:"), _("Drv:"), _("Internet:")]
        for l, t in zip(labels, text):
            self[l] = StaticText(t)

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

        self["config"].l.setList(cfg_list)

    def on_config_change(self, cfg=None):
        self.update_fields()

    def get_egami_rules(self):
        """Returns the specialized bash conditional engine for EGAMI parsing execution."""
        return (
            '[ -d /usr/emu_scripts ] && d="/usr/emu_scripts" && p="EGcam_"; '
            'if [ -n "$d" ]; then '
            'for s in $d/${p}*.sh; do [[ "$s" != *"_Ci.sh"* ]] && [ -f "$s" ] && "$s" stop; done; '
            'sleep 2; l=0; '
            'for s in $d/${p}*[nN][cC][aA][mI]*.sh; do [ -f "$s" ] && { "$s" start & l=1; break; }; done; '
            'if [ $l -eq 0 ]; then '
            'for s in $d/${p}*[oO][sS][cC][aA][mM]*.sh; do [ -f "$s" ] && { "$s" start & break; }; done; '
            'fi; fi'
        )

    def is_label_duplicated(self, target_label):
        """Scans active configuration files to check if the exact label already exists."""
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
        
        for path in targets:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        content = f.read()
                    blocks = content.split("[reader]")
                    for block in blocks:
                        if not block.strip():
                            continue
                        for line in block.splitlines():
                            if line.strip().startswith("label"):
                                parts = line.split("=", 1)
                                if len(parts) == 2 and parts[1].strip() == target_label:
                                    return True
                except Exception as e:
                    print(f"[ServerEagleSat] Label validation parsing failure on {path}:", e)
        return False

    def keyGreenSave(self):
        lbl_val = self.label_custom.value if self.label_choice.value == "Custom" else self.label_choice.value
        
        # Validation: Stop processing if the label is already taken
        if self.is_label_duplicated(lbl_val):
            warning_msg = _(f"The Reader label '{lbl_val}' already exists!\nPlease change the label name and try again.")
            self.session.open(MessageBox, warning_msg, MessageBox.TYPE_ERROR)
            return

        summary_report = self.add_reader()
        
        # Trigger softcam cycle using the centralized helper function
        success, restart_report = restart_softcam_services(custom_egami_cmd=self.get_egami_rules())
        
        final_message = f"{summary_report}\n---------------------------------------\n{restart_report}"
        self.session.open(MessageBox, final_message, MessageBox.TYPE_INFO)

    def sharing(self):
        self.checkAvailableSharingConfigs()

    def checkAvailableSharingConfigs(self):
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

        self.session.open(MessageBox, message, MessageBox.TYPE_INFO)

    def build_entry_string(self, label, enable, protocol, host, port, user, password, extra_dict=None):
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
        return self.write_to_targets(entry, self.host.value, self.port.value, self.user.value, self.passw.value)

    def write_to_targets(self, entry_str, host, port, user, password):
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
        
        return summary

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
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("No backup readers found in history file."), MessageBox.TYPE_INFO)
            return

        last = readers[-1]
        msg = _("--- Last Saved Reader Backup Data ---\n\n")
        for key, value in last.items():
            msg += f"• {key.capitalize()}: {value}\n"
        
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def scriptslist(self):
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("Restoration canceled: No backup dataset available."), MessageBox.TYPE_ERROR)
            return

        last = readers[-1]
        lbl_val = last.get("label", "Backup_Reader")
        
        # Validation: Stop backup process if the restored label name matches an existing one
        if self.is_label_duplicated(lbl_val):
            warning_msg = _(f"The backup reader label '{lbl_val}' already exists!\nPlease change the label name or delete the previous entry to restore.")
            self.session.open(MessageBox, warning_msg, MessageBox.TYPE_ERROR)
            return

        enable_val = last.get("enable", "1")
        proto = last.get("protocol", "cccam").lower()
        
        device_str = last.get("device", "localhost,22222")
        if "," in device_str:
            host_val, port_val = device_str.split(",", 1)
        else:
            host_val, port_val = device_str, "22222"
            
        user_val = last.get("user", "User")
        pass_val = last.get("password", "Pass")

        entry = self.build_entry_string(lbl_val, enable_val, proto, host_val.strip(), port_val.strip(), user_val, pass_val, last)
        
        summary_report = self.write_to_targets(entry, host_val.strip(), port_val.strip(), user_val, pass_val)
        
        # Trigger softcam cycle on restoration call as well
        success, restart_report = restart_softcam_services(custom_egami_cmd=self.get_egami_rules())
        
        final_message = f"{summary_report}\n---------------------------------------\n{restart_report}"
        self.session.open(MessageBox, final_message, MessageBox.TYPE_INFO)

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])
        
    def keyOK(self):
        # Allow standard Enigma2 configuration lists to invoke virtual keyboard setups
        ConfigListScreen.keyOK(self)
