# MiniGUI
Repositorio creado para el TFG de Tecnologías de la Telecomunicación de Daniel Polo Álvarez: MiniGUI (nombre
provisional)
## Objetivo 
El objetivo de este Trabajo de Fin de Grado es crear una GUI (*Graphical User Interface*, por sus siglas en inglés) o 
Interfaz Gráfica de Usuario que permita al usuario poder crear una red de arquitectura de ordenadores a su gusto con
los elementos básicos: hubs, switches, routers y ordenadores/hosts (por ahora, con vistas a añadir controladores SDN en
el futuro). Este programa está escrito en Python, y usa como paquete gráfico Qt, con su adaptación al lenguaje usado 
como PyQt5.
## Historial de versiones
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