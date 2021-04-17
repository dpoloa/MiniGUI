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
# import qdarkstyle


class ElementGUI(QGraphicsPixmapItem):
    """"Class for main elements"""
    def __init__(self, x, y, tool):
        # Initial attributes
        self.images = imagesMiniGUI()
        self.tool = tool
        self.name = ""
        self.links = []

        # Icon and image of the element
        self.icon = self.images[self.tool]
        self.img = QPixmap(self.icon).scaled(50, 50, Qt.KeepAspectRatio)

        super(ElementGUI, self).__init__(self.img)

        # Definition of offset to center image where user clicked
        offset = self.boundingRect().topLeft() - self.boundingRect().center()
        self.setOffset(offset.x(), offset.y())

        # Setting of flag and internal attributes of the element
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setFocus()

        # Positioning of element on the scene
        self.setPos(x, y)
        self.setZValue(100)

    # Auxiliary functions

    # Método a mejorar (debemos dejar que se siga viendo el icono, que pasa a estar un poco
    # más azulado (u oscurecido)
    @staticmethod
    def changePixmapColor(img):
        painter = QPainter(img)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setBrush(Qt.blue)
        painter.setOpacity(0.8)
        painter.drawRect(img.rect())
        painter.end()

        return img

    # Attribute access functions

    def addNewLink(self, name):
        self.links.append(name)

    def updateIcon(self):
        self.images = imagesMiniGUI()
        self.icon = self.images[self.tool]
        self.img = QPixmap(self.icon).scaled(50, 50, Qt.KeepAspectRatio)
        self.setPixmap(self.img)

    def updateName(self, name):
        self.name = name

    # Event handlers

    def itemChange(self, change, value):
        """This functions activates when element is moved in the scene"""
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            scene = self.scene()
            if scene is not None and isinstance(scene, CanvasGUI):
                scene.updateLinks(self)

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction(self.tool + " properties")
        action = context_menu.exec_(event.screenPos())

    def hoverEnterEvent(self, event):
        new_pixmap = self.changePixmapColor(self.img)
        self.setPixmap(new_pixmap)

    def hoverLeaveEvent(self, event):
        self.img = QPixmap(self.icon).scaled(50, 50, Qt.KeepAspectRatio)
        self.setPixmap(self.img)


class LinkGUI(QGraphicsLineItem):
    """Class for links of main elements"""
    def __init__(self, x1, y1, x2, y2):
        super(LinkGUI, self).__init__(x1, y1, x2, y2)

        # Initial attributes
        self.name = ""
        self.items = []

        # Set color and width of the link
        self.pen = QPen()
        self.pen.setWidth(4)
        self.pen.setColor(Qt.darkCyan)
        self.setPen(self.pen)

        # Setting of internal attributes
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

    # Attributes access/update functions

    def addItemsLinked(self, name1, name2):
        self.items = list((name1, name2))

    def updateEndPoint(self, x2, y2):
        line = self.line()
        self.setLine(line.x1(), line.y1(), x2, y2)

    def updateName(self, name):
        self.name = name

    # Event handlers

    def contextMenuEvent(self, event):
        context_menu = QMenu()
        properties_act = context_menu.addAction("Link properties")
        action = context_menu.exec_(event.screenPos())

    def hoverEnterEvent(self, event):
        self.pen.setColor(Qt.darkRed)
        self.setPen(self.pen)

    def hoverLeaveEvent(self, event):
        self.pen.setColor(Qt.darkCyan)
        self.setPen(self.pen)


