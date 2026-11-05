import os
import json
from datetime import date, timedelta
import redis
import psycopg2
from dotenv import load_dotenv

# Carga las variables de entorno definidas en el archivo .env local.
load_dotenv()


# Crea y devuelve un cliente de conexión a la base de datos Redis.
def obtener_conexion_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        password=os.getenv("REDIS_PASSWORD"),
        db=0,
        decode_responses=True
    )


# Crea y devuelve una conexión activa a la base de datos PostgreSQL.
def obtener_conexion_pg():
   return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=int(os.getenv("PGPORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

# Calcula las plazas libres iniciales desde PostgreSQL y las carga en Redis por albergue y noche.
def inicializar_contadores(fecha_inicio=date(2027, 5, 1), total_dias=30):
    cliente_redis = obtener_conexion_redis()
    conexion_postgres = obtener_conexion_pg()
    cursor_postgres = conexion_postgres.cursor()

    cursor_postgres.execute("SELECT id, prazas FROM albergues;")
    plazas_totales_por_albergue = dict(cursor_postgres.fetchall())

    cursor_postgres.execute("SELECT albergue_id, noite, COUNT(*) FROM reservas GROUP BY albergue_id, noite;")
    reservas_ocupadas = {}
    for id_albergue, fecha_noche, cantidad_ocupadas in cursor_postgres.fetchall():
        reservas_ocupadas[(id_albergue, fecha_noche.isoformat())] = cantidad_ocupadas

    lote_comandos_redis = cliente_redis.pipeline()
    for desplazamiento_dias in range(total_dias):
        fecha_noche_texto = (fecha_inicio + timedelta(days=desplazamiento_dias)).isoformat()
        for id_albergue, plazas_totales in plazas_totales_por_albergue.items():
            plazas_ocupadas = reservas_ocupadas.get((id_albergue, fecha_noche_texto), 0)
            plazas_libres = max(0, plazas_totales - plazas_ocupadas)
            clave_redis = f"prazas:{id_albergue}:{fecha_noche_texto}"
            lote_comandos_redis.set(clave_redis, plazas_libres)

    lote_comandos_redis.execute()
    cursor_postgres.close()
    conexion_postgres.close()

# Descuenta una plaza de forma atómica en Redis con Lua y registra la reserva en PostgreSQL.
def reservar(id_albergue, fecha_noche, id_peregrino):
    cliente_redis = obtener_conexion_redis()
    fecha_noche_texto = fecha_noche.isoformat() if isinstance(fecha_noche, date) else str(fecha_noche)
    clave_redis = f"prazas:{id_albergue}:{fecha_noche_texto}"

    # Script de Lua para comprobar plazas y decrementar de forma atómica en Redis
    script_lua = """
    local plazas = tonumber(redis.call('get', KEYS[1]))
    if (plazas and plazas > 0) then
        redis.call('decr', KEYS[1])
        return 1
    else
        return 0
    end
    """
    ejecutor_script = cliente_redis.register_script(script_lua)
    reserva_exitoso = ejecutor_script(keys=[clave_redis])

    # Si Redis devuelve 0, no hay plazas libres y se rechaza la reserva
    if (not reserva_exitoso):
        return False

    conexion_postgres = None
    try:
        conexion_postgres = obtener_conexion_pg()
        cursor_postgres = conexion_postgres.cursor()
        
        # Guardamos la reserva en PostgreSQL
        cursor_postgres.execute(
            "INSERT INTO reservas (albergue_id, peregrino_id, noite) VALUES (%s, %s, %s);",
            (id_albergue, id_peregrino, fecha_noche_texto)
        )
        conexion_postgres.commit()
        cursor_postgres.close()
        conexion_postgres.close()
        return True
        
    except Exception:
        # Si PostgreSQL falla, cerramos conexión y devolvemos la plaza a Redis (compensación)
        if (conexion_postgres):
            conexion_postgres.close()
        cliente_redis.incr(clave_redis)
        return False

# Busca albergues disponibles de un camino y noche, utilizando caché en Redis con TTL de 60 segundos.
def consultar_albergues_disponibles_con_cache(camino_buscado, fecha_noche):
    cliente_redis = obtener_conexion_redis()
    fecha_noche_texto = fecha_noche.isoformat() if isinstance(fecha_noche, date) else str(fecha_noche)
    
    # Construimos una clave única para la caché de esta consulta
    clave_cache = f"cache:camino:{camino_buscado}:{fecha_noche_texto}"
    
    # Intentamos leer primero desde la caché de Redis
    resultado_en_cache = cliente_redis.get(clave_cache)
    if (resultado_en_cache):
        # Si existe en caché, lo convertimos de texto JSON a lista de Python y lo devolvemos
        return json.loads(resultado_en_cache)
    
    # Si no está en caché (cache miss), consultamos a PostgreSQL
    conexion_postgres = obtener_conexion_pg()
    cursor_postgres = conexion_postgres.cursor()
    
    # Buscamos los albergues del camino y unimos con Redis para ver sus plazas libres
    cursor_postgres.execute(
        "SELECT id, nome, concello, prezo FROM albergues WHERE camino = %s;",
        (camino_buscado,)
    )
    albergues_del_camino = cursor_postgres.fetchall()
    cursor_postgres.close()
    conexion_postgres.close()
    
    lista_disponibles = []
    for id_albergue, nombre_albergue, concello, precio in albergues_del_camino:
        clave_prazas = f"prazas:{id_albergue}:{fecha_noche_texto}"
        plazas_libres = cliente_redis.get(clave_prazas)
        
        # Si hay plazas libres (convertidas a número y mayores que 0)
        if (plazas_libres and int(plazas_libres) > 0):
            lista_disponibles.append({
                "id": id_albergue,
                "nome": nombre_albergue,
                "concello": concello,
                "prezo": float(precio),
                "prazas_libres": int(plazas_libres)
            })
    
    # Guardamos el resultado en la caché de Redis con un TTL de 60 segundos
    cliente_redis.setex(clave_cache, 60, json.dumps(lista_disponibles))
    
    return lista_disponibles