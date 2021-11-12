# MiniGUI
Repositorio creado para el TFG de Tecnologías de la Telecomunicación de Daniel Polo Álvarez: MiniGUI (nombre
provisional), estudiante de la Universidad Rey Juan Carlos.
## Objetivo 
El objetivo de este Trabajo de Fin de Grado es crear una GUI (*Graphical User Interface*, por sus siglas en inglés) o 
Interfaz Gráfica de Usuario que permita al usuario poder crear una red de arquitectura de ordenadores a su gusto con
los elementos básicos: hubs, switches, routers y ordenadores/hosts (por ahora, con vistas a añadir controladores SDN en
el futuro). Este programa está escrito en Python, y usa como paquete gráfico Qt, con su adaptación al lenguaje usado 
como PyQt5.
## Historial de versiones
#### Versión 00.01.08
En esta versión se han introducido los siguientes cambios:
* Se ha modificado la apariencia de los menús contextuales de los nodos. Ahora aparecen listadas todas las opciones en 
todo momento, pero algunas de ellas están desactivadas si Mininet no está activo.
* Se ha cambiado el código relacionado con los botones de herramienta, los cuales fallaban en contadas ocasiones. Se ha
subsanado el error.
* Se ha arreglado un fallo que, al crear un enlace entre dos nodos y abrir el menú contextual de uno de ellos antes de
finalizar la unión, creaba una línea en la escena y no podía eliminarse. 
#### Versión 00.01.07
La aplicación ha tenido los siguientes cambios:
* Se ha modificado la función updateSceneInfo de la clase MiniGUI para evitar errores debido a la interferencia entre 
comandos ejecutados en Mininet y la llamada del actualizador automático (*Assertion error*, provocado por una
instrucción *assert*, el cual se usa para comprobar que todo está bien).
* Se han modificado los colores de las líneas para que sean más intuitivas, además de que se ha aumentado su grosor
para facilitar su selección/eliminación. Se han modificado funciones relacionadas con las líneas para una mejor
experiencia de usuario.
* Se han modificado el color de las etiquetas de dirección IP en modo oscuro para permitir una mayor diferenciación
respecto al nuevo grosor de las líneas.
#### Versión 00.01.06
En esta nueva versión:
* Se ha modificado el nombre de la clase CanvasGUI, ahora SceneGUI, para adaptarse mejor a lo que representa.
* Se ha eliminado el atributo "settings" de la clase MiniGUI al ser redundante.
* Se ha detectado un error que permitía crear, abrir o guardar un proyecto, modificar propiedades de la aplicación o 
salir de ella aun cuando la simulación de Mininet seguía activada. Este error ha sido subsanado impidiendo el uso de
la barra de menú cuando Mininet se está ejecutando.
* Las funciones que incorporan la nueva funcionalidad descrita en el punto anterior han modificado su nombre para 
adaptarse a su nuevo cometido.
* Se han añadido cláusulas de excepción en funciones críticas para evitar posibles fallos.
* Se ha eliminado código duplicado en las clases HostDialog() y RouterDialog().
* Se ha corregido un fallo que modificada el texto del botón de acción de Mininet cuando la escena estaba completamente
vacía.
#### Versión 00.01.05
Esta nueva versión trae las siguientes novedades/correcciones:
* Corrige un error que impedía que Mininet pudiera arrancarse.
* Corrige un error que, al salir de la aplicación a través de la opción "Quit" del menú "File" o al usar el comando 
"Ctrl + Q" sin haber guardado previamente el progreso, no salía la ventana de diálogo de guardado del archivo. 
* Se han eliminado partes del código pertenecientes a funcionalidades no disponibles en la versión 01.00.00.
* Se ha modificado el nombre de la ubicación de las imágenes usadas como iconos en la aplicación.
* Se han remodelado algunas variables globales siguiendo las normas de estilo de Python.
#### Versión 00.01.04
En esta nueva versión se han realizado cambios en algunas funcionalidades:
* Se han eliminado los botones para arrancar, parar y actualizar la escena. Ahora solo hay un único botón que cambia en 
función del estado de Mininet ("Start" cuando Mininet no está activo y "Stop" cuando sí lo está). De esta forma, la 
actualización se realizará de forma automática (ahora mismo cada 5 segundos).
* Se han modificado algunos mensajes que aparecían en las ventanas de diálogo en ciertas ocasiones para una mayor 
comprensión por parte del usuario.
* Se ha modificado la pestaña "Interfaces" del host para que tenga la misma apariencia que la del router.
* Se han modificado las siguientes características de la pestaña "Routing" tanto en el host como en el router:
  * Se ha cambiado el mensaje que aparecía encima del recuadro para escribir el comando.
  * Se ha añadido una funcionalidad de control de entrada para comprobar que el comando forma parte de la familia de
  comandos "route" o "ip route".
  * Se ha cambiado el mensaje del botón "Send" por "Apply". Además, cuando se envía el comando se limpia el formulario 
  para escribir el comando.
  * Se ha arreglado el fallo que no permitía eliminar la ruta elegida. 
