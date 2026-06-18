# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor

def main(session, **kwargs):
    from .ServerEagleSat import ServerEagleSat
    session.open(ServerEagleSat)

def menu_entry(menuid, **kwargs):
    if menuid == "mainmenu":
        return [("ServerEagleSat", main, "server_eagle", None)]
    return []

def Plugins(**kwargs):
    return [
        # Plugin menu entry
        PluginDescriptor(
            name="ServerEagleSat",
            description="Configure your CCCam/Newcamd reader and manage softcams",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main,
            icon="plugin.png"
        ),

        # Main menu entry
        PluginDescriptor(
            name="ServerEagleSat",
            where=PluginDescriptor.WHERE_MENU,
            fnc=menu_entry
        )
    ]
