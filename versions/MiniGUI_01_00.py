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

# Package import
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
import os
import json

# Mininet package import
from mininet.net import Mininet
from mininet.term import makeTerm, cleanUpScreens
from mininet.node import Node


# Extended class from Mininet base class

class Router(Node):
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
    """Base class for hosts, switches, routers and link dialogs"""
    def __init__(self, parent=None):
        super(BaseDialog, self).__init__(parent=parent)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        self.layout.addWidget(button_box)
        self.setLayout(self.layout)


class HostDialog(BaseDialog):
    """Dialog class for hosts"""
    def __init__(self, host, parent=None):
        super(HostDialog, self).__init__(parent=parent)

        self.host = host
        self.results = {}
        self.properties = host.getNodeProperties()

        self.setWindowTitle("Host properties: " + str(host.getNodeName()))
        self.setFixedWidth(450)

        self.setHostDialog()

    def setHostDialog(self):
        tab_menu = QTabWidget()
        self.layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setPropertiesTab(), "Properties")
        # Second tab: VLAN interfaces
        tab_menu.addTab(self.setVlanInterfaces(), "VLAN Interfaces")

    def setPropertiesTab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Hostname
        name_label = QLabel("Host name")
        name_edit_label = QLineEdit(str(self.host.getNodeName()))
        self.results["node_name"] = name_edit_label
        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)

        # IP Address
        ip_label = QLabel("IP Address")
        ip_edit_label = QLineEdit(str(self.properties["IP"]))
        self.results["IP"] = ip_edit_label
        layout.addWidget(ip_label)
        layout.addWidget(ip_edit_label)

        # Default route
        droute_label = QLabel("Default route")
        droute_edit_label = QLineEdit()
        if "default_route" in self.properties:
            droute_edit_label.setText(self.properties["default_route"])
        self.results["default_route"] = droute_edit_label
        layout.addWidget(droute_label)
        layout.addWidget(droute_edit_label)

        layout.addStretch()

        widget.setLayout(layout)

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

        self.results = {}
        self.switch = switch
        self.properties = switch.getNodeProperties()

        self.setWindowTitle("Switch properties: " + str(switch.getNodeName()))
        self.setFixedWidth(450)

        self.setSwitchDialog()

    # WIP --> To be defined
    def setSwitchDialog(self):
        pass


class RouterDialog(BaseDialog):
    """Dialog class for routers"""
    def __init__(self, router, parent=None):
        super(RouterDialog, self).__init__(parent=parent)

        self.results = {}
        self.router = router
        self.properties = router.getNodeProperties()

        self.setWindowTitle("Router properties: " + str(router.getNodeName()))
        self.setFixedWidth(450)

        self.setRouterDialog()

    def setRouterDialog(self):
        tab_menu = QTabWidget()
        self.layout.insertWidget(0, tab_menu)

        # First tab: basic properties
        tab_menu.addTab(self.setPropertiesTab(), "Properties")
        # Second tab: Ethernet interfaces
        tab_menu.addTab(self.setEthernetIntfs(), "Ethernet interfaces")

    def setPropertiesTab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Router name
        name_label = QLabel("Router name")
        name_edit_label = QLineEdit(str(self.router.getNodeName()))
        self.results["node_name"] = name_edit_label
        layout.addWidget(name_label)
        layout.addWidget(name_edit_label)

        # Default route
        droute_label = QLabel("Default route")
        droute_edit_label = QLineEdit()
        if "default_route" in self.properties:
            droute_edit_label.setText(self.properties["default_route"])
        self.results["default_route"] = droute_edit_label
        layout.addWidget(droute_label)
        layout.addWidget(droute_edit_label)

        layout.addStretch()

        widget.setLayout(layout)

        return widget

    def setEthernetIntfs(self):
        widget = QWidget()
        layout = QGridLayout()
        widget.setLayout(layout)
        layout.setColumnMinimumWidth(1, 10)

        router_intfs = self.router.getNodeIntfs()
        intf_ip_list = {}

        layout.addWidget(QLabel("Interface name"), 0, 0)
        layout.addWidget(QLabel("IP Address"), 0, 2)

        for index in range(len(router_intfs)):
            intf_name = "eth" + str(index)

            intf_name_label = QLabel(intf_name)
            layout.addWidget(intf_name_label, index + 1, 0, Qt.AlignRight)

            intf_ip_label = QLineEdit(router_intfs[intf_name])
            intf_ip_list[intf_name] = intf_ip_label
            layout.addWidget(intf_ip_label, index + 1, 2)

        self.results["eth_intfs"] = intf_ip_list

        return widget


