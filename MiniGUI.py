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

# Packages import
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
import os
import json


class NodeGUI(QGraphicsPixmapItem):
    """"Class for main elements"""
    def __init__(self, x, y, tool, name=None, ip=None):
        super(NodeGUI, self).__init__()

        # Initial attributes
        self.tool = tool
        self.name = name
        self.width = 64
        self.height = 64
        self.icon = None
        self.image = None
        self.links = []
        self.properties = {}

        # Setting up initial attributes
        self.setNodeAttributes(x, y, ip)

    def setNodeAttributes(self, x, y, ip=None):
        images = imagesMiniGUI()

        # Setting up icon and image of the node
        self.icon = images[self.tool]
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
        # Moving element in order to center it where user has clicked
        offset = self.boundingRect().topLeft() - self.boundingRect().center()
        self.moveBy(offset.x(), offset.y())

    # Auxiliary functions

    # WIP
    def changePixmapColor(self):
        # Modification of original image
        painter = QPainter(self.image)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setBrush(Qt.blue)
        painter.drawRect(self.image.rect())
        painter.end()
        # Setting new image as the icon within scene
        self.setPixmap(self.image)

    def returnOriginalPixmap(self):
        # Retrieving original icon
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Attribute access functions

    def addNewLink(self, name):
        self.links.append(name)

    def updateIcon(self):
        images = imagesMiniGUI()
        self.icon = images[self.tool]
        self.image = QPixmap(self.icon).scaled(self.width, self.height, Qt.KeepAspectRatio)
        self.setPixmap(self.image)

    # Event handlers

    def itemChange(self, change, value):
        """This function activates when element is moved in the scene"""
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            scene = self.scene()
            if scene is not None and isinstance(scene, CanvasGUI):
                scene.updateLinks(self)

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction(self.tool + " properties")
        action = context_menu.exec_(event.screenPos())

    def focusInEvent(self, event):
        """This function initiates when the node gains focus from the scene. To get the attention from the user, the
        program change the node color to highlight it"""
        self.returnOriginalPixmap()
        self.changePixmapColor()

    def focusOutEvent(self, event):
        """This function is the contrary of the previous one. It is used to retrieve the original icon"""
        self.returnOriginalPixmap()

    def hoverEnterEvent(self, event):
        # In case the node is already colored due to focus, it is not needed to color the node again.
        if self.hasFocus():
            return
        self.changePixmapColor()

    def hoverLeaveEvent(self, event):
        if self.hasFocus():
            return
        self.returnOriginalPixmap()


class LinkGUI(QGraphicsLineItem):
    """Class for links of main elements"""
    def __init__(self, x1, y1, x2, y2):
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

    # Attributes access/update functions

    def addNodesLinked(self, name1, name2):
        self.items = list((name1, name2))

    def updateEndPoint(self, x2, y2):
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    def updateName(self, name):
        self.name = name

    # Auxiliary functions

    def changeLineColor(self):
        self.pen.setColor(Qt.darkRed)
        self.setPen(self.pen)

    def returnOriginalLine(self):
        self.pen.setColor(Qt.darkCyan)
        self.setPen(self.pen)

    # Event handlers

    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction("Link properties")
        action = context_menu.exec_(event.screenPos())

    def focusInEvent(self, event):
        self.returnOriginalLine()
        self.changeLineColor()

    def focusOutEvent(self, event):
        self.returnOriginalLine()

    def hoverEnterEvent(self, event):
        if self.hasFocus():
            return
        self.changeLineColor()

    def hoverLeaveEvent(self, event):
        if self.hasFocus():
            return
        self.returnOriginalLine()


