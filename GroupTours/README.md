#GROUP TOURS APP

Installando los requerimientos para la app

1. pip install -r requeriments.txt

2. Crear un nueva base de datos llamada GroupTours desde postgres

3. crear el archivo .env dentro de la carpeta GroupTours principal con los datos de la base de datos
    DBUSER=postgres
    DBPASS=tu contraseña

4. Ejutar los siguientes compandos
    python manage.py makemigrations
    python manage.py migrate
    
5. Ejecutar el servidor
    python manage.py runserver

6. Control + Click sobre el enlace
    http://127.0.0.1:8000/