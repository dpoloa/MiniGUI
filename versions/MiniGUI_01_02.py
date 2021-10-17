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
import json
import sys
import os

# Mininet package import
from mininet.net import Mininet
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Node
from mininet.cli import CLI


# Thread class

class MiniCLI(threading.Thread):
    """Thread class for Mininet CLI object, needed to not conflict with PyQt5 event loop"""
    def __init__(self, net=None):
        super(MiniCLI, self).__init__(daemon=True)
        self.net = net

    def run(self):
        if self.net is not None:
            CLI(self.net)


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

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.base_layout = QVBoxLayout()
        self.base_layout.addWidget(button_box)
        self.setLayout(self.base_layout)


class HostDialog(BaseDialog):
    """Dialog class for hosts"""
    def __init__(self, host, parent=None):
        super(HostDialog, self).__init__(parent=parent)

        self.host = host
        self.results = {}
        self.properties = host.properties

        self.setWindowTitle("Host properties: " + str(host.node_name))
        self.setFixedWidth(600)

        self.setHostDialog()

    def setHostDialog(self):
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setHostInformation(), "Host info")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Connection info")
        # Third tab: default route --> maybe moved to another tab in future versions
        tab_menu.addTab(self.setRoutingTable(), "Routing")
        # Fourth tab: VLAN interfaces --> WIP
        tab_menu.addTab(self.setVlanInterfaces(), "VLAN Interfaces")

    def setHostInformation(self):
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
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        # Left layout for IP address and netmask
        widget_left = QWidget()
        layout_left = QVBoxLayout()
        layout_left.setContentsMargins(0, 0, 9, 0)
        widget_left.setLayout(layout_left)
        layout.addWidget(widget_left)

        # IP address
        ip_label = QLabel("IP Address")
        ip_edit_label = QLineEdit(str(self.properties["IP"]))
        self.results["IP"] = ip_edit_label
        layout_left.addWidget(ip_label)
        layout_left.addWidget(ip_edit_label)

        # Netmask
        mask_label = QLabel("Netmask")
        mask_edit_label = QLineEdit(str(self.properties["PrefixLen"]))
        self.results["PrefixLen"] = mask_edit_label
        layout_left.addWidget(mask_label)
        layout_left.addWidget(mask_edit_label)

        # Right layout for Ethernet interfaces
        eth_group = QGroupBox("Ethernet interfaces")
        eth_group.setAlignment(Qt.AlignHCenter)
        layout.addWidget(eth_group)

        eth_layout = QGridLayout()
        eth_layout.setColumnMinimumWidth(1, 10)
        eth_group.setLayout(eth_layout)

        host_intfs = self.host.properties["eth_intfs"]
        host_scene = self.host.scene()

        if not host_intfs:
            eth_layout.addWidget(QLabel("There are no interfaces already defined"), 0, 0, 1, -1, Qt.AlignHCenter)
            layout.addStretch()
            return widget

        intf_state_list = {}
        eth_layout.addWidget(QLabel("Interface name"), 0, 0)
        eth_layout.addWidget(QLabel("Is interface up?"), 0, 2)

        index = 1
        for interface in host_intfs:
            intf_name_label = QLabel(str(interface))
            intf_state_button = QCheckBox()
            intf_id = self.host.searchLinkByIntf(interface)
            if host_scene.sceneLinks[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignLeft)
            eth_layout.addWidget(intf_state_button, index + 1, 2)
            intf_state_list[interface] = intf_state_button
            index = index + 1

        self.results["eth_intfs_state"] = intf_state_list

        layout_left.addStretch()
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        eth_layout.addWidget(spacer)

        return widget

    # This function could be moved to another tab in future versions
    def setRoutingTable(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Default route
        droute_label = QLabel("Default route")
        droute_edit_label = QLineEdit()
        if "DefaultRoute" in self.properties:
            droute_edit_label.setText(self.properties["DefaultRoute"])

        self.results["DefaultRoute"] = droute_edit_label

        layout.addWidget(droute_label)
        layout.addWidget(droute_edit_label)
        layout.addStretch()

        return widget

    # WIP --> To be defined
    def setVlanInterfaces(self):
        widget = QWidget()
        layout = QVBoxLayout()

        return widget


class SwitchDialog(BaseDialog):
    """Dialog class for switches"""
    def __init__(self, switch, parent=None):
        super(SwitchDialog, self).__init__(parent=parent)

        self.switch = switch

        self.setWindowTitle("Switch routing table: " + str(switch.node_name))
        self.setFixedWidth(300)

        self.showRoutingTable()

    def showRoutingTable(self):
        route_layout = QGridLayout()
        route_layout.setColumnMinimumWidth(1, 10)
        route_layout.setColumnMinimumWidth(3, 10)
        route_layout.setColumnMinimumWidth(5, 10)
        self.base_layout.insertLayout(0, route_layout)

        route_table = self.switch.net_controller.getRoutingTable(self.switch)
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

        self.results = {}
        self.router = router
        self.properties = router.properties

        self.setWindowTitle("Router properties: " + str(router.node_name))
        self.setFixedWidth(450)

        self.setRouterDialog()

    def setRouterDialog(self):
        tab_menu = QTabWidget()
        self.base_layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setRouterInformation(), "Router info")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Connection info")
        # Third tab: default route --> maybe moved to another tab in future versions
        tab_menu.addTab(self.setRoutingTable(), "Routing")

    def setRouterInformation(self):
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
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # IP Address
        ip_label = QLabel("Default IP (& eth0) Address")
        ip_edit_label = QLineEdit(str(self.properties["IP"]))
        self.results["IP"] = ip_edit_label
        layout.addWidget(ip_label)
        layout.addWidget(ip_edit_label)

        # Netmask
        mask_label = QLabel("IP Mask")
        mask_edit_label = QLineEdit(str(self.properties["PrefixLen"]))
        self.results["PrefixLen"] = mask_edit_label
        layout.addWidget(mask_label)
        layout.addWidget(mask_edit_label)

        # Layout for Ethernet interfaces
        eth_group = QGroupBox("Ethernet interfaces")
        eth_group.setAlignment(Qt.AlignHCenter)
        layout.addWidget(eth_group)

        eth_layout = QGridLayout()
        eth_layout.setColumnMinimumWidth(1, 10)
        eth_layout.setColumnMinimumWidth(3, 10)
        eth_layout.setColumnMinimumWidth(5, 10)
        eth_group.setLayout(eth_layout)

        router_intfs = self.router.properties["eth_intfs"]
        router_scene = self.router.scene()

        if not router_intfs:
            eth_layout.addWidget(QLabel("There are no interfaces already defined"), 0, 0, 1, -1, Qt.AlignHCenter)
            layout.addStretch()
            return widget

        # Dictionaries for results
        intf_ip_list = {}
        intf_mask_list = {}
        intf_state_list = {}

        # Title labels
        eth_layout.addWidget(QLabel("Interface name"), 0, 0)
        eth_layout.addWidget(QLabel("IP Address"), 0, 2)
        eth_layout.addWidget(QLabel("IP Mask"), 0, 4)
        eth_layout.addWidget(QLabel("Up?"), 0, 6)

        # Structure of the grid layout
        index = 1
        for interface in router_intfs:
            intf_name_label = QLabel(str(interface))
            eth_layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)

            if router_intfs[interface] == "":
                eth_ip = ""
                eth_mask = ""
            else:
                eth_ip = router_intfs[interface].split("/")[0]
                eth_mask = router_intfs[interface].split("/")[1]

            intf_ip_label = QLineEdit(str(eth_ip))
            intf_mask_label = QLineEdit(str(eth_mask))

            if interface == self.router.node_name + "-eth0":
                # WIP --> To be reviewed in future versions
                intf_ip_label.setReadOnly(True)
                intf_mask_label.setReadOnly(True)
            else:
                intf_ip_list[interface] = intf_ip_label
                intf_mask_list[interface] = intf_mask_label

            intf_state_button = QCheckBox()
            intf_id = self.router.searchLinkByIntf(interface)
            if router_scene.sceneLinks[intf_id].isLinkUp():
                intf_state_button.setChecked(True)

            intf_state_list[interface] = intf_state_button
            eth_layout.addWidget(intf_ip_label, index + 1, 2)
            eth_layout.addWidget(intf_mask_label, index + 1, 4)
            eth_layout.addWidget(intf_state_button, index + 1, 6)

            index = index + 1

        self.results["eth_intfs_ip"] = intf_ip_list
        self.results["eth_intfs_mask"] = intf_mask_list
        self.results["eth_intfs_state"] = intf_state_list

        layout.addStretch()

        return widget

    def setRoutingTable(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Default route
        droute_label = QLabel("Default route")
        droute_edit_label = QLineEdit()
        if "DefaultRoute" in self.properties:
            droute_edit_label.setText(self.properties["DefaultRoute"])

        self.results["DefaultRoute"] = droute_edit_label

        layout.addWidget(droute_label)
        layout.addWidget(droute_edit_label)
        layout.addStretch()

        return widget


# MiniGUI graphical classes

class TagGUI(QGraphicsTextItem):
    """Base class for scene tags (name, interfaces, IP address)"""
    def __init__(self, text=None, parent=None):
        super(TagGUI, self).__init__(text, parent)
        font = QFont()
        font.setBold(True)
        self.setFont(font)


class IpTagGUI(TagGUI):
    """Tag class for IP addresses"""
    def __init__(self, text=None, parent=None):
        super(IpTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        scene = self.scene()
        if scene is not None and isinstance(scene, CanvasGUI):
            global app_theme
            if app_theme == "light":
                self.setDefaultTextColor(Qt.darkBlue)
            elif app_theme == "dark":
                self.setDefaultTextColor(Qt.blue)


class EthTagGUI(TagGUI):
    """Tag class for interface name"""
    def __init__(self, text=None, parent=None):
        super(EthTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        scene = self.scene()
        if scene is not None and isinstance(scene, CanvasGUI):
            global app_theme
            if app_theme == "light":
                self.setDefaultTextColor(Qt.darkCyan)
            elif app_theme == "dark":
                self.setDefaultTextColor(Qt.cyan)


class NameTagGUI(TagGUI):
    """Tag class for node name"""
    def __init__(self, text=None, parent=None):
        super(NameTagGUI, self).__init__(text, parent)
        self.updateColor()

    def updateColor(self):
        scene = self.scene()
        if scene is not None and isinstance(scene, CanvasGUI):
            global app_theme
            if app_theme == "light":
                self.setDefaultTextColor(Qt.black)
            elif app_theme == "dark":
                self.setDefaultTextColor(Qt.white)


class NodeGUI(QGraphicsPixmapItem):
    """"Class for node elements"""
    def __init__(self, x, y, node_type, name=None, properties=None, new_node=False, net_ctrl=None):
        super(NodeGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial attributes
        self.width = 64
        self.height = 64
        self.node_name = name
        self.node_type = node_type
        self.icon = None
        self.image = None
        self.links = {}
        self.properties = {}
        self.scene_tags = {"name": None, "IP": {}, "eth": {}}

        # Setting up initial attributes
        self.setNodeAttributes(x, y, properties, new_node)

    def setNodeAttributes(self, x, y, properties=None, new_node=False):
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
            self.properties["DefaultRoute"] = ""
            if not new_node:
                self.properties["eth_intfs"] = properties["eth_intfs"]
                self.properties["DefaultRoute"] = properties["DefaultRoute"]
        elif self.node_type == "Switch" and properties is not None:
            self.properties = properties

    # Auxiliary functions

    def addNewLink(self, name):
        """Add a new link to the node and creating a new interface for it"""
        if name not in self.links:
            new_intf = self.assignIntfName()
            self.links[name] = new_intf
            if self.node_type == "Host" or (self.node_type == "Router" and len(self.links) == 1):
                self.properties["eth_intfs"][new_intf] = (str(self.properties["IP"]) + "/" +
                                                          str(self.properties["PrefixLen"]))
            else:
                self.properties["eth_intfs"][new_intf] = ""

            return new_intf
        else:
            return self.links[name]

    def deleteLink(self, name):
        """Deletes a link and all the archives related to it (properties & scene tags)"""
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
        if "eth_intfs" not in self.properties:
            return self.node_name + "-eth0"

        intf_base = self.node_name + "-eth"
        intf_count = 0
        for index in range(len(self.properties["eth_intfs"])):
            coincidence = False
            intf_name = intf_base + str(intf_count)
            if str(intf_name) in self.properties["eth_intfs"]:
                intf_count = intf_count + 1
                coincidence = True

            if not coincidence:
                return intf_name

        intf_name = self.node_name + "-eth" + str(intf_count)

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

        if self.node_type == "Host":
            for eth in self.scene_tags["IP"]:
                tag = self.scene_tags["IP"][eth]
                tag.setPlainText(str(self.properties["IP"]))
                tag.setX((self.scene_tags["eth"][eth].boundingRect().width() - tag.boundingRect().width()) / 2)
        elif self.node_type == "Router":
            for eth in self.properties["eth_intfs"]:
                if eth in self.scene_tags["IP"]:
                    tag = self.scene_tags["IP"][eth]
                    tag.setPlainText(str(self.properties["eth_intfs"][eth]).split("/")[0])
                    tag.setX((self.scene_tags["eth"][eth].boundingRect().width() - tag.boundingRect().width()) / 2)
                elif eth not in self.scene_tags["IP"] and self.properties["eth_intfs"][eth] != "":
                    scene = self.scene()
                    eth_tag = self.scene_tags["eth"][eth]
                    if scene is not None and isinstance(scene, CanvasGUI):
                        scene.addSceneLinkIpTags(self, eth, eth_tag)

    def nodePropertiesDialog(self):
        """Allows user to change the node's parameters or access to net information"""
        # Creating dialog according to node type
        if self.node_type == "Host":
            dialog = HostDialog(self, self.net_controller)
        elif self.node_type == "Switch":
            dialog = SwitchDialog(self, self.net_controller)
        elif self.node_type == "Router":
            dialog = RouterDialog(self, self.net_controller)
        else:
            return

        if dialog.exec() and self.node_type != "Switch":
            scene = self.scene()
            modify_scene = False

            # Node name
            new_name = dialog.results["node_name"].text()
            if isinstance(scene, CanvasGUI) and new_name != self.node_name and scene.isFeasibleName(new_name):
                scene.sceneNodes[new_name] = scene.sceneNodes.pop(self.node_name)
                self.node_name = new_name
                self.changeSceneNameTag(new_name)

            # IP Address
            new_ip = dialog.results["IP"].text()
            if new_ip != self.properties["IP"] and scene.isFeasibleIP(new_ip):
                self.properties["IP"] = new_ip
                modify_scene = True

            # Netmask
            new_mask = dialog.results["PrefixLen"].text()
            if new_mask != self.properties["PrefixLen"]:
                self.properties["PrefixLen"] = new_mask

            # Default route
            new_droute = dialog.results["DefaultRoute"].text()
            if new_droute != self.properties["DefaultRoute"]:
                self.properties["DefaultRoute"] = new_droute

            # Ethernet interfaces
            if len(new_ip) > 0 and len(new_mask):
                modify_scene = True
                if self.node_type == "Host":
                    for eth in self.properties["eth_intfs"]:
                        self.properties["eth_intfs"][eth] = str(new_ip) + "/" + str(new_mask)
                elif self.node_type == "Router":
                    self.properties["eth_intfs"][self.node_name + "-eth0"] = str(new_ip) + "/" + str(new_mask)

            if "eth_intfs_ip" in dialog.results:
                for eth in dialog.results["eth_intfs_ip"]:
                    new_eth_ip = dialog.results["eth_intfs_ip"][eth].text()
                    new_eth_mask = dialog.results["eth_intfs_mask"][eth].text()
                    if len(new_eth_ip) > 0 and len(new_eth_mask) > 0:
                        self.properties["eth_intfs"][eth] = str(new_eth_ip) + "/" + str(new_eth_mask)
                        modify_scene = True

            if "eth_intfs_state" in dialog.results:
                for eth in dialog.results["eth_intfs_state"]:
                    new_eth_state = dialog.results["eth_intfs_state"][eth].isChecked()
                    scene.sceneLinks[self.searchLinkByIntf(eth)].setLinkState(new_eth_state)
                    if scene.net_running:
                        self.net_controller.updateNetLink(scene.sceneLinks[self.searchLinkByIntf(eth)])

            # If needed, modify scene accordingly
            if modify_scene:
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
        images = imagesMiniGUI()
        self.icon = images[self.node_type]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Event handlers

    def itemChange(self, change, value):
        """This function activates when element is moved in the scene"""
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            scene = self.scene()
            if scene is not None and isinstance(scene, CanvasGUI):
                scene.updateSceneLinks(self)

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        """Context menu for nodes (hosts & switches)"""
        context_menu = QMenu()
        scene = self.scene()

        if scene is None or not isinstance(scene, CanvasGUI):
            return

        # Contextual menu changes according to the node's type: if Switch, menu is different
        if self.node_type != "Switch":
            menu_text = str(self.node_type) + " properties"
            properties_act = QAction(menu_text, self.net_controller)
            properties_act.setStatusTip("Open " + str(self.node_type).lower() + " properties menu")
            properties_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(properties_act)

            if scene.net_running:
                xterm_act = QAction("XTerm", self.net_controller)
                xterm_act.setStatusTip("Open " + str(self.node_type).lower() + " properties menu")
                xterm_act.triggered.connect(lambda: self.net_controller.xterm(name=self.node_name))
                context_menu.addAction(xterm_act)

        elif self.node_type == "Switch" and scene.net_running:
            routing_act = QAction("See routing table", self.net_controller)
            routing_act.setStatusTip("See switch routing table")
            routing_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(routing_act)

        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        """This function initiates when the node gains focus from the scene. To get the attention from the user, the
        program change the node color to highlight it"""
        self.setPixmap(self.image)
        self.changePixmapColor()

    def focusOutEvent(self, event):
        """This function is the contrary of the previous one. It is used to retrieve the original icon"""
        self.setPixmap(self.image)

    def hoverEnterEvent(self, event):
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, CanvasGUI):
            scene_tool = node_scene.current_tool

        if scene_tool is not None and scene_tool == "Delete":
            self.changePixmapColor(mode="Delete")
            return
        elif self.hasFocus():
            return
        else:
            self.changePixmapColor()

    def hoverLeaveEvent(self, event):
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, CanvasGUI):
            scene_tool = node_scene.current_tool

        if scene_tool is not None and scene_tool == "Delete" and self.hasFocus():
            self.changePixmapColor()
            return
        elif self.hasFocus():
            return
        else:
            self.setPixmap(self.image)


class LinkGUI(QGraphicsLineItem):
    """Class for links of node elements"""
    def __init__(self, x1, y1, x2, y2, net_ctrl=None):
        super(LinkGUI, self).__init__(x1, y1, x2, y2)

        # Initial attributes
        self.link_name = ""
        self.nodes = []
        self.is_up = True
        self.scene_tags = {}
        self.net_ctrl = net_ctrl

        # Aesthetic attribute
        self.pen = QPen()

        # Setting up initial attributes
        self.setLinkAttributes()

    def setLinkAttributes(self):
        # Set color and width of the link
        self.pen.setWidth(2)
        self.pen.setColor(Qt.darkBlue)
        self.setPen(self.pen)

        # Setting of internal attributes
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

    # Auxiliary functions

    def isLinkUp(self):
        return self.is_up

    def setLinkState(self, is_up=True):
        self.is_up = is_up
        if is_up:
            self.pen.setStyle(Qt.SolidLine)
        else:
            self.pen.setStyle(Qt.DashLine)

        self.changeLineColor()

    def updateEndPoint(self, x2, y2):
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    def deleteSceneTags(self):
        scene = self.scene()
        if scene is not None and isinstance(scene, CanvasGUI):
            tags = self.scene_tags
            for tag in tags:
                scene.removeItem(tags[tag])

    def changeLineColor(self):
        if self.is_up and self.hasFocus():
            self.pen.setColor(Qt.blue)
        elif self.is_up and not self.hasFocus():
            self.pen.setColor(Qt.darkBlue)
        elif not self.is_up and self.hasFocus():
            self.pen.setColor(Qt.red)
        elif not self.is_up and not self.hasFocus():
            self.pen.setColor(Qt.darkRed)

        self.setPen(self.pen)

    # Event handlers

    # WIP --> could be deleted in future versions
    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction("Link properties")
        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        self.changeLineColor()

    def focusOutEvent(self, event):
        self.changeLineColor()

    def hoverEnterEvent(self, event):
        if self.hasFocus():
            return
        self.changeLineColor()

    def hoverLeaveEvent(self, event):
        if self.hasFocus():
            return
        self.changeLineColor()


class CanvasGUI(QGraphicsScene):
    def __init__(self, net_ctrl=None):
        super(CanvasGUI, self).__init__()

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
        name_tag = QGraphicsTextItem(name, node)
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

        node = NodeGUI(x, y, node_type, node_name, node_properties, node_new, net_ctrl=self.net_controller)
        self.sceneNodes[node_name] = node

        # Addition of node to scene, gaining focus and modifying the scene
        self.addSceneNodeNameTag(node, node_name)
        self.addItem(node)
        node.setFocus()

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
        if node.node_type == "Host":
            return True
        elif node.node_type == "Switch":
            return False
        else:
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
        orig_tag = EthTagGUI(orig_eth, None)
        dest_tag = EthTagGUI(dest_eth, None)

        self.new_link.scene_tags[orig_node.node_name] = orig_tag
        self.new_link.scene_tags[dest_node.node_name] = dest_tag
        orig_node.scene_tags["eth"][orig_eth] = orig_tag
        dest_node.scene_tags["eth"][dest_eth] = dest_tag
        self.addItem(orig_tag)
        self.addItem(dest_tag)

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
        link = self.new_link

        orig_eth = orig_node.addNewLink(new_name)
        dest_eth = dest_node.addNewLink(new_name)
        self.addSceneLinkEthTags(orig_node, orig_eth, dest_node, dest_eth)

        # Resetting temporary variables to initial state
        self.new_link = None
        self.link_orig_node = None
        self.scene_modified = True

        return link

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
        ip_orig_tag_offset = 0
        ip_dest_tag_offset = 0
        if link_orig_tag.childItems():
            ip_orig_tag_offset = orig_tag_offset_y
        if link_dest_tag.childItems():
            ip_dest_tag_offset = dest_tag_offset_y

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
        node_links = node.links
        node_name = node.node_name
        node_pos = node.scenePos()
        if not node_links:
            self.scene_modified = True
            return

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

        # Separate code depending on item's class
        if isinstance(item, NodeGUI):
            self.sceneNodes.pop(item.node_name)
            self.removeItem(item)
            for link in item.links:
                links_to_remove.append(link)

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
        if "nodes" in data:
            nodes_list = data["nodes"]
            for node in nodes_list:
                node_name = node["name"]
                node_type = node["type"]
                node_x_pos = node["x_pos"]
                node_y_pos = node["y_pos"]
                node_links = node["links"]
                node_properties = node["properties"]
                new_node = self.addSceneNode(node_x_pos, node_y_pos, node_type, node_name, node_properties)
                new_node.links = node_links

        if "links" in data:
            links_list = data["links"]
            for link in links_list:
                link_nodes = link["nodes"]
                link_state = link["state"]
                link_name = link["name"]
                scene_element = []
                for node_name in link_nodes:
                    scene_element.append(self.sceneNodes[node_name])

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

    # WIP --> to be continued and defined in following versions
    @staticmethod
    def isFeasibleIP(ip):
        if len(ip) == 0:
            return False

        return True

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
        """ This function checks if a connection is possible between two nodes or wherever the user release
        the mouse button."""
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
        """Function to change the focus and the selection of the scene to the element that the user has clicked on."""
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
                elif isinstance(item, NodeGUI):
                    item.updateIcon()
                elif isinstance(item, QGraphicsTextItem):
                    global app_theme
                    if app_theme == "dark":
                        item.setDefaultTextColor(Qt.white)
                    else:
                        item.setDefaultTextColor(Qt.black)

        return QGraphicsScene.event(self, event)

    def keyPressEvent(self, event):
        """Function related to key-pressed events. Now used only for element deleting."""
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
        elif self.current_tool == "Link":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and isinstance(item, NodeGUI):
                self.link_orig_node = item
                offset = item.boundingRect().center()
                self.addSceneLink(item.scenePos().x() + offset.x(), item.scenePos().y() + offset.y())
        elif self.current_tool == "Delete":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and not isinstance(item, QGraphicsTextItem):
                self.removeSceneItem(item)
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

        # Program configuration setting
        self.settings = None

        # File attribute (used for saving process)
        self.file = None

        # Main window attributes settings
        self.menu_bar = QMenuBar()
        self.tool_bar = QToolBar()
        self.status_bar = QStatusBar()
        self.tool_buttons = {}
        self.exec_buttons = {}
        self.active_tool = None

        # Scene variables initialization
        self.canvas = QGraphicsView()
        self.scene = CanvasGUI(net_ctrl=self)

        # Mininet variables
        self.net = None
        self.master_cli = None
        self.net_indicators = {}

        # Retrieving the user preferences saved in other sessions
        self.setPreferencesGUI()

        # Interface personalization setting
        self.setMainWindowGUI()
        self.setStatusBarGUI()
        self.setMenuBarGUI()
        self.setToolBarGUI()

    # Application initialization functions

    # WIP
    def setPreferencesGUI(self):
        """Checking and retrieving of user preferences from previous sessions"""
        global app_theme
        self.settings = QSettings('MiniGUI', 'settings')

        # Application mode
        app_theme = self.settings.value('AppTheme')
        if app_theme is None:
            app_theme = "light"
        elif app_theme == "dark":
            changeAppPalette()

        # Directory of last opened project
        self.file = self.settings.value("ProjectPath")

    def setMainWindowGUI(self):
        """Main window setting"""
        self.setGeometry(500, 200, 1000, 600)
        self.setWindowTitle("MiniGUI")
        self.setCentralWidget(self.canvas)

        self.canvas.setScene(self.scene)

        font = app.font()
        font.setPixelSize(14)
        app.setFont(font)

    def setStatusBarGUI(self):
        """Status bar setting"""
        # Assignation
        self.setStatusBar(self.status_bar)

        # 1st label: net status with text
        label_widget = QLabel("Red no activa")
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
        edit_menu = self.menu_bar.addMenu("Edit")
        pref_menu = self.menu_bar.addMenu("Preferences")
        help_menu = self.menu_bar.addMenu("About")

        # Menu actions
        new_action = QAction("New", self)
        open_action = QAction("Open", self)
        save_action = QAction("Save", self)
        save_as_action = QAction("Save as", self)
        quit_action = QAction("Quit", self)
        undo_action = QAction("Undo", self)
        redo_action = QAction("Redo", self)
        cut_action = QAction("Cut", self)
        copy_action = QAction("Copy", self)
        paste_action = QAction("Paste", self)
        dark_theme_action = QAction("Dark theme", self)
        about_action = QAction("About MiniGUI", self)

        # Action shortcuts
        new_action.setShortcut("Ctrl+N")
        open_action.setShortcut("Ctrl+O")
        save_action.setShortcut("Ctrl+S")
        quit_action.setShortcut("Ctrl+Q")
        undo_action.setShortcut("Ctrl+Z")
        redo_action.setShortcut("Ctrl+Y")
        cut_action.setShortcut("Ctrl+X")
        copy_action.setShortcut("Ctrl+C")
        paste_action.setShortcut("Ctrl+V")
        about_action.setShortcut("F1")

        # Action attribute changes
        dark_theme_action.setCheckable(True)

        # Update of checkable buttons according to preferences
        global app_theme
        if app_theme == "dark":
            dark_theme_action.setChecked(True)

        # Actions status tips
        new_action.setStatusTip("Create a new project")
        open_action.setStatusTip("Open an existing project")
        save_action.setStatusTip("Save the current project")
        save_as_action.setStatusTip("Save the current project as another")
        quit_action.setStatusTip("Exit MiniGUI")
        undo_action.setStatusTip("Undo step")
        redo_action.setStatusTip("Redo step")
        cut_action.setStatusTip("Cut to clipboard")
        copy_action.setStatusTip("Copy to clipboard")
        paste_action.setStatusTip("Paste from clipboard")
        dark_theme_action.setStatusTip("Cambiar entre modo claro y oscuro")
        about_action.setStatusTip("Show information about MiniGUI")

        # Action connecting to functions/events
        new_action.triggered.connect(self.newProject)
        open_action.triggered.connect(self.openProject)
        save_action.triggered.connect(self.saveProject)
        save_as_action.triggered.connect(self.saveProject)
        quit_action.triggered.connect(qApp.exit)
        dark_theme_action.toggled.connect(lambda: self.changeStyle())
        about_action.triggered.connect(self.showAbout)

        # Action introduction into menus
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(cut_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        pref_menu.addAction(dark_theme_action)
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
                little_spacer.setFixedWidth(20)
                self.tool_bar.addWidget(little_spacer)

            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(QIcon(images[button]))
            b.setText(str(button))
            b.setToolTip(str(button))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            b.pressed.connect(lambda tool_name=button: self.manageTools(tool_name))

            self.tool_bar.addWidget(b)
            self.tool_buttons[button] = b

        # Big spacer for aesthetic purposes
        big_spacer = QWidget()
        big_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tool_bar.addWidget(big_spacer)

        # Button to run Mininet
        run_button = QToolButton()
        run_button.setText("Run")
        run_button.setStyleSheet("color: green; height: 50px; width: 60px; font: bold")
        run_button.clicked.connect(lambda: self.runNet())
        self.tool_bar.addWidget(run_button)
        self.exec_buttons["Run"] = run_button

        # Button to stop Mininet
        stop_button = QToolButton()
        stop_button.setText("Stop")
        stop_button.setStyleSheet("color: red; height: 50px; width: 60px; font: bold")
        stop_button.clicked.connect(lambda: self.stopNet())
        self.tool_bar.addWidget(stop_button)
        self.exec_buttons["Stop"] = stop_button

        # Button to update scene with Mininet information
        update_button = QToolButton()
        update_button.setText("Update")
        update_button.setStyleSheet("color: orange; height: 50px; width: 60px; font: bold")
        update_button.clicked.connect(lambda: self.updateSceneInfo())
        self.tool_bar.addWidget(update_button)
        self.exec_buttons["Update"] = update_button

        # Select tool as default
        self.active_tool = "Select"
        self.scene.current_tool = "Select"
        self.tool_buttons["Select"].setChecked(True)

    # Auxiliary functions

    def restartTools(self):
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(True)
        self.manageTools("Select")

    def stopTools(self):
        self.manageTools("Select")
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(False)

    def manageTools(self, tool_name):
        """Method to check up the current tool and manage the buttons"""
        if tool_name == self.active_tool:
            if tool_name == "Select":
                self.tool_buttons["Select"].toggle()
            else:
                self.tool_buttons["Select"].setChecked(True)
                self.active_tool = "Select"
                self.scene.current_tool = "Select"
        else:
            self.tool_buttons[self.active_tool].toggle()
            self.active_tool = tool_name
            self.scene.current_tool = tool_name

    def updateToolBarIcons(self):
        images = imagesMiniGUI()
        for button in self.tool_buttons:
            self.tool_buttons[button].setIcon(QIcon(images[self.tool_buttons[button].text()]))

        global app_theme
        if app_theme == "light":
            self.exec_buttons["Run"].setStyleSheet("color: green; height: 50px; width: 60px; font: bold")
            self.exec_buttons["Stop"].setStyleSheet("color: red; height: 50px; width: 60px; font: bold")
            self.exec_buttons["Update"].setStyleSheet("color: orange; height: 50px; width: 60px; font: bold")
        elif app_theme == "dark":
            self.exec_buttons["Run"].setStyleSheet("color: green; height: 50px; width: 60px; font: bold;"
                                                   "hover { background-color: rgb(53, 53, 53)}")
            self.exec_buttons["Stop"].setStyleSheet("color: red; height: 50px; width: 60px; font: bold;"
                                                    "hover { background-color: rgb(53, 53, 53)}")
            self.exec_buttons["Update"].setStyleSheet("color: orange; height: 50px; width: 60px; font: bold;"
                                                      "hover { background-color: rgb(53, 53, 53)}")

    def updateNetIndicators(self):
        if self.net is None:
            self.net_indicators["Text"].setText("Red no activa")
            self.net_indicators["Color"].setStyleSheet("background-color: red")
        elif self.net is not None:
            self.net_indicators["Text"].setText("Red activa")
            self.net_indicators["Color"].setStyleSheet("background-color: green")

    # Scene-related functions

    def modifiedSceneDialog(self):
        """This function's objective is to warn the user that his/her current project has not been saved and lets the
        user to decide to save it, continue without saving or cancelling the action"""
        dialog = QMessageBox(self)
        dialog.setTextFormat(Qt.RichText)
        dialog.setText("<b>Scene has been modified</b>")
        dialog.setInformativeText("Do you want to save the scene?")
        dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Cancel | QMessageBox.Discard)
        dialog.setDefaultButton(QMessageBox.Save)
        dialog.setIcon(QMessageBox.Warning)

        return dialog.exec()

    def clearProject(self):
        """Function used to clear the scene and its related parameters"""
        self.file = None
        self.setWindowTitle("MiniGUI")

        self.scene.clear()
        self.scene.sceneNodes.clear()
        self.scene.sceneLinks.clear()
        self.scene.scene_modified = False
        self.scene.default_ip_last = 1
        self.scene.default_ip = self.scene.default_ip_base + str(self.scene.default_ip_last)
        for tool in self.scene.item_count:
            self.scene.item_count[tool] = 0

    def newProject(self):
        """Function to create a new project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        self.clearProject()

    def openProject(self):
        """It opens a previous existing project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        # Getting directory of last opened project
        if self.file is None:
            directory = os.getcwd()
        else:
            directory = os.path.dirname(self.file)

        dialogfilename = QFileDialog.getOpenFileName(self, "Open file", directory,
                                                     "Mininet topology (*.mn);;All files (*)", "")

        if dialogfilename[0] != "":
            file = open(str(dialogfilename[0]), "r")
            topology_data = json.load(file)

            self.clearProject()
            self.file = str(dialogfilename[0])
            self.setWindowTitle("MiniGUI - " + str(dialogfilename[0]).split("/")[-1])
            self.scene.loadScene(topology_data)

    def saveProject(self):
        """This functions allows the user to store project information in an external file"""
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
                self.file = filepath
                file = open(filepath, "w")
            else:
                return
        else:
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
        """Creation of Mininet node objects"""
        for node in self.scene.sceneNodes:
            node_addr = None
            node_name = self.scene.sceneNodes[node].node_name
            node_type = self.scene.sceneNodes[node].node_type
            node_properties = self.scene.sceneNodes[node].properties
            if node_type != "Switch":
                node_addr = str(node_properties['IP']) + "/" + str(node_properties['PrefixLen'])

            if node_type == "Controller":
                # Still in progress
                pass
            elif node_type == "Host":
                self.net.addHost(node_name, cls=None, ip=node_addr,
                                 defaultRoute=('via ' + str(node_properties["DefaultRoute"])))
            elif node_type == "Router":
                self.net.addHost(node_name, cls=Router, ip=node_addr,
                                 defaultRoute=('via ' + str(node_properties["DefaultRoute"])))
            elif node_type == "Switch":
                self.net.addSwitch(node_name, cls=None)

        # If no controller added, one by default is introduced --> to be checked
        if not self.net.controllers:
            self.net.addController('c0')

    def buildLinks(self):
        """Creation of Mininet link objects between nodes"""
        for link in self.scene.sceneLinks:
            nodes_linked = self.scene.sceneLinks[link].nodes
            if self.scene.sceneLinks[link].isLinkUp():
                link_status = "up"
            else:
                link_status = "down"

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

    def buildNet(self):
        """Function used to create and build the net"""
        self.net = Mininet(topo=None, build=False)

        self.buildNodes()
        self.buildLinks()

        self.net.build()

    def runNet(self):
        """Function called to iniciate Mininet"""
        if self.net is not None:
            return
        elif not self.scene.items():
            self.emptySceneDialog()
            return

        # Net creation and start
        self.buildNet()
        self.net.start()

        # Scene modification
        self.scene.net_running = True
        self.updateNetIndicators()
        self.stopTools()

        # CLI creation
        self.master_cli = MiniCLI(self.net)
        self.master_cli.start()

    def stopNet(self):
        """Function called to stop Mininet"""
        if self.net is None:
            return

        # XTerm cleanse
        cleanUpScreens()

        # CLI (WIP) and net stop
        self.master_cli = None
        self.net.stop()
        self.net = None

        # Scene modification
        self.restartTools()
        self.updateNetIndicators()
        self.scene.net_running = False

    def updateNetNode(self, node):
        """Function to update Mininet node's information when simulation is running"""
        if self.net is None and not isinstance(node, NodeGUI):
            return

        net_node = self.net.nameToNode[node.node_name]

        # IP address update
        for intf in node.properties["eth_intfs"]:
            intf_addr = node.properties["eth_intfs"][intf]
            net_node.cmd("ifconfig " + str(intf) + " " + str(intf_addr))

        # Default route update
        if len(net_node.cmdPrint("ip route show default")) > 0:
            net_node.cmd("ip route del default")
        net_node.cmd("ip route add default via " + str(node.properties["DefaultRoute"]))

    def updateNetLink(self, link):
        """Function to update Mininet link's information when simulation is running"""
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
                # Inicialization
                first_intf = True
                node_intfs = self.scene.sceneNodes[node].properties["eth_intfs"]
                net_node = self.net.nameToNode[self.scene.sceneNodes[node].node_name]

                # Interface information (IP address, netmask)
                for intf in node_intfs:
                    output = net_node.cmdPrint("ip addr show dev " + str(intf))
                    new_ip = output.split("inet ")[1].split("/")[0]
                    new_mask = output.split(" brd")[1].split("/")[-1]
                    self.scene.sceneNodes[node].properties["eth_intfs"][intf] = (str(new_ip) + "/" + str(new_mask))
                    if first_intf:
                        self.scene.sceneNodes[node].properties["IP"] = new_ip
                        self.scene.sceneNodes[node].properties["PrefixLen"] = new_mask
                        first_intf = False

                # Node's default route
                output = net_node.cmdPrint("ip route")
                if len(output.split("via ")) > 1:
                    new_default_route = output.split("via ")[1].split(" dev")[0]
                    self.scene.sceneNodes[node].properties["DefaultRoute"] = str(new_default_route)

                # Scene modification
                self.scene.sceneNodes[node].changeSceneIpTags()
                self.scene.updateSceneLinks(self.scene.sceneNodes[node])

        # Link state (up or down)
        for link in self.scene.sceneLinks:
            node_name = self.scene.sceneLinks[link].nodes[0]
            intf_name = self.scene.sceneNodes[node_name].links[link]
            net_node = self.net.nameToNode[node_name]
            output = str(net_node.cmdPrint("ethtool " + str(intf_name)))
            if output.split("Link detected: ")[1].split("\r\n")[0] == "yes":
                self.scene.sceneLinks[link].setLinkState(is_up=True)
            else:
                self.scene.sceneLinks[link].setLinkState(is_up=False)

        self.scene.scene_modified = True

    def getRoutingTable(self, node):
        """This function returns the routing table of switch"""
        if self.net is None and not isinstance(node, NodeGUI):
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
        for element in result.split(" "):
            if str(element) != "":
                if index > 3:
                    if index % 4 == 0:
                        output["Port"].append(element.split("\n")[0])
                    elif index % 4 == 1:
                        output["VLAN"].append(element.split("\n")[0])
                    elif index % 4 == 2:
                        output["MAC"].append(element.split("\n")[0])
                    elif index % 4 == 3:
                        output["Age"].append(element.split("\n")[0])

                index = index + 1

        return output

    def xterm(self, name=None):
        """This function is used to call a personal terminal for an specific node"""
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
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                event.ignore()

        self.writePreferences()

    def showEvent(self, event):
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def resizeEvent(self, event):
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def changeEvent(self, event):
        """Function used to know if the palette has been changed"""
        if event.type() == QEvent.PaletteChange and self.tool_buttons:
            self.updateToolBarIcons()
        else:
            QWidget.changeEvent(self, event)

    # Preferences functions

    def writePreferences(self):
        """This function saves in a external configuration file the user's preferences"""
        global app_theme
        self.settings = QSettings('MiniGUI', 'settings')
        self.settings.setValue("AppTheme", str(app_theme))
        self.settings.setValue("ProjectPath", str(self.file))

    @staticmethod
    def changeStyle():
        global app_theme
        if app_theme == "light":
            app_theme = "dark"
        else:
            app_theme = "light"

        changeAppPalette()

    # Pop-up related functions

    def showAbout(self):
        """This function creates a window displaying the information about the application itself"""
        about = QDialog(self)
        about.setWindowTitle("About MiniGUI")

        layout_v = QVBoxLayout()
        layout_h = QHBoxLayout()

        global app_theme
        if app_theme == "light":
            about_icon = QPixmap("./images/logo-urjc_color.png")
        else:
            about_icon = QPixmap("./images/logo-urjc_blanco.png")

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
    global app_theme
    if app_theme == "light":
        return {
            "Host": "./images_01_02/laptop.png",
            "Switch": "./images_01_02/switch.png",
            "Router": "./images_01_02/router.png",
            "Link": "./images_01_02/cable.png",
            "Select": "./images_01_02/select.png",
            "Delete": "./images_01_02/delete.png"
        }
    else:
        return {
            "Host": "./images_01_02/laptop.png",
            "Switch": "./images_01_02/switch.png",
            "Router": "./images_01_02/router.png",
            "Link": "./images_01_02/cable_white.png",
            "Select": "./images_01_02/select_white.png",
            "Delete": "./images_01_02/delete_white.png"
        }


def changeAppPalette():
    global app_theme
    if app_theme == "light":
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
    app_theme = "light"
    gui_app = MiniGUI()
    gui_app.show()
    sys.exit(app.exec())