class CanvasGUI(QGraphicsScene):
    def __init__(self):
        super(CanvasGUI, self).__init__()

        # Initial variable
        self.current_tool = None

        # Model initialization
        self.item_letter = {"House": "h", "Car": "c", "Link": "l"}
        self.item_count = {"House": 0, "Car": 0, "Link": 0}

        # Event handling initialization
        self.new_link = None
        self.link_item = None

    # Scene functions

    def addElement(self, x, y, tool, name=None):
        """Function to add a main element to the scene"""
        pixmap = ElementGUI(x, y, tool)

        # Name checking (used in case of loading from a previous project)
        if name is not None:
            new_name = name
        else:
            new_name = self.item_letter[tool] + str(self.item_count[tool])

        self.item_count[tool] = self.item_count[tool] + 1
        pixmap.updateName(new_name)

        # Creation of an appendix text to name the main element
        text = QGraphicsTextItem(new_name, pixmap)
        text.setPos(- text.boundingRect().width() / 2, pixmap.boundingRect().bottomLeft().y() * 3/4)

        self.addItem(pixmap)

    def addLink(self, x, y):
        """Function to inicializate a new link on the scene"""
        self.new_link = LinkGUI(x, y, x, y)
        self.addItem(self.new_link)

    def removeElement(self, item):
        """Deletes an element/link from the scene and all elements related to it"""
        # Initial variable in order to remove links later
        links_to_remove = []

        # Separate code depending on item's class
        if isinstance(item, ElementGUI):
            for scene_item in self.items():
                if isinstance(scene_item, LinkGUI) and scene_item.name in item.links:
                    links_to_remove.append(scene_item.name)
                    self.removeItem(scene_item)

        if isinstance(item, LinkGUI):
            links_to_remove.append(item.name)

        # Update of all elements related to the to-be-deleted item
        for link in links_to_remove:
            for scene_item in self.items():
                if isinstance(scene_item, ElementGUI) and link in scene_item.links:
                    scene_item.links.remove(link)

        self.removeItem(item)

    def updateLinks(self, item):
        """Function to update links position if one of the main elements moves"""
        item_links = item.links
        item_name = item.name
        item_pos = item.scenePos()
        if not item_links:
            return

        links_list = []
        for scene_item in self.items():
            if isinstance(scene_item, LinkGUI) and scene_item.name in item_links:
                links_list.append(scene_item)

        for link in links_list:
            for link_item_name in link.items:
                if link_item_name != item_name:
                    for scene_item in self.items():
                        if isinstance(scene_item, ElementGUI) and link_item_name == scene_item.name:
                            scene_item_pos = scene_item.scenePos()
                            link.setLine(item_pos.x(), item_pos.y(), scene_item_pos.x(), scene_item_pos.y())

    def updateLinkItemInfo(self):
        """Last function to be called when a link is set up between tow main elements"""
        line = self.new_link.line()
        orig_item = self.itemAt(line.p1(), QTransform())
        dest_item = self.itemAt(line.p2(), QTransform())

        # Naming
        name = self.item_letter["Link"] + str(self.item_count["Link"])
        self.item_count["Link"] = self.item_count["Link"] + 1
        self.new_link.updateName(name)

        # Updating of link information in both elements and link
        self.new_link.addItemsLinked(orig_item.name, dest_item.name)
        orig_item.addNewLink(name)
        dest_item.addNewLink(name)

        # Resetting temporary variables to initial state
        self.new_link = None
        self.link_item = None

    def loadScene(self, data):
        """Function called when loading a scene from an external file"""
        if "houses" in data:
            houses_list = data["houses"]
            for house in houses_list:
                house_name = house["name"]
                house_x_pos = house["x_pos"]
                house_y_pos = house["y_pos"]
                self.addElement(house_x_pos, house_y_pos, "House", house_name)

        if "cars" in data:
            cars_list = data["cars"]
            for car in cars_list:
                car_name = car["name"]
                car_x_pos = car["x_pos"]
                car_y_pos = car["y_pos"]
                self.addElement(car_x_pos, car_y_pos, "Car", car_name)

        if "links" in data:
            links_list = data["links"]
            for link in links_list:
                link_items_name = link["items"]
                scene_element = []
                for item_name in link_items_name:
                    for scene_item in self.items():
                        if isinstance(scene_item, ElementGUI) and item_name == scene_item.name:
                            scene_element.append(scene_item)

                orig_coor = scene_element[0].scenePos()
                dest_coor = scene_element[1].scenePos()
                self.addLink(orig_coor.x(), orig_coor.y())
                self.new_link.updateEndPoint(dest_coor.x(), dest_coor.y())
                self.updateLinkItemInfo()

    def saveScene(self):
        """Function called to save the state of the current project"""
        file_dictionary = {}
        house_saved = []
        car_saved = []
        link_saved = []

        for item in self.items():
            if isinstance(item, ElementGUI):
                node = {
                    "name": item.name,
                    "x_pos": item.scenePos().x(),
                    "y_pos": item.scenePos().y()
                }
                if item.tool == "House":
                    house_saved.append(node)
                elif item.tool == "Car":
                    car_saved.append(node)

            elif isinstance(item, LinkGUI):
                node = {
                    "items": item.items
                }
                link_saved.append(node)

        file_dictionary["houses"] = house_saved
        file_dictionary["cars"] = car_saved
        file_dictionary["links"] = link_saved

        return file_dictionary

    # Handlers

    def event(self, event):
        """Auxiliary function used for applications changes such as palette"""
        if event.type() == QEvent.PaletteChange:
            for item in self.items():
                if isinstance(item, ElementGUI):
                    item.updateIcon()
                if isinstance(item, QGraphicsTextItem):
                    item.setDefaultTextColor(Qt.white)
            return True
        else:
            return QGraphicsScene.event(self, event)

    def keyPressEvent(self, event):
        """Function related to key-pressed events. Now used only for element deleting."""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            item = self.focusItem()
            if item is not None:
                self.removeElement(item)

    def mousePressEvent(self, event):
        """Handler for mouse press events: depending on the selected tool, different actions are taken"""
        if self.current_tool == "Select":
            super().mousePressEvent(event)
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None:
                item.setFocus()
        elif self.current_tool == "Link":
            item = self.itemAt(event.scenePos(), QTransform())
            if item is not None and isinstance(item, ElementGUI):
                self.link_item = item
                self.addLink(item.scenePos().x(), item.scenePos().y())
        else:
            self.addElement(event.scenePos().x(), event.scenePos().y(), self.current_tool)

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
            if item == self.link_item or item == self.new_link or not isinstance(item, ElementGUI):
                self.removeItem(self.new_link)
            else:
                self.new_link.updateEndPoint(item.scenePos().x(), item.scenePos().y())
                self.new_link.setFocus()
                self.updateLinkItemInfo()


