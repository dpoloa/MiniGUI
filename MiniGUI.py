#!/usr/bin/env python3

"""
MiniGUI: Graphical User Interface for Mininet

This program allows the user to create a computer
network in an easy and comfortable way. It is related
to the Final Degree Project for Telecommunications
Technologies Degree from Universidad Rey Juan Carlos.

Author:         Daniel Polo Álvarez
Email:          d.poloa@alumnos.urjc.es
University:     Universidad Rey Juan Carlos

Mentors:        José Centeno González (jose.centeno@urjc.es)
                Eva María Castro Barbero (eva.castro@urjc.es)
"""

# PyQt5 package import
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Mininet package import
from mininet.net import Mininet
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Node
from mininet.cli import CLI

# Python general packages import
import subprocess
import threading
import math
import json
import time
import sys
import os
import re

# Global application variables
MINIGUI_VERSION = '01.00.00'
DEFAULT_TIMER = 5.0
APP_THEME = "light"


# Thread classes

class MiniCLI(threading.Thread):
    """
    Thread class for Mininet CLI, needed to not conflict
    with PyQt5 event loop
    """
    def __init__(self, net=None):
        super(MiniCLI, self).__init__(daemon=True)
        self.net = net

    def run(self):
        if self.net is not None:
            CLI(self.net)
            print("CLI execution has finished")


class SceneAutoUpdate(QThread):
    """
    Thread class to update automatically the scene with information
    from Mininet simulation
    """
    updateSignal = pyqtSignal()

    def __init__(self, timer=None):
        super(SceneAutoUpdate, self).__init__()
        self.update_active = True
        if not isinstance(timer, float):
            self.timer = DEFAULT_TIMER
        else:
            self.timer = timer

    def run(self):
        time.sleep(10.0)
        while self.update_active:
            time.sleep(self.timer)
            self.updateSignal.emit()


# Extended class from Mininet base class