class NodeGUI(QGraphicsPixmapItem):
    """"Class for node elements"""
    def __init__(self, x, y, node_type, name=None, properties=None, new_node=False, net_ctrl=None):
        super(NodeGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial attributes
        self.width = 64
        self.height = 64
        self.name = name
        self.node_type = node_type
        self.icon = None
        self.image = None
        self.links = {}
        self.scene_tags = {}
        self.properties = {}

        # Setting up initial attributes
        self.setNodeAttributes(x, y, properties, new_node)

    def setNodeAttributes(self, x, y, properties=None, new_node=False):
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
        self.setPos(x, y)
        self.setZValue(100)

        # Moving element in order to center it where user has clicked (only for new elements)
        if new_node:
            offset = self.boundingRect().topLeft() - self.boundingRect().center()
            self.moveBy(offset.x(), offset.y())

        # Properties assignment / creation
        self.properties["IP"] = properties["IP"]
        self.properties["default_route"] = ""
        if not new_node:
            self.links = properties["links"]
            self.properties["eth_intfs"] = properties["eth_intfs"]
            self.properties["default_route"] = properties["default_route"]

    # Access / Creation / Removing attribute functions

    def getNodeType(self):
        return self.node_type

    def getNodeName(self):
        return self.name

    def setNodeName(self, name):
        self.name = name

    def getNodeLinks(self):
        return self.links

    def addNewLink(self, name):
        if name not in self.links:
            new_intf = self.assignIntfName()
            self.links[name] = new_intf
            self.properties["eth_intfs"][new_intf] = ""

    def deleteLink(self, name):
        if name in self.links:
            intf = self.links.pop(name)
            self.properties["eth_intfs"].pop(intf)

    def getNodeIntfs(self):
        return self.properties["eth_intfs"]

    def getNodeProperties(self):
        return self.properties

    def addSceneNameTag(self, tag):
        self.scene_tags["name"] = tag

    def addSceneIpTag(self, tag):
        self.scene_tags["IP"] = tag

    def updateIcon(self):
        images = imagesMiniGUI()
        self.icon = images[self.node_type]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Auxiliary functions

    def assignIntfName(self):
        # Esta función se encargará de asignar un nombre de interfaz a cada enlace
        if "eth_intfs" not in self.properties:
            self.properties["eth_intfs"] = {}
            return "eth0"

        intf_base = "eth"
        intf_count = 0
        for index in range(len(self.properties["eth_intfs"])):
            coincidence = False
            intf_name = intf_base + str(intf_count)
            if str(intf_name) in self.properties["eth_intfs"]:
                intf_count = intf_count + 1
                coincidence = True

            if not coincidence:
                return intf_name

        intf_name = intf_base + str(intf_count)

        return intf_name

    def changeSceneName(self, new_name):
        tag = self.scene_tags["name"]
        tag.setPlainText(str(new_name))
        tag.setX((self.boundingRect().width() - tag.boundingRect().width()) / 2)

    def changeSceneIp(self, new_ip):
        tag = self.scene_tags["IP"]
        tag.setPlainText(str(new_ip))
        tag.setX((self.boundingRect().width() - tag.boundingRect().width()) / 2)

    def nodePropertiesDialog(self):
        if self.node_type == "Host":
            dialog = HostDialog(self, self.net_controller)
        elif self.node_type == "Switch":
            dialog = SwitchDialog(self, self.net_controller)
        elif self.node_type == "Router":
            dialog = RouterDialog(self, self.net_controller)
        else:
            return

        if dialog.exec():
            scene = self.scene()
            # Nombre del elemento
            new_name = dialog.results["node_name"].text()
            if isinstance(scene, CanvasGUI) and scene.isFeasibleName(new_name):
                scene.sceneNodes[new_name] = scene.sceneNodes.pop(self.getNodeName())
                self.setNodeName(new_name)
                self.changeSceneName(new_name)
            # Dirección IP
            if self.node_type == "Host":
                new_ip = dialog.results["IP"].text()
                if new_ip != self.properties["IP"] and scene.isFeasibleIP(new_ip):
                    self.properties["IP"] = new_ip
                    self.changeSceneIp(new_ip)
            # Ruta por defecto
            new_droute = dialog.results["default_route"].text()
            if "default_route" in self.properties and new_droute != self.properties["default_route"]:
                self.properties["default_route"] = new_droute
            # Interfaces Ethernet
            if self.node_type == "Router":
                for eth in self.properties["eth_intfs"]:
                    new_eth_ip = dialog.results["eth_intfs"][eth].text()
                    if len(new_eth_ip) > 0:
                        self.properties["eth_intfs"][eth] = new_eth_ip

    def changePixmapColor(self, mode=None):
        painter = QPainter()
        image = QImage(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        mask = QImage(image)
        mask_color = Qt.blue

        if mode is not None and mode == "Delete":
            mask_color = Qt.red

        painter.begin(mask)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(mask.rect(), mask_color)
        painter.end()

        painter.begin(image)
        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
        painter.drawImage(0, 0, mask)
        painter.end()

        self.setPixmap(QPixmap(image))

    # WIP --> may be deleted in following versions
    def returnOriginalPixmap(self):
        # Retrieving original icon
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
        context_menu = QMenu()

        # Contextual menu changes according to if Mininet is running or not
        scene = self.scene()
        if scene is not None and isinstance(scene, CanvasGUI) and not scene.isNetRunning():
            menu_text = str(self.getNodeType()) + " properties"
            properties_act = QAction(menu_text, self.net_controller)
            properties_act.setStatusTip("Open " + str(self.getNodeType()).lower() + " properties menu")
            properties_act.triggered.connect(lambda: self.nodePropertiesDialog())
            context_menu.addAction(properties_act)
        elif scene is not None and isinstance(scene, CanvasGUI) and scene.isNetRunning():
            xterm_act = QAction("XTerm", self.net_controller)
            xterm_act.setStatusTip("Open " + str(self.getNodeType()).lower() + " properties menu")
            xterm_act.triggered.connect(lambda: self.net_controller.xterm(name=self.getNodeName()))
            context_menu.addAction(xterm_act)

        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        """This function initiates when the node gains focus from the scene. To get the attention from the user, the
        program change the node color to highlight it"""
        self.returnOriginalPixmap()
        self.changePixmapColor()

    def focusOutEvent(self, event):
        """This function is the contrary of the previous one. It is used to retrieve the original icon"""
        self.returnOriginalPixmap()

    def hoverEnterEvent(self, event):
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, CanvasGUI):
            scene_tool = node_scene.getSelectedSceneTool()

        if scene_tool is not None and scene_tool == "Delete":
            self.changePixmapColor(mode="Delete")
            return

        if self.hasFocus():
            return

        self.changePixmapColor()

    def hoverLeaveEvent(self, event):
        # Scene selected tool changes mask color
        scene_tool = None
        node_scene = self.scene()
        if isinstance(node_scene, CanvasGUI):
            scene_tool = node_scene.getSelectedSceneTool()

        if scene_tool is not None and scene_tool == "Delete" and self.hasFocus():
            self.changePixmapColor()
            return

        if self.hasFocus():
            return

        self.returnOriginalPixmap()


class LinkGUI(QGraphicsLineItem):
    """Class for links of node elements"""
    def __init__(self, x1, y1, x2, y2, net_ctrl=None):
        super(LinkGUI, self).__init__(x1, y1, x2, y2)

        # Initial attributes
        self.name = ""
        self.items = []
        self.pen = QPen()

        # Setting up initial attributes
        self.setLinkAttributes()

    def setLinkAttributes(self):
        # Set color and width of the link
        self.pen.setWidth(4)
        self.pen.setColor(Qt.darkCyan)
        self.setPen(self.pen)

        # Setting of internal attributes
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

    # Access / Creation / Removing attribute functions

    def getLinkName(self):
        return self.name

    def setLinkName(self, name):
        self.name = name

    def getNodesLinked(self):
        return self.items

    def addNodesLinked(self, name1, name2):
        self.items = list((name1, name2))

    def updateEndPoint(self, x2, y2):
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    # Auxiliary functions

    def changeLineColor(self):
        self.pen.setColor(Qt.darkRed)
        self.setPen(self.pen)

    def returnOriginalLine(self):
        self.pen.setColor(Qt.darkCyan)
        self.setPen(self.pen)

    # Event handlers

    # WIP
    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction("Link properties")
        action = context_menu.exec(event.screenPos())

    def focusInEvent(self, event):
        self.returnOriginalLine()
        self.changeLineColor()

    def focusOutEvent(self, event):
        self.returnOriginalLine()

    # WIP --> To be defined
    def hoverEnterEvent(self, event):
        if self.hasFocus():
            return
        self.changeLineColor()

    # WIP --> To be defined
    def hoverLeaveEvent(self, event):
        if self.hasFocus():
            return
        self.returnOriginalLine()


class CanvasGUI(QGraphicsScene):
    def __init__(self, net_ctrl=None):
        super(CanvasGUI, self).__init__()

        # Pointer to main program
        self.net_controller = net_ctrl

        # Initial variables
        self.scene_modified = False
        self.net_running = False
        self.current_tool = None

        # Node & Link dictionaries
        self.sceneNodes = {}
        self.sceneLinks = {}

        # Model initialization
        self.item_letter = {"Host": "h", "Switch": "s", "Router": "r", "Link": "l"}
        self.item_count = {"Host": 0, "Switch": 0, "Router": 0, "Link": 0}

        # Event handling initialization
        self.new_link = None
        self.link_orig_item = None

        # IP address variables
        self.default_ip_last = 1
        self.default_ip_base = "10.0.0."
        self.default_ip = self.default_ip_base + str(self.default_ip_last)

    # Attribute access functions

    def getSelectedSceneTool(self):
        return self.current_tool

    def setNetRunning(self, state=False):
        self.net_running = state

    def isNetRunning(self):
        return self.net_running

    # Scene functions

    # WIP --> To be reviewed in following versions
    @staticmethod
    def addSceneNodeTags(node, name, ip):
        """This function creates tags for node and links them to it"""

        # Name tag
        name_tag = QGraphicsTextItem(name, node)
        node.addSceneNameTag(name_tag)
        name_tag.setPos((node.boundingRect().width() - name_tag.boundingRect().width()) / 2,
                        node.boundingRect().bottomLeft().y())

        # IP Address tag. Only represented when node is host.
        if ip is None:
            return

        ip_tag = QGraphicsTextItem(ip, node)
        node.addSceneIpTag(ip_tag)
        ip_tag.setPos((node.boundingRect().width() - ip_tag.boundingRect().width()) / 2,
                      node.boundingRect().bottomLeft().y() + name_tag.boundingRect().bottomLeft().y() / 2)

    def addSceneNode(self, x, y, node_type, name=None, properties=None):
        """Function to add a node element to the scene"""
        # Properties checking (in case the element is loaded up from previous projects)
        if properties is None:
            properties = {"IP": None}
            if node_type == "Host":
                properties["IP"] = self.default_ip

        if name is not None:
            node_name = name
            node_new = False
        else:
            while True:
                node_name = self.item_letter[node_type] + str(self.item_count[node_type])
                if self.isFeasibleName(node_name):
                    break

                self.item_count[node_type] = self.item_count[node_type] + 1

            node_new = True

        node = NodeGUI(x, y, node_type, node_name, properties, node_new, net_ctrl=self.net_controller)
        self.sceneNodes[node_name] = node

        # Addition of node to scene, gaining focus and modifying the scene
        self.addSceneNodeTags(node, node_name, properties["IP"])
        self.addItem(node)
        node.setFocus()

        self.scene_modified = True
        self.item_count[node_type] = self.item_count[node_type] + 1
        self.default_ip_last = self.default_ip_last + 1
        self.default_ip = self.default_ip_base + str(self.default_ip_last)

    def addSceneLink(self, x, y):
        """Function to inicializate a new link on the scene"""
        self.new_link = LinkGUI(x, y, x, y, net_ctrl=self.net_controller)
        self.addItem(self.new_link)

    def removeSceneItem(self, item):
        """Deletes an node/link from the scene and all links related to it"""
        # Initial variable in order to remove links later
        links_to_remove = []

        # Separate code depending on item's class
        if isinstance(item, NodeGUI):
            self.sceneNodes.pop(item.name)
            for link in item.links:
                links_to_remove.append(link)
                self.removeItem(self.sceneLinks[link])
                self.sceneLinks.pop(link)

        if isinstance(item, LinkGUI):
            links_to_remove.append(item.getLinkName())

        # Update of all elements related to the to-be-deleted item
        for link in links_to_remove:
            for node in self.sceneNodes:
                if link in self.sceneNodes[node].getNodeLinks():
                    self.sceneNodes[node].deleteLink(link)

        # Removal of item from scene, modifying the scene
        self.removeItem(item)
        self.scene_modified = True

    def finishSceneLink(self, name=None):
        """Last function to be called when a link is set up between two nodes"""
        line = self.new_link.line()
        orig_item = self.itemAt(line.p1(), QTransform())
        dest_item = self.itemAt(line.p2(), QTransform())

        # Naming
        if name is None:
            while True:
                new_name = self.item_letter["Link"] + str(self.item_count["Link"])
                if self.isFeasibleName(new_name):
                    break

                self.item_count["Link"] = self.item_count["Link"] + 1
        else:
            new_name = name

        # Updating of link information in both elements and link
        self.new_link.setLinkName(new_name)
        self.new_link.addNodesLinked(orig_item.getNodeName(), dest_item.getNodeName())
        self.sceneLinks[new_name] = self.new_link
        orig_item.addNewLink(new_name)
        dest_item.addNewLink(new_name)

        # Resetting temporary variables to initial state
        self.new_link = None
        self.link_orig_item = None
        self.scene_modified = True

    def updateSceneLinks(self, item):
        """Function to update links position if one of the nodes moves"""
        item_links = item.getNodeLinks()
        item_name = item.getNodeName()
        item_pos = item.scenePos()
        if not item_links:
            self.scene_modified = True
            return

        links_list = []
        for link in self.sceneLinks:
            if link in item_links:
                links_list.append(link)

        for link in links_list:
            for link_item_name in self.sceneLinks[link].getNodesLinked():
                if link_item_name != item_name:
                    scene_item = self.sceneNodes[link_item_name]
                    scene_item_pos = scene_item.scenePos()
                    offset_item = item.boundingRect().center()
                    offset_scene_item = scene_item.boundingRect().center()
                    self.sceneLinks[link].setLine(item_pos.x() + offset_item.x(),
                                                  item_pos.y() + offset_item.y(),
                                                  scene_item_pos.x() + offset_scene_item.x(),
                                                  scene_item_pos.y() + offset_scene_item.y())

        self.scene_modified = True

    def loadScene(self, data):
        """Function called when loading a scene from an external file"""
        if "hosts" in data:
            hosts_list = data["hosts"]
            for host in hosts_list:
                host_name = host["name"]
                host_x_pos = host["x_pos"]
                host_y_pos = host["y_pos"]
                host_properties = host["properties"]
                host_properties["links"] = host["links"]
                self.addSceneNode(host_x_pos, host_y_pos, "Host", host_name, host_properties)

        if "switches" in data:
            switches_list = data["switches"]
            for switch in switches_list:
                switch_name = switch["name"]
                switch_x_pos = switch["x_pos"]
                switch_y_pos = switch["y_pos"]
                switch_properties = switch["properties"]
                switch_properties["links"] = switch["links"]
                self.addSceneNode(switch_x_pos, switch_y_pos, "Switch", switch_name, switch_properties)

        if "routers" in data:
            routers_list = data["routers"]
            for router in routers_list:
                router_name = router["name"]
                router_x_pos = router["x_pos"]
                router_y_pos = router["y_pos"]
                router_properties = router["properties"]
                router_properties["links"] = router["links"]
                self.addSceneNode(router_x_pos, router_y_pos, "Router", router_name, router_properties)

        if "links" in data:
            links_list = data["links"]
            for link in links_list:
                link_items_name = link["items"]
                link_name = link["name"]
                scene_element = []
                for item_name in link_items_name:
                    scene_element.append(self.sceneNodes[item_name])

                orig_coor = scene_element[0].scenePos() + scene_element[0].boundingRect().center()
                dest_coor = scene_element[1].scenePos() + scene_element[1].boundingRect().center()
                self.addSceneLink(orig_coor.x(), orig_coor.y())
                self.new_link.updateEndPoint(dest_coor.x(), dest_coor.y())
                self.finishSceneLink(name=link_name)

        self.scene_modified = False

    def saveScene(self):
        """Function called to save the state of the current project"""
        # Initial variables
        file_dictionary = {}
        hosts_saved = []
        switches_saved = []
        routers_saved = []
        link_saved = []

        for item in self.sceneNodes:
            node = {
                "name": self.sceneNodes[item].getNodeName(),
                "x_pos": self.sceneNodes[item].scenePos().x(),
                "y_pos": self.sceneNodes[item].scenePos().y(),
                "links": self.sceneNodes[item].getNodeLinks(),
                "properties": self.sceneNodes[item].getNodeProperties()
            }
            if self.sceneNodes[item].getNodeType() == "Host":
                hosts_saved.append(node)
            elif self.sceneNodes[item].getNodeType() == "Switch":
                switches_saved.append(node)
            elif self.sceneNodes[item].getNodeType() == "Router":
                routers_saved.append(node)

        for link in self.sceneLinks:
            node = {
                "name": self.sceneLinks[link].getLinkName(),
                "items": self.sceneLinks[link].getNodesLinked()
            }
            link_saved.append(node)

        file_dictionary["hosts"] = hosts_saved
        file_dictionary["switches"] = switches_saved
        file_dictionary["routers"] = routers_saved
        file_dictionary["links"] = link_saved

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
            if isinstance(item, NodeGUI) and item.getNodeName() == name:
                return False
            elif isinstance(item, LinkGUI) and item.getLinkName() == name:
                return False

        return True

    def checkFeasibleLink(self, last_item):
        """ This function checks if a connection is possible between two nodes or wherever the user release
        the mouse button."""
        if last_item == self.link_orig_item or last_item == self.new_link:
            return False

        if isinstance(self.link_orig_item, NodeGUI) and isinstance(last_item, NodeGUI):
            if self.link_orig_item.getNodeType() == "Host" and last_item.getNodeType() == "Host":
                return False

        orig_item_links = self.link_orig_item.getNodeLinks()
        dest_item_links = last_item.getNodeLinks()
        for orig_link in orig_item_links:
            for dest_link in dest_item_links:
                if dest_link == orig_link:
                    return False

        return True

    def selectSceneItem(self, item):
        """Function to change the focus and the selection of the scene to the element that the user has clicked on."""
        if not isinstance(item, NodeGUI) and not isinstance(item, LinkGUI):
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
                if isinstance(item, NodeGUI):
                    item.updateIcon()
                if isinstance(item, QGraphicsTextItem):
                    global app_theme
                    if app_theme == "dark":
                        item.setDefaultTextColor(Qt.white)
                    else:
                        item.setDefaultTextColor(Qt.black)

        return QGraphicsScene.event(self, event)

    def keyPressEvent(self, event):
        """Function related to key-pressed events. Now used only for element deleting."""
        if self.isNetRunning():
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
                self.link_orig_item = item
                offset = item.boundingRect().center()
                self.addSceneLink(item.scenePos().x() + offset.x(), item.scenePos().y() + offset.y())
        elif self.current_tool == "Delete":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and not isinstance(item, QGraphicsTextItem):
                self.removeSceneItem(item)
        else:
            if event.button() != Qt.LeftButton:
                return

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
                self.new_link = None
                self.link_orig_item = None


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
        self.menu_bar = self.menuBar()
        self.tool_bar = self.addToolBar("Tool Bar")
        self.tool_buttons = {}
        self.exec_buttons = {}
        self.active_tool = None

        # Scene variables initialization
        self.canvas = QGraphicsView()
        self.scene = CanvasGUI(net_ctrl=self)

        # Mininet variables
        self.net = None

        # Interface personalization setting
        self.setMainWindowGUI()
        self.setMenuBarGUI()
        self.setToolBarGUI()

        # Retrieving the user preferences saved in other sessions
        self.setSettings()

    # Application initialization functions

    def setMainWindowGUI(self):
        """Main window setting"""
        self.setGeometry(500, 200, 1000, 600)
        self.setWindowTitle("MiniGUI")
        self.statusBar()
        self.setCentralWidget(self.canvas)

        self.canvas.setScene(self.scene)
        self.canvas.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.canvas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        font = app.font()
        font.setPixelSize(14)
        app.setFont(font)

    def setMenuBarGUI(self):
        """Main menu bar setting"""
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
        run_button.setCheckable(True)
        run_button.setText("Run")
        run_button.setStyleSheet("color: green; height: 50px; width: 50px; font: bold")
        run_button.pressed.connect(lambda: self.runNet())
        self.tool_bar.addWidget(run_button)
        self.exec_buttons["Run"] = run_button

        # Button to stop Mininet
        stop_button = QToolButton()
        stop_button.setCheckable(True)
        stop_button.setText("Stop")
        stop_button.setStyleSheet("color: red; height: 50px; width: 50px; font: bold")
        stop_button.pressed.connect(lambda: self.stopNet())
        self.tool_bar.addWidget(stop_button)
        self.exec_buttons["Stop"] = stop_button

        # Select tool as default
        self.active_tool = "Select"
        self.scene.current_tool = "Select"
        self.tool_buttons["Select"].setChecked(True)

    # WIP
    def setSettings(self):
        """Checking and retrieving of user preferences from other sessions"""
        self.settings = QSettings('MiniGUI', 'settings')
        global app_theme
        app_theme = self.settings.value('app theme')
        if app_theme is None:
            app_theme = "light"

    # Auxiliary functions

    def restartTools(self):
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(True)

        self.manageTools("Select")

    def stopTools(self):
        self.manageTools("Select")
        for button in self.tool_buttons:
            self.tool_buttons[button].setEnabled(False)

    def updateToolBarIcons(self):
        images = imagesMiniGUI()
        for button in self.tool_buttons:
            self.tool_buttons[button].setIcon(QIcon(images[self.tool_buttons[button].text()]))

        global app_theme
        if app_theme == "light":
            self.exec_buttons["Run"].setStyleSheet("color: green; height: 50px; width: 50px; font: bold")
            self.exec_buttons["Stop"].setStyleSheet("color: red; height: 50px; width: 50px; font: bold")
        elif app_theme == "dark":
            self.exec_buttons["Run"].setStyleSheet("color: green; height: 50px; width: 50px; font: bold;"
                                                   "hover { background-color: rgb(53, 53, 53)}")
            self.exec_buttons["Stop"].setStyleSheet("color: red; height: 50px; width: 50px; font: bold;"
                                                    "hover { background-color: rgb(53, 53, 53)}")

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

    # WIP
    def openProject(self):
        """It opens a previous existing project"""
        if self.scene.scene_modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        dialogfilename = QFileDialog.getOpenFileName(self, "Open file", os.getcwd(),
                                                     "Mininet topology (*.mn);;All files (*)", "")

        if dialogfilename[0] != "":
            file = open(str(dialogfilename[0]), "r")
            topology_data = json.load(file)

            self.clearProject()
            self.file = str(dialogfilename[0])
            self.setWindowTitle("MiniGUI - " + str(dialogfilename[0]).split("/")[-1])
            self.scene.loadScene(topology_data)

    # WIP
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
        for item in self.scene.sceneNodes:
            node_name = self.scene.sceneNodes[item].getNodeName()
            node_type = self.scene.sceneNodes[item].getNodeType()
            node_properties = self.scene.sceneNodes[item].getNodeProperties()

            if node_type == "Controller":
                # Still in progress
                pass
            elif node_type == "Router":
                default_ip = list(node_properties["eth_intfs"].values())[0]
                self.net.addHost(node_name, cls=Router, ip=str(default_ip))
            elif node_type == "Switch":
                self.net.addSwitch(node_name, cls=None)
            elif node_type == "Host":
                self.net.addHost(node_name, cls=None, ip=str(node_properties['IP']),
                                 defaultRoute=('via ' + str(node_properties["default_route"])))

        # If no controller added, one by default is introduced
        if not self.net.controllers:
            self.net.addController('c0')

    def buildLinks(self):
        for link in self.scene.sceneLinks:
            items_linked = self.scene.sceneLinks[link].getNodesLinked()

            first_item_router = None
            second_item_router = None
            for node in self.scene.sceneNodes:
                node_item = self.scene.sceneNodes[node]
                if items_linked[0] == node_item.getNodeName() and node_item.getNodeType() == "Router":
                    first_item_router = node_item
                if items_linked[1] == node_item.getNodeName() and node_item.getNodeType() == "Router":
                    second_item_router = node_item

            # According to the linked items, three cases can be distinguished:

            # CASE I: non router --> non router
            if first_item_router is None and second_item_router is None:
                node_1, node_2 = self.net.nameToNode[items_linked[0]], self.net.nameToNode[items_linked[1]]
                self.net.addLink(node_1, node_2)
                continue

            # CASE II: non router --> router or viceversa
            router_item = None
            if first_item_router is not None and second_item_router is None:
                node_router = self.net.nameToNode[items_linked[0]]
                node_non_router = self.net.nameToNode[items_linked[1]]
                router_item = first_item_router
            elif first_item_router is None and second_item_router is not None:
                node_router = self.net.nameToNode[items_linked[1]]
                node_non_router = self.net.nameToNode[items_linked[0]]
                router_item = second_item_router

            if router_item is not None:
                link_name = self.scene.sceneLinks[link].getLinkName()
                router_intfs = router_item.getNodeIntfs()
                router_links = router_item.getNodeLinks()
                router_link_intf = router_links[link_name]
                router_link_ip = router_intfs[router_link_intf]
                self.net.addLink(node_non_router, node_router,
                                 intfName2=(router_item.getNodeName() + '-' + str(router_link_intf)),
                                 params2={'ip': str(router_link_ip)})
                continue

            # CASE III: router --> router
            link_name = self.scene.sceneLinks[link].getLinkName()

            router_1_intfs = first_item_router.getNodeIntfs()
            router_1_links = first_item_router.getNodeLinks()
            router_1_link_intf = router_1_links[link_name]
            router_1_link_ip = router_1_intfs[router_1_link_intf]

            router_2_intfs = second_item_router.getNodeIntfs()
            router_2_links = second_item_router.getNodeLinks()
            router_2_link_intf = router_2_links[link_name]
            router_2_link_ip = router_2_intfs[router_2_link_intf]

            node_1 = self.net.nameToNode[items_linked[0]]
            node_2 = self.net.nameToNode[items_linked[1]]

            self.net.addLink(node_1, node_2,
                             intfName1=(first_item_router.getNodeName() + '-' + str(router_1_link_intf)),
                             params1={'ip': str(router_1_link_ip)},
                             intfName2=(second_item_router.getNodeName() + '-' + str(router_2_link_intf)),
                             params2={'ip': str(router_2_link_ip)})

    def buildNet(self):
        """Function used to create and build the net"""
        self.net = Mininet(topo=None, build=False)

        self.buildNodes()
        self.buildLinks()

        self.net.build()

    def runNet(self):
        """Function called to iniciate Mininet"""
        if not self.scene.items():
            self.emptySceneDialog()
            return

        self.stopTools()
        self.scene.setNetRunning(True)
        self.buildNet()
        self.net.start()

    def stopNet(self):
        """Function called to stop Mininet"""
        if self.net is not None:
            self.net.stop()
            cleanUpScreens()
            self.net = None
            self.scene.setNetRunning(False)
            self.restartTools()

    def xterm(self, name=None):
        """This function is used to call a personal terminal for an specific node"""
        if self.net is None or name is None:
            return

        try:
            node = self.scene.sceneNodes[name]
        except KeyError:
            return

        node_name = node.getNodeName()
        node_type = node.getNodeType()
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

    def showEvent(self, event):
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def resizeEvent(self, event):
        self.canvas.setSceneRect(QRectF(self.canvas.viewport().rect()))

    def changeEvent(self, event):
        """Function used to know if the palette has been changed"""
        if event.type() == QEvent.PaletteChange:
            self.updateToolIcons()
        else:
            QWidget.changeEvent(self, event)

    # Preferences functions

    @staticmethod
    def changeStyle():
        global app_theme
        if app_theme == "light":
            app_theme = "dark"
        else:
            app_theme = "light"

        changeAppStyle()

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


def changeAppStyle():
    """Function used to change the application palette"""
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
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app_theme = "light"
    gui_app = MiniGUI()
    gui_app.show()
    sys.exit(app.exec())
