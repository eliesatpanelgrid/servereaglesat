# -*- coding: utf-8 -*-
"""
Helpers.py
Common helpers for ElieSatPanel plugin (network, image, python, storage, ram, password check).
"""

import os
import re
import sys
import socket
import subprocess
import uuid

# ---------------- NETWORK HELPERS ----------------
def get_local_ip():
    """Return the primary local IPv4 address or 'No IP'."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "No IP"
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def check_internet(host="8.8.8.8", timeout=1):
    """Ping `host` once. Returns 'Online' or 'Offline'."""
    try:
        subprocess.check_call(
            ["ping", "-c", "1", "-W", str(timeout), host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return "Online"
    except Exception:
        return "Offline"


# ---------------- IMAGE / PYTHON HELPERS ----------------
def get_image_name():
    """Try to get the image/creator name from /etc/image-version or /etc/issue."""
    try:
        path = "/etc/image-version"
        if os.path.exists(path):
            try:
                f = open(path, "r")
                lines = [ln.strip() for ln in f if ln.strip()]
                f.close()
                for line in lines:
                    lower = line.lower()
                    if lower.startswith("creator="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
                    if lower.startswith("imagename=") or lower.startswith("image="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
                if lines:
                    return lines[0].split()[-1]
            except Exception:
                pass

        issue = "/etc/issue"
        if os.path.exists(issue):
            try:
                f = open(issue, "r")
                first = f.readline().strip()
                f.close()
                if first:
                    return first.split()[0]
            except Exception:
                pass
    except Exception:
        pass
    return "Unknown"


def get_python_version():
    """Return the running Python version like '3.10.6' or '2.7.18'."""
    try:
        vi = sys.version_info
        return "%d.%d.%d" % (vi[0], vi[1], vi[2])
    except Exception:
        return "Unknown"


# ---------------- STORAGE / RAM HELPERS ----------------
def get_storage_info(mounts=None):
    """
    Return a multi-line string with storage usage.
    mounts: dict of display-name -> path. Defaults to {'Hdd': '/media/hdd'}.
    """
    if mounts is None:
        mounts = {"Hdd": "/media/hdd"}

    info = []
    for name, path in mounts.items():
        if os.path.ismount(path):
            try:
                stat = os.statvfs(path)
                total = (stat.f_blocks * stat.f_frsize) / float(1024 ** 3)
                free = (stat.f_bfree * stat.f_frsize) / float(1024 ** 3)
                used = total - free
                info.append("%s: %.1fGB / %.1fGB" % (name, used, total))
            except Exception:
                info.append("%s: Error" % name)
        else:
            info.append("%s: Not Available" % name)
    return "\n".join(info)


def get_ram_info():
    """Return RAM usage as 'Ram: usedMB / totalMB'."""
    try:
        mem = {}
        f = open("/proc/meminfo", "r")
        for line in f:
            parts = line.split(":", 1)
            if len(parts) == 2:
                mem[parts[0]] = parts[1].strip()
        f.close()

        total_kb = int(mem.get("MemTotal", "0 kB").split()[0])
        avail_kb = int(mem.get("MemAvailable",
                        mem.get("MemFree", "0 kB")).split()[0])

        total_mb = total_kb // 1024
        used_mb = total_mb - (avail_kb // 1024)

        return "Ram: %dMB / %dMB" % (used_mb, total_mb)
    except Exception:
        return "Ram: Not Available"


# ---------------- PASSWORD CHECKER HELPERS ----------------
UNLOCK_FLAG = "/etc/eliesat_unlocked.cfg"
MAIN_MAC_FILE = "/etc/eliesat_main_mac.cfg"


def read_main_mac():
    """Read the saved main MAC from file or detect it."""
    if os.path.exists(MAIN_MAC_FILE):
        try:
            f = open(MAIN_MAC_FILE, "r")
            mac = f.read().strip().upper()
            f.close()
            if mac:
                return mac
        except Exception:
            pass

    mac = get_local_mac()
    if mac:
        try:
            f = open(MAIN_MAC_FILE, "w")
            f.write(mac)
            f.close()
        except Exception:
            pass
    return mac


def get_local_mac():
    """Return the MAC address of the first available interface."""
    ifaces = ("eth0", "eth1", "wan0", "wlan0", "wlan1", "lan0")
    for iface in ifaces:
        path = "/sys/class/net/%s/address" % iface
        try:
            if os.path.exists(path):
                f = open(path)
                mac = f.read().strip()
                f.close()
                if mac and mac != "00:00:00:00:00:00":
                    return mac.upper()
        except Exception:
            pass

    try:
        mac_int = uuid.getnode()
        mac_hex = "%012X" % mac_int
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
    except Exception:
        return None


def make_password_from_mac(mac):
    """
    Password logic matching PanelManager plugin.
    """
    if not mac:
        return None

    mac_clean = mac.replace(":", "").replace("-", "").upper()
    if len(mac_clean) < 10:
        return None

    base = mac_clean[3] + mac_clean[5] + mac_clean[7] + mac_clean[9]
    digits = "".join([c for c in base if c.isdigit()])
    mult = int(digits) * 5 if digits else 0

    return ("%s%s" % (mult, base))[:4]


def is_device_unlocked():
    """Check if device is unlocked."""
    if not os.path.exists(UNLOCK_FLAG):
        return False
    try:
        f = open(UNLOCK_FLAG, "r")
        saved = f.read().strip()
        f.close()
        expected = make_password_from_mac(read_main_mac())
        return bool(saved and expected and saved == expected)
    except Exception:
        return False