class CanvasGUI(QGraphicsScene):
    def __init__(self):
        super(CanvasGUI, self).__init__()

        # Initial variables
        self.current_tool = None
        self.modified = False

        # Model initialization
        self.item_letter = {"Host": "h", "Switch": "s", "Router": "r", "Link": "l"}
        self.item_count = {"Host": 0, "Switch": 0, "Router": 0, "Link": 0}

        # Event handling initialization
        self.new_link = None
        self.link_orig_item = None

        # IP address variables
        self.default_ip_num = 1
        self.default_ip_base = "10.0.0."
        self.default_ip = self.default_ip_base + str(self.default_ip_num)

    # Scene functions

    @staticmethod
    def addSceneNodeTags(node, name, ip):
        """This function creates tags for item and links them to it"""
        name_tag = QGraphicsTextItem(name, node)
        ip_tag = QGraphicsTextItem(ip, node)

        name_tag.setPos((node.boundingRect().width() - name_tag.boundingRect().width()) / 2,
                        node.boundingRect().bottomLeft().y())
        ip_tag.setPos((node.boundingRect().width() - ip_tag.boundingRect().width()) / 2,
                      node.boundingRect().bottomLeft().y() + name_tag.boundingRect().bottomLeft().y() / 2)

    def addSceneNode(self, x, y, tool, name=None, ip=None):
        """Function to add a main element to the scene"""
        # Name checking (used in case of loading from a previous project)
        if name is not None:
            node_name = name
        else:
            node_name = self.item_letter[tool] + str(self.item_count[tool])
        # IP address checking (used in case of loading from a previous project)
        if ip is not None:
            node_ip = ip
        else:
            node_ip = self.default_ip

        node = NodeGUI(x, y, tool, node_name, node_ip)

        # Addition of node to scene, gaining focus and modifying the scene
        self.addSceneNodeTags(node, node_name, node_ip)
        self.addItem(node)
        node.setFocus()

        self.modified = True
        self.item_count[tool] = self.item_count[tool] + 1
        self.default_ip_num = self.default_ip_num + 1
        self.default_ip = self.default_ip_base + str(self.default_ip_num)

    def addSceneLink(self, x, y):
        """Function to inicializate a new link on the scene"""
        self.new_link = LinkGUI(x, y, x, y)
        self.addItem(self.new_link)

    def removeSceneItem(self, item):
        """Deletes an element/link from the scene and all elements related to it"""
        # Initial variable in order to remove links later
        links_to_remove = []

        # Separate code depending on item's class
        if isinstance(item, NodeGUI):
            for scene_item in self.items():
                if isinstance(scene_item, LinkGUI) and scene_item.name in item.links:
                    links_to_remove.append(scene_item.name)
                    self.removeItem(scene_item)

        if isinstance(item, LinkGUI):
            links_to_remove.append(item.name)

        # Update of all elements related to the to-be-deleted item
        for link in links_to_remove:
            for scene_item in self.items():
                if isinstance(scene_item, NodeGUI) and link in scene_item.links:
                    scene_item.links.remove(link)

        # Removal of item from scene, modifying the scene
        self.removeItem(item)
        self.modified = True

    def updateSceneLinks(self, item):
        """Function to update links position if one of the main elements moves"""
        item_links = item.links
        item_name = item.name
        item_pos = item.scenePos()
        if not item_links:
            self.modified = True
            return

        links_list = []
        for scene_item in self.items():
            if isinstance(scene_item, LinkGUI) and scene_item.name in item_links:
                links_list.append(scene_item)

        for link in links_list:
            for link_item_name in link.items:
                if link_item_name != item_name:
                    for scene_item in self.items():
                        if isinstance(scene_item, NodeGUI) and link_item_name == scene_item.name:
                            scene_item_pos = scene_item.scenePos()
                            offset_item = item.boundingRect().center()
                            offset_scene_item = scene_item.boundingRect().center()
                            link.setLine(item_pos.x() + offset_item.x(),
                                         item_pos.y() + offset_item.y(),
                                         scene_item_pos.x() + offset_scene_item.x(),
                                         scene_item_pos.y() + offset_scene_item.y())

        self.modified = True

    def finishSceneLink(self):
        """Last function to be called when a link is set up between tow main elements"""
        line = self.new_link.line()
        orig_item = self.itemAt(line.p1(), QTransform())
        dest_item = self.itemAt(line.p2(), QTransform())

        # Naming
        name = self.item_letter["Link"] + str(self.item_count["Link"])
        self.item_count["Link"] = self.item_count["Link"] + 1
        self.new_link.updateName(name)

        # Updating of link information in both elements and link
        self.new_link.addNodesLinked(orig_item.name, dest_item.name)
        orig_item.addNewLink(name)
        dest_item.addNewLink(name)

        # Resetting temporary variables to initial state
        self.new_link = None
        self.link_orig_item = None
        self.modified = True

    def loadScene(self, data):
        """Function called when loading a scene from an external file"""
        if "hosts" in data:
            hosts_list = data["hosts"]
            for host in hosts_list:
                host_name = host["name"]
                host_x_pos = host["x_pos"]
                host_y_pos = host["y_pos"]
                host_ip = host["ip"]
                self.addSceneNode(host_x_pos, host_y_pos, "Host", host_name, host_ip)

        if "switches" in data:
            switches_list = data["switches"]
            for switch in switches_list:
                switch_name = switch["name"]
                switch_x_pos = switch["x_pos"]
                switch_y_pos = switch["y_pos"]
                switch_ip = switch["ip"]
                self.addSceneNode(switch_x_pos, switch_y_pos, "Switch", switch_name, switch_ip)

        if "routers" in data:
            routers_list = data["routers"]
            for router in routers_list:
                router_name = router["name"]
                router_x_pos = router["x_pos"]
                router_y_pos = router["y_pos"]
                router_ip = router["ip"]
                self.addSceneNode(router_x_pos, router_y_pos, "Router", router_name, router_ip)

        if "links" in data:
            links_list = data["links"]
            for link in links_list:
                link_items_name = link["items"]
                scene_element = []
                for item_name in link_items_name:
                    for scene_item in self.items():
                        if isinstance(scene_item, NodeGUI) and item_name == scene_item.name:
                            scene_element.append(scene_item)

                orig_coor = scene_element[0].scenePos() + scene_element[0].boundingRect().center()
                dest_coor = scene_element[1].scenePos() + scene_element[1].boundingRect().center()
                self.addSceneLink(orig_coor.x(), orig_coor.y())
                self.new_link.updateEndPoint(dest_coor.x(), dest_coor.y())
                self.finishSceneLink()

        self.modified = False

    def saveScene(self):
        """Function called to save the state of the current project"""
        file_dictionary = {}
        hosts_saved = []
        switches_saved = []
        routers_saved = []
        link_saved = []

        for item in self.items():
            if isinstance(item, NodeGUI):
                node = {
                    "name": item.name,
                    "x_pos": item.scenePos().x(),
                    "y_pos": item.scenePos().y(),
                    "ip": item.properties["IP"]
                }
                if item.tool == "Host":
                    hosts_saved.append(node)
                elif item.tool == "Switch":
                    switches_saved.append(node)
                elif item.tool == "Router":
                    routers_saved.append(node)

            elif isinstance(item, LinkGUI):
                node = {
                    "items": item.items
                }
                link_saved.append(node)

        file_dictionary["hosts"] = hosts_saved
        file_dictionary["switches"] = switches_saved
        file_dictionary["routers"] = routers_saved
        file_dictionary["links"] = link_saved

        self.modified = False

        return file_dictionary

    # Auxiliary functions

    def checkFeasibleLink(self, last_item):
        if last_item == self.link_orig_item or last_item == self.new_link:
            return False

        if isinstance(self.link_orig_item, NodeGUI) and isinstance(last_item, NodeGUI):
            if self.link_orig_item.tool == "Host" and last_item.tool == "Host":
                return False

        orig_item_links = self.link_orig_item.links
        dest_item_links = last_item.links
        for orig_link in orig_item_links:
            for dest_link in dest_item_links:
                if dest_link == orig_link:
                    return False

        return True

    # WIP
    def selectSceneItem(self, item):
        # 1st version: ItemIsSelectable
        if not isinstance(item, NodeGUI) and not isinstance(item, LinkGUI):
            return

        self.clearSelection()
        self.clearFocus()

        item.setSelected(True)
        item.setFocus()

    # Handlers

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
            return True
        else:
            return QGraphicsScene.event(self, event)

    def keyPressEvent(self, event):
        """Function related to key-pressed events. Now used only for element deleting."""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            item = self.focusItem()
            if item is not None:
                self.removeSceneItem(item)

    def mousePressEvent(self, event):
        """Handler for mouse press events: depending on the selected tool, different actions are taken"""
        if event.button() != Qt.LeftButton:
            return

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


