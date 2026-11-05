import os
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

# Definimos la ruta de la carpeta donde se guardarán las copias de seguridad
DIRECTORIO_COPIAS = Path("copias")


# Crea la carpeta de copias si no existe y devuelve la fecha y hora actual formateada para el nombre del archivo.
def preparar_entorno_copia():
    if (not DIRECTORIO_COPIAS.exists()):
        DIRECTORIO_COPIAS.mkdir(parents=True, exist_ok=True)
    
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    return marca_tiempo

# Ejecuta pg_dump dentro del contenedor de PostgreSQL y guarda los datos en un archivo .sql.
def hacer_copia_postgres(marca_tiempo):
    usuario_pg = os.getenv("POSTGRES_USER")
    base_datos_pg = os.getenv("POSTGRES_DB")
    archivo_destino = DIRECTORIO_COPIAS / f"backup_postgres_{marca_tiempo}.sql"

    # 1. Obtenemos el ID del contenedor de PostgreSQL que está corriendo
    resultado_id = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=postgres"],
        capture_output=True,
        text=True,
        check=True
    )
    id_contenedor = resultado_id.stdout.strip()

    if (not id_contenedor):
        raise RuntimeError("No se encontró el contenedor de PostgreSQL en ejecución.")

    # 2. Ejecutamos pg_dump y guardamos la salida directamente en el archivo .sql
    with open(archivo_destino, "w", encoding="utf-8") as archivo_salida:
        subprocess.run(
            ["docker", "exec", "-i", id_contenedor, "pg_dump", "-U", usuario_pg, "-d", base_datos_pg],
            stdout=archivo_salida,
            check=True
        )

    return archivo_destino

# Ejecuta mongodump dentro del contenedor de MongoDB y guarda la coleccion en un archivo .archive comprimido.
def hacer_copia_mongo(marca_tiempo):
    usuario_mongo = os.getenv("MONGO_USER")
    password_mongo = os.getenv("MONGO_PASSWORD")
    base_datos_mongo = os.getenv("MONGO_DB")
    archivo_destino = DIRECTORIO_COPIAS / f"backup_mongo_{marca_tiempo}.archive"

    # 1. Obtenemos el ID del contenedor de MongoDB que está en ejecución
    resultado_id = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=mongo"],
        capture_output=True,
        text=True,
        check=True
    )
    id_contenedor = resultado_id.stdout.strip()

    if (not id_contenedor):
        raise RuntimeError("No se encontró el contenedor de MongoDB en ejecución.")

    # 2. Ejecutamos mongodump autenticándonos contra la base de datos admin
    with open(archivo_destino, "wb") as archivo_salida:
        subprocess.run(
            [
                "docker", "exec", "-i", id_contenedor,
                "mongodump",
                f"--username={usuario_mongo}",
                f"--password={password_mongo}",
                "--authenticationDatabase=admin",
                f"--db={base_datos_mongo}",
                "--archive",
                "--gzip"
            ],
            stdout=archivo_salida,
            check=True
        )

    return archivo_destino
# Coordina la ejecucion completa de las copias de seguridad de PostgreSQL y MongoDB.
def ejecutar_copias_seguridad():
    marca_tiempo = preparar_entorno_copia()
    ruta_copia_pg = hacer_copia_postgres(marca_tiempo)
    ruta_copia_mongo = hacer_copia_mongo(marca_tiempo)
    return ruta_copia_pg, ruta_copia_mongo


if (__name__ == "__main__"):
    ejecutar_copias_seguridad()