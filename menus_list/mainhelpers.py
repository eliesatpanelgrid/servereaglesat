# -*- coding: utf-8 -*-
import os
import time
import subprocess
import socket
import binascii
from enigma import getDesktop
from Screens.MessageBox import MessageBox
from Components.Console import Console as iConsole
from Components.Harddisk import harddiskmanager
from Tools.Directories import fileExists
from Plugins.Extensions.ServerEagleSat.__init__ import Version

class MockHDD:
    """Simulates an HDD object for testing without imports"""
    def __init__(self, model_name, total_kb, free_kb):
        self._model = model_name
        self._total = total_kb
        self._free = free_kb

    def model(self):
        return self._model

    def free(self):
        return self._free

    def capacity(self):
        return self._total


class SystemInfo:

    # ------------------------- DEVICES / HDD -------------------------
    def devices(self, self_ref):
        try:
            # Example HDD list
            hddlist = [
                (0, MockHDD("HDD1", 5000000, 2000000)),
                (1, MockHDD("HDD2", 1000000, 500000))
            ]

            if not hddlist:
                self_ref["device"].text = "None detected"
                return

            list_str = ""
            for hdd_item in hddlist:
                hdd = hdd_item[1]
                free_kb = int(hdd.free())
                total_kb = int(hdd.capacity())

                if free_kb > 1024:
                    free_gb = free_kb / 1024
                    total_gb = total_kb / 1024
                    list_str += "%s  %.2f GB  (%.2f GB free)\n" % (hdd.model(), total_gb, free_gb)
                else:
                    list_str += "%s  %d MB  (%d MB free)\n" % (hdd.model(), total_kb, free_kb)

            self_ref["device"].text = list_str.strip()
        except Exception:
            self_ref["device"].text = "Error detecting HDDs"

    
    # ------------------------- CPU -------------------------
    def cpuinfo(self, self_ref):
        try:
            if fileExists("/proc/cpuinfo"):
                cpu_count = 0
                processor = cpu_speed = cpu_family = cpu_variant = temp = ''
                core = _("core")
                cores = _("cores")
                for line in open('/proc/cpuinfo'):
                    if "system type" in line:
                        processor = line.split(':')[-1].split()[0].strip()
                    elif "cpu MHz" in line:
                        cpu_speed = line.split(':')[-1].strip()
                    elif "cpu type" in line:
                        processor = line.split(':')[-1].strip()
                    elif "model name" in line:
                        processor = line.split(':')[-1].strip().replace('Processor ', '')
                    elif "cpu family" in line:
                        cpu_family = line.split(':')[-1].strip()
                    elif "cpu variant" in line:
                        cpu_variant = line.split(':')[-1].strip()
                    elif line.startswith('processor'):
                        cpu_count += 1

                if not cpu_speed:
                    try:
                        cpu_speed = int(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()) / 1000
                    except:
                        cpu_speed = '-'

                # Temperature detection
                if fileExists("/proc/stb/sensors/temp0/value") and fileExists("/proc/stb/sensors/temp0/unit"):
                    temp = "%s%s%s" % (
                        open("/proc/stb/sensors/temp0/value").read().strip(),
                        chr(176).encode("latin-1"),
                        open("/proc/stb/sensors/temp0/unit").read().strip()
                    )
                elif fileExists("/proc/stb/fp/temp_sensor_avs"):
                    temp = "%s%sC" % (open("/proc/stb/fp/temp_sensor_avs").read().strip(), chr(176).encode("latin-1"))

                if cpu_variant == '':
                    self_ref["CPU"].text = _("%s, %s Mhz (%d %s) %s") % (
                        processor, cpu_speed, cpu_count, cpu_count > 1 and cores or core, temp)
                else:
                    self_ref["CPU"].text = "%s(%s), %s %s" % (processor, cpu_family, cpu_variant, temp)
            else:
                self_ref["CPU"].text = _("undefined")
        except Exception:
            self_ref["CPU"].text = _("undefined")

    # ------------------------- MEMORY -------------------------
    def memInfo(self, self_ref):
        try:
            memtotal = memfree = swaptotal = swapfree = 0
            for line in open("/proc/meminfo"):
                if "MemTotal:" in line:
                    memtotal = line.split()[1]
                elif "MemFree:" in line:
                    memfree = line.split()[1]
                elif "SwapTotal:" in line:
                    swaptotal = line.split()[1]
                elif "SwapFree:" in line:
                    swapfree = line.split()[1]
            self_ref["memTotal"].text = _("Total: %s Kb  Free: %s Kb") % (memtotal, memfree)
            self_ref["swapTotal"].text = _("Total: %s Kb  Free: %s Kb") % (swaptotal, swapfree)
        except Exception:
            self_ref["memTotal"].text = _("unknown")
            self_ref["swapTotal"].text = _("unknown")

    # ------------------------- FLASH -------------------------
    def FlashMem(self, self_ref):
        try:
            st = os.statvfs("/")
            avail = st.f_bsize * st.f_bavail / 1024
            size = st.f_bsize * st.f_blocks / 1024
            self_ref["flashTotal"].text = _("Total: %s Kb  Free: %s Kb") % (size, avail)
        except Exception:
            self_ref["flashTotal"].text = _("unknown")

    # ------------------------- NETWORK -------------------------
    def network_info(self, self_ref):
        self_ref.iConsole.ePopen("ifconfig -a",
                                 lambda res, ret, extra: self.network_result(self_ref, res, ret, extra))

    def network_result(self, self_ref, result, retval, extra_args):
        ip = ''
        if retval == 0 and len(result) > 0:
            mac = []
            for line in result.splitlines(True):
                if 'HWaddr' in line:
                    mac.append(line.split()[-1].strip('\n'))
                elif 'inet addr:' in line and 'Bcast:' in line:
                    ip = line.split()[1].split(':')[-1]
            self_ref["macInfo"].text = '/'.join(mac) if mac else _("unknown")
        else:
            self_ref["macInfo"].text = _("unknown")
        self_ref["ipInfo"].text = ip if ip else _("unknown")

    def intInfo(self, self_ref):
        try:
            socket.setdefaulttimeout(0.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('8.8.8.8', 53))
            s.close()
            self_ref["internet"].text = _("Connected")
            return True
        except:
            self_ref["internet"].text = _("Disconnected")
            return False

    # ------------------------- PYTHON & GSTREAMER -------------------------
    def getPythonVersionString(self, self_ref):
        try:
            status, output = subprocess.getstatusoutput("python -V")
            self_ref["python"].text = output.split(' ')[1]
        except Exception:
            self_ref["python"].text = _("unknown")

    def getGStreamerVersionString(self, self_ref):
        import enigma
        try:
            self_ref["gstreamer"].text = enigma.getGStreamerVersionString().strip('GStreamer ')
        except Exception:
            self_ref["gstreamer"].text = _("unknown")

    # ------------------------- MAIN INFO -------------------------
    def mainInfo(self, self_ref):
        try:
            # Hardware type
            self_ref["Hardware"].text = self.HardWareType(self_ref)

            # Image type
            self_ref["Image"].text = self.getImageTypeString(self_ref)

            # Kernel version
            self_ref["Kernel"].text = self.getKernelVersionString(self_ref)

            # Enigma/OS version
            self_ref["EnigmaVersion"].text = self.getImageVersionString(self_ref)

            # Driver version detection
            status_path = self.status(self_ref)
            self_ref["driver"].text = _("unknown")
            if fileExists(status_path):
                package_found = False
                for line in open(status_path):
                    if any(x in line and "Package:" in line for x in ["-dvb-modules", "kernel-module-player2",
                                                                      "formuler-dvb-modules", "vuplus-dvb-proxy-vusolo4k"]):
                        package_found = True
                    if "Version:" in line and package_found:
                        package_found = False
                        self_ref["driver"].text = line.split()[-1]
                        break
        except Exception:
            self_ref["Hardware"].text = _("unknown")
            self_ref["Image"].text = _("unknown")
            self_ref["Kernel"].text = _("unknown")
            self_ref["EnigmaVersion"].text = _("unknown")
            self_ref["driver"].text = _("unknown")

    # ------------------------- SUPPORT METHODS -------------------------
    def status(self, self_ref):
        paths = ["/usr/lib/opkg/status", "/usr/lib/ipkg/status",
                 "/var/lib/opkg/status", "/var/opkg/status"]
        for path in paths:
            if fileExists(path):
                return path
        return ''

    def HardWareType(self, self_ref):
        paths = [("/proc/stb/info/boxtype", ""),
                 ("/proc/stb/info/vumodel", "VU+"),
                 ("/proc/stb/info/model", "")]
        for path, prefix in paths:
            if os.path.isfile(path):
                return prefix + open(path).read().strip().upper()
        return _("unavailable")

    def getImageTypeString(self, self_ref):
        try:
            if os.path.isfile("/etc/issue"):
                for line in open("/etc/issue"):
                    if not line.startswith('Welcome') and '\l' in line:
                        return line.capitalize().replace('\n', ' ').replace('\l', ' ').strip()
        except:
            pass
        return _("undefined")

    def getKernelVersionString(self, self_ref):
        try:
            return open("/proc/version").read().split()[2]
        except:
            return _("unknown")

    def getImageVersionString(self, self_ref):
        try:
            paths = ['/var/lib/opkg/status', '/usr/lib/ipkg/status', '/usr/lib/opkg/status', '/var/opkg/status']
            st = None
            for path in paths:
                if os.path.isfile(path):
                    st = os.stat(path)
                    break
            if st:
                tm = time.localtime(st.st_mtime)
                if tm.tm_year >= 2011:
                    return time.strftime("%Y-%m-%d %H:%M:%S", tm)
        except:
            pass
        return _("unavailable")

    # ------------------------- UPDATE -------------------------
    def update_me(self, self_ref):
        try:
            from .menus.compat import compat_Request, compat_urlopen, PY3
            from Plugins.Extensions.ElieSatPanel.__init__ import installer

            remote_version = '0.0'
            remote_changelog = ''

            req = compat_Request(installer, headers={'User-Agent': 'Mozilla/5.0'})
            page = compat_urlopen(req).read()
            data = page.decode("utf-8") if PY3 else page.encode("utf-8")

            if data:
                lines = data.split("\n")
                for line in lines:
                    if line.startswith("version"):
                        remote_version = line.split("=")[1].strip("'")
                    if line.startswith("changelog"):
                        remote_changelog = line.split("=")[1].strip("'")
                        break

            if float(Version) < float(remote_version):
                self_ref.session.openWithCallback(
                    lambda answer: self.install_update(self_ref, answer),
                    MessageBox,
                    _("New version %s is available.\n%s\n\nDo you want to install it now?" % (
                        remote_version, remote_changelog)),
                    MessageBox.TYPE_YESNO
                )
        except Exception as e:
            print("Update check failed:", e)

    def install_update(self, self_ref, answer=False):
        if answer:
            from Plugins.Extensions.ServerEagleSat.__init__ import installer
            self_ref.session.open(
                iConsole,
                title=_('Updating please wait...'),
                cmdlist=['wget -q "--no-check-certificate" ' + installer + ' -O - | /bin/sh'],
                finishedCallback=lambda result: None,
                closeOnSuccess=False
            )