# Main class: main window of application
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
        self.scene = CanvasGUI()

        # Interface personalization setting
        self.setMainWindowGUI()
        self.setMenuBarGUI()
        self.setToolBarGUI()
        self.setSettings()

    # Application initialization functions

    # WIP
    def setSettings(self):
        self.settings = QSettings('MiniGUI', 'settings')
        global app_theme
        app_theme = self.settings.value('app theme')
        if app_theme is None:
            app_theme = "light"

    def setMainWindowGUI(self):
        """Main window setting"""
        self.setGeometry(500, 200, 1000, 600)
        self.setWindowTitle("MiniGUI")
        self.statusBar()
        self.setCentralWidget(self.canvas)
        self.canvas.setScene(self.scene)

    def setMenuBarGUI(self):
        """Setting of the menu bar"""
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
        # Tool bar initialization
        self.tool_bar.setIconSize(QSize(50, 50))
        self.tool_bar.setMovable(False)
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

        # Button to run Mininet --> WIP (no functionality yet)
        run_button = QToolButton()
        run_button.setCheckable(True)
        run_button.setText("Run")
        run_button.setStyleSheet("color: green; height: 50px; width: 50px; font: bold")
        self.tool_bar.addWidget(run_button)
        self.exec_buttons["Run"] = run_button

        # Button to stop Mininet --> WIP (no functionality yet)
        stop_button = QToolButton()
        stop_button.setCheckable(True)
        stop_button.setText("Stop")
        stop_button.setStyleSheet("color: red; height: 50px; width: 50px; font: bold")
        self.tool_bar.addWidget(stop_button)
        self.exec_buttons["Stop"] = stop_button

        # Select tool as default
        self.active_tool = "Select"
        self.scene.current_tool = "Select"
        self.tool_buttons["Select"].setChecked(True)

    # Scene-related functions

    def modifiedSceneDialog(self):
        """This function's objective is to warn the user that his/her current project has not been saved and lets the
        user to decide to save it, continue without saving or cancelling the action"""
        dialog = QMessageBox(self)
        dialog.setText("Scene has been modified")
        dialog.setInformativeText("Do you want to save the scene?")
        dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Cancel | QMessageBox.Discard)
        dialog.setDefaultButton(QMessageBox.Save)

        return dialog.exec()

    def clearProject(self):
        """Function used to clear the scene and its related parameters"""
        self.file = None
        self.setWindowTitle("MiniGUI")
        self.scene.clear()
        self.scene.modified = False
        self.scene.default_ip_last = 1
        for tool in self.scene.item_count:
            self.scene.item_count[tool] = 0

    # WIP
    def newProject(self):
        if self.scene.modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        self.clearProject()

    # WIP
    def openProject(self):
        if self.scene.modified:
            result = self.modifiedSceneDialog()
            if result == QMessageBox.Save:
                self.saveProject()
            elif result == QMessageBox.Cancel:
                return

        dialogfilename = QFileDialog.getOpenFileName(self, "Open file", os.path.expanduser("~"),
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
        """
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Save file as")
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setNameFilters({"Mininet topology (*.mn)", "All files (*)"})
        dialog.selectNameFilter("Mininet topology (*.mn)")
        dialog.setDirectory(os.path.expanduser("~"))
        dialog.exec_()
        """
        try:
            sender_text = self.sender().text()
        except AttributeError:
            sender_text = ""

        if self.file is None or sender_text == "Save as":
            dialogfilename = QFileDialog.getSaveFileName(self, "Save file as", os.path.expanduser("~"),
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

    def updateToolIcons(self):
        """Function used to update buttons if bright/dark mode is changed"""
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

    # Event handling functions

    def closeEvent(self, event):
        if self.scene.modified:
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
        about = QDialog(self)
        about.setWindowTitle("About MiniGUI")

        layout_v = QVBoxLayout()
        layout_h = QHBoxLayout()

        global app_theme
        if app_theme == "light":
            about_icon = QPixmap("logo-urjc_color.png")
        else:
            about_icon = QPixmap("logo-urjc_blanco.png")

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
    sys.exit(app.exec_())
