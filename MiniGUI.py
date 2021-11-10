#!/usr/bin/env python3

"""
MiniGUI: Interfaz gráfica de usuario para Mininet

Nombre provisional y programa en desarrollo. Este programa
permite al usuario utilizar una interfaz gráfica con la
cual puede crear redes de comunicación de una forma
sencilla.

Autor:          Daniel Polo Álvarez
Correo:         d.poloa@alumnos.urjc.es
Universidad:    Universidad Rey Juan Carlos
"""

# PyQt5 package import
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Python package import
import subprocess
import threading
import math
import json
import time
import sys
import os
import re

# Mininet package import
from mininet.net import Mininet
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Node
from mininet.cli import CLI

# Constants
DEFAULT_TIMER = 5.0
APP_THEME = "light"


# Thread classes

class MiniCLI(threading.Thread):
    """Thread class for Mininet CLI object, needed to not conflict with PyQt5 event loop"""
    def __init__(self, net=None):
        super(MiniCLI, self).__init__(daemon=True)
        self.net = net

    def run(self):
        if self.net is not None:
            CLI(self.net)
            print("CLI execution has finished")


class SceneAutoUpdate(QThread):
    """Thread class to update automatically the scene with information from Mininet objects"""
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
    def __init__(self, parent=None):
        super(BaseDialog, self).__init__(parent=parent)

        # Default buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Base layout for dialog
        self.base_layout = QVBoxLayout()
        self.base_layout.addWidget(button_box)
        self.setLayout(self.base_layout)