* Ahora las ventanas de propiedades pueden moverse independientemente de la ventana principal.
* Se han modificado los iconos de "switch", "router" y "delete" de la aplicación, tomando un tono más grisáceo (y donde
el último ha cambiado de ser una papelera a unas tijeras).
* Se ha modificado el color de las enlaces para una mejor visualización en el modo oscuro.
* Se ha arreglado un fallo que no permitía guardar correctamente el proyecto al cargar el proyecto tras haber salido 
previamente de la aplicación.
* Se ha realizado una nueva limpieza del código, eliminando funciones de funcionalidades no continuadas.
#### Versión 00.01.03
Esta nueva versión añade nuevas opciones de personalización y mejoras que ayudarán al usuario a disfrutar de una mejor
experiencia:
* Se han añadido dos opciones más junto con la elección de tema claro/oscuro: uso de controladores (versión básica o 
avanzada) y acceso al CLI. El uso de controladores implica un mayor conocimiento de las redes de comunicaciones y de
los protocolos OpenFlow y OpenVSwitch, mientras el usar el CLI permite tener un mayor control sobre la simulación.
* Se ha remodelado completamente el cuadro de diálogo de propiedades del router, modificando el nombre de las pestañas y 
su contenido. Ahora, la nueva pestaña "Interfaces" guarda toda la información propias de las interfaces del router, 
mientras que la pestaña "Routing" muestra todas las rutas almacenadas en la tabla del router con la posibilidad de 
eliminarlas o añadir algunas nuevas (incluyendo la ruta por defecto) haciendo uso de su propia sintaxis.
* El cuadro de diálogo del host también ha sufrido un lavado de cara, modificando nombres y diseños de algunas pestañas,
además de mostrar la tabla de routing en la pestaña correspondiente cuando Mininet está activo.
* Se ha modificado el color de las etiquetas de nombres de interfaz para una mayor diferenciación respecto a otras 
etiquetas, además de arreglar un pequeño fallo que impedía darles a dichas etiquetas el color deseado cuando se iniciaba
la aplicación.
* El indicador de estado del simulador (red activa o no) se ha modificado y traducido al inglés para estar en 
consonancia con el resto de la aplicación.
* Las etiquetas de nombres de interfaz, cuando estaban solas (sin ser acompañadas por la etiqueta de dirección IP
correspondiente), no eran muy visibles cuando la línea estaba completamente horizontal, al atravesar longitudinalmente 
el texto de la etiqueta. Este error se ha corregido en esta versión.
* A partir de esta versión, además de la actualización manual de la escena, el propio simulador actualizará la escena
de forma completamente automática cada cierto intervalo de tiempo. 
#### Versión 00.01.02
Esta actualización trae consigo las siguientes mejoras y cambios:
* Ahora el programa es capaz de recordar algunas de tus preferencias como el directorio donde has guardado tu último 
proyecto (a través del cuadro de diálogo de "Abrir proyecto") y el modo de la aplicación (claro u oscuro).
* Se ha solucionado un pequeño error que salía en el terminal donde se ejecutaba MiniGUI al arrancarlo (QStandardPaths).
* Se ha añadido una nueva clase para las etiquetas del nombre de los nodos (NameTagGUI), que extiende la clase base
TagGUI.
* Se ha solucionado un error que impedía que los iconos de herramientas no cambiasen de color cuando el tema de la 
aplicación cambiaba de claro a oscuro.
* Se ha añadido una comprobación para saber si el programa está siendo ejecutado como superusuario (necesario para 
poder ejecutar Mininet).
#### Versión 00.01.01
En esta versión se han introducido las siguientes mejoras y cambios:
* Se ha añadido un indicador en la barra inferior de información para conocer el estado de la red simulada en cualquier 
  momento: rojo cuando la red no está activa y verde cuando sí lo está.
