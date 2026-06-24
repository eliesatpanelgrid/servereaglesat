# -*- coding: utf-8 -*-

from Screens.Screen import Screen
from enigma import getDesktop

# Import your direct hardware helper class
from Plugins.Extensions.ServerEagleSat.menus_list.mainhelpers import SystemInfo
# Import your standalone network helpers
from Plugins.Extensions.ServerEagleSat.menus_list.Helpers import get_local_ip, check_internet

import os
import subprocess
from threading import Timer

from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

# Import native Message Box components for interactive questions
from Screens.MessageBox import MessageBox

from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel


class Eagle5(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # CRITICAL BUGFIX: Automatically create the file that causes the Kitte888 skin converter to crash
        try:
            log_path = "/tmp/kitte888-cs_Ecm_Reader.log"
            if not os.path.exists(log_path):
                with open(log_path, "w") as f:
                    f.write("Eagle5 Crash Protection Active\n")
                os.chmod(log_path, 0o777)
        except Exception as e:
            print("[ServerEagleSat] Failed to inject skin crash protection patch:", e)

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
                "red": self.removeAllCams,       # Redirect red button to uninstaller
                "info": self.infoKey,
                "green": self.scriptslist,       # Green maps to scripts list
                "yellow": self.grid,
                "blue": self.openPluginBrowser,   # Blue maps to direct plugin installation
            }
        )

        # UI BARS
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # COLOR KEYS LABELS
        self["key_red"] = Label("Remove All Cams")  # Updated layout text
        self["key_green"] = Label("Scripts")
        self["key_yellow"] = Label("News")
        self["key_blue"] = Label(_("Install Plugins"))

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
            from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console
            cmd = f"wget --no-check-certificate {script_url} -qO - | /bin/sh"
            title = _(f"Installing {emu_name}...")
            self.session.open(Console, title, [cmd])

    def removeAllCams(self):
        """Phase 1: Pure background scanning and extraction across all image builds (DreamOS and OpenAlliance)"""
        packages_list = [
            "enigma2-plugin-softcams-ultracam-oscam", "enigma2-plugin-softcams-ultracam-ncam",
            "enigma2-plugin-softcams-gosatplus-oscam", "enigma2-plugin-softcams-gosatplus-ncam",
            "enigma2-plugin-softcams-oscam-icam", "enigma2-plugin-softcams-ncam-icam",
            "enigma2-plugin-softcams-icam-oscam", "enigma2-plugin-softcams-powecam-oscam",
            "enigma2-plugin-softcams-powercam-oscam", "enigma2-plugin-softcams-powercam-ncam",
            "enigma2-plugin-softcams-icam-ncam", "enigma2-plugin-softcams-supcam-oscam",
            "enigma2-plugin-softcams-supcam-ncam", "enigma2-plugin-softcams-oscam-all-images",
            "enigma2-plugin-softcams-oscam-emu-levi45", "enigma2-plugin-softcams-oscamicamall",
            "enigma2-plugin-softcams-gosatplusv2-oscam", "enigma2-plugin-softcams-oscam",
            "enigma2-plugin-softcams-oscamicam", "enigma2-plugin-softcams-oscamicamnew",
            "enigma2-plugin-softcams-oscam-emu", "enigma2-plugin-softcams-oscam-sks",
            "enigma2-softcams-oscam-all-images", "enigma2-plugin-softcams-oscam-t2mi",
            "enigma2-plugin-cams-oscam", "enigma2-plugin-extensions-oscamstatus",
            "enigma2-plugin-softcams-ncam", "enigma2-plugin-softcams-revcamv2-ncam",
            "enigma2-plugin-softcams-gosatplusv2-ncam", "enigma2-plugin-cams-ncam",
            "enigma2-softcams-cccam-images", "enigma2-softcams-cccam",
            "enigma2-plugin-softcams-cccam", "enigma2-plugin-softcams-cccam-2.3.9",
            "enigma2-plugin-softcams-mgcamd", "enigma2-plugin-softcams-mgcamd-1.45c",
            "enigma2-plugin-softcams-gosatplus2", "enigma2-plugin-softcams-powercam",
            "enigma2-plugin-softcams-revcamv2", "enigma2-plugin-softcams-gbox",
            "enigma2-plugin-softcams-supcam", "enigma2-plugin-softcams-ghostcam",
            "enigma2-plugin-softcams-ultracam", "enigma2-plugin-softcams-camofs"
        ]

        # 1. Kill active softcam binary processes natively
        os.system('for emu in oscam Ncam ncam powercam powecam cccam CCcam mgcamd gbox supCam supcam ultracam ultracam-oscam ultracam-ncam oscamicam icam; do killall -9 "$emu" >/dev/null 2>&1; pkill -9 -f "$emu" >/dev/null 2>&1; done')
        
        # 2. Complete pure direct filesystem binary purge
        os.system('for path in /usr/bin /usr/bin/cam /usr/camd /usr/emu /usr/softcams /var/emu /usr/scr /usr/scr/cam /var/scr /var/bin; do if [ -d "$path" ]; then for file in OSCam* oscam* ncam* Ncam* powercam* powecam* oscamicam* CCcam* cccam* mgcamd* gbox* supcam* supCam* revcam* ultracam* icam*; do rm -rf "$path/$file" >/dev/null 2>&1; done; fi; done')
        os.system("rm -rf /etc/ncam* /etc/tuxbox/config/oscam* /etc/tuxbox/config/ncam* /etc/tuxbox/config/gbox* /usr/keys/* /usr/camscript/Ncam* /usr/emu_scripts/EGcam* /etc/init.d/softcam* /usr/emu/start/*emu /usr/LTCAM/*ncam.sh /etc/*emu.emu > /dev/null 2>&1")
        os.system('for spath in /usr/script /usr/camscript /usr/emuscript /usr/script/cam /etc/cam.d /usr/emu_scripts; do if [ -d "$spath" ]; then rm -rf "$spath"/*cam.sh "$spath"/*em.sh "$spath"/*emu "$spath"/*Oscam* "$spath"/*OSCam* "$spath"/*OScam* "$spath"/*ncam* "$spath"/*Ncam* "$spath"/*NCam* "$spath"/*gbox* "$spath"/*mgcamd* > /dev/null 2>&1; fi; done')

        # Re-ensure file generation so skin component doesn't crash during uninstallation transitions
        try:
            with open("/tmp/kitte888-cs_Ecm_Reader.log", "w") as f:
                f.write("Eagle5 Crash Protection Active\n")
            os.chmod("/tmp/kitte888-cs_Ecm_Reader.log", 0o777)
        except Exception:
            pass

        # 3. Detect architecture manager types and discover installed packages matching our target list
        is_dreamos = os.path.exists("/usr/bin/apt-get") or os.path.exists("/usr/bin/apt")
        removed_packages = []

        try:
            if is_dreamos:
                installed_output = subprocess.check_output("apt-list --installed", shell=True, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
                for pkg in packages_list:
                    if pkg in installed_output:
                        os.system("apt-get remove -y --purge %s > /dev/null 2>&1" % pkg)
                        removed_packages.append(pkg)
                os.system("apt-get autoremove -y > /dev/null 2>&1")
            else:
                installed_output = subprocess.check_output("opkg list-installed", shell=True, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
                for pkg in packages_list:
                    if pkg in installed_output:
                        os.system("opkg remove --force-depends %s > /dev/null 2>&1" % pkg)
                        removed_packages.append(pkg)
                os.system("opkg configure > /dev/null 2>&1")
        except Exception as e:
            print("[ServerEagleSat Submenu] Package Tracking Exception Handler triggered:", e)

        # Build dynamic readout text summarizing findings
        if removed_packages:
            summary_msg = "The following softcam packages have been completely uninstalled:\n"
            summary_msg += "---------------------------------------------------------\n"
            for p in removed_packages:
                summary_msg += f"• {p}\n"
            summary_msg += "\n:تم إزالة الحزم التالية بنجاح"
        else:
            summary_msg = "No softcam system packages were found active.\nلم يتم العثور على حزم نظام مثبتة للإيموهات.\n"

        summary_msg += "\n\nDo you want to remove configurations and keys data?\nهل تريد حذف ملفات الإعدادات ومفاتيح الشفرات؟"

        # Show summary info display screen context directly combined inside the primary prompt question box
        self.session.openWithCallback(self.askRemoveConfigs, MessageBox, summary_msg, MessageBox.TYPE_YESNO)

    def askRemoveConfigs(self, answer):
        """Phase 2: Dynamic filesystem configurations tracking clean up execution block."""
        if answer:
            os.system("rm -rf /etc/tuxbox/config > /dev/null 2>&1")
            os.system("rm -rf /etc/tuxbox/gosatplus > /dev/null 2>&1")
            os.system("rm -rf /etc/tuxbox/powercam > /dev/null 2>&1")
            os.system("rm -rf /etc/tuxbox/ultracam > /dev/null 2>&1")
            os.system("rm -rf /etc/CCcam.cfg > /dev/null 2>&1")
            os.system("rm -rf /usr/keys/* > /dev/null 2>&1")
        
        # Immediate routing path to final hardware reboot prompt step
        self.session.openWithCallback(self.processRebootAnswer, MessageBox, "Do you want to reboot your STB to apply changes?\nهل تريد إعادة تشغيل الجهاز لتطبيق التغييرات؟", MessageBox.TYPE_YESNO)

    def processRebootAnswer(self, answer):
        """Phase 3: Force global system device environment reboot sequence."""
        if answer:
            os.system("reboot")

    def keyOK(self):
        self.runScript()

    def openPluginBrowser(self):
        """Safely opens the native setup panel downloadable extensions list"""
        try:
            from Screens.PluginBrowser import PluginDownloadBrowser
            self.session.open(PluginDownloadBrowser, 0)
        except Exception as e:
            print("[ServerEagleSat Submenu] PluginDownloadBrowser import failed:", e)
            try:
                from Screens.PluginBrowser import PluginBrowser
                self.session.open(PluginBrowser)
            except Exception as e2:
                print("[ServerEagleSat Submenu] Completely failed to access plugin structures:", e2)

    def cccam(self):
        self.runScript()

    def keyNumberGlobal(self, number):
        if number == 0:
            from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def iptv(self): pass
    def grid(self): pass
    def scriptslist(self): pass

    def infoKey(self):
        from Plugins.Extensions.ServerEagleSat.menus_list.Console import Console
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])