class Router(Node):
    """Extended class to convert Linux node in router"""
    def __init__(self, name, **params):
        super(Router, self).__init__(name, **params)

    def config(self, **params):
        super(Router, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(Router, self).terminate()


# Node/Link properties dialog classes

class BaseDialog(QDialog):
    """Base class for hosts, switches and routers dialogs"""
    def __init__(self):
        super(BaseDialog, self).__init__()

        # Default buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Base layout for dialog
        self.base_layout = QVBoxLayout()
        self.base_layout.addWidget(button_box)
        self.setLayout(self.base_layout)


class HostDialog(BaseDialog):
    """Dialog class to display host information"""
    def __init__(self, host):
        """
        :param host: reference to node object
        :type host: NodeGUI
        """
        super(HostDialog, self).__init__()

        # Class attributes
        self.host = host
        self.results = {}

        # Modification of window's properties
        self.setWindowTitle("Host properties: " + str(host.node_name))
        self.setFixedWidth(450)

        # Host structure initialization
        self.setHostDialog()

    def setHostDialog(self):
        """Builds the base layout, dividing it in tabs"""
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setHostInformation(), "Information")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Interfaces")
        # Third tab: routing table
        tab_menu.addTab(self.setRoutingTable(), "Routing")

    def setHostInformation(self):
        """Displays the host's name and saves its changes

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Host's name label
        name_label = QLabel("Host name")
        name_edit_label = QLineEdit(str(self.host.node_name))
        self.results["node_name"] = name_edit_label

        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)
        layout.addStretch()

        return widget

    def setEthernetIntfs(self):
        """Displays the host's Ethernet interfaces

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        eth_layout = QGridLayout()
        eth_layout.setAlignment(Qt.AlignTop)
        eth_layout.setColumnMinimumWidth(1, 10)
        eth_layout.setColumnMinimumWidth(5, 10)
        widget.setLayout(eth_layout)

        host_intfs = self.host.properties["eth_intfs"]
        host_scene = self.host.scene()

        if not host_intfs:
            eth_layout.addWidget(QLabel("There are no interfaces already defined"), 0, 0, 1, -1, Qt.AlignHCenter)
            return widget

        intf_ip_list = {}
        intf_mask_list = {}
        intf_state_list = {}

        # Design of the layout
        eth_layout.addWidget(QLabel("Interface"), 0, 0)
        eth_layout.addWidget(QLabel("IP Address"), 0, 2)
        eth_layout.addWidget(QLabel("Netmask"), 0, 4)
        eth_layout.addWidget(QLabel("Up?"), 0, 6)

        index = 1
        for interface in host_intfs:
            # Interface name label and slash separator
            intf_name_label = QLabel(str(interface))
            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)
            eth_layout.addWidget(QLabel("/"), index + 1, 3)

            # Retrieving interface information
            if host_intfs[interface] == "":
                eth_ip = ""
                eth_mask = ""
            else:
                eth_ip = host_intfs[interface].split("/")[0]
                eth_mask = host_intfs[interface].split("/")[1]

            # IP address label
            intf_ip_label = QLineEdit(str(eth_ip))
            intf_ip_list[interface] = intf_ip_label
            eth_layout.addWidget(intf_ip_label, index + 1, 2)

            # Netmask label
            intf_mask_label = QLineEdit(str(eth_mask))
            intf_mask_list[interface] = intf_mask_label
            eth_layout.addWidget(intf_mask_label, index + 1, 4)

            # Interface (& link) status
            intf_state_button = QCheckBox()
            intf_id = self.host.searchLinkByIntf(interface)
            if host_scene.scene_links[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            intf_state_list[interface] = intf_state_button
            eth_layout.addWidget(intf_state_button, index + 1, 6)

            index = index + 1

        self.results["eth_intfs_ip"] = intf_ip_list
        self.results["eth_intfs_mask"] = intf_mask_list
        self.results["eth_intfs_state"] = intf_state_list

        return widget

    def setRoutingTable(self):
        """Displays the host's updated routing table

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        widget.setLayout(layout)

        # 1st case: Mininet simulation is not running
        scene = self.host.scene()
        if not scene.net_running:
            label = QLabel("Routing table is not available as Mininet network is not active")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # 2nd case: error at retrieving the routing table
        route_list = self.host.net_controller.getNetNodeRoutingTable(self.host)
        if route_list == "Error":
            label = QLabel("An error occurred getting the routing table. Please, restart the dialog")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # Apply command layout
        layout.addWidget(QLabel("Write down your route / ip route command:"))

        # Widget and layout creation for line command field
        widget_top = QWidget()
        layout_top = QHBoxLayout()
        layout_top.setContentsMargins(0, 0, 0, 0)
        widget_top.setLayout(layout_top)
        layout.addWidget(widget_top)

        line_command = QLineEdit()
        layout_top.addWidget(line_command)

        apply_button = QPushButton("Apply")
        layout_top.addWidget(apply_button)

        # Routing table widget
        route_widget = QWidget()
        layout.addWidget(route_widget)

        route_layout = QGridLayout()
        route_layout.setColumnMinimumWidth(1, 10)
        route_layout.setColumnMinimumWidth(3, 10)
        route_layout.setColumnMinimumWidth(5, 10)
        route_widget.setLayout(route_layout)

        self.updateRoutingTableLayout(route_widget, route_list)

        # Connecting action to apply_button
        apply_button.pressed.connect(lambda: self.sendCommandToNet(line_command.text(), route_widget))
        apply_button.pressed.connect(lambda: line_command.clear())

        layout.addStretch()

        return widget

    # Auxiliary functions for dynamic widget from routing table tab

    def sendCommandToNet(self, command, widget):
        """
        Filters the command sent by the user and, if correct, sends it
        adn retrieves the output from Mininet simulation.

        :param command: instruction introduced by the user
        :type command: str
        :param widget: dynamic widget to be updated (if needed)
        :type widget: QWidget
        """
        # Command filtering: checking beginning of command
        if not (command.startswith("route") or command.startswith("ip route")):
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command failed</b>")
            dialog.setInformativeText("The command you inserted must start with route or ip route")
            dialog.exec()
            return
        elif command in ["route", "ip route"] or re.match("route -[FCvne]", command):
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command incomplete</b>")
            dialog.setInformativeText("Please, complete the (ip) route command to modify the routing table")
            dialog.exec()
            return

        # Command filtering: checking command parsing
        command_split = str(command).split()
        for element in command_split:
            if re.match(r"[,;:|]", element):
                dialog = QMessageBox(self)
                dialog.setIcon(QMessageBox.Warning)
                dialog.setTextFormat(Qt.RichText)
                dialog.setText("<b>Command failed</b>")
                dialog.setInformativeText("The command you inserted has special character. Please, delete it")
                dialog.exec()
                return

        # If appropriate, command is sent and output is retrieved
        output = self.host.net_controller.updateNetNodeRoutingTable(self.host, command)
        if output is not None:
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command failed</b>")
            dialog.setInformativeText("The command you inserted was not recognized or is incomplete."
                                      " See details for more information")
            dialog.setDetailedText(str(output))
            dialog.exec()
        else:
            route_list = self.host.net_controller.getNetNodeRoutingTable(self.host)
            self.updateRoutingTableLayout(widget, route_list)

    def updateRoutingTableLayout(self, route_widget, route_list):
        """Modifies the dynamic widget updating the host's routing list

        :param route_widget: widget in charge of displaying the routing table
        :type route_widget: QWidget
        :param route_list: dictionary with a tabulated routing table information
        :type route_list: dict
        """
        # Dynamic widget's layout emptying
        route_layout = route_widget.layout()
        if route_layout is not None:
            for index in reversed(range(route_layout.count())):
                route_layout.itemAt(index).widget().deleteLater()

        # Dynamic widget's layout update
        if not route_list["Destination"]:
            route_layout.addWidget(QLabel("There are no entries yet"), 0, 0, 1, -1, Qt.AlignHCenter)
        else:
            route_layout.addWidget(QLabel("Destination"), 0, 0)
            route_layout.addWidget(QLabel("Gateway"), 0, 2)
            route_layout.addWidget(QLabel("Interface"), 0, 4)
            route_layout.addWidget(QLabel("Delete route"), 0, 6)
            for index in range(len(route_list["Destination"])):
                route_layout.addWidget(QLabel(str(route_list["Destination"][index])), index + 1, 0)
                route_layout.addWidget(QLabel(str(route_list["Gateway"][index])), index + 1, 2)
                route_layout.addWidget(QLabel(str(route_list["Interface"][index])), index + 1, 4)
                del_command = ("ip route del " + str(route_list["Destination"][index]) +
                               " dev " + route_list["Interface"][index])
                del_button = QPushButton("Delete")
                del_button.pressed.connect(lambda command=del_command: self.sendCommandToNet(command, route_widget))
                route_layout.addWidget(del_button, index + 1, 6)


class SwitchDialog(BaseDialog):
    """Dialog class to display switch information"""
    def __init__(self, switch):
        """
        :param switch: reference to node object
        :type switch: NodeGUI
        """
        super(SwitchDialog, self).__init__()

        # Class attributes
        self.switch = switch

        # Modification of window's properties
        self.setWindowTitle("Switch routing table: " + str(switch.node_name))
        self.setFixedWidth(300)

        # Switch structure initialization
        self.showMacDirectionsTable()

    def showMacDirectionsTable(self):
        """Shows the result of command 'ovs-appctl fdb/show' applied on the switch"""
        route_layout = QGridLayout()
        route_layout.setColumnMinimumWidth(1, 10)
        route_layout.setColumnMinimumWidth(3, 10)
        route_layout.setColumnMinimumWidth(5, 10)
        self.base_layout.insertLayout(0, route_layout)
        self.base_layout.insertStretch(1)

        route_table = self.switch.net_controller.getSwitchStoredRoutes(self.switch)
        if route_table is None:
            route_layout.addWidget(QLabel("This command returned error"), 0, 0, 1, -1, Qt.AlignHCenter)
        elif not route_table["Port"]:
            route_layout.addWidget(QLabel("There are no entries yet"), 0, 0, 1, -1, Qt.AlignHCenter)
        else:
            route_layout.addWidget(QLabel("Port"), 0, 0)
            route_layout.addWidget(QLabel("VLAN"), 0, 2)
            route_layout.addWidget(QLabel("MAC"), 0, 4)
            route_layout.addWidget(QLabel("Age"), 0, 6)
            for index in range(len(route_table["Port"])):
                route_layout.addWidget(QLabel(str(route_table["Port"][index])), index + 1, 0)
                route_layout.addWidget(QLabel(str(route_table["VLAN"][index])), index + 1, 2)
                route_layout.addWidget(QLabel(str(route_table["MAC"][index])), index + 1, 4)
                route_layout.addWidget(QLabel(str(route_table["Age"][index])), index + 1, 6)


class RouterDialog(BaseDialog):
    """Dialog class to display router information"""
    def __init__(self, router):
        """
        :param router: reference to node object
        :type router: NodeGUI
        """
        super(RouterDialog, self).__init__()

        # Class attributes
        self.router = router
        self.results = {}

        # Modification of window's properties
        self.setWindowTitle("Router properties: " + str(router.node_name))
        self.setFixedWidth(450)

        # Router structure initialization
        self.setRouterDialog()

    def setRouterDialog(self):
        """Builds the base layout, dividing it in tabs"""
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setRouterInformation(), "Information")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Interfaces")
        # Third tab: routing table
        tab_menu.addTab(self.setRoutingTable(), "Routing")

    def setRouterInformation(self):
        """Displays the router's name and saves its changes

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Router's name label
        name_label = QLabel("Router name")
        name_edit_label = QLineEdit(str(self.router.node_name))
        self.results["node_name"] = name_edit_label

        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)
        layout.addStretch()

        return widget

    def setEthernetIntfs(self):
        """Displays the router's Ethernet interfaces

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        eth_layout = QGridLayout()
        eth_layout.setAlignment(Qt.AlignTop)
        eth_layout.setColumnMinimumWidth(1, 10)
        eth_layout.setColumnMinimumWidth(5, 10)
        widget.setLayout(eth_layout)

        router_intfs = self.router.properties["eth_intfs"]
        router_scene = self.router.scene()

        if not router_intfs:
            eth_layout.addWidget(QLabel("There are no interfaces already defined"), 0, 0, 1, -1, Qt.AlignHCenter)
            return widget

        intf_ip_list = {}
        intf_mask_list = {}
        intf_state_list = {}

        # Design of the layout
        eth_layout.addWidget(QLabel("Interface"), 0, 0)
        eth_layout.addWidget(QLabel("IP Address"), 0, 2)
        eth_layout.addWidget(QLabel("Netmask"), 0, 4)
        eth_layout.addWidget(QLabel("Up?"), 0, 6)

        index = 1
        for interface in router_intfs:
            # Interface name label
            intf_name_label = QLabel(str(interface))
            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)
            eth_layout.addWidget(QLabel("/"), index + 1, 3)

            # Retrieving interface information
            if router_intfs[interface] == "":
                eth_ip = ""
                eth_mask = ""
            else:
                eth_ip = router_intfs[interface].split("/")[0]
                eth_mask = router_intfs[interface].split("/")[1]

            # IP address label
            intf_ip_label = QLineEdit(str(eth_ip))
            intf_ip_list[interface] = intf_ip_label
            eth_layout.addWidget(intf_ip_label, index + 1, 2)

            # Netmask label
            intf_mask_label = QLineEdit(str(eth_mask))
            intf_mask_list[interface] = intf_mask_label
            eth_layout.addWidget(intf_mask_label, index + 1, 4)

            # Interface (& link) status
            intf_state_button = QCheckBox()
            intf_id = self.router.searchLinkByIntf(interface)
            if router_scene.scene_links[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            intf_state_list[interface] = intf_state_button
            eth_layout.addWidget(intf_state_button, index + 1, 6)

            index = index + 1

        self.results["eth_intfs_ip"] = intf_ip_list
        self.results["eth_intfs_mask"] = intf_mask_list
        self.results["eth_intfs_state"] = intf_state_list

        return widget

    def setRoutingTable(self):
        """Displays the router's updated routing table

        :returns widget with interactive fields
        :rtype QWidget
        """
        # Creation of tab's main widget and layout
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        widget.setLayout(layout)

        # 1st case: Mininet simulation is not running
        scene = self.router.scene()
        if not scene.net_running:
            label = QLabel("Routing table is not available as Mininet network is not active")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # 2nd case: error at retrieving the routing table
        route_list = self.router.net_controller.getNetNodeRoutingTable(self.router)
        if route_list == "Error":
            label = QLabel("An error occurred getting the routing table. Please, restart the dialog")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # Apply command layout
        layout.addWidget(QLabel("Write down your route / ip route command:"))

        # Widget and layout creation for line command field
        widget_top = QWidget()
        layout_top = QHBoxLayout()
        layout_top.setContentsMargins(0, 0, 0, 0)
        widget_top.setLayout(layout_top)
        layout.addWidget(widget_top)

        line_command = QLineEdit()
        layout_top.addWidget(line_command)

        apply_button = QPushButton("Apply")
        layout_top.addWidget(apply_button)

        # Routing table widget
        route_widget = QWidget()
        layout.addWidget(route_widget)

        route_layout = QGridLayout()
        route_layout.setColumnMinimumWidth(1, 10)
        route_layout.setColumnMinimumWidth(3, 10)
        route_layout.setColumnMinimumWidth(5, 10)
        route_widget.setLayout(route_layout)

        self.updateRoutingTableLayout(route_widget, route_list)

        # Connecting action to apply_button
        apply_button.pressed.connect(lambda: self.sendCommandToNet(line_command.text(), route_widget))
        apply_button.pressed.connect(lambda: line_command.clear())

        layout.addStretch()

        return widget

    # Auxiliary functions for dynamic widget from routing table tab

    def sendCommandToNet(self, command, widget):
        """
        Filters the command sent by the user and, if correct, sends it
        and retrieves the output from Mininet simulation.

        :param command: instruction introduced by the user
        :type command: str
        :param widget: dynamic widget to be updated (if needed)
        :type widget: QWidget
        """
        # Command filtering: checking beginning of command
        if not (command.startswith("route") or command.startswith("ip route")):
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command failed</b>")
            dialog.setInformativeText("The command you inserted must start with route or ip route")
            dialog.exec()
            return
        elif command in ["route", "ip route"] or re.match("route -[FCvne]", command):
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command incomplete</b>")
            dialog.setInformativeText("Please, complete the (ip) route command to modify the routing table")
            dialog.exec()
            return

        # Command filtering: checking command parsing
        command_split = str(command).split()
        for element in command_split:
            if re.match(r"[,;:|]", element):
                dialog = QMessageBox(self)
                dialog.setIcon(QMessageBox.Warning)
                dialog.setTextFormat(Qt.RichText)
                dialog.setText("<b>Command failed</b>")
                dialog.setInformativeText("The command you inserted has special character. Please, delete it")
                dialog.exec()
                return

        # If appropriate, command is sent and output is retrieved
        output = self.router.net_controller.updateNetNodeRoutingTable(self.router, command)
        if output is not None:
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setTextFormat(Qt.RichText)
            dialog.setText("<b>Command failed</b>")
            dialog.setInformativeText("The command you inserted was not recognized or is incomplete."
                                      " See details for more information")
            dialog.setDetailedText(str(output))
            dialog.exec()
        else:
            route_list = self.router.net_controller.getNetNodeRoutingTable(self.router)
            self.updateRoutingTableLayout(widget, route_list)

    def updateRoutingTableLayout(self, route_widget, route_list):
        """Modifies the dynamic widget updating the host's routing list

        :param route_widget: widget in charge of displaying the routing table
        :type route_widget: QWidget
        :param route_list: dictionary with a tabulated routing table information
        :type route_list: dict
        """
        # Dynamic widget's layout emptying
        route_layout = route_widget.layout()
        if route_layout is not None:
            for index in reversed(range(route_layout.count())):
                route_layout.itemAt(index).widget().deleteLater()

        # Dynamic widget's layout update
        if not route_list["Destination"]:
            route_layout.addWidget(QLabel("There are no entries yet"), 0, 0, 1, -1, Qt.AlignHCenter)
        else:
            route_layout.addWidget(QLabel("Destination"), 0, 0)
            route_layout.addWidget(QLabel("Gateway"), 0, 2)
            route_layout.addWidget(QLabel("Interface"), 0, 4)
            route_layout.addWidget(QLabel("Delete route"), 0, 6)
            for index in range(len(route_list["Destination"])):
                route_layout.addWidget(QLabel(str(route_list["Destination"][index])), index + 1, 0)
                route_layout.addWidget(QLabel(str(route_list["Gateway"][index])), index + 1, 2)
                route_layout.addWidget(QLabel(str(route_list["Interface"][index])), index + 1, 4)
                del_command = ("ip route del " + str(route_list["Destination"][index]) +
                               " dev " + route_list["Interface"][index])
                del_button = QPushButton("Delete")
                del_button.pressed.connect(lambda command=del_command: self.sendCommandToNet(command, route_widget))
                route_layout.addWidget(del_button, index + 1, 6)


# MiniGUI scene-related classes

class TagGUI(QGraphicsTextItem):
    """Base class for scene tags (name, interfaces, IP address)"""
    def __init__(self, text=None, parent=None):
        """
        :param text: text to be introduced in tag
        :type text: str
        :param parent: element in charge of tag
        """
        super(TagGUI, self).__init__(text, parent)

        # Text font change
        font = QFont()
        font.setBold(True)
        self.setFont(font)


class EthTagGUI(TagGUI):
    """Extended class for node's interface name tags"""
    def __init__(self, text=None, parent=None):
        """
        :param text: text to be introduced in tag
        :type text: str
        :param parent: element in charge of tag
        """
        super(EthTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """Changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.darkCyan)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.cyan)


class IpTagGUI(TagGUI):
    """Extended class for interface's IP address tags"""
    def __init__(self, text=None, parent=None):
        """
        :param text: text to be introduced in tag
        :type text: str
        :param parent: element in charge of tag
        """
        super(IpTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """Changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.darkBlue)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.green)


class NameTagGUI(TagGUI):
    """Extended class for node's name tags"""
    def __init__(self, text=None, parent=None):
        """
        :param text: text to be introduced in tag
        :type text: str
        :param parent: element in charge of tag
        """
        super(NameTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """Changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.black)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.white)


class NodeGUI(QGraphicsPixmapItem):
    """Represents a node (host, switch or router) of SceneGUI class"""
    def __init__(self, x, y, node_type, node_name, properties=None, new_node=False, net_ctrl=None):
        """
        :param x: horizontal position of node
        :type x: float
        :param y: vertical position of node
        :type y: float
        :param node_type: type of the new node
        :type node_type: str
        :param node_name: name of the new node
        :type node_name: str
        :param properties: properties of the node in previous sessions (optional)
        :type properties: dict
        :param new_node: determines if the node is created in this session or not
        :type new_node: bool
        :param net_ctrl: pointer to MiniGUI class (optional)
        :type net_ctrl: MiniGUI
        """
        super(NodeGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial attributes
        self.width = 64
        self.height = 64
        self.node_name = node_name
        self.node_type = node_type
        self.icon = None
        self.image = None
        self.links = {}
        self.properties = {}
        self.scene_tags = {"name": None, "IP": {}, "eth": {}}

        # Setting up initial attributes
        self.setNodeAttributes(x, y, properties, new_node)

    def setNodeAttributes(self, x, y, properties=None, new_node=False):
        """Defines all the internal properties of the node

        :param x: horizontal position of node
        :type x: float
        :param y: vertical position of node
        :type y: float
        :param properties: properties of the node in previous sessions (optional)
        :type properties: dict
        :param new_node: determines if the node is created in this session or not
        :type new_node: bool
        """
        # Acquisition of images
        images = imagesMiniGUI()

        # Setting up icon and image of the node
        self.icon = images[self.node_type]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

        # Setting of flag and internal attributes of the element
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)

        # Positioning of element on the scene
        self.setZValue(100)
        self.setPos(x, y)

        # Moving element in order to center it where user has clicked (only for new elements)
        if new_node:
            offset = self.boundingRect().topLeft() - self.boundingRect().center()
            self.moveBy(offset.x(), offset.y())

        # Properties assignment / creation
        self.properties["eth_intfs"] = {}
        if self.node_type != "Switch":
            self.properties["IP"] = properties["IP"]
            self.properties["PrefixLen"] = properties["PrefixLen"]
            if not new_node:
                self.properties["eth_intfs"] = properties["eth_intfs"]
        elif self.node_type == "Switch" and properties is not None:
            self.properties = properties

    # Auxiliary functions

    def addNewLink(self, name):
        """Adds a new link to the node and creates a new interface for it

        :param name: new link's name
        :type name: str
        """
        if name not in self.links:
            # Creating a new interface name and assignation to link
            new_intf = self.assignIntfName()
            self.links[name] = new_intf

            # Creation of interface properties
            if self.node_type != "Switch" and len(self.links) == 1:
                self.properties["eth_intfs"][new_intf] = (str(self.properties["IP"]) + "/" +
                                                          str(self.properties["PrefixLen"]))
            else:
                self.properties["eth_intfs"][new_intf] = ""

            return new_intf
        else:
            return self.links[name]

    def deleteLink(self, name):
        """Deletes a link and everything related to it (properties & scene tags)

        :param name: to-be-deleted link's name
        :type name: str
        """
        if name in self.links:
            intf = self.links.pop(name)
            self.properties["eth_intfs"].pop(intf)
            self.scene_tags["eth"].pop(intf)
            if intf in self.scene_tags["IP"]:
                self.scene_tags["IP"].pop(intf)

    def searchLinkByIntf(self, intf_name):
        """Searches a link through its associated interface

        :param intf_name: interface's name
        :type intf_name: str
        """
        for link in self.links:
            if intf_name == self.links[link]:
                return link

        return None

    def assignIntfName(self):
        """Checks all interfaces and assigns a new name for the new interface

        :returns name for the new interface
        :rtype str
        """
        if not self.properties["eth_intfs"]:
            return self.node_name + "-eth0"

        intf_count = 0
        intf_base = self.node_name + "-eth"
        intf_name = intf_base + str(intf_count)
        for index in range(len(self.properties["eth_intfs"])):
            if str(intf_name) in self.properties["eth_intfs"]:
                intf_count = intf_count + 1
                intf_name = intf_base + str(intf_count)
            else:
                break

        return intf_name

    def changeSceneNameTag(self, new_name):
        """
        Updates the name tag with its new content and changes
        its horizontal position in scene

        :param new_name: new text for the name tag
        :type new_name: str
        """
        tag = self.scene_tags["name"]
        tag.setPlainText(str(new_name))
        tag.setX((self.boundingRect().width() - tag.boundingRect().width()) / 2)

    def changeSceneIpTags(self):
        """
        Updates the IP tag with its new content and changes
        its horizontal position in scene
        """
        if "IP" not in self.scene_tags:
            return

        for eth in self.properties["eth_intfs"]:
            if eth in self.scene_tags["IP"]:
                tag = self.scene_tags["IP"][eth]
                tag.setPlainText(str(self.properties["eth_intfs"][eth]).split("/")[0])
                tag.setX((self.scene_tags["eth"][eth].boundingRect().width() - tag.boundingRect().width()) / 2)
            elif eth not in self.scene_tags["IP"] and self.properties["eth_intfs"][eth] != "":
                scene = self.scene()
                eth_tag = self.scene_tags["eth"][eth]
                if scene is not None and isinstance(scene, SceneGUI):
                    scene.addSceneLinkIpTags(self, eth, eth_tag)

    def nodePropertiesDialog(self):
        """
        Allows user to change the node's parameters or access
        to net information
        """
        # Creating dialog according to node type
        if self.node_type == "Host":
            dialog = HostDialog(self)
        elif self.node_type == "Switch":
            dialog = SwitchDialog(self)
        elif self.node_type == "Router":
            dialog = RouterDialog(self)
        else:
            return

        if dialog.exec() and self.node_type != "Switch":
            scene = self.scene()

            # Node name
            new_name = dialog.results["node_name"].text()
            if isinstance(scene, SceneGUI) and new_name != self.node_name and scene.isFeasibleName(new_name):
                scene.scene_nodes[new_name] = scene.scene_nodes.pop(self.node_name)
                self.node_name = new_name
                self.changeSceneNameTag(new_name)

            # IP Address per Ethernet interface
            if "eth_intfs_ip" in dialog.results:
                for eth in dialog.results["eth_intfs_ip"]:
                    new_eth_ip = dialog.results["eth_intfs_ip"][eth].text()
                    new_eth_mask = dialog.results["eth_intfs_mask"][eth].text()
                    if len(new_eth_ip) > 0 and len(new_eth_mask) > 0:
                        self.properties["eth_intfs"][eth] = str(new_eth_ip) + "/" + str(new_eth_mask)
                        if eth == (self.node_name + "-eth0"):
                            self.properties["IP"] = new_eth_ip
                            self.properties["PrefixLen"] = new_eth_mask

            # Link status
            if "eth_intfs_state" in dialog.results:
                for eth in dialog.results["eth_intfs_state"]:
                    new_eth_state = dialog.results["eth_intfs_state"][eth].isChecked()
                    scene.scene_links[self.searchLinkByIntf(eth)].setLinkState(new_eth_state)
                    if scene.net_running:
                        self.net_controller.updateNetLinkStatus(scene.scene_links[self.searchLinkByIntf(eth)])

            # Changes are added to scene
            self.changeSceneIpTags()
            scene.updateSceneLinks(self)

            # If needed, update Mininet nodes with new information
            if scene.net_running:
                self.net_controller.updateNetNodeInterfaces(self)

    def changePixmapColor(self, mode=None):
        """Changes the node's scene icon according to the selected tool

        :param mode: name of operation being executed (select or delete)
        :type mode: str
        """
        # Initial variables
        painter = QPainter()
        image = QImage(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        mask = QImage(image)
        mask_color = Qt.blue

        if mode is not None and mode == "Delete":
            mask_color = Qt.red

        # 1st layer
        painter.begin(mask)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(mask.rect(), mask_color)
        painter.end()

        # 2nd layer
        painter.begin(image)
        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
        painter.drawImage(0, 0, mask)
        painter.end()

        self.setPixmap(QPixmap(image))

    def updateIcon(self):
        """Updates the node's pixmap"""
        images = imagesMiniGUI()
        self.icon = images[self.node_type]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Event handlers

    def itemChange(self, change, value):
        """It is called when element is moved in the scene

        :param change: what kind of change the node has done
        :type change: QGraphicsItem.GraphicsItemChange
        :param value: value of the change
        :type value: QVariant
        """
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            scene = self.scene()
            if scene is not None and isinstance(scene, SceneGUI):
                scene.updateSceneLinks(self)

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        """It is called when user clicks with the mouse right button on the node

        :param event: application's event
        :type event: QGraphicsSceneContextMenuEvent
        """
        # Initialization
        context_menu = QMenu()
        scene = self.scene()

        if scene is None or not isinstance(scene, SceneGUI):
            return

        # Contextual menu changes according to the node's type: if Switch, menu is different
        if self.node_type != "Switch":
            # Properties menu
            menu_text = str(self.node_type) + " properties"
            properties_act = QAction(menu_text, self.net_controller)
            properties_act.setStatusTip("Open " + str(self.node_type).lower() + " properties menu")
            properties_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(properties_act)

            # XTerm
            xterm_act = QAction("XTerm", self.net_controller)
            xterm_act.setStatusTip("Open " + str(self.node_type).lower() + " XTerm")
            xterm_act.triggered.connect(lambda: self.net_controller.xterm(node=self))
            context_menu.addAction(xterm_act)
            if not scene.net_running:
                xterm_act.setEnabled(False)

        elif self.node_type == "Switch":
            # Switch MAC addresses list
            routing_act = QAction("See MAC addresses", self.net_controller)
            routing_act.setStatusTip("See switch learned MAC addresses")
            routing_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(routing_act)
            if not scene.net_running:
                routing_act.setEnabled(False)

        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        """It is called when link gains focus from the scene

        :param event: application's event
        :type event: QFocusEvent
        """
        self.setPixmap(self.image)
        self.changePixmapColor()

    def focusOutEvent(self, event):
        """It is called when link loses focus from the scene

        :param event: application's event
        :type event: QFocusEvent
        """
        self.setPixmap(self.image)

    def hoverEnterEvent(self, event):
        """It is called when pointer enters the link's space

        :param event: application's event
        :type event: QGraphicsSceneHoverEvent
        """
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, SceneGUI):
            scene_tool = node_scene.current_tool

        if scene_tool is not None and scene_tool == "Delete":
            self.changePixmapColor(mode="Delete")
        elif self.hasFocus():
            return
        else:
            self.changePixmapColor()

    def hoverLeaveEvent(self, event):
        """It is called when pointer leaves the link's space

        :param event: application's event
        :type event: QGraphicsSceneHoverEvent
        """
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, SceneGUI):
            scene_tool = node_scene.current_tool

        if scene_tool is not None and scene_tool == "Delete" and self.hasFocus():
            self.changePixmapColor()
        elif self.hasFocus():
            return
        else:
            self.setPixmap(self.image)


class LinkGUI(QGraphicsLineItem):
    """Represents the link that connects two nodes of SceneGUI class"""
    def __init__(self, x1, y1, x2, y2, net_ctrl=None):
        """
        :param x1: horizontal position of first link's end
        :type x1: float
        :param y1: vertical position of first link's end
        :type y1: float
        :param x2: horizontal position of second link's end
        :type x2: float
        :param y2: vertical position of second link's end
        :type y2: float
        :param net_ctrl: pointer to MiniGUI class (optional)
        :type net_ctrl: MiniGUI
        """
        super(LinkGUI, self).__init__(x1, y1, x2, y2)

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial attributes
        self.link_name = ""
        self.nodes = []
        self.is_up = True
        self.scene_tags = {}

        # Aesthetic attribute
        self.pen = QPen()

        # Setting up initial attributes
        self.setLinkAttributes()

    def setLinkAttributes(self):
        """Sets up the link's internal properties"""
        # Set color and width of the link
        self.pen.setWidth(2)
        if APP_THEME == "light":
            self.pen.setColor(Qt.gray)
        else:
            self.pen.setColor(Qt.darkGray)

        self.setPen(self.pen)

        # Setting of internal attributes
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

    # Auxiliary functions

    def isLinkUp(self):
        """Returns a boolean with the link state

        :returns the state of the link
        :rtype bool
        """
        return self.is_up

    def setLinkState(self, is_up=True):
        """Sets up the link's state and modifies its style accordingly

        :param is_up: new link's state
        :type is_up: bool
        """
        # Setting up new link's state
        self.is_up = is_up

        # Modification of link's style
        if is_up:
            self.pen.setStyle(Qt.SolidLine)
        else:
            self.pen.setStyle(Qt.DashLine)

        self.changeLineColor()

    def updateEndPoint(self, x2, y2):
        """Changes the position of one of the ends of the line

        :param x2: new horizontal position of link's end
        :type x2: float
        :param y2: new vertical position of link's end
        :type y2: float
        """
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    def deleteSceneTags(self):
        """Deletes all the scene tags related to this link"""
        scene = self.scene()
        if scene is not None and isinstance(scene, SceneGUI):
            tags = self.scene_tags
            for tag in tags:
                scene.removeItem(tags[tag])

    def changeLineColor(self):
        """
        Changes the line color attending the link's state and if
        the scene is focused on the item
        """
        if self.is_up and self.hasFocus():
            self.pen.setColor(Qt.darkBlue)
        elif self.is_up and not self.hasFocus() and APP_THEME == "light":
            self.pen.setColor(Qt.gray)
        elif self.is_up and not self.hasFocus() and APP_THEME == "dark":
            self.pen.setColor(Qt.darkGray)
        elif not self.is_up and self.hasFocus():
            self.pen.setColor(Qt.darkRed)
        elif not self.is_up and not self.hasFocus():
            self.pen.setColor(Qt.red)

        self.setPen(self.pen)

    # Event handlers

    def focusInEvent(self, event):
        """It is called when link gains focus from the scene

        :param event: application's event
        :type event: QFocusEvent
        """
        self.changeLineColor()

    def focusOutEvent(self, event):
        """It is called when link loses focus from the scene

        :param event: application's event
        :type event: QFocusEvent
        """
        self.changeLineColor()

    def hoverEnterEvent(self, event):
        """It is called when pointer enters the link's space

        :param event: application's event
        :type event: QGraphicsSceneHoverEvent
        """
        scene = self.scene()
        if self.is_up and scene.current_tool != "Delete":
            self.pen.setColor(Qt.darkBlue)
        else:
            self.pen.setColor(Qt.darkRed)

        self.setPen(self.pen)

    def hoverLeaveEvent(self, event):
        """It is called when pointer leaves the link's space

        :param event: application's event
        :type event: QGraphicsSceneHoverEvent
        """
        self.changeLineColor()


class SceneGUI(QGraphicsScene):
    """It displays the topology network created by the user"""
    def __init__(self, net_ctrl=None):
        """
        :param net_ctrl: reference to MiniGUI main class
        :type: MiniGUI
        """
        super(SceneGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Internal variables
        self.net_running = False
        self.current_tool = None
        self.scene_modified = False

        # Node & Link dictionaries
        self.scene_nodes = {}
        self.scene_links = {}

        # Item counting initialization
        self.item_count = {"Host": 0, "Switch": 0, "Router": 0, "Link": 0}
        self.item_letter = {"Host": "h", "Switch": "s", "Router": "r", "Link": "l"}

        # Event handling initialization
        self.new_link = None
        self.link_orig_node = None

        # IP address related variables
        self.default_ip_last = 1
        self.default_ip_base = "10.0.0."
        self.default_ip = self.default_ip_base + str(self.default_ip_last)

    # Scene-related functions

    @staticmethod
    def addSceneNodeNameTag(node, name):
        """Creates a name tag and links it to the node

        :param node: reference to node object
        :type node: NodeGUI
        :param name: node name assigned to tag
        :type name: str
        """
        name_tag = NameTagGUI(name, node)
        node.scene_tags["name"] = name_tag
        new_pos_x = (node.boundingRect().width() - name_tag.boundingRect().width()) / 2
        new_pos_y = node.boundingRect().bottomLeft().y()
        name_tag.setPos(new_pos_x, new_pos_y)

    def addSceneNode(self, x, y, node_type, name=None, properties=None):
        """Adds a new node to the scene

        :param x: node's horizontal position in scene
        :type x: float
        :param y: node's vertical position in scene
        :type y: float
        :param node_type: node's type
        :type node_type: str
        :param name: node's name (optional)
        :type name: str
        :param properties: node's properties
        :type properties: dict
        :returns node object
        :rtype NodeGUI
        """
        # Property checking (in case the node is loaded up from previous project)
        if properties is None and node_type != "Switch":
            node_properties = {"IP": self.default_ip, "PrefixLen": 8}
            self.default_ip_last = self.default_ip_last + 1
            self.default_ip = self.default_ip_base + str(self.default_ip_last)
        else:
            node_properties = properties

        # Name checking
        if name is not None:
            node_new = False
            node_name = name
        else:
            node_new = True
            while True:
                node_name = self.item_letter[node_type] + str(self.item_count[node_type])
                if self.isFeasibleName(node_name):
                    break
                else:
                    self.item_count[node_type] = self.item_count[node_type] + 1

        # Creation of node and saving into scene's node list
        node = NodeGUI(x, y, node_type, node_name, node_properties, node_new, self.net_controller)
        self.scene_nodes[node_name] = node

        # Addition of node to scene, gaining focus and modifying the scene
        self.addSceneNodeNameTag(node, node_name)
        self.addItem(node)
        node.setFocus()

        # Modification of scene's state variables
        self.scene_modified = True
        self.item_count[node_type] = self.item_count[node_type] + 1

        return node

    def addSceneLink(self, x, y):
        """Initiates the process of creation of a new link in the scene

        :param x: link's first end horizontal position in scene
        :type x: float
        :param y: node's first end vertical position in scene
        :type y: float
        """
        self.new_link = LinkGUI(x, y, x, y, net_ctrl=self.net_controller)
        self.addItem(self.new_link)

    @staticmethod
    def checkNodeIpTag(node, eth):
        """Returns boolean depending on if IP tag must be created or not

        :param node: reference o node object
        :type node: NodeGUI
        :param eth: interface name
        :type eth: str
        :returns evaluation if an IP tag is needed or not
        :rtype bool
        """
        if node.node_type != "Switch":
            node_eths = node.properties["eth_intfs"]
            if eth in node_eths and node_eths[eth] != "":
                return True

        return False

    @staticmethod
    def addSceneLinkIpTags(node, eth, eth_tag):
        """Adds a IP tag for a node to the scene

        :param node: reference to node object
        :type node: NodeGUI
        :param eth: interface related to IP address tag
        :type eth: str
        :param eth_tag: interface tag
        :type eth_tag: EthTagGUI
        """
        # Getting IP address from interface
        node_ip_dict = node.properties["eth_intfs"]
        tag_text = node_ip_dict[eth].split("/")[0]

        # Creating IP tag and association with node
        ip_tag = IpTagGUI(tag_text, eth_tag)
        node.scene_tags["IP"][str(eth)] = ip_tag

        # Location of IP tag in scene
        ip_tag_x_pos = (eth_tag.boundingRect().width() - ip_tag.boundingRect().width()) / 2
        ip_tag_y_pos = eth_tag.boundingRect().bottomLeft().y() * 0.75
        ip_tag.setPos(ip_tag_x_pos, ip_tag_y_pos)

    def addSceneLinkEthTags(self, orig_node, orig_eth, dest_node, dest_eth):
        """Creates and adds the Ethernet interface (& IP) tags to scene

        :param orig_node: reference to first node object
        :type orig_node: NodeGUI
        :param orig_eth: first node interface name
        :type orig_eth: str
        :param dest_node: reference to second node object
        :type dest_node: NodeGUI
        :param dest_eth: second node interface name
        :type dest_eth: str
        """
        # Creating the interface tags
        orig_tag = EthTagGUI(orig_eth, None)
        dest_tag = EthTagGUI(dest_eth, None)

        # Storing pointer in link and scene
        self.new_link.scene_tags[orig_node.node_name] = orig_tag
        self.new_link.scene_tags[dest_node.node_name] = dest_tag
        orig_node.scene_tags["eth"][orig_eth] = orig_tag
        dest_node.scene_tags["eth"][dest_eth] = dest_tag
        self.addItem(orig_tag)
        self.addItem(dest_tag)

        # Checking if ip tag must be crated along
        if self.checkNodeIpTag(orig_node, orig_eth):
            self.addSceneLinkIpTags(orig_node, orig_eth, orig_tag)

        if self.checkNodeIpTag(dest_node, dest_eth):
            self.addSceneLinkIpTags(dest_node, dest_eth, dest_tag)

        # Update of newest tags' position within the scene
        self.updateSceneLinkTags(self.new_link, orig_node, dest_node)

    def finishSceneLink(self, name=None):
        """Finishes the creation process of a link between two nodes

        :param name: link's name (optional)
        :type name: str
        """
        # Retrieving information from link and selected nodes
        line = self.new_link.line()
        orig_node = self.itemAt(line.p1(), QTransform())
        dest_node = self.itemAt(line.p2(), QTransform())
        if not isinstance(orig_node, NodeGUI) or not isinstance(dest_node, NodeGUI):
            return

        # Link's naming (if needed)
        if name is None:
            while True:
                new_name = self.item_letter["Link"] + str(self.item_count["Link"])
                if self.isFeasibleName(new_name):
                    break
                else:
                    self.item_count["Link"] = self.item_count["Link"] + 1
        else:
            new_name = name

        # Updating of link information in both elements and link
        self.new_link.link_name = new_name
        self.new_link.nodes = [orig_node.node_name, dest_node.node_name]
        self.scene_links[new_name] = self.new_link

        # Adding new link to node and new interface tags to scene
        orig_eth = orig_node.addNewLink(new_name)
        dest_eth = dest_node.addNewLink(new_name)
        self.addSceneLinkEthTags(orig_node, orig_eth, dest_node, dest_eth)

        # Resetting temporary variables to initial state
        self.new_link = None
        self.link_orig_node = None
        self.scene_modified = True

    @staticmethod
    def updateSceneLinkTags(link, orig_node, dest_node):
        """Moves and allocates the interface and IP scene tags correctly

        :param link: reference to the moved link
        :type link: LinkGUI
        :param orig_node: reference to first node object
        :type orig_node: NodeGUI
        :param dest_node: reference to second node object
        :type dest_node: NodeGUI
        """
        # New positions of nodes (and line)
        line = link.line()
        orig_pos_x = line.x1()
        orig_pos_y = line.y1()
        dest_pos_x = line.x2()
        dest_pos_y = line.y2()

        # Calculating absolute horizontal and vertical distance
        long_x = abs(orig_pos_x - dest_pos_x)
        long_y = abs(orig_pos_y - dest_pos_y)

        # Getting tags to update their position
        link_tags = link.scene_tags
        link_orig_tag = link_tags[orig_node.node_name]
        link_dest_tag = link_tags[dest_node.node_name]

        # Horizontal axis offset correction
        orig_tag_offset_x = abs(link_orig_tag.boundingRect().width() / 2)
        dest_tag_offset_x = abs(link_dest_tag.boundingRect().width() / 2)
        orig_tag_offset_y = link_orig_tag.boundingRect().center().y() - link_orig_tag.boundingRect().topLeft().y()
        dest_tag_offset_y = link_dest_tag.boundingRect().center().y() - link_dest_tag.boundingRect().topLeft().y()

        # If node's interface has an IP tag associated, vertical axis must be corrected to with an offset
        if link_orig_tag.childItems():
            ip_orig_tag_offset = orig_tag_offset_y
        else:
            ip_orig_tag_offset = orig_tag_offset_y * math.atan2(long_x, long_y) / (math.pi / 2)

        if link_dest_tag.childItems():
            ip_dest_tag_offset = dest_tag_offset_y
        else:
            ip_dest_tag_offset = dest_tag_offset_y * math.atan2(long_x, long_y) / (math.pi / 2)

        # Tag's location update according to relative position of both nodes
        if orig_pos_x > dest_pos_x and orig_pos_y > dest_pos_y:
            link_orig_tag.setPos(orig_pos_x - (long_x / 4) - orig_tag_offset_x,
                                 orig_pos_y - (long_y / 4) - orig_tag_offset_y - ip_orig_tag_offset)
            link_dest_tag.setPos(dest_pos_x + (long_x / 4) - dest_tag_offset_x,
                                 dest_pos_y + (long_y / 4) - dest_tag_offset_y - ip_dest_tag_offset)
        elif orig_pos_x > dest_pos_x and orig_pos_y < dest_pos_y:
            link_orig_tag.setPos(orig_pos_x - (long_x / 4) - orig_tag_offset_x,
                                 orig_pos_y + (long_y / 4) - orig_tag_offset_y - ip_orig_tag_offset)
            link_dest_tag.setPos(dest_pos_x + (long_x / 4) - dest_tag_offset_x,
                                 dest_pos_y - (long_y / 4) - dest_tag_offset_y - ip_dest_tag_offset)
        elif orig_pos_x < dest_pos_x and orig_pos_y > dest_pos_y:
            link_orig_tag.setPos(orig_pos_x + (long_x / 4) - orig_tag_offset_x,
                                 orig_pos_y - (long_y / 4) - orig_tag_offset_y - ip_orig_tag_offset)
            link_dest_tag.setPos(dest_pos_x - (long_x / 4) - dest_tag_offset_x,
                                 dest_pos_y + (long_y / 4) - dest_tag_offset_y - ip_dest_tag_offset)
        elif orig_pos_x < dest_pos_x and orig_pos_y < dest_pos_y:
            link_orig_tag.setPos(orig_pos_x + (long_x / 4) - orig_tag_offset_x,
                                 orig_pos_y + (long_y / 4) - orig_tag_offset_y - ip_orig_tag_offset)
            link_dest_tag.setPos(dest_pos_x - (long_x / 4) - dest_tag_offset_x,
                                 dest_pos_y - (long_y / 4) - dest_tag_offset_y - ip_dest_tag_offset)

    def updateSceneLinks(self, node):
        """Updates links position if one of the nodes moves

        :param node: reference to node object
        :type node: NodeGUI
        """
        # Initial variables
        node_links = node.links
        node_name = node.node_name
        node_pos = node.scenePos()

        # Updating scene variable
        self.scene_modified = True

        # If there is no link related to the node, functions returns
        if not node_links:
            return

        # If there are links related to the node, each one of them is updated
        for link in node_links:
            for linked_node_name in self.scene_links[link].nodes:
                if linked_node_name != node_name:
                    dest_node = self.scene_nodes[linked_node_name]
                    dest_node_pos = dest_node.scenePos()
                    offset_node = node.boundingRect().center()
                    offset_dest_node = dest_node.boundingRect().center()
                    self.scene_links[link].setLine(node_pos.x() + offset_node.x(),
                                                   node_pos.y() + offset_node.y(),
                                                   dest_node_pos.x() + offset_dest_node.x(),
                                                   dest_node_pos.y() + offset_dest_node.y())
                    self.updateSceneLinkTags(self.scene_links[link], node, dest_node)

    def removeSceneItem(self, item):
        """Deletes a node/link from the scene and all links related to it

        :param item: item to be deleted
        :type item: QGraphicsItem
        """
        # Initial variable in order to remove links later
        links_to_remove = []

        # If item to delete is a node, extract its links and delete the item
        if isinstance(item, NodeGUI):
            self.scene_nodes.pop(item.node_name)
            self.removeItem(item)
            for link in item.links:
                links_to_remove.append(link)

        # If item to delete is a link, extract its name
        if isinstance(item, LinkGUI):
            links_to_remove.append(item.link_name)

        # Update of all elements related to the to-be-deleted item
        for link in links_to_remove:
            self.scene_links[link].deleteSceneTags()
            self.removeItem(self.scene_links[link])
            self.scene_links.pop(link)
            for node in self.scene_nodes:
                if link in self.scene_nodes[node].links:
                    self.scene_nodes[node].deleteLink(link)

        self.scene_modified = True

    def loadScene(self, data):
        """Loads the network topology from external file

        :param data: structured network topology data
        :type data: dict
        """
        # Addition of nodes to the scene
        if "nodes" in data:
            nodes_list = data["nodes"]
            for node in nodes_list:
                try:
                    node_name = node["name"]
                    node_type = node["type"]
                    node_x_pos = node["x_pos"]
                    node_y_pos = node["y_pos"]
                    node_links = node["links"]
                    node_properties = node["properties"]
                except KeyError:
                    dialog = QMessageBox()
                    dialog.setIcon(QMessageBox.Warning)
                    dialog.setTextFormat(Qt.RichText)
                    dialog.setText("<b>Mininet topology file corrupted</b>")
                    dialog.setInformativeText("Project nodes data is corrupted."
                                              "Please, verify JSON format is correct.")
                    dialog.exec()
                    return
                else:
                    new_node = self.addSceneNode(node_x_pos, node_y_pos, node_type, node_name, node_properties)
                    new_node.links = node_links
        else:
            return

        # Addition of links to the scene
        if "links" in data:
            links_list = data["links"]
            for link in links_list:
                try:
                    link_nodes = link["nodes"]
                    link_state = link["state"]
                    link_name = link["name"]
                except KeyError:
                    dialog = QMessageBox()
                    dialog.setIcon(QMessageBox.Warning)
                    dialog.setTextFormat(Qt.RichText)
                    dialog.setText("<b>Mininet topology file corrupted</b>")
                    dialog.setInformativeText("Project links data is corrupted."
                                              "Please, verify JSON format is correct.")
                    dialog.exec()
                    return
                else:
                    scene_element = []
                    for node_name in link_nodes:
                        scene_element.append(self.scene_nodes[node_name])

                # Associating the links to its correspondent nodes
                orig_coor = scene_element[0].scenePos() + scene_element[0].boundingRect().center()
                dest_coor = scene_element[1].scenePos() + scene_element[1].boundingRect().center()
                self.addSceneLink(orig_coor.x(), orig_coor.y())
                self.new_link.updateEndPoint(dest_coor.x(), dest_coor.y())
                self.new_link.setLinkState(link_state)
                self.finishSceneLink(name=link_name)

        self.scene_modified = False

    def saveScene(self):
        """Saves the current network topology of the project

        :returns: structured network topology data
        :rtype: dict
        """
        # Initial variables
        file_dictionary = {}
        nodes_saved = []
        links_saved = []

        # Saving nodes
        for item in self.scene_nodes:
            node = {
                "name": self.scene_nodes[item].node_name,
                "type": self.scene_nodes[item].node_type,
                "x_pos": self.scene_nodes[item].scenePos().x(),
                "y_pos": self.scene_nodes[item].scenePos().y(),
                "links": self.scene_nodes[item].links,
                "properties": self.scene_nodes[item].properties
            }
            nodes_saved.append(node)

        # Saving links
        for item in self.scene_links:
            link = {
                "name": self.scene_links[item].link_name,
                "nodes": self.scene_links[item].nodes,
                "state": self.scene_links[item].isLinkUp()
            }
            links_saved.append(link)

        file_dictionary["nodes"] = nodes_saved
        file_dictionary["links"] = links_saved

        self.scene_modified = False

        return file_dictionary

    # Auxiliary functions

    def isFeasibleName(self, name):
        """Checks if a given name is already taken or not"""
        if len(name) == 0:
            return False

        for item in self.items():
            if isinstance(item, NodeGUI) and item.node_name == name:
                return False
            elif isinstance(item, LinkGUI) and item.link_name == name:
                return False

        return True

    def isFeasibleLink(self, dest_item):
        """Checks if the connection between two items is possible

        :param dest_item: item selected at the end of the linking process
        :type dest_item: QGraphicsItem
        :returns feasibility of the link
        :rtype bool
        """
        # Checking if the second item is the link itself or the first node
        if dest_item == self.link_orig_node or dest_item == self.new_link:
            return False
        # Checking if the link between the two items is allowed
        elif (isinstance(self.link_orig_node, NodeGUI) and
                isinstance(dest_item, NodeGUI) and
                self.link_orig_node.node_type == "Host" and
                dest_item.node_type == "Host"):
            return False
        else:
            # Checking if there is already a link between these two nodes
            orig_node_links = self.link_orig_node.links
            for orig_link in orig_node_links:
                if orig_link in dest_item.links:
                    return False

        return True

    def selectSceneItem(self, item):
        """
        Changes the focus and the selection of the scene to the element
        that the user has clicked on

        :param item: scene element, selected by the user
        :type item: QGraphicsItem
        """
        if not isinstance(item, (NodeGUI, LinkGUI)):
            return

        # Clearing scene's attention spot from previous item (if needed)
        self.clearSelection()
        self.clearFocus()

        # Selecting and focusing on item
        item.setSelected(True)
        item.setFocus()

    # Event handlers

    def event(self, event):
        """It is called when there are application changes such as palette

        :param event: application's event
        :type event: QEvent
        """
        if event.type() == QEvent.PaletteChange:
            for item in self.items():
                if isinstance(item, (IpTagGUI, EthTagGUI, NameTagGUI)):
                    item.updateColor()
                elif isinstance(item, LinkGUI):
                    item.changeLineColor()
                elif isinstance(item, NodeGUI):
                    item.updateIcon()

        return QGraphicsScene.event(self, event)

    def keyPressEvent(self, event):
        """It is called when user presses keys in the keyboard

        :param event: application's event
        :type event: QKeyEvent
        """
        # If Mininet is running, deleting is not available
        if self.net_running:
            return

        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            item = self.focusItem()
            if item is not None:
                self.removeSceneItem(item)

    def mousePressEvent(self, event):
        """It is called when user presses the mouse on the scene

        :param event: application's event
        :type event: QGraphicsSceneMouseEvent
        """
        # Checking if link creation process has been stopped
        if self.new_link is not None:
            self.removeItem(self.new_link)
            self.link_orig_node = None
            self.new_link = None

        if self.current_tool == "Select":
            super().mousePressEvent(event)
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None:
                self.selectSceneItem(item)
            else:
                self.clearSelection()
        elif self.current_tool == "Delete":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and not isinstance(item, TagGUI):
                self.removeSceneItem(item)
        elif self.current_tool == "Link":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and isinstance(item, NodeGUI):
                self.link_orig_node = item
                offset = item.boundingRect().center()
                self.addSceneLink(item.scenePos().x() + offset.x(), item.scenePos().y() + offset.y())
        elif event.button() == Qt.LeftButton:
            self.addSceneNode(event.scenePos().x(), event.scenePos().y(), self.current_tool)
            self.selectSceneItem(self.focusItem())

    def mouseMoveEvent(self, event):
        """It is called when user moves the mouse over the scene

        :param event: application's event
        :type event: QGraphicsSceneMouseEvent
        """
        super().mouseMoveEvent(event)
        if self.current_tool == "Link" and self.new_link is not None:
            self.new_link.updateEndPoint(event.scenePos().x(), event.scenePos().y())

    def mouseReleaseEvent(self, event):
        """It is called when user stops pressing the mouse on the scene

        :param event: application's event
        :type event: QGraphicsSceneMouseEvent
        """
        super().mouseReleaseEvent(event)
        if self.current_tool == "Link" and self.new_link is not None:
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and self.isFeasibleLink(item):
                offset = item.boundingRect().center()
                self.new_link.updateEndPoint(item.scenePos().x() + offset.x(), item.scenePos().y() + offset.y())
                self.selectSceneItem(self.new_link)
                self.finishSceneLink()
            else:
                self.removeItem(self.new_link)
                self.link_orig_node = None
                self.new_link = None


# Application main class

class MiniGUI(QMainWindow):
    """It holds all the application's structure: scene, tools, etc."""
    def __init__(self):
        super(MiniGUI, self).__init__()

        # Main window components
        self.menu_bar = QMenuBar()
        self.tool_bar = QToolBar()
        self.status_bar = QStatusBar()
        self.net_button = QToolButton()
        self.tool_buttons = QButtonGroup()
        self.net_indicators = {}

        # Scene-related variables
        self.canvas = QGraphicsView()
        self.scene = SceneGUI(net_ctrl=self)

        # Mininet-related variables
        self.net = None
        self.thread_cli = None
        self.thread_updater = None

        # Auxiliary variables
        self.project_path = None
        self.app_prefs = {"LastProjectPath": "", "Mode": "basic", "CLI": True}

        # Modification of internal properties
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # User preferences retrieval
        self.setPreferencesGUI()

        # Main window initialization
        self.setMainWindowGUI()
        self.setStatusBarGUI()
        self.setMenuBarGUI()
        self.setToolBarGUI()

    # Main window initialization functions

    def setPreferencesGUI(self):
        """
        Checks and retrieves the user preferences from previous
        sessions through external configuration files
        """
        # Retrieval of external file
        settings = QSettings('MiniGUI', 'settings')

        # Application theme assignation
        global APP_THEME
        APP_THEME = settings.value('AppTheme')
        if APP_THEME is None:
            APP_THEME = "light"
        elif APP_THEME == "dark":
            changeAppPalette()

        # Application mode assignation
        app_mode = settings.value('AppMode')
        if app_mode not in ["basic", "advanced"]:
            self.app_prefs["Mode"] = "basic"
        else:
            self.app_prefs["Mode"] = app_mode

        # Use of CLI in Mininet executions
        app_cli = settings.value('AppCLI')
        if app_cli == "True":
            self.app_prefs["CLI"] = True
        else:
            self.app_prefs["CLI"] = False

        # Directory of last opened project
        self.app_prefs["LastProjectPath"] = settings.value("ProjectPath")

    def setMainWindowGUI(self):
        """
        Sets the internal values of the main window base class:
        geometry, size, title, font and central widget
        """
        # Geometry, size and title assignation
        self.setMinimumSize(500, 300)
        self.setWindowTitle("MiniGUI")
        self.setGeometry(500, 200, 1000, 600)

        # Scene allocation within main window
        self.canvas.setScene(self.scene)
        self.setCentralWidget(self.canvas)

        # Application's font modification
        font = app.font()
        font.setPixelSize(14)
        app.setFont(font)

    def setStatusBarGUI(self):
        """Organises the main window's status bar"""
        # Assignation of status bar to main window
        self.setStatusBar(self.status_bar)

        # Adding 1st permanent label: net status through text
        label_widget = QLabel("Mininet network is not active")
        self.status_bar.addPermanentWidget(label_widget)
        self.net_indicators["Text"] = label_widget

        # Adding 2nd permanent label: net status through coloured square
        color_widget = QWidget()
        color_widget.setFixedWidth(20)
        color_widget.setStyleSheet("background-color: red")
        self.status_bar.addPermanentWidget(color_widget)
        self.net_indicators["Color"] = color_widget

    def setMenuBarGUI(self):
        """Organises the main window's menu bar"""
        # Assignation
        self.setMenuBar(self.menu_bar)

        # Submenus definition and addition to menu bar
        file_menu = self.menu_bar.addMenu("File")
        pref_menu = self.menu_bar.addMenu("Preferences")
        help_menu = self.menu_bar.addMenu("About")

        # Submenus options
        new_action = QAction("New", self)
        open_action = QAction("Open", self)
        save_action = QAction("Save", self)
        save_as_action = QAction("Save as", self)
        quit_action = QAction("Quit", self)
        app_theme_action = QAction("Dark theme", self)
        app_mode_action = QAction("Advanced mode", self)
        app_cli_action = QAction("CLI terminal", self)
        about_action = QAction("About MiniGUI", self)

        # Action keyboard shortcuts
        new_action.setShortcut("Ctrl+N")
        open_action.setShortcut("Ctrl+O")
        save_action.setShortcut("Ctrl+S")
        save_as_action.setShortcut("Ctrl+Alt+S")
        quit_action.setShortcut("Ctrl+Q")
        about_action.setShortcut("F1")

        # Action properties definition and update according to
        # retrieved user preferences (if needed)
        app_theme_action.setCheckable(True)
        app_mode_action.setCheckable(True)
        app_cli_action.setCheckable(True)

        if APP_THEME == "dark":
            app_theme_action.setChecked(True)
        if self.app_prefs["Mode"] == "advanced":
            app_mode_action.setChecked(True)
        if self.app_prefs["CLI"]:
            app_cli_action.setChecked(True)

        # Action status tips
        new_action.setStatusTip("Create a new project")
        open_action.setStatusTip("Open an existing project")
        save_action.setStatusTip("Save the current project")
        save_as_action.setStatusTip("Save the current project as another")
        quit_action.setStatusTip("Exit MiniGUI")
        app_theme_action.setStatusTip("Change between light & dark theme")
        app_mode_action.setStatusTip("Change between basic & advanced mode")
        app_cli_action.setStatusTip("Use CLI terminal when scene is running or not")
        about_action.setStatusTip("Show information about MiniGUI")

        # Action connections to functions & events
        new_action.triggered.connect(self.newProject)
        open_action.triggered.connect(self.openProject)
        save_action.triggered.connect(self.saveProject)
        save_as_action.triggered.connect(self.saveProject)
        quit_action.triggered.connect(self.close)
        app_theme_action.toggled.connect(lambda: self.changePreferences(preference="theme"))
        app_mode_action.toggled.connect(lambda: self.changePreferences(preference="mode"))
        app_cli_action.toggled.connect(lambda: self.changePreferences(preference="CLI"))
        about_action.triggered.connect(self.showAbout)

        # Action additions to submenus
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)
        pref_menu.addAction(app_theme_action)
        pref_menu.addAction(app_mode_action)
        pref_menu.addAction(app_cli_action)
        help_menu.addAction(about_action)

    def setToolBarGUI(self):
        """Organises the main window's tool bar"""
        # Assignation
        self.addToolBar(self.tool_bar)

        # Tool bar properties modifications
        self.tool_bar.setMovable(False)
        self.tool_bar.setIconSize(QSize(50, 50))

        # Introduction of tools into the bar
        button_id = 1
        images = imagesMiniGUI()
        for button in images:
            # Button creation
            b = QToolButton()
            b.setCheckable(True)
            b.setText(str(button))
            b.setToolTip(str(button))
            b.setIcon(QIcon(images[button]))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)

            if button not in ["Select", "Delete"]:
                # Status tip only for adding elements button
                b.setStatusTip("Adds a " + str(button).lower() + " to the scene")
            elif button == "Select":
                # Little spacer for aesthetic reason
                little_spacer = QWidget()
                little_spacer.setFixedWidth(100)
                self.tool_bar.addWidget(little_spacer)
                # Button modification
                b.setChecked(True)
                b.setStatusTip("Allows interaction with elements in the scene")
            elif button == "Delete":
                b.setStatusTip("Deletes an element of the scene")

            # Adding button to tool bar and button group
            self.tool_bar.addWidget(b)
            self.tool_buttons.addButton(b, button_id)
            button_id = button_id + 1

        # Connecting button group with method
        self.tool_buttons.buttonClicked.connect(lambda: self.setCurrentTool(self.tool_buttons.checkedButton().text()))

        # Big spacer for aesthetic purpose
        big_spacer = QWidget()
        big_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tool_bar.addWidget(big_spacer)

        # Mininet-related button modification
        self.updateNetButtonStyle()
        self.net_button.setText("Start")
        self.net_button.clicked.connect(lambda: self.accessNet())
        self.tool_bar.addWidget(self.net_button)

        # Choosing "Select" tool as default
        self.setCurrentTool("Select")

    # Main window modifying functions

    def disableMenuAndToolBar(self):
        """Disables both menu and tool bar"""
        self.setCurrentTool("Select")
        self.menu_bar.setEnabled(False)
        for button in self.tool_buttons.buttons():
            button.setEnabled(False)

    def enableMenuAndToolBar(self):
        """Enables both menu and tool bar"""
        self.menu_bar.setEnabled(True)
        self.setCurrentTool(self.tool_buttons.checkedButton().text())
        for button in self.tool_buttons.buttons():
            button.setEnabled(True)

    def setCurrentTool(self, tool_name):
        """Sets up the scene's current tool

        :param tool_name: name of the selected tool
        :type tool_name: str
        """
        self.scene.current_tool = tool_name

    def updateNetButtonStyle(self):
        """Updates the style of the Mininet-related button"""
        if APP_THEME == "light" and self.net is None:
            self.net_button.setStyleSheet("color: green; height: 50px; width: 60px; font: bold")
        elif APP_THEME == "light" and self.net is not None:
            self.net_button.setStyleSheet("color: red; height: 50px; width: 60px; font: bold")
        elif APP_THEME == "dark" and self.net is None:
            self.net_button.setStyleSheet("color: lime; height: 50px; width: 60px; font: bold;"
                                          "hover { background-color: rgb(53, 53, 53)}")
        elif APP_THEME == "dark" and self.net is not None:
            self.net_button.setStyleSheet("color: red; height: 50px; width: 60px; font: bold;"
                                          "hover { background-color: rgb(53, 53, 53)}")

    def updateNetIndicators(self):
        """Updates the information shown in the status bar related to Mininet status"""
        if self.net is None:
            self.net_indicators["Text"].setText("Mininet network is not active")
            self.net_indicators["Color"].setStyleSheet("background-color: red")
        elif self.net is not None:
            self.net_indicators["Text"].setText("Mininet network is active!")
            self.net_indicators["Color"].setStyleSheet("background-color: green")

    def updateToolBarIcons(self):
        """Updates the icon for each tool, according to app's theme"""
        images = imagesMiniGUI()
        for button in self.tool_buttons.buttons():
            button.setIcon(QIcon(images[button.text()]))

    # Scene-related functions

    def modifiedSceneDialog(self):
        """Dialog with important information for the user

        Creates a dialog, warns the user that his/her current project has
        not been saved and enables the decision to save it, continue
        without saving or cancel the action

        :returns: dialog with information
        :rtype: QMessageBox
        """
        dialog = QMessageBox(self)
        dialog.setTextFormat(Qt.RichText)
        dialog.setText("<b>Scene has been modified</b>")
        dialog.setInformativeText("Do you want to save the scene?")
        dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Cancel | QMessageBox.Discard)
        dialog.setDefaultButton(QMessageBox.Save)
        dialog.setIcon(QMessageBox.Warning)

        return dialog.exec()

    def clearProject(self):
        """Clears the scene and its internal parameters"""
        # Main window cleaning
        self.app_prefs["LastProjectPath"] = self.project_path
        self.setWindowTitle("MiniGUI")
        self.project_path = None

        # Scene cleaning
        self.scene.clear()
        self.scene.scene_nodes.clear()
        self.scene.scene_links.clear()
        self.scene.scene_modified = False
        self.scene.default_ip_last = 1
        self.scene.default_ip = self.scene.default_ip_base + str(self.scene.default_ip_last)
        for tool in self.scene.item_count:
            self.scene.item_count[tool] = 0

    def newProject(self):
        """Creates a new project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        self.clearProject()

    def openProject(self):
        """This function opens a previous existing project"""
        # Modified scene checking
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        # Retrieval of last opened project (if done)
        if not self.app_prefs["LastProjectPath"]:
            directory = os.getcwd()
        else:
            directory = os.path.dirname(str(self.app_prefs["LastProjectPath"]))

        # New dialog to let the user choose the project to open
        file_path = QFileDialog.getOpenFileName(self, "Open file", directory,
                                                "Mininet topology (*.mn);;All files (*)", "")

        # File and format checking
        if file_path[0] != "":
            project_file = open(str(file_path[0]), "r")
            try:
                topology_data = json.load(project_file)
            except json.JSONDecodeError:
                dialog = QMessageBox()
                dialog.setIcon(QMessageBox.Warning)
                dialog.setTextFormat(Qt.RichText)
                dialog.setText("<b>Error decoding JSON format</b>")
                dialog.setInformativeText("This file does not have a JSON format."
                                          "Please, fix the issue and try again")
                dialog.exec()
                return
            else:
                self.clearProject()
                self.project_path = str(file_path[0])
                self.setWindowTitle("MiniGUI - " + str(file_path[0]).split("/")[-1])
                self.scene.loadScene(topology_data)

    def saveProject(self):
        """Saves the project information in an external file"""
        # Checking the action that triggered the function
        try:
            sender_text = self.sender().text()
        except AttributeError:
            sender_text = ""

        if self.project_path is None or sender_text == "Save as":
            result = QFileDialog.getSaveFileName(self, "Save file as", os.getcwd(),
                                                 "Mininet topology (*.mn);;All files (*)", "")

            if result[0]:
                file_path = str(result[0])
                if result[1].startswith("Mininet") and not result[0].endswith(".mn"):
                    file_path = file_path + ".mn"

                self.setWindowTitle("MiniGUI - " + file_path.split("/")[-1])
                self.app_prefs["LastProjectPath"] = file_path
                self.project_path = file_path
            else:
                return

        project_file = open(self.project_path, "w")
        json_file_dictionary = self.scene.saveScene()
        project_file.write(json.dumps(json_file_dictionary, sort_keys=True, indent=4, separators=(',', ':')))
        project_file.close()

    # Mininet-related functions

    def emptySceneDialog(self):
        """Creates a dialog to remind that the scene is empty

        :rtype: QMessageBox
        """
        dialog = QMessageBox(self)
        dialog.setTextFormat(Qt.RichText)
        dialog.setText("<b>Error! Scene is empty</b>")
        dialog.setInformativeText("Mininet cannot start with an empty scene. Please, add elements")
        dialog.setIcon(QMessageBox.Warning)

        return dialog.exec()

    def buildNodes(self):
        """Builds the Mininet node objects and adds them to the network"""
        for node in self.scene.scene_nodes:
            # Extraction of node's information
            node_addr = None
            node_name = self.scene.scene_nodes[node].node_name
            node_type = self.scene.scene_nodes[node].node_type
            node_properties = self.scene.scene_nodes[node].properties
            if node_type != "Switch":
                node_addr = str(node_properties['IP']) + "/" + str(node_properties['PrefixLen'])

            # Addition of nodes to the network
            if node_type == "Host":
                self.net.addHost(node_name, cls=None, ip=node_addr)
            elif node_type == "Router":
                self.net.addHost(node_name, cls=Router, ip=node_addr)
            elif node_type == "Switch":
                self.net.addSwitch(node_name, cls=None)

        # If no controller added and advanced mode is selected, one is introduced by default
        if self.app_prefs["Mode"] == "advanced" and not self.net.controllers:
            self.net.addController('c0')

    def buildLinks(self):
        """Builds the Mininet link objects between nodes"""
        for link in self.scene.scene_links:
            # Extraction of link's information
            nodes_linked = self.scene.scene_links[link].nodes
            if self.scene.scene_links[link].isLinkUp():
                link_status = "up"
            else:
                link_status = "down"

            # Retrieval of scene nodes to build link
            link_name = self.scene.scene_links[link].link_name
            node_1 = self.scene.scene_nodes[nodes_linked[0]]
            node_2 = self.scene.scene_nodes[nodes_linked[1]]

            # Initialization
            two_switches_linked = False
            one_switch_linked = False

            # Depending on which case both nodes are, actions will be taken
            if node_1.node_type == "Switch" and node_2.node_type == "Switch":
                two_switches_linked = True
            elif node_1.node_type != "Switch" and node_2.node_type == "Switch":
                one_switch_linked = True
            elif node_1.node_type == "Switch" and node_2.node_type != "Switch":
                node_1 = self.scene.scene_nodes[nodes_linked[1]]
                node_2 = self.scene.scene_nodes[nodes_linked[0]]
                one_switch_linked = True

            # 1st node information
            node_1_intfs = node_1.properties["eth_intfs"]
            node_1_links = node_1.links
            node_1_link_intf = node_1_links[link_name]
            node_1_link_ip = node_1_intfs[node_1_link_intf]

            # 2nd node information
            node_2_intfs = node_2.properties["eth_intfs"]
            node_2_links = node_2.links
            node_2_link_intf = node_2_links[link_name]
            node_2_link_ip = node_2_intfs[node_2_link_intf]

            # Mininet node object extraction
            net_node_1 = self.net.nameToNode[node_1.node_name]
            net_node_2 = self.net.nameToNode[node_2.node_name]

            # Creation of link depending on case
            if two_switches_linked:
                self.net.addLink(net_node_1, net_node_2,
                                 intfName1=str(node_1_link_intf), intfName2=str(node_2_link_intf))
            elif one_switch_linked:
                self.net.addLink(net_node_1, net_node_2, intfName1=str(node_1_link_intf),
                                 params1={'ip': str(node_1_link_ip)}, intfName2=str(node_2_link_intf))
            else:
                self.net.addLink(net_node_1, net_node_2,
                                 intfName1=str(node_1_link_intf), params1={'ip': str(node_1_link_ip)},
                                 intfName2=str(node_2_link_intf), params2={'ip': str(node_2_link_ip)})

            # Configuration of link's status
            self.net.configLinkStatus(nodes_linked[0], nodes_linked[1], link_status)

    def startNet(self):
        """Builds the Mininet network, starts it and disables scene modification"""
        # Net creation and start
        self.net = Mininet(topo=None, build=False)
        self.buildNodes()
        self.buildLinks()
        self.net.build()
        self.net.start()

        # Main window and scene modification
        self.updateNetIndicators()
        self.disableMenuAndToolBar()
        self.scene.net_running = True

        # Thread to update automatically the scene with Mininet info
        self.thread_updater = SceneAutoUpdate()
        self.thread_updater.updateSignal.connect(lambda: self.updateSceneInfo())
        self.thread_updater.start()

        # If basic mode has been selected, commands must be executed to inicialice Mininet correctly
        if self.app_prefs["Mode"] == "basic":
            for node in self.scene.scene_nodes:
                if self.scene.scene_nodes[node].node_type == "Switch":
                    switch_name = self.scene.scene_nodes[node].node_name
                    subprocess.run(['ovs-ofctl', 'add-flow', str(switch_name), 'action=normal'])

        # CLI creation
        if self.app_prefs["CLI"]:
            print("*** Starting CLI: please, write exit before exiting CLI to prevent GUI freezing")
            self.thread_cli = MiniCLI(self.net)
            self.thread_cli.start()

    def stopNet(self):
        """Stops the Mininet execution and enables back scene modification"""
        # XTerm cleanse
        cleanUpScreens()

        # CLI, thread to update scene automatically and net stop
        self.thread_updater.update_active = False
        self.thread_cli = None
        self.net.stop()
        self.net = None

        # Main window and scene modification
        self.updateNetIndicators()
        self.enableMenuAndToolBar()
        self.scene.net_running = False

    def accessNet(self):
        """Starts/stops Mininet execution and updates Mininet-related button accordingly"""
        # Mininet status checking
        if self.net_button.text() == "Start":
            if not self.scene.items():
                self.emptySceneDialog()
                return
            else:
                self.startNet()
                self.net_button.setText("Stop")
        elif self.net_button.text() == "Stop":
            self.stopNet()
            self.net_button.setText("Start")

        # Mininet-related button update
        self.updateNetButtonStyle()

    def updateNetNodeInterfaces(self, node):
        """Updates Mininet node's interface information when simulation is running

        :param node: object with node information
        :type node: NodeGUI
        """
        if self.net is None and not isinstance(node, NodeGUI):
            return

        # Retrieval of Mininet node
        net_node = self.net.nameToNode[node.node_name]

        # IP address update
        for intf in node.properties["eth_intfs"]:
            intf_addr = node.properties["eth_intfs"][intf]
            net_node.cmd("ifconfig " + str(intf) + " " + str(intf_addr))

    def updateNetNodeRoutingTable(self, node, command):
        """Updates Mininet node's routing table sending a command and gets its output.

        :param node: object with node information
        :type node: NodeGUI
        :param command: command to be sent to Mininet
        :type command: str
        :returns: command output or None
        :rtype: str or None
        """
        if self.net is None or not isinstance(node, NodeGUI):
            return

        net_node = self.net.nameToNode[node.node_name]
        result = net_node.cmdPrint(str(command))
        if len(result) != 0:
            return result
        else:
            return None

    def getNetNodeRoutingTable(self, node=None):
        """Retrieves the routing table for hosts and routers

        :param node: reference to node object
        :type node: NodeGUI
        :returns: dictionary empty or with tabulated data
        :rtype: dict
        """
        if self.net is None or not isinstance(node, NodeGUI):
            return

        net_node = self.net.nameToNode[node.node_name]
        result = net_node.cmdPrint("route -n")
        if len(result) == 0:
            return "Error"

        output = {"Destination": [], "Gateway": [], "Interface": []}

        index = 0
        ip_address = ""
        for element in result.split():
            if re.match(r"([0-9]+\.){3}[0-9]", element) and index % 4 == 0:
                index = index + 1
                if element == "0.0.0.0":
                    output["Destination"].append("default")
                else:
                    ip_address = str(element)
            elif re.match(r"([0-9]+\.){3}[0-9]", element) and index % 4 == 1:
                index = index + 1
                output["Gateway"].append(element)
            elif re.match(r"([0-9]+\.){3}[0-9]", element) and index % 4 == 2:
                index = index + 1
                if ip_address:
                    decimal_mask = 0
                    for element_byte in element.split("."):
                        decimal_mask = decimal_mask + bin(int(element_byte)).count("1")
                    output["Destination"].append(ip_address + "/" + str(decimal_mask))
                    ip_address = ""
            elif re.match(r"^[hr][0-9]+-eth[0-9]+", element) and index % 4 == 3:
                index = index + 1
                output["Interface"].append(element)

        return output

    def getSwitchStoredRoutes(self, node=None):
        """Returns the routing table of hosts and switch

        :param node: reference to node object
        :type node: NodeGUI
        :returns: dictionary empty or with tabulated data
        :rtype: dict
        """
        if self.net is None or not isinstance(node, NodeGUI) or node.node_type != "Switch":
            return

        # Command execution to obtain switch's routing table
        proc = subprocess.Popen(['ovs-appctl', 'fdb/show', str(node.node_name)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        (result, err) = proc.communicate()

        # Output checking
        if len(err) > 0:
            return None

        # Output parsing and structuring
        index = 0
        output = {"Port": [], "VLAN": [], "MAC": [], "Age": []}
        for element in result.split():
            if index > 3:
                if index % 4 == 0:
                    output["Port"].append(element)
                elif index % 4 == 1:
                    output["VLAN"].append(element)
                elif index % 4 == 2:
                    output["MAC"].append(element)
                elif index % 4 == 3:
                    output["Age"].append(element)

            index = index + 1

        return output

    def updateNetLinkStatus(self, link):
        """Updates Mininet link's status information when simulation is running

        :param link: object with link information
        :type link: LinkGUI
        """
        if self.net is None and not isinstance(link, LinkGUI):
            return

        # Retrieving link's status
        if link.isLinkUp():
            link_status = "up"
        else:
            link_status = "down"

        # Net link state update
        link_nodes = link.nodes
        self.net.configLinkStatus(link_nodes[0], link_nodes[1], link_status)

    def updateSceneInfo(self):
        """Updates the scene information with Mininet output automatically when triggered"""
        if self.net is None:
            return

        for node in self.scene.scene_nodes:
            if self.scene.scene_nodes[node].node_type != "Switch":
                # Initialization
                first_intf = True
                node_intfs = self.scene.scene_nodes[node].properties["eth_intfs"]
                net_node = self.net.nameToNode[self.scene.scene_nodes[node].node_name]

                # Interface information (IP address, netmask)
                for intf in node_intfs:
                    try:
                        output = net_node.cmdPrint("ip addr show dev " + str(intf))
                    except AssertionError:
                        pass
                    else:
                        new_ip = output.split("inet ")[1].split("/")[0]
                        new_mask = output.split(" brd")[1].split("/")[-1]
                        self.scene.scene_nodes[node].properties["eth_intfs"][intf] = (str(new_ip) + "/" + str(new_mask))
                        if first_intf:
                            self.scene.scene_nodes[node].properties["IP"] = new_ip
                            self.scene.scene_nodes[node].properties["PrefixLen"] = new_mask
                            first_intf = False

                # Scene modification
                self.scene.scene_nodes[node].changeSceneIpTags()
                self.scene.updateSceneLinks(self.scene.scene_nodes[node])

        # Link state (up or down)
        for link in self.scene.scene_links:
            node_name = self.scene.scene_links[link].nodes[0]
            intf_name = self.scene.scene_nodes[node_name].links[link]
            net_node = self.net.nameToNode[node_name]
            try:
                output = str(net_node.cmdPrint("ethtool " + str(intf_name)))
            except AssertionError:
                pass
            else:
                if output.split("Link detected: ")[1].split("\r\n")[0] == "yes":
                    self.scene.scene_links[link].setLinkState(is_up=True)
                else:
                    self.scene.scene_links[link].setLinkState(is_up=False)

        self.scene.scene_modified = True

    def xterm(self, node=None):
        """Creates a personal XTerm for an specific host or router

        :param node: reference to node object
        :type node: NodeGUI
        """
        # Checking if net is available and name is not none
        if self.net is None or node is None:
            return

        # Obtaining information from node object and creating xterm
        node_name = node.node_name
        node_type = node.node_type
        term = makeTerm(self.net.nameToNode[node_name], node_type)
        self.net.terms += term

    # Event handlers

    def closeEvent(self, event):
        """It is called when main window (application) is about to be closed

        :param event: application's event
        :type event: QEvent
        """
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                event.ignore()

        self.writePreferences()

    def showEvent(self, event):
        """It is called when the main window (application) is shown

        :param event: application's event
        :type event: QEvent
        """
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def resizeEvent(self, event):
        """It is called when the main window (application) is resized

        :param event: application's event
        :type event: QEvent
        """
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def changeEvent(self, event):
        """It is called when an external window parameter is changed (like palette)

        :param event: application's event
        :type event: QEvent
        """
        if event.type() == QEvent.PaletteChange:
            self.updateToolBarIcons()
            self.updateNetButtonStyle()
        else:
            QWidget.changeEvent(self, event)

    # User preference functions

    def writePreferences(self):
        """Saves the user's preferences in a external configuration file"""
        settings = QSettings('MiniGUI', 'settings')
        settings.setValue("AppTheme", str(APP_THEME))
        settings.setValue("AppMode", str(self.app_prefs["Mode"]))
        settings.setValue("AppCLI", str(self.app_prefs["CLI"]))
        if self.app_prefs["LastProjectPath"]:
            settings.setValue("ProjectPath", str(self.app_prefs["LastProjectPath"]))

    def changePreferences(self, preference=None):
        """Changes the user's preferences

        :param preference: option to change one of the app's preferences
        :type preference: str
        """
        if preference == "theme":
            global APP_THEME
            if APP_THEME == "light":
                APP_THEME = "dark"
            else:
                APP_THEME = "light"
            changeAppPalette()
        elif preference == "mode":
            if self.app_prefs["Mode"] == "basic":
                self.app_prefs["Mode"] = "advanced"
            else:
                self.app_prefs["Mode"] = "basic"
        elif preference == "CLI":
            if self.app_prefs["CLI"]:
                self.app_prefs["CLI"] = False
            else:
                self.app_prefs["CLI"] = True

    # Information function

    def showAbout(self):
        """Displays a new dialog with information about the application"""
        about = QDialog(self)
        about.setWindowTitle("About MiniGUI")

        layout_v = QVBoxLayout()
        layout_h = QHBoxLayout()

        if APP_THEME == "light":
            about_icon = QPixmap("./images/logo-urjc.png")
        else:
            about_icon = QPixmap("./images/logo-urjc_white.png")

        about_icon_resize = about_icon.scaled(128, 128, Qt.KeepAspectRatio)

        label1 = QLabel(about)
        label1.setPixmap(about_icon_resize)

        label2 = QLabel(about)
        label2.setText("MiniGUI: Graphical User Interface editor for Mininet\n\n"
                       "Author: Daniel Polo Álvarez (d.poloa@alumnos.urjc.es)\n\n"
                       "Universidad Rey Juan Carlos (URJC)")

        button = QDialogButtonBox(QDialogButtonBox.Ok)
        button.accepted.connect(about.accept)
        button.setCenterButtons(True)

        layout_h.addWidget(label1, alignment=Qt.AlignTop)
        layout_h.setSpacing(20)
        layout_h.addWidget(label2, alignment=Qt.AlignTop)
        layout_v.addLayout(layout_h)
        layout_v.addWidget(button, alignment=Qt.AlignCenter)

        about.setLayout(layout_v)

        about.show()