# Clase creadora de la interfaz principal
class MiniGUI(QMainWindow):
    """Main class of the application. It holds all the structure along with the scene"""
    def __init__(self):
        super(QMainWindow, self).__init__()

        # Program configuration setting
        self.settings = None

        # Main window attributes settings
        self.menu_bar = self.menuBar()
        self.tool_bar = self.addToolBar("Tool Bar")
        self.tool_buttons = {}
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
        quit_action.triggered.connect(qApp.exit)
        dark_theme_action.toggled.connect(lambda: self.changeStyle())
        about_action.triggered.connect(self.showAbout)

        # Action introduction into menus
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
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
            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(QIcon(images[button]))
            b.setText(str(button))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            b.pressed.connect(lambda tool_name=button: self.manageTools(tool_name))

            self.tool_bar.addWidget(b)
            self.tool_buttons[button] = b

        # Select tool as default
        self.active_tool = "Select"
        self.scene.current_tool = "Select"
        self.tool_buttons["Select"].setChecked(True)

    # Scene-related functions

    # To be completed
    def newProject(self):
        self.scene.clear()
        for tool in self.scene.item_count:
            self.scene.item_count[tool] = 0

    def openProject(self):
        # WIP: we can use a long method or a static method (see next function)
        dialogfilename = QFileDialog.getOpenFileName(self, "Open file", os.path.expanduser("~"),
                                                     "Mininet topology (*.mn);;All files (*)", "")

        if dialogfilename[0] != "":
            file = open(str(dialogfilename[0]), "r")
            topology_data = json.load(file)

            self.newProject()
            self.scene.loadScene(topology_data)

    def saveProject(self):
        # WIP: we can use a long method or a static method
        """
        # Creamos la ventana emergente que permite al usuario guardar el archivo
        dialog = QFileDialog(self)
        # Definimos el nombre de la ventana
        dialog.setWindowTitle("Save file as")
        # Dejamos que el usuario pueda elegir cualquier archivo (modo para guardar archivos)
        dialog.setFileMode(QFileDialog.AnyFile)
        # Creamos los filtros necesarios
        dialog.setNameFilters({"Mininet topology (*.mn)", "All files (*)"})
        dialog.selectNameFilter("Mininet topology (*.mn)")
        # Elegimos como directorio definitivo por defecto el $HOME
        dialog.setDirectory(os.path.expanduser("~"))
        # Ejecutamos el diálogo
        dialog.exec_()
        """
        dialogfilename = QFileDialog.getSaveFileName(self, "Save file as", os.path.expanduser("~"),
                                                     "Mininet topology (*.mn);;All files (*)", "")

        if dialogfilename[0] != "":
            filename = str(dialogfilename[0])
            if dialogfilename[1].startswith("Mininet") and not dialogfilename[0].endswith(".mn"):
                filename = filename + ".mn"
                print(filename)

            file = open(filename, "w")
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

    # Event handling functions

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
        about_win = QDialog(self)
        about_win.setWindowTitle("About MiniGUI")

        layout_v = QVBoxLayout()
        layout_h = QHBoxLayout()

        global app_theme
        if app_theme == "light":
            about_icon = QPixmap("logo-urjc_color.png")
        else:
            about_icon = QPixmap("logo-urjc_blanco.png")

        about_icon_resize = about_icon.scaled(100, 100, Qt.KeepAspectRatio)

        label1 = QLabel(about_win)
        label1.setPixmap(about_icon_resize)

        label2 = QLabel(about_win)
        label2.setText("MiniGUI: network graphical editor, made specifically for you\n\n"
                       "Author: Daniel Polo Álvarez (d.poloa@alumnos.urjc.es)\n\n"
                       "Universidad Rey Juan Carlos (URJC)\n\n"
                       "Prueba\n"
                       "Prueba\n"
                       "Prueba\n"
                       "Prueba\n"
                       "Prueba\n"
                       "Prueba\n"
                       "Prueba\n")

        button = QDialogButtonBox(QDialogButtonBox.Ok)
        button.accepted.connect(about_win.accept)
        button.setCenterButtons(True)

        layout_h.addWidget(label1, alignment=Qt.AlignTop)
        layout_h.setSpacing(20)
        layout_h.addWidget(label2, alignment=Qt.AlignTop)
        layout_v.addLayout(layout_h)
        layout_v.addWidget(button, alignment=Qt.AlignCenter)

        about_win.setLayout(layout_v)

        about_win.show()


def imagesMiniGUI():
    """This function returns a set of images depending on the mode selected: bright or dark"""
    global app_theme
    if app_theme == "light":
        return {
            "Select": "select.png",
            "House": "house.png",
            "Car": "car.png",
            "Link": "cable.png"
        }
    else:
        return {
            "Select": "select_white.png",
            "House": "house_white.png",
            "Car": "car_white.png",
            "Link": "cable_white.png"
        }


def changeAppStyle():
    # WIP
    """Function used to change the application palette"""
    global app_theme
    if app_theme == "light":
        palette = app.style().standardPalette()
        app.setPalette(palette)
    else:
        # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
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
