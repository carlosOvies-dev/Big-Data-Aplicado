import time
import statistics
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.reservas import (
    obtener_conexion_redis,
    obtener_conexion_pg,
    inicializar_contadores,
    reservar,
    consultar_albergues_disponibles_con_cache
)


def buscar_escenario_concurrencia(cursor):
    query = """
        SELECT a.id, r.noite, (a.prazas - COUNT(r.id)) AS libres
        FROM albergues a
        JOIN reservas r ON r.albergue_id = a.id
        GROUP BY a.id, a.prazas, r.noite
        HAVING (a.prazas - COUNT(r.id)) >= 5
        ORDER BY libres ASC, a.id ASC, r.noite ASC
        LIMIT 1;
    """
    cursor.execute(query)
    fila = cursor.fetchone()
    if fila is not None:
        return fila[0], fila[1], int(fila[2])
    return 1, date(2027, 5, 1), 5


def obtener_peregrinos_libres(cursor, noite, cantidad=50):
    query = """
        SELECT p.id
        FROM peregrinos p
        WHERE NOT EXISTS (
            SELECT 1 FROM reservas r
            WHERE r.peregrino_id = p.id AND r.noite = %s
        )
        ORDER BY p.id ASC
        LIMIT %s;
    """
    cursor.execute(query, (noite, cantidad))
    return [fila[0] for fila in cursor.fetchall()]


def contar_reservas_pg(cursor, albergue_id, noite):
    cursor.execute(
        "SELECT COUNT(*) FROM reservas WHERE albergue_id = %s AND noite = %s;",
        (albergue_id, noite)
    )
    return int(cursor.fetchone()[0])


def ejecutar_pruebas():
    print("=== INICIANDO PROBAS DA APLICACIÓN ===")

    # 1. Inicializar contadores para as 30 noites
    print("1. Inicializando contadores en Redis (30 noites)...")
    inicializar_contadores(fecha_inicio=date(2027, 5, 1), total_dias=30)

    r_client = obtener_conexion_redis()
    conn = obtener_conexion_pg()
    cursor = conn.cursor()

    # 2. Proba de concorrencia sen sobreventa
    albergue_id, noite_prueba, prazas_libres = buscar_escenario_concurrencia(cursor)
    peregrinos_libres = obtener_peregrinos_libres(cursor, noite_prueba, 50)
    reservas_antes = contar_reservas_pg(cursor, albergue_id, noite_prueba)
    clave_redis = f"prazas:{albergue_id}:{noite_prueba.isoformat()}"

    print(
        f"\n2. Proba de concorrencia: 50 solicitudes simultáneas para "
        f"albergue {albergue_id} na noite {noite_prueba.isoformat()} "
        f"({prazas_libres} prazas libres)..."
    )

    aceptadas = 0
    rexeitadas = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        futuros = [
            executor.submit(reservar, albergue_id, noite_prueba, pid)
            for pid in peregrinos_libres
        ]
        for futuro in as_completed(futuros):
            if futuro.result():
                aceptadas += 1
            else:
                rexeitadas += 1

    valor_redis = r_client.get(clave_redis)
    if isinstance(valor_redis, bytes):
        contador_final = int(valor_redis.decode("utf-8"))
    else:
        contador_final = int(valor_redis)

    reservas_despois = contar_reservas_pg(cursor, albergue_id, noite_prueba)
    novas_pg = reservas_despois - reservas_antes

    print(
        f"Prazas libres: {prazas_libres} | Solicitudes: {len(peregrinos_libres)} | "
        f"Aceptadas: {aceptadas} | Rexeitadas: {rexeitadas} | "
        f"Contador final Redis: {contador_final} | Reservas novas PostgreSQL: {novas_pg}"
    )

    if aceptadas == prazas_libres and contador_final == 0 and novas_pg == prazas_libres:
        print("OK: aceptáronse exactamente as prazas libres. Non hai sobreventa.")

    # 3. Demostración da caché con TTL
    camino_prueba = "Francés"
    r_client.delete(f"cache:camino:{camino_prueba}:{noite_prueba.isoformat()}")

    inicio_sen = time.perf_counter()
    consultar_albergues_disponibles_con_cache(camino_prueba, noite_prueba)
    t_sen_cache = (time.perf_counter() - inicio_sen) * 1000.0

    inicio_con = time.perf_counter()
    consultar_albergues_disponibles_con_cache(camino_prueba, noite_prueba)
    t_con_cache = (time.perf_counter() - inicio_con) * 1000.0

    print("\n3. Demostración de caché (TTL 60 s):")
    print(f"Sen caché (PostgreSQL): {t_sen_cache:.3f} ms ({t_sen_cache / 1000.0:.6f} s)")
    print(f"Con caché (Redis):      {t_con_cache:.3f} ms ({t_con_cache / 1000.0:.6f} s)")

    # 4. Consulta de dispoñibilidade: PostgreSQL vs Redis (100 repeticións)
    query_pg = """
        SELECT a.prazas - COUNT(r.id) FROM albergues a
        LEFT JOIN reservas r ON r.albergue_id = a.id AND r.noite = %s
        WHERE a.id = %s GROUP BY a.id;
    """

    tempos_pg = []
    for _ in range(100):
        t0 = time.perf_counter()
        cursor.execute(query_pg, (noite_prueba, albergue_id))
        cursor.fetchone()
        tempos_pg.append((time.perf_counter() - t0) * 1000.0)

    tempos_redis = []
    for _ in range(100):
        t0 = time.perf_counter()
        r_client.get(clave_redis)
        tempos_redis.append((time.perf_counter() - t0) * 1000.0)

    media_pg = statistics.mean(tempos_pg)
    mediana_pg = statistics.median(tempos_pg)
    media_redis = statistics.mean(tempos_redis)
    mediana_redis = statistics.median(tempos_redis)

    print("\n4. Consulta de dispoñibilidade: PostgreSQL vs Redis (100 repeticións):")
    print(f"PostgreSQL -> Media: {media_pg:.3f} ms | Mediana: {mediana_pg:.3f} ms")
    print(f"Redis      -> Media: {media_redis:.3f} ms | Mediana: {mediana_redis:.3f} ms")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    ejecutar_pruebas()