def imagesMiniGUI():
    """Returns a set of images depending on the mode selected: light or dark

    :returns: dictionary with the images path
    :rtype: dict
    """
    if APP_THEME == "light":
        return {
            "Host": "./images/laptop.png",
            "Switch": "./images/switch.png",
            "Router": "./images/router.png",
            "Link": "./images/cable.png",
            "Select": "./images/select.png",
            "Delete": "./images/delete.png"
        }
    else:
        return {
            "Host": "./images/laptop.png",
            "Switch": "./images/switch.png",
            "Router": "./images/router.png",
            "Link": "./images/cable_white.png",
            "Select": "./images/select_white.png",
            "Delete": "./images/delete_white.png"
        }


def changeAppPalette():
    """Changes the application palette according to the selected theme"""
    if APP_THEME == "light":
        palette = app.style().standardPalette()
        app.setPalette(palette)
    else:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)


if __name__ == '__main__':
    # Checking that the program is executed with superuser privileges
    if os.getuid() != 0:
        sys.exit('ERROR: MiniGUI must run as root. Use sudo ./MiniGUI.py')
    elif not os.path.isdir("/tmp/runtime-root"):
        os.makedirs("/tmp/runtime-root")

    # Information message for user
    print("Welcome to MiniGUI, version " + str(MINIGUI_VERSION) + "!")

    # Creation of environmental variable
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/runtime-root"

    # Application initialization
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    minigui = MiniGUI()
    minigui.show()
    sys.exit(app.exec())