* Se ha mejorado y modificado la ventana de diálogo de los elementos host y router.
* Cuando se cree el enlace entre dos elementos, dos nuevas etiquetas aparecen encima del enlace:
  * La primera refleja el nombre de la interfaz a la que está conectada dicho enlace en cada elemento/nodo, lo cual 
    ayudará al usuario a distinguir cuál es la interfaz que debe modificar para que funcione todo el sistema. 
  * Debajo de dicha etiqueta aparecerá la dirección IP asociada a dicha interfaz si está definida.
* Se han creado nuevas clases para una mayor especialización de las etiquetas: TagGUI (clase base), EthTagGUI e 
  IpTagGUI (clases extendidas de la clase base).
* Se ha añadido el CLI, el cual se ejecuta en el mismo terminal donde se llamó por primera vez al simulador. Tiene todas
  las funcionalidades implementadas por el propio Mininet, aunque algunas funcionalidades como salidas no controladas o 
  forzosas con Ctrl+D o Ctrl+C todavía no están disponibles.
* Ahora puedes modificar ciertas características de tu simulación en directo desde la ventana de propiedades del nodo, 
  además de poder actualizar en directo cualquier cambio que se haya hecho desde Mininet en la escena.
* Se ha redefinido parte del código para una mayor escalabilidad y sencillez.
#### Versión 00.01.00
**¡Aquí está la primera versión funcional de MiniGUI!** Ya es posible crear tu propia red y guardar ciertos campos 
básicos gracias a Mininet, código de libre acceso que permite crear redes de ordenadores a través de hosts y switches 
haciendo uso de las tecnologías OpenFlow y OpenVSwitch (ver http://mininet.org/ para más información, 
https://github.com/mininet/mininet para ver el código base, actualizado cada poco tiempo).

Esta primera versión ofrece al usuario la capacidad de crear sus propios hosts, switches y routers (siendo estos últimos
una versión específica de los switches, por lo que se ha creado una clase específica a partir de una clase base de 
Mininet) y almacenar ciertas características propias como su dirección IP y su ruta por defecto (ruta usada para 
comunicarse con redes con distinto dominio IP), además de poder especificar qué dirección IP tiene el router por cada 
una de sus interfaces.

Además de este anuncio, en esta versión se han introducido diversas mejoras y nuevas funcionalidades:
* Se ha modificado la función changePixmapColor() de la clase NodeGUI, al igual que los controladores de los eventos 
  "hover", para poder ver de forma más visual cada uno de los siguientes casos:
  * Si el elemento tiene la atención de la escena (_"item has focus"_), se añade al icono del elemento una capa de color 
    azulado que se mantiene hasta que la atención de la escena cambie.
  * Si el elemento es sobrevolado por el cursor (eventos _hover_), el elemento tomará un color azulado excepto si el 
  usuario tiene activada la herramienta de borrado (icono papelera), donde dicha capa será de color rojizo.
* Arreglado un fallo que no permitía abrir el explorador de archivos en el directorio predeterminado al guardar un 
  proyecto por primera vez o al abrir un proyecto existente.
* Se han introducido funciones en las clases NodeGUI, LinkGUI y CanvasGUI para acceder y cambiar atributos, además de 
  poder modificar, añadir o eliminar partes de otras características de la clase.
* Se han introducido dos diccionarios que almacenan los punteros a los nodos y los enlaces a través de su nombre para 
  acceder a ellos de una forma fácil y limpia cada vez que sea requerido, además de hacer el código más accesible y 
  claro.
* Cada nodo (host, switch y router) tienen su propia ventana de propiedades que puede ser accedida a través del menú 
  contextual cuando la red no está activa. Cuando la red pasa a estar operativa, el menú contextual permite acceder al 
  terminal propio del nodo para poder ejecutar en él los comandos. (*¿Por qué no pruebas a ejecutar un ping?*)
#### Versión 00.00.03
En esta versión introducimos algunos de los elementos finales que estarán presentes en la versión 00.01.00: ordenadores, 
switches y routers. Con estos añadidos aparece una nueva función que permite o no la unión entre nodos del sistema (por 
ahora no se permiten, por ejemplo, uniones entre ordenadores). Además, se han realizado los siguientes cambios:
* Se ha modificado la forma que tiene el programa de hacer aparecer un nodo cuando el usuario hacía click en la escena. 
  Además, para poder mantener la funcionalidad de versiones anteriores, otras funciones se han visto modificadas.
* Se ha corregido un error que provocaba que las etiquetas de los nodos saliesen descentradas.
* Se ha mejorado la comprobación de enlace entre dos nodos. En la anterior versión no se comprobaba si los dos elementos 
  ya habían sido previamente enlazados, mientras que en la nueva versión sí se corrige.
* También se han añadido dos nuevos atributos en la clase NodeGUI (width, height) para armonizar todos los valores de 
  tamaño de los iconos. Además, se han comenzado a añadir propiedades propias de Mininet en dicha clase, como puede ser 
  la dirección IP.
* Antes de que el usuario pueda darle una dirección IP específica al nuevo elemento, el programa le asigna una IP 
  predeterminada. Además, la IP queda siempre reflejada en la escena al unirse al elemento como etiqueta.
#### Versión 00.00.02
En esta versión se han realizado los siguientes cambios:
* Se ha añadido un botón para eliminar elementos y hacer más accesible esta funcionalidad para el usuario.
* Se ha añadido la funcionalidad de "marcar" un elemento: si el usuario clica sobre algún nodo/enlace de la escena, 
  alrededor del elemento saldrá una línea discontinua. Además, el elemento mantendrá un color más llamativo para marcar 
  que ha sido el último en elegirse.
* Se ha añadido una nueva funcionalidad: el programa avisa al usuario antes de salir del programa, crear o abrir un 
  nuevo proyecto en el caso de que no haya guardado el proyecto actual. Además, para saber en qué proyecto se encuentra 
  el usuario, el título de la ventana se modifica tomando como apellido el nombre del proyecto.
* Se han añadido los botones de arrancado y apagado de Mininet. Por ahora, estos botones no realizan ninguna tarea; su 
  funcionalidad será añadida en versiones posteriores.
* Se han modificado tanto el nombre de algunas funciones como su contenido para conseguir una mejor comprensión del 
  código
#### Versión 00.00.01
Se ha subido una primera versión de cómo puede funcionar la parte visual del programa. Por ahora se
puede elegir entre dos "herramientas" (casa, coche) y se pueden unir entre ellas a través de la herramienta "enlace" 
(por ahora se permite enlazar cualquier elemento entre sí). Se pueden mover los elementos libremente, además de que los
enlaces son capaces de seguir el movimiento que realizan los elementos a los que están unidos. Para eliminar cualquier 
elemento, el usuario debe seleccionarlo primero y luego pulsar la tecla Suprimir.

También se ha implementado una primera versión del archivo de guardado, así como una función de lectura de dichos
archivos que permite recuperar los diagramas creados anteriormente. Este archivo de guardado está escrito en lenguaje
JSON.

Por último, se ha añadido un modo oscuro a la aplicación para dar al usuario la posibilidad de poder alternar entre
los dos temas de forma rápida y sencilla.