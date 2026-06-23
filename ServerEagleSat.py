#!/usr/bin/python
# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from enigma import getDesktop
from .menus_list.mainhelpers import SystemInfo
from .menus_list.compat import readFromFile
from .menus_list.Console import Console
import os
import importlib
from threading import Timer
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Console import Console as iConsole
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Plugins.Extensions.ServerEagleSat.__init__ import Version, Panel

# ==========================
# ABOUT PICTURE SCREEN
# ==========================
class ServerEagleSatAbout(Screen):
    skin = """
        <screen name="ServerEagleSatAbout" position="center,center" size="1254,1254" title="About" flags="wfNoBorder">
            <widget name="about_pic" position="0,0" size="1254,1254" zPosition="1" alphatest="on" />
        </screen>
    """
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["about_pic"] = Pixmap()
        
        self["actions"] = NumberActionMap(["WizardActions", "ColorActions", "ShortcutActions"], {
            "ok": self.close,
            "back": self.close,
            "cancel": self.close
        })
        
        self.onLayoutFinish.append(self.showPicture)

    def showPicture(self):
        path = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/about.jpg")
        if fileExists(path):
            pix = LoadPixmap(cached=False, path=path)
            if pix:
                self["about_pic"].instance.setPixmap(pix)
        else:
            print("[ServerEagleSat] About image missing at:", path)

# ==========================
# MAIN SCREEN
# ==========================
class ServerEagleSat(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # SKIN
        self.skin = readFromFile("/skins_list/mainmenu-fhd.xml")
        self.setTitle(_("ServerEagleSat"))

        # CORE
        self.iConsole = iConsole()
        self.indexpos = None
        self.system_info = SystemInfo()

        # ACTIONS
        self["NumberActions"] = NumberActionMap(
            ["NumberActions"],
            {'0': self.keyNumberGlobal}
        )
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

        # UI
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))
        self["key_red"] = Label("Iptv Adder")
        self["key_green"] = Label("Cccam Adder")
        self["key_yellow"] = Label("News")
        self["key_blue"] = Label("Scripts")

        # MENU
        self.list = []
        self["menu"] = List(self.list)
        self.mList()

        # LABELS
        labels = ["MemoryLabel", "SwapLabel", "FlashLabel", "gstreamerLabel",
                  "pythonLabel", "CPULabel", "ipLabel", "macLabel",
                  "HardwareLabel", "ImageLabel", "KernelLabel",
                  "EnigmaVersionLabel", "driverLabel", "internetLabel",
                  "satellitesListLabel"]

        text = [_("Ram:"), _("Swap:"), _("Flash:"), _("Gst:"), _("Py:"), _("Prc:"),
                _("IP address:"), _("Mac Address:"), _("Hdw:"), _("Img:"), _("Krn:"), _("Upd:"), _("Drv:"), _("Internet:"),
                _("               Hispasat 30W (MEO, NOS),           AMOS 4.0W (Yes),           Eutelsat 5W (Fransat, Bis TV),           Thor 8.0W (Focus Sat, UPC Direct, Digi Romania/Hungary, Canal Digital),           BulgariaSat 1.9E (Neo Sat),           Eutelsat 9.0E (Discovery, MTVA),           Hot Bird 13.0E (Vivacom Bulgaria, Polsat, NC+/Cyfra, SRG Swiss, Globalcast France, Eurosport, Discovery, Adult, Rai, Tuvisat, Mediaset Italy),           Eutelsat 16.0E (Digitalb, Tring Sport, Max TV, SK, Antiksat, Pink, HRT, Hayat HD, TVR),           Astra 19.0E (Sky Germany, TNT Sat France, Movistar, SRG Astra, ORF Austria, HD+),           Astra 23.0E (Ziggo Nederland, TV Vlaanderen, Skylink),           Astra 28.0E (Sky UK SD),           Eutelsat 36.0E (NTV Plus),           Hellas Sat 39.0E (Dolce Romania),           Türksat 42.0E (D-Smart),            TürkmenÄlem 52.5E (Big Bang),           Express 80.0E (Telekarta).                   ")]

        for l, t in zip(labels, text):
            self[l] = StaticText(t)

        # VALUES
        values = ["memTotal", "swapTotal", "flashTotal", "device", "gstreamer", "python",
                  "Hardware", "Image", "CPU", "Kernel", "ipInfo", "macInfo",
                  "EnigmaVersion", "driver", "internet"]
        for v in values:
            self[v] = StaticText()

        # FOOTER
        self["Version"] = Label(_("V" + Version))
        self["Panel"] = Label(_(Panel))

        # ICON
        self["boxicon"] = Pixmap()
        self.onLayoutFinish.append(self.loadBoxIcon)

        # SYSTEM INFO
        self.system_info.memInfo(self)
        self.system_info.FlashMem(self)
        self.system_info.devices(self)
        self.system_info.mainInfo(self)
        self.system_info.cpuinfo(self)
        self.system_info.getPythonVersionString(self)
        self.system_info.getGStreamerVersionString(self)
        self.system_info.network_info(self)
        self.system_info.intInfo(self)
        Timer(0.5, lambda: self.system_info.update_me(self)).start()

    # MENU
    def mList(self):
        self.list = []
        items = [
            ("Install emus", 5, _("تنزيل و تثبيت الإيميوهات")),
            ("Install softcam", 6, _("تنزيل و تثبيت ملف السوفتكام")),
            ("Install astra-sm", 7, _("تنزيل و تثييت الباكجات الخاصة بالمالتي ستريم")),
            ("Add reader", 1, _("كتابة إشتراك شيرينج و إضافة ريدر")),
            ("Live oscam status", 2, _("عرض حالة الأوسكام")),
            ("Live ncam status", 3, _("عرض حالة الأنكام")),
            ("Preview softcam file", 4, _("تصفح ملف السوفتكام و التعديل فيه")),
            ("Preview emus files", 8, _("تصفح ملفي الاوسكام الانكام سيرفر و التعديل فيهم")),
            ("Preview log file", 9, _(" تصفح ملف اللوج")),
            ("Preview expiracy date", 10, _("تصفح المدة المتبقية لإنتهاء اشتراك (سيرفر ايجل)")),
            ("About", 11, _("About"))
        ]
        for name, idx, desc in items:
            img_path = "Extensions/ServerEagleSat/icons_list/menu/%s.png" % name
            img = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, img_path))
            self.list.append((_(name), idx, desc, img))
        self["menu"].setList(self.list)

    # ICON
    def loadBoxIcon(self):
        try:
            box = "default"
            if os.path.exists("/etc/hostname"):
                box = open("/etc/hostname").read().strip().lower()
            folder = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/boxicons/")
            icon = os.path.join(folder, "%s.png" % box)
            if not fileExists(icon):
                icon = os.path.join(folder, "default.png")
            pix = LoadPixmap(cached=True, path=icon)
            if pix:
                self["boxicon"].instance.setPixmap(pix)
                self["boxicon"].show()
        except Exception as e:
            print("ICON ERROR:", e)

    # KEYS
    def keyOK(self, item=None):
        if item is None:
            item = self["menu"].getCurrent()[1]
        self.select_item(item)

    def select_item(self, item):
        if item == 11:
            self.session.open(ServerEagleSatAbout)
            return
        try:
            module = importlib.import_module(
                "Plugins.Extensions.ServerEagleSat.submenus_list.Eagle%d" % item
            )
            cls = getattr(module, "Eagle%d" % item)
            self.session.open(cls)
        except Exception as e:
            print("PLUGIN LOAD ERROR:", e)

    def keyNumberGlobal(self, number):
        if number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])

    def exit(self):
        self.close()

    def iptv(self): pass
    def cccam(self): pass
    def grid(self): pass
    def scriptslist(self): pass

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])

# ==========================
# PLUGIN ENTRY
# ==========================
def main(session, **kwargs):
    session.open(ServerEagleSat)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="ServerEagleSat",
            description="ServerEagleSat Panel",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        )
    ]