class HostDialog(BaseDialog):
    """Dialog class for hosts"""
    def __init__(self, host, parent=None):
        super(HostDialog, self).__init__(parent=parent)

        # Class attributes
        self.host = host
        self.results = {}

        # Modification of window's properties
        self.setWindowTitle("Host properties: " + str(host.node_name))
        self.setFixedWidth(450)

        self.setHostDialog()

    def setHostDialog(self):
        """This function structures the base layout in tabs"""
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setHostInformation(), "Information")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Interfaces")
        # Third tab: routing table
        tab_menu.addTab(self.setRoutingTable(), "Routing")

    def setHostInformation(self):
        """Function to show the host's name and retrieve it if changed by the user"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Hostname
        name_label = QLabel("Host name")
        name_edit_label = QLineEdit(str(self.host.node_name))
        self.results["node_name"] = name_edit_label

        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)
        layout.addStretch()

        return widget

    def setEthernetIntfs(self):
        """This function shows the Ethernet interfaces that the host has"""
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
            intf_name_label = QLabel(str(interface))
            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)
            eth_layout.addWidget(QLabel("/"), index + 1, 3)

            if host_intfs[interface] == "":
                eth_ip = ""
                eth_mask = ""
            else:
                eth_ip = host_intfs[interface].split("/")[0]
                eth_mask = host_intfs[interface].split("/")[1]

            intf_ip_label = QLineEdit(str(eth_ip))
            intf_ip_list[interface] = intf_ip_label

            intf_mask_label = QLineEdit(str(eth_mask))
            intf_mask_list[interface] = intf_mask_label

            eth_layout.addWidget(intf_ip_label, index + 1, 2)
            eth_layout.addWidget(intf_mask_label, index + 1, 4)

            intf_state_button = QCheckBox()
            intf_id = self.host.searchLinkByIntf(interface)
            if host_scene.sceneLinks[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            intf_state_list[interface] = intf_state_button
            eth_layout.addWidget(intf_state_button, index + 1, 6)

            index = index + 1

        self.results["eth_intfs_ip"] = intf_ip_list
        self.results["eth_intfs_mask"] = intf_mask_list
        self.results["eth_intfs_state"] = intf_state_list

        return widget

    def setRoutingTable(self):
        """This function shows the routing table of the host"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        widget.setLayout(layout)

        scene = self.host.scene()
        if not scene.net_running:
            label = QLabel("Routing table is not available as Mininet network is not active")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        route_list = self.host.net_controller.getRoutingTable(self.host)
        if route_list == "Error":
            label = QLabel("An error occurred getting the routing table. Please, restart the dialog")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # Apply command layout
        layout.addWidget(QLabel("Write down your route / ip route command:"))

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

    # Auxiliary functions for dynamic widget

    def sendCommandToNet(self, command, widget):
        """This function sends a command to the Mininet object and retrieves its output"""
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
        output = self.host.net_controller.updateRoutingTable(self.host, command)
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
            route_list = self.host.net_controller.getRoutingTable(self.host)
            self.updateRoutingTableLayout(widget, route_list)

    def updateRoutingTableLayout(self, route_widget, route_list):
        """This function is in charge of modifying the dynamic widget and update it"""
        if not isinstance(route_widget, QWidget):
            return

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
    """Dialog class for switches"""
    def __init__(self, switch, parent=None):
        super(SwitchDialog, self).__init__(parent=parent)

        # Class attributes
        self.switch = switch

        # Modification of window's properties
        self.setWindowTitle("Switch routing table: " + str(switch.node_name))
        self.setFixedWidth(300)

        self.showMacDirectionsTable()

    def showMacDirectionsTable(self):
        """This function shows the result of command 'ovs-appctl fdb/show' applied on the switch"""
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
    """Dialog class for routers"""
    def __init__(self, router, parent=None):
        super(RouterDialog, self).__init__(parent=parent)

        # Class attributes
        self.results = {}
        self.router = router

        # Modification of window's properties
        self.setWindowTitle("Router properties: " + str(router.node_name))
        self.setFixedWidth(450)

        self.setRouterDialog()

    def setRouterDialog(self):
        """This function structures the base layout in tabs"""
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setRouterInformation(), "Information")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Interfaces")
        # Third tab: Routing table
        tab_menu.addTab(self.setRoutingTable(), "Routing")

    def setRouterInformation(self):
        """Function to show the router's name and retrieve it if changed by the user"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Router name
        name_label = QLabel("Router name")
        name_edit_label = QLineEdit(str(self.router.node_name))
        self.results["node_name"] = name_edit_label

        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)
        layout.addStretch()

        return widget

    def setEthernetIntfs(self):
        """This function shows the Ethernet interfaces that the router has"""
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
            intf_name_label = QLabel(str(interface))
            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)
            eth_layout.addWidget(QLabel("/"), index + 1, 3)

            if router_intfs[interface] == "":
                eth_ip = ""
                eth_mask = ""
            else:
                eth_ip = router_intfs[interface].split("/")[0]
                eth_mask = router_intfs[interface].split("/")[1]

            intf_ip_label = QLineEdit(str(eth_ip))
            intf_ip_list[interface] = intf_ip_label

            intf_mask_label = QLineEdit(str(eth_mask))
            intf_mask_list[interface] = intf_mask_label

            eth_layout.addWidget(intf_ip_label, index + 1, 2)
            eth_layout.addWidget(intf_mask_label, index + 1, 4)

            intf_state_button = QCheckBox()
            intf_id = self.router.searchLinkByIntf(interface)
            if router_scene.sceneLinks[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            intf_state_list[interface] = intf_state_button
            eth_layout.addWidget(intf_state_button, index + 1, 6)

            index = index + 1

        self.results["eth_intfs_ip"] = intf_ip_list
        self.results["eth_intfs_mask"] = intf_mask_list
        self.results["eth_intfs_state"] = intf_state_list

        return widget

    def setRoutingTable(self):
        """This function shows the routing table of the router"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        widget.setLayout(layout)

        # Checking if scene is available. If not, data cannot be retrieved.
        scene = self.router.scene()
        if not scene.net_running:
            label = QLabel("Routing table is not available as Mininet network is not active")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # Checking if router has entries in its routing table. If there is an error, message is shown.
        route_list = self.router.net_controller.getRoutingTable(self.router)
        if route_list == "Error":
            label = QLabel("An error occurred getting the routing table. Please, restart the dialog")
            label.setAlignment(Qt.AlignHCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addStretch()
            return widget

        # Design for the top layout
        layout.addWidget(QLabel("Write down your route / ip route command:"))

        widget_top = QWidget()
        layout_top = QHBoxLayout()
        layout_top.setContentsMargins(0, 0, 0, 0)
        widget_top.setLayout(layout_top)
        layout.addWidget(widget_top)

        line_command = QLineEdit()
        layout_top.addWidget(line_command)

        send_button = QPushButton("Apply")
        layout_top.addWidget(send_button)

        # Design for the dynamic widget (container of the routing table)
        route_widget = QWidget()
        layout.addWidget(route_widget)

        route_layout = QGridLayout()
        route_layout.setColumnMinimumWidth(1, 10)
        route_layout.setColumnMinimumWidth(3, 10)
        route_layout.setColumnMinimumWidth(5, 10)
        route_widget.setLayout(route_layout)

        self.updateRoutingTableLayout(route_widget, route_list)

        # Button connection to certain actions
        send_button.pressed.connect(lambda: self.sendCommandToNet(line_command.text(), route_widget))
        send_button.pressed.connect(lambda: line_command.clear())

        layout.addStretch()

        return widget

    # Auxiliary functions to dynamize the dialog

    def sendCommandToNet(self, command, widget):
        """This function sends a command to the Mininet object and retrieves its output"""
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
        output = self.router.net_controller.updateRoutingTable(self.router, command)
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
            route_list = self.router.net_controller.getRoutingTable(self.router)
            self.updateRoutingTableLayout(widget, route_list)

    def updateRoutingTableLayout(self, route_widget, route_list):
        """This function is in charge of modifying the dynamic widget and update it."""
        if not isinstance(route_widget, QWidget):
            return

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


# MiniGUI graphical classes

class TagGUI(QGraphicsTextItem):
    """Base class for scene tags (name, interfaces, IP address)"""
    def __init__(self, text=None, parent=None):
        super(TagGUI, self).__init__(text, parent)
        font = QFont()
        font.setBold(True)
        self.setFont(font)


class EthTagGUI(TagGUI):
    """Extended class for node's interface name tags"""
    def __init__(self, text=None, parent=None):
        super(EthTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """This function changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.darkCyan)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.cyan)


class IpTagGUI(TagGUI):
    """Extended class for interface's IP address tags"""
    def __init__(self, text=None, parent=None):
        super(IpTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """This function changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.darkBlue)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.green)


class NameTagGUI(TagGUI):
    """Extended class for node's name tags"""
    def __init__(self, text=None, parent=None):
        super(NameTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        """This function changes the text color if app theme is changed"""
        if APP_THEME == "light":
            self.setDefaultTextColor(Qt.black)
        elif APP_THEME == "dark":
            self.setDefaultTextColor(Qt.white)


class NodeGUI(QGraphicsPixmapItem):
    """"Class for node elements"""
    def __init__(self, x, y, node_type, node_name, properties=None, new_node=False, net_ctrl=None):
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
        """This function defines all the properties of the node"""
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
        """Add a new link to the node and creating a new interface for it"""
        if name not in self.links:
            new_intf = self.assignIntfName()
            self.links[name] = new_intf
            if self.node_type != "Switch" and len(self.links) == 1:
                self.properties["eth_intfs"][new_intf] = (str(self.properties["IP"]) + "/" +
                                                          str(self.properties["PrefixLen"]))
            else:
                self.properties["eth_intfs"][new_intf] = ""

            return new_intf
        else:
            return self.links[name]

    def deleteLink(self, name):
        """Deletes a link and everything related to it (properties & scene tags)"""
        if name in self.links:
            intf = self.links.pop(name)
            self.properties["eth_intfs"].pop(intf)
            self.scene_tags["eth"].pop(intf)
            if intf in self.scene_tags["IP"]:
                self.scene_tags["IP"].pop(intf)

    def searchLinkByIntf(self, intf):
        """Searches a link through its associated interface"""
        for link in self.links:
            if intf == self.links[link]:
                return link

        return None

    def assignIntfName(self):
        """This function checks all interfaces and creates a new name for the last interface"""
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
        """Updates the name tag with its new content and changes its horizontal position in scene"""
        tag = self.scene_tags["name"]
        tag.setPlainText(str(new_name))
        tag.setX((self.boundingRect().width() - tag.boundingRect().width()) / 2)

    def changeSceneIpTags(self):
        """Updates the IP tag with its new content and changes its horizontal position in scene"""
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
        """Allows user to change the node's parameters or access to net information"""
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
                scene.sceneNodes[new_name] = scene.sceneNodes.pop(self.node_name)
                self.node_name = new_name
                self.changeSceneNameTag(new_name)

            # IP Address per Ethernet interface
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
                    scene.sceneLinks[self.searchLinkByIntf(eth)].setLinkState(new_eth_state)
                    if scene.net_running:
                        self.net_controller.updateNetLink(scene.sceneLinks[self.searchLinkByIntf(eth)])

            # Changes are added to scene
            self.changeSceneIpTags()
            scene.updateSceneLinks(self)

            # If needed, update Mininet nodes with new information
            if scene.net_running:
                self.net_controller.updateNetNode(self)

    def changePixmapColor(self, mode=None):
        """Changes the node's scene icon according to the selected tool"""
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
        """This function updates the node's pixmap"""
        images = imagesMiniGUI()
        self.icon = images[self.node_type]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Event handlers

    def itemChange(self, change, value):
        """This function activates when element is moved in the scene"""
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            scene = self.scene()
            if scene is not None and isinstance(scene, SceneGUI):
                scene.updateSceneLinks(self)

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        """Context menu for nodes (hosts & switches)"""
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
            xterm_act.setStatusTip("Open " + str(self.node_type).lower() + " properties menu")
            xterm_act.triggered.connect(lambda: self.net_controller.xterm(name=self.node_name))
            context_menu.addAction(xterm_act)
            if not scene.net_running:
                xterm_act.setEnabled(False)

        elif self.node_type == "Switch":
            # Switch MAC
            routing_act = QAction("See MAC addresses", self.net_controller)
            routing_act.setStatusTip("See switch learned MAC addresses")
            routing_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(routing_act)
            if not scene.net_running:
                routing_act.setEnabled(False)

        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        """
        This function initiates when the node gains focus from the scene. To get the attention from the user, the
        program change the node color to highlight it
        """
        self.setPixmap(self.image)
        self.changePixmapColor()

    def focusOutEvent(self, event):
        """This function is the contrary of the previous one. It is used to retrieve the original icon"""
        self.setPixmap(self.image)

    def hoverEnterEvent(self, event):
        """This function is activated when the mouse enters in the element space"""
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
        """This function is activated when the mouse leaves in the element space"""
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
    """Class for links of node elements"""
    def __init__(self, x1, y1, x2, y2, net_ctrl=None):
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
        """This function sets the link's initial properties"""
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
        """This function returns a boolean with the link state: if up, true; if down, false"""
        return self.is_up

    def setLinkState(self, is_up=True):
        """This function modifies the line style according to the link's state"""
        self.is_up = is_up
        if is_up:
            self.pen.setStyle(Qt.SolidLine)
        else:
            self.pen.setStyle(Qt.DashLine)

        self.changeLineColor()

    def updateEndPoint(self, x2, y2):
        """This function changes the position of one of the ends of the line"""
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    def deleteSceneTags(self):
        """This function deletes all the scene tags related to this link"""
        scene = self.scene()
        if scene is not None and isinstance(scene, SceneGUI):
            tags = self.scene_tags
            for tag in tags:
                scene.removeItem(tags[tag])

    def changeLineColor(self):
        """This function changes the line color attending the link's state and if the scene is focused on the item"""
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
        """This function activates when link gains focus from the scene"""
        self.changeLineColor()

    def focusOutEvent(self, event):
        """This function activates when link loses focus from the scene"""
        self.changeLineColor()

    def hoverEnterEvent(self, event):
        """This function activates when link is user's pointer enters the element"""
        scene = self.scene()
        if self.is_up and scene.current_tool != "Delete":
            self.pen.setColor(Qt.darkBlue)
        else:
            self.pen.setColor(Qt.darkRed)

        self.setPen(self.pen)

    def hoverLeaveEvent(self, event):
        """This function activates when link is user's pointer leaves the element"""
        self.changeLineColor()


class SceneGUI(QGraphicsScene):
    def __init__(self, net_ctrl=None):
        super(SceneGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial variables
        self.scene_modified = False
        self.current_tool = None
        self.net_running = False

        # Node & Link dictionaries
        self.sceneNodes = {}
        self.sceneLinks = {}

        # Model initialization
        self.item_letter = {"Host": "h", "Switch": "s", "Router": "r", "Link": "l"}
        self.item_count = {"Host": 0, "Switch": 0, "Router": 0, "Link": 0}

        # Event handling initialization
        self.new_link = None
        self.link_orig_node = None

        # IP address variables
        self.default_ip_last = 1
        self.default_ip_base = "10.0.0."
        self.default_ip = self.default_ip_base + str(self.default_ip_last)

    # Scene functions

    @staticmethod
    def addSceneNodeNameTag(node, name):
        """This function creates a name tag and links it to the node"""
        name_tag = NameTagGUI(name, node)
        node.scene_tags["name"] = name_tag
        new_pos_x = (node.boundingRect().width() - name_tag.boundingRect().width()) / 2
        new_pos_y = node.boundingRect().bottomLeft().y()
        name_tag.setPos(new_pos_x, new_pos_y)

    def addSceneNode(self, x, y, node_type, name=None, properties=None):
        """Function to add a node element to the scene"""
        # Properties checking (in case the element is loaded up from previous projects)
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
        self.sceneNodes[node_name] = node

        # Addition of node to scene, gaining focus and modifying the scene
        self.addSceneNodeNameTag(node, node_name)
        self.addItem(node)
        node.setFocus()

        # Modification of scene's state variables
        self.scene_modified = True
        self.item_count[node_type] = self.item_count[node_type] + 1

        return node

    def addSceneLink(self, x, y):
        """Function to inicializate a new link on the scene"""
        self.new_link = LinkGUI(x, y, x, y, net_ctrl=self.net_controller)
        self.addItem(self.new_link)

    @staticmethod
    def checkNodeIpTag(node, eth):
        """Returns boolean depending on if IP tag must be created or not"""
        if node.node_type != "Switch":
            node_eths = node.properties["eth_intfs"]
            if eth in node_eths and node_eths[eth] != "":
                return True

        return False

    @staticmethod
    def addSceneLinkIpTags(node, eth, eth_tag):
        """Function to add IP tags to scene"""
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
        """This function creates and adds the Ethernet interface tags to scene"""
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

        self.updateSceneLinkTags(self.new_link, orig_node, dest_node)

    def finishSceneLink(self, name=None):
        """Last function to be called when a link is set up between two nodes"""
        line = self.new_link.line()
        orig_node = self.itemAt(line.p1(), QTransform())
        dest_node = self.itemAt(line.p2(), QTransform())
        if not isinstance(orig_node, NodeGUI) or not isinstance(dest_node, NodeGUI):
            return

        # Naming
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
        self.sceneLinks[new_name] = self.new_link

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
        """This function is in charge of moving and locating the interface and IP scene tags correctly"""
        # New positions of nodes (and line)
        line = link.line()
        orig_pos_x = line.x1()
        orig_pos_y = line.y1()
        dest_pos_x = line.x2()
        dest_pos_y = line.y2()

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
        """Function to update links position if one of the nodes moves"""
        # Initial variables
        node_links = node.links
        node_name = node.node_name
        node_pos = node.scenePos()

        # If there is no link related to the node, functions returns
        if not node_links:
            self.scene_modified = True
            return

        # If there are links related to the node, each one of them is updated
        for link in node_links:
            for linked_node_name in self.sceneLinks[link].nodes:
                if linked_node_name != node_name:
                    dest_node = self.sceneNodes[linked_node_name]
                    dest_node_pos = dest_node.scenePos()
                    offset_node = node.boundingRect().center()
                    offset_dest_node = dest_node.boundingRect().center()
                    self.sceneLinks[link].setLine(node_pos.x() + offset_node.x(),
                                                  node_pos.y() + offset_node.y(),
                                                  dest_node_pos.x() + offset_dest_node.x(),
                                                  dest_node_pos.y() + offset_dest_node.y())
                    self.updateSceneLinkTags(self.sceneLinks[link], node, dest_node)

        self.scene_modified = True

    def removeSceneItem(self, item):
        """Deletes an node/link from the scene and all links related to it"""
        # Initial variable in order to remove links later
        links_to_remove = []

        # If item to delete is a node, extract its links and delete the item
        if isinstance(item, NodeGUI):
            self.sceneNodes.pop(item.node_name)
            self.removeItem(item)
            for link in item.links:
                links_to_remove.append(link)

        # If item to delete is a link, extract its name
        if isinstance(item, LinkGUI):
            links_to_remove.append(item.link_name)

        # Update of all elements related to the to-be-deleted item
        for link in links_to_remove:
            self.sceneLinks[link].deleteSceneTags()
            self.removeItem(self.sceneLinks[link])
            self.sceneLinks.pop(link)
            for node in self.sceneNodes:
                if link in self.sceneNodes[node].links:
                    self.sceneNodes[node].deleteLink(link)

        self.scene_modified = True

    def loadScene(self, data):
        """Function called when loading a scene from an external file"""
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
                    dialog.setInformativeText("Project nodes data is corrupted. Please, verify JSON format is correct.")
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
                    dialog.setInformativeText("Project links data is corrupted. Please, verify JSON format is correct.")
                    dialog.exec()
                    return
                else:
                    scene_element = []
                    for node_name in link_nodes:
                        scene_element.append(self.sceneNodes[node_name])

                # Associating the links to its correspondent nodes
                orig_coor = scene_element[0].scenePos() + scene_element[0].boundingRect().center()
                dest_coor = scene_element[1].scenePos() + scene_element[1].boundingRect().center()
                self.addSceneLink(orig_coor.x(), orig_coor.y())
                self.new_link.updateEndPoint(dest_coor.x(), dest_coor.y())
                self.new_link.setLinkState(link_state)
                self.finishSceneLink(name=link_name)

        self.scene_modified = False

    def saveScene(self):
        """Function called to save the state of the current project"""
        # Initial variables
        file_dictionary = {}
        nodes_saved = []
        links_saved = []

        # Saving nodes
        for item in self.sceneNodes:
            node = {
                "name": self.sceneNodes[item].node_name,
                "type": self.sceneNodes[item].node_type,
                "x_pos": self.sceneNodes[item].scenePos().x(),
                "y_pos": self.sceneNodes[item].scenePos().y(),
                "links": self.sceneNodes[item].links,
                "properties": self.sceneNodes[item].properties
            }
            nodes_saved.append(node)

        # Saving links
        for item in self.sceneLinks:
            link = {
                "name": self.sceneLinks[item].link_name,
                "nodes": self.sceneLinks[item].nodes,
                "state": self.sceneLinks[item].isLinkUp()
            }
            links_saved.append(link)

        file_dictionary["nodes"] = nodes_saved
        file_dictionary["links"] = links_saved

        self.scene_modified = False

        return file_dictionary

    # Auxiliary functions

    def isFeasibleName(self, name):
        """This functions checks if a given name is already taken or not"""
        if len(name) == 0:
            return False

        for item in self.items():
            if isinstance(item, NodeGUI) and item.node_name == name:
                return False
            elif isinstance(item, LinkGUI) and item.link_name == name:
                return False

        return True

    def checkFeasibleLink(self, dest_node):
        """
        This function checks if a connection is possible between two nodes or wherever the user release
        the mouse button
        """
        if dest_node == self.link_orig_node or dest_node == self.new_link:
            return False

        if isinstance(self.link_orig_node, NodeGUI) and isinstance(dest_node, NodeGUI):
            if self.link_orig_node.node_type == "Host" and dest_node.node_type == "Host":
                return False

        orig_node_links = self.link_orig_node.links
        dest_node_links = dest_node.links
        for orig_link in orig_node_links:
            for dest_link in dest_node_links:
                if dest_link == orig_link:
                    return False

        return True

    def selectSceneItem(self, item):
        """Function to change the focus and the selection of the scene to the element that the user has clicked on"""
        if not isinstance(item, (NodeGUI, LinkGUI)):
            return

        self.clearSelection()
        self.clearFocus()

        item.setSelected(True)
        item.setFocus()

    # Event handlers

    def event(self, event):
        """Auxiliary function used for applications changes such as palette"""
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
        """Function related to key-pressed events. Now used only for element deleting"""
        # If Mininet is running, deleting is not available
        if self.net_running:
            return

        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            item = self.focusItem()
            if item is not None:
                self.removeSceneItem(item)

    def mousePressEvent(self, event):
        """Handler for mouse press events: depending on the selected tool, different actions are taken"""
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
        else:
            if event.button() == Qt.LeftButton:
                self.addSceneNode(event.scenePos().x(), event.scenePos().y(), self.current_tool)
                self.selectSceneItem(self.focusItem())

    def mouseMoveEvent(self, event):
        """Handler for mouse move events. Now only used when link tool is selected to move link along with mouse"""
        super().mouseMoveEvent(event)
        if self.current_tool == "Link" and self.new_link is not None:
            self.new_link.updateEndPoint(event.scenePos().x(), event.scenePos().y())

    def mouseReleaseEvent(self, event):
        """Handler for mouse release events. Only used to check if link has been correctly added to the scene"""
        super().mouseReleaseEvent(event)
        if self.current_tool == "Link" and self.new_link is not None:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, NodeGUI) and self.checkFeasibleLink(item):
                offset = item.boundingRect().center()
                self.new_link.updateEndPoint(item.scenePos().x() + offset.x(), item.scenePos().y() + offset.y())
                self.selectSceneItem(self.new_link)
                self.finishSceneLink()
            else:
                self.removeItem(self.new_link)
                self.link_orig_node = None
                self.new_link = None


# Main window and scene container class

class MiniGUI(QMainWindow):
    """Main class of the application. It holds all the structure along with the scene"""
    def __init__(self):
        super(QMainWindow, self).__init__()

        # File attribute (used for saving process)
        self.file = None

        # Preference attribute dictionary
        self.app_prefs = {"Mode": "basic", "CLI": True, "ProjectPath": ""}

        # Main window attributes settings
        self.menu_bar = QMenuBar()
        self.tool_bar = QToolBar()
        self.status_bar = QStatusBar()
        self.net_button = None
        self.tool_buttons = {}
        self.net_indicators = {}

        # Scene variables initialization
        self.canvas = QGraphicsView()
        self.scene = SceneGUI(net_ctrl=self)

        # Mininet variables
        self.net = None
        self.thread_cli = None
        self.thread_updater = None

        # Retrieving the user preferences saved in other sessions
        self.setPreferencesGUI()

        # Interface personalization setting
        self.setMainWindowGUI()
        self.setStatusBarGUI()
        self.setMenuBarGUI()
        self.setToolBarGUI()

    # Application initialization functions

    def setPreferencesGUI(self):
        """Checking and retrieving of user preferences from previous sessions"""
        settings = QSettings('MiniGUI', 'settings')

        # Application theme
        global APP_THEME
        APP_THEME = settings.value('AppTheme')
        if APP_THEME is None:
            APP_THEME = "light"
        elif APP_THEME == "dark":
            changeAppPalette()

        # Application mode (basic or advanced)
        app_mode = settings.value('AppMode')
        if app_mode != "basic" and app_mode != "advanced":
            self.app_prefs["Mode"] = "basic"
        else:
            self.app_prefs["Mode"] = app_mode

        # Use of CLI or not
        app_cli = settings.value('AppCLI')
        if app_cli == "True":
            self.app_prefs["CLI"] = True
        else:
            self.app_prefs["CLI"] = False

        # Directory of last opened project
        self.app_prefs["ProjectPath"] = settings.value("ProjectPath")

    def setMainWindowGUI(self):
        """Main window setting"""
        # Setting window's main properties
        self.setMinimumSize(500, 300)
        self.setWindowTitle("MiniGUI")
        self.setGeometry(500, 200, 1000, 600)

        # Relating QGraphicsScene to QGraphicsView
        self.canvas.setScene(self.scene)
        self.setCentralWidget(self.canvas)

        # Changing application's font
        font = app.font()
        font.setPixelSize(14)
        app.setFont(font)

    def setStatusBarGUI(self):
        """Status bar setting"""
        # Assignation
        self.setStatusBar(self.status_bar)

        # 1st label: net status with text
        label_widget = QLabel("Mininet network is not active")
        self.status_bar.addPermanentWidget(label_widget)
        self.net_indicators["Text"] = label_widget

        # 2nd label: net status with a coloured square
        color_widget = QWidget()
        color_widget.setFixedWidth(20)
        color_widget.setStyleSheet("background-color: red")
        self.status_bar.addPermanentWidget(color_widget)
        self.net_indicators["Color"] = color_widget

    def setMenuBarGUI(self):
        """Main menu bar setting"""
        # Assignation
        self.setMenuBar(self.menu_bar)

        # Menu bar submenus initialization
        file_menu = self.menu_bar.addMenu("File")
        pref_menu = self.menu_bar.addMenu("Preferences")
        help_menu = self.menu_bar.addMenu("About")

        # Menu actions
        new_action = QAction("New", self)
        open_action = QAction("Open", self)
        save_action = QAction("Save", self)
        save_as_action = QAction("Save as", self)
        quit_action = QAction("Quit", self)
        app_theme_action = QAction("Dark theme", self)
        app_mode_action = QAction("Advanced mode", self)
        app_cli_action = QAction("CLI terminal", self)
        about_action = QAction("About MiniGUI", self)

        # Action shortcuts
        new_action.setShortcut("Ctrl+N")
        open_action.setShortcut("Ctrl+O")
        save_action.setShortcut("Ctrl+S")
        quit_action.setShortcut("Ctrl+Q")
        about_action.setShortcut("F1")

        # Action attribute changes
        app_theme_action.setCheckable(True)
        app_mode_action.setCheckable(True)
        app_cli_action.setCheckable(True)

        # Update of 'checkable' buttons according to preferences
        if APP_THEME == "dark":
            app_theme_action.setChecked(True)
        if self.app_prefs["Mode"] == "advanced":
            app_mode_action.setChecked(True)
        if self.app_prefs["CLI"]:
            app_cli_action.setChecked(True)

        # Actions status tips
        new_action.setStatusTip("Create a new project")
        open_action.setStatusTip("Open an existing project")
        save_action.setStatusTip("Save the current project")
        save_as_action.setStatusTip("Save the current project as another")
        quit_action.setStatusTip("Exit MiniGUI")
        app_theme_action.setStatusTip("Change between light & dark theme")
        app_mode_action.setStatusTip("Change between basic & advanced mode")
        app_cli_action.setStatusTip("Use CLI terminal when scene is running or not")
        about_action.setStatusTip("Show information about MiniGUI")

        # Action connecting to functions/events
        new_action.triggered.connect(self.newProject)
        open_action.triggered.connect(self.openProject)
        save_action.triggered.connect(self.saveProject)
        save_as_action.triggered.connect(self.saveProject)
        quit_action.triggered.connect(self.close)
        app_theme_action.toggled.connect(lambda: self.changePreferences(preference="theme"))
        app_mode_action.toggled.connect(lambda: self.changePreferences(preference="mode"))
        app_cli_action.toggled.connect(lambda: self.changePreferences(preference="CLI"))
        about_action.triggered.connect(self.showAbout)

        # Action introduction into menus
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
        """Tool bar setting"""
        # Assignation
        self.addToolBar(self.tool_bar)

        # Tool bar initialization
        self.tool_bar.setMovable(False)
        self.tool_bar.setIconSize(QSize(50, 50))
        self.tool_bar.setContextMenuPolicy(Qt.PreventContextMenu)

        # Setting up tools
        images = imagesMiniGUI()
        for button in images:
            # Little spacer for aesthetic reason
            if button == "Select":
                little_spacer = QWidget()
                little_spacer.setFixedWidth(100)
                self.tool_bar.addWidget(little_spacer)

            b = QToolButton()
            b.setCheckable(True)
            b.setText(str(button))
            b.setToolTip(str(button))
            b.setIcon(QIcon(images[button]))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            b.pressed.connect(lambda tool_name=button: self.manageTools(tool_name))

            self.tool_bar.addWidget(b)
            self.tool_buttons[button] = b

        # Big spacer for aesthetic purposes
        big_spacer = QWidget()
        big_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tool_bar.addWidget(big_spacer)

        # Button related to Mininet action
        net_button = QToolButton()
        net_button.setText("Start")
        net_button.setStyleSheet("color: green; height: 50px; width: 60px; font: bold")
        net_button.clicked.connect(lambda: self.accessNet())
        self.tool_bar.addWidget(net_button)
        self.net_button = net_button

        # Select tool as default
        self.scene.current_tool = "Select"
        self.tool_buttons["Select"].setChecked(True)

    # Auxiliary functions

    def enableMenuAndToolBar(self):
        """This function enables both menu and tool bar"""
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(True)
        self.manageTools("Select")
        self.menu_bar.setEnabled(True)

    def disableMenuAndToolBar(self):
        """This function disables both menu and tool bar"""
        self.manageTools("Select")
        self.menu_bar.setEnabled(False)
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(False)

    def manageTools(self, tool_name):
        """Method to check up the current tool and manage the buttons"""
        if tool_name == self.scene.current_tool:
            if tool_name == "Select":
                self.tool_buttons["Select"].toggle()
            else:
                self.tool_buttons["Select"].setChecked(True)
                self.scene.current_tool = "Select"
        else:
            self.tool_buttons[self.scene.current_tool].toggle()
            self.scene.current_tool = tool_name

    def updateToolBarIcons(self):
        """This function updates the icon for each tool"""
        images = imagesMiniGUI()
        for button in self.tool_buttons:
            self.tool_buttons[button].setIcon(QIcon(images[self.tool_buttons[button].text()]))

    def updateNetButtonStyle(self):
        """This function updates the style of the Mininet action button"""
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
        """This function update the information shown in the status bar related to Mininet state"""
        if self.net is None:
            self.net_indicators["Text"].setText("Mininet network is not active")
            self.net_indicators["Color"].setStyleSheet("background-color: red")
        elif self.net is not None:
            self.net_indicators["Text"].setText("Mininet network is active!")
            self.net_indicators["Color"].setStyleSheet("background-color: green")

    # Scene-related functions

    def modifiedSceneDialog(self):
        """
        This function's objective is to warn the user that his/her current project has not been saved and lets the
        user to decide to save it, continue without saving or cancelling the action
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
        """This function clears the scene and the project related parameters"""
        # Main window parameters
        self.file = None
        self.app_prefs["ProjectPath"] = ""
        self.setWindowTitle("MiniGUI")

        # Scene parameters
        self.scene.clear()
        self.scene.sceneNodes.clear()
        self.scene.sceneLinks.clear()
        self.scene.scene_modified = False
        self.scene.default_ip_last = 1
        self.scene.default_ip = self.scene.default_ip_base + str(self.scene.default_ip_last)
        for tool in self.scene.item_count:
            self.scene.item_count[tool] = 0

    def newProject(self):
        """This function creates a new project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        self.clearProject()

    def openProject(self):
        """This function opens a previous existing project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        # Getting directory of last opened project
        if not self.app_prefs["ProjectPath"]:
            directory = os.getcwd()
        else:
            directory = os.path.dirname(str(self.app_prefs["ProjectPath"]))

        dialogfilename = QFileDialog.getOpenFileName(self, "Open file", directory,
                                                     "Mininet topology (*.mn);;All files (*)", "")

        if dialogfilename[0] != "":
            file = open(str(dialogfilename[0]), "r")
            try:
                topology_data = json.load(file)
            except json.JSONDecodeError:
                return None
            else:
                self.clearProject()
                self.file = str(dialogfilename[0])
                self.app_prefs["ProjectPath"] = str(dialogfilename[0])
                self.setWindowTitle("MiniGUI - " + str(dialogfilename[0]).split("/")[-1])
                self.scene.loadScene(topology_data)

    def saveProject(self):
        """This function allows the user to store project information in an external file"""
        try:
            sender_text = self.sender().text()
        except AttributeError:
            sender_text = ""

        if self.file is None or sender_text == "Save as":
            dialogfilename = QFileDialog.getSaveFileName(self, "Save file as", os.getcwd(),
                                                         "Mininet topology (*.mn);;All files (*)", "")

            if dialogfilename[0] != "":
                filepath = str(dialogfilename[0])
                if dialogfilename[1].startswith("Mininet") and not dialogfilename[0].endswith(".mn"):
                    filepath = filepath + ".mn"

                self.setWindowTitle("MiniGUI - " + filepath.split("/")[-1])
                self.app_prefs["ProjectPath"] = filepath
                self.file = filepath
            else:
                return

        file = open(self.file, "w")
        file_dictionary = self.scene.saveScene()
        file.write(json.dumps(file_dictionary, sort_keys=True, indent=4, separators=(',', ':')))
        file.close()

    # Mininet-related functions

    def emptySceneDialog(self):
        """Simple dialog to remind the user that the scene is empty"""
        dialog = QMessageBox(self)
        dialog.setTextFormat(Qt.RichText)
        dialog.setText("<b>Error! Scene is empty</b>")
        dialog.setInformativeText("Mininet cannot start with an empty scene. Please, add elements")
        dialog.setIcon(QMessageBox.Warning)

        return dialog.exec()

    def buildNodes(self):
        """This function creates the Mininet node objects"""
        for node in self.scene.sceneNodes:
            node_addr = None
            node_name = self.scene.sceneNodes[node].node_name
            node_type = self.scene.sceneNodes[node].node_type
            node_properties = self.scene.sceneNodes[node].properties
            if node_type != "Switch":
                node_addr = str(node_properties['IP']) + "/" + str(node_properties['PrefixLen'])

            if node_type == "Host":
                self.net.addHost(node_name, cls=None, ip=node_addr)
            elif node_type == "Router":
                self.net.addHost(node_name, cls=Router, ip=node_addr)
            elif node_type == "Switch":
                self.net.addSwitch(node_name, cls=None)

        # If no controller added and advanced mode is selected, one by default is introduced
        if self.app_prefs["Mode"] == "advanced" and not self.net.controllers:
            self.net.addController('c0')

    def buildLinks(self):
        """This function creates the Mininet link objects between nodes"""
        for link in self.scene.sceneLinks:
            nodes_linked = self.scene.sceneLinks[link].nodes
            if self.scene.sceneLinks[link].isLinkUp():
                link_status = "up"
            else:
                link_status = "down"

            # Retrieving scene nodes to build link
            link_name = self.scene.sceneLinks[link].link_name
            node_1 = self.scene.sceneNodes[nodes_linked[0]]
            node_2 = self.scene.sceneNodes[nodes_linked[1]]

            # Initialization
            two_switches_linked = False
            one_switch_linked = False

            # Depending on which case both nodes are, actions will be taken
            if node_1.node_type == "Switch" and node_2.node_type == "Switch":
                two_switches_linked = True
            elif node_1.node_type != "Switch" and node_2.node_type == "Switch":
                one_switch_linked = True
            elif node_1.node_type == "Switch" and node_2.node_type != "Switch":
                node_1 = self.scene.sceneNodes[nodes_linked[1]]
                node_2 = self.scene.sceneNodes[nodes_linked[0]]
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

            self.net.configLinkStatus(nodes_linked[0], nodes_linked[1], link_status)

    def startNet(self):
        """This function is used to start Mininet"""

        # Net creation and start
        self.net = Mininet(topo=None, build=False)
        self.buildNodes()
        self.buildLinks()
        self.net.build()
        self.net.start()

        # Scene modification
        self.updateNetIndicators()
        self.disableMenuAndToolBar()
        self.scene.net_running = True

        # Thread to update automatically the scene with Mininet info
        self.thread_updater = SceneAutoUpdate()
        self.thread_updater.updateSignal.connect(lambda: self.updateSceneInfo())
        self.thread_updater.start()

        # If basic mode has been selected, commands must be executed to inicialice Mininet correctly
        if self.app_prefs["Mode"] == "basic":
            for node in self.scene.sceneNodes:
                if self.scene.sceneNodes[node].node_type == "Switch":
                    switch_name = self.scene.sceneNodes[node].node_name
                    subprocess.run(['ovs-ofctl', 'add-flow', str(switch_name), 'action=normal'])

        # CLI creation
        if self.app_prefs["CLI"]:
            print("*** Starting CLI: please, write exit before exiting CLI to prevent GUI freezing")
            self.thread_cli = MiniCLI(self.net)
            self.thread_cli.start()

    def stopNet(self):
        """This function stops the Mininet execution"""

        # XTerm cleanse
        cleanUpScreens()

        # CLI, thread to update scene automatically and net stop
        self.thread_updater.update_active = False
        self.thread_cli = None
        self.net.stop()
        self.net = None

        # Scene modification
        self.updateNetIndicators()
        self.enableMenuAndToolBar()
        self.scene.net_running = False

    def accessNet(self):
        """THis function starts/stops Mininet execution and updates its related button accordingly"""
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

        self.updateNetButtonStyle()

    def updateNetNode(self, node):
        """This function updates Mininet node's information when simulation is running"""
        if self.net is None and not isinstance(node, NodeGUI):
            return

        net_node = self.net.nameToNode[node.node_name]

        # IP address update
        for intf in node.properties["eth_intfs"]:
            intf_addr = node.properties["eth_intfs"][intf]
            net_node.cmd("ifconfig " + str(intf) + " " + str(intf_addr))

    def updateNetLink(self, link):
        """This function updates Mininet link's information when simulation is running"""
        if self.net is None and not isinstance(link, LinkGUI):
            return

        if link.isLinkUp():
            link_status = "up"
        else:
            link_status = "down"

        link_nodes = link.nodes
        self.net.configLinkStatus(link_nodes[0], link_nodes[1], link_status)

    def updateSceneInfo(self):
        """This function allows user to update the scene information with Mininet output"""
        if self.net is None:
            return

        for node in self.scene.sceneNodes:
            if self.scene.sceneNodes[node].node_type != "Switch":
                # Initialization
                first_intf = True
                node_intfs = self.scene.sceneNodes[node].properties["eth_intfs"]
                net_node = self.net.nameToNode[self.scene.sceneNodes[node].node_name]

                # Interface information (IP address, netmask)
                for intf in node_intfs:
                    try:
                        output = net_node.cmdPrint("ip addr show dev " + str(intf))
                    except AssertionError:
                        pass
                    else:
                        new_ip = output.split("inet ")[1].split("/")[0]
                        new_mask = output.split(" brd")[1].split("/")[-1]
                        self.scene.sceneNodes[node].properties["eth_intfs"][intf] = (str(new_ip) + "/" + str(new_mask))
                        if first_intf:
                            self.scene.sceneNodes[node].properties["IP"] = new_ip
                            self.scene.sceneNodes[node].properties["PrefixLen"] = new_mask
                            first_intf = False

                # Scene modification
                self.scene.sceneNodes[node].changeSceneIpTags()
                self.scene.updateSceneLinks(self.scene.sceneNodes[node])

        # Link state (up or down)
        for link in self.scene.sceneLinks:
            node_name = self.scene.sceneLinks[link].nodes[0]
            intf_name = self.scene.sceneNodes[node_name].links[link]
            net_node = self.net.nameToNode[node_name]
            try:
                output = str(net_node.cmdPrint("ethtool " + str(intf_name)))
            except AssertionError:
                pass
            else:
                if output.split("Link detected: ")[1].split("\r\n")[0] == "yes":
                    self.scene.sceneLinks[link].setLinkState(is_up=True)
                else:
                    self.scene.sceneLinks[link].setLinkState(is_up=False)

        self.scene.scene_modified = True

    def updateRoutingTable(self, node, command):
        """This function sends an update command to node and gets its output"""
        if self.net is None or not isinstance(node, NodeGUI):
            return

        net_node = self.net.nameToNode[node.node_name]
        result = net_node.cmdPrint(str(command))
        if len(result) != 0:
            return result
        else:
            return None

    def getRoutingTable(self, node=None):
        """This function retrieves the routing table for hosts and routers"""
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
        """This function returns the routing table of hosts and switch"""
        if self.net is None or not isinstance(node, NodeGUI) or node.node_type != "Switch":
            return

        # Command execution to obtain switch's routing table
        proc = subprocess.Popen(['ovs-appctl', 'fdb/show', str(node.node_name)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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

    def xterm(self, name=None):
        """This function is used to call a personal XTerm for an specific node"""
        if self.net is None or name is None:
            return

        try:
            node = self.scene.sceneNodes[name]
        except KeyError:
            return

        node_name = node.node_name
        node_type = node.node_type
        term = makeTerm(self.net.nameToNode[node_name], node_type)
        self.net.terms += term

    # Event handling functions

    def closeEvent(self, event):
        """This function is called when main window (application) is about to be closed"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                event.ignore()

        self.writePreferences()

    def showEvent(self, event):
        """This function is called when the main window (application) is shown for the first time"""
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def resizeEvent(self, event):
        """This function is called when the main window (application) is resized"""
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def changeEvent(self, event):
        """This function is called when an external window parameter is changed (like palette)"""
        if event.type() == QEvent.PaletteChange and self.tool_buttons:
            self.updateToolBarIcons()
            self.updateNetButtonStyle()
        else:
            QWidget.changeEvent(self, event)

    # Preferences functions

    def writePreferences(self):
        """This function saves the user's preferences in a external configuration file"""
        settings = QSettings('MiniGUI', 'settings')
        settings.setValue("AppTheme", str(APP_THEME))
        settings.setValue("AppMode", str(self.app_prefs["Mode"]))
        settings.setValue("AppCLI", str(self.app_prefs["CLI"]))
        if self.app_prefs["ProjectPath"]:
            settings.setValue("ProjectPath", str(self.app_prefs["ProjectPath"]))

    def changePreferences(self, preference=None):
        """This function allows the user to change some preferences"""
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

    # Pop-up related functions

    def showAbout(self):
        """This function creates a new dialog displaying the information about the application itself"""
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
        label2.setText("MiniGUI: network graphical editor, made specifically for you\n\n"
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
    """This function returns a set of images depending on the mode selected: bright or dark"""
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
    """This function changes the application palette according to the selected theme"""
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
    # Checking that program is executed as superuser
    if os.getuid() != 0:
        sys.exit('ERROR: MiniGUI must run as root. Use sudo ./MiniGUI.py')
    elif not os.path.isdir("/tmp/runtime-root"):
        os.makedirs("/tmp/runtime-root")
    # Environmental variable
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/runtime-root"
    # App initialization
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui_app = MiniGUI()
    gui_app.show()
    sys.exit(app.exec())
