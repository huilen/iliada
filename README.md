# Requisitos
- Python 3
- Pip
# Instalación
Ir al directorio del proyecto e instalar dependencias con pip:
```
pip install -r requirements.txt
```
# Uso
1. Colocar los archivos de Markdown en el directorio sources/<número
de canto>, por ejemplo para el canto 1 deberían tenerse los siguientes
archivos:
```
sources/1/griego.md
sources/1/notas.md
sources/1/traduccion.md
sources/1/comentario.md
```
2. Ejecutar el script de la siguiente forma:
```
python combine.py <número de canto> [<color de página en hexadecimal>]
```
Por ejemplo, para el canto 1 sería así:
```
python combine.py 1
```
Y si se quiere especificar un color de página, sería así:
```
python combine.py 1 f2eee8
```
Si el script se ejecutó satisfactoriamente, el resultado va a ser un 
archivo con el nombre `canto1.html`.

# Subir al sitio

Para subir todo al sitio, hay que ejecutar el script deploy.sh (para
lo cual antes hay que configurar las credenciales de AWS con el
comando `aws configure`), o bien se puede subir directamente por S3
desde la consola de AWS.

# Cambios

Todos los cambios de estilo deben realizarse sobre el archivo
template.html, no sobre los archivos de salida, ya que estos son
pisados automáticamente cuando se ejecuta el script.
