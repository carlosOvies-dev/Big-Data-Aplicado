"""Xerador de datos de proba para a rede de albergues Camiño Aberto (ficticia).

ESQUELETO DO P1. Xa funciona: xera albergues e mostra un resumo. O resto
das funcións están marcadas con TODO e, mentres non as completes, avisan
e devolven unha lista baleira para que o script se poida executar desde o
primeiro día.

Exemplos (desde a raíz do proxecto):
  python -m src.xera_datos --sen-carga                    # só xerar e mostrar
  python -m src.xera_datos --albergues 60 --semente 7 --sen-carga
  python -m src.xera_datos                                 # xerar e cargar (cando estea feito)
"""
import argparse
import random
from datetime import date

from faker import Faker

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from pymongo import MongoClient

load_dotenv()

# ------------------------------------------------------------------ catálogos
# Concellos galegos de cada camiño, en orde de etapas. Podes engadir máis.
CAMIÑOS = {
    "Francés":   ["Pedrafita do Cebreiro", "Triacastela", "Samos", "Sarria", "Portomarín",
                  "Palas de Rei", "Melide", "Arzúa", "O Pino"],
    "Portugués": ["Tui", "O Porriño", "Redondela", "Pontevedra", "Caldas de Reis", "Padrón", "Teo"],
    "Norte":     ["Ribadeo", "Lourenzá", "Mondoñedo", "Abadín", "Vilalba", "Guitiriz", "Sobrado"],
    "Primitivo": ["A Fonsagrada", "Castroverde", "Lugo", "Friol", "Melide"],
    "Inglés":    ["Ferrol", "Neda", "Pontedeume", "Betanzos", "Abegondo", "Ordes"],
}
NOMES_ALBERGUE = ["Vieiras", "Pedra Miúda", "O Cruceiro", "A Ponte Vella", "Bordón", "A Cabaciña",
                  "Fonte Vella", "Os Carballos", "A Estrela", "Camiño Real", "Casa do Peregrino",
                  "A Xesta", "O Muíño", "Santa Mariña", "O Hórreo", "A Lareira", "Sete Fontes"]


def pendente(nome):
    print(f"  [pendente] {nome}() aínda non está feita")
    return []


# ------------------------------------------------------------------ xeración
#XERAR ALBERGUE
def xera_albergues(n, rng):
    """EXEMPLO RESOLTO: úsao como modelo para o resto de funcións.

    Devolve unha lista de dicionarios, un por albergue. Todo o azar sae de `rng`
    (un random.Random), non do módulo `random` directamente: así a semente controla
    o resultado.
    """
    albergues = []
    for i in range(1, n + 1):
        camino = rng.choice(list(CAMIÑOS))
        concello = rng.choice(CAMIÑOS[camino])
        albergues.append({
            "id": i,
            "nome": f"Albergue {rng.choice(NOMES_ALBERGUE)} ({concello})",
            "camino": camino,
            "concello": concello,
            "prazas": rng.randint(8, 60),
            "prezo": float(rng.randint(10, 22)),
        })
    return albergues


#XERAR PEREGRINOS
def xera_peregrinos(n, rng, fake):
    """Xera unha lista de peregrinos ficticios."""
    peregrinos = []

    for i in range(1, n + 1):
        nome = fake.first_name()
        apelidos = fake.last_name() + " " + fake.last_name()

        documento = f"PER-{i:06d}"
        email = f"peregrino{i}@exemplo.com"
        pais = "España"

        # Xeramos unha data de nacemento reproducible entre 18 e 80 anos.
        ano = rng.randint(1947, 2009)
        mes = rng.randint(1, 12)
        dia = rng.randint(1, 28)
        data_nacemento = date(ano, mes, dia)

        peregrinos.append({
            "id": i,
            "nome": nome,
            "apelidos": apelidos,
            "documento": documento,
            "email": email,
            "pais": pais,
            "data_nacemento": data_nacemento.isoformat(),
        })

    return peregrinos


#XERAR RESERVAS
def xera_reservas(n, albergues, peregrinos, desde, dias, rng):
    """Xera reservas sen superar a capacidade dos albergues."""
    reservas = []
    ocupacion = {}
    peregrinos_por_noite = set()

    if not albergues or not peregrinos or dias <= 0:
        return reservas

    noites = [
        desde.fromordinal(desde.toordinal() + i)
        for i in range(dias)
    ]

    intentos = 0
    max_intentos = n * 10

    while len(reservas) < n and intentos < max_intentos:
        intentos += 1

        albergue = rng.choice(albergues)
        peregrino = rng.choice(peregrinos)
        noite = rng.choice(noites)

        id_albergue = albergue["id"]
        id_peregrino = peregrino["id"]
        clave = (id_albergue, noite)
        clave_peregrino = (id_peregrino, noite)

        # Non repetir peregrino nin superar as prazas desa noite.
        if clave_peregrino in peregrinos_por_noite:
            continue

        ocupadas = ocupacion.get(clave, 0)
        if ocupadas >= albergue["prazas"]:
            continue

        reservas.append({
            "id": len(reservas) + 1,
            "albergue_id": id_albergue,
            "peregrino_id": id_peregrino,
            "noite": noite.isoformat(),
        })

        ocupacion[clave] = ocupadas + 1
        peregrinos_por_noite.add(clave_peregrino)

    return reservas



#FICHAS
def xera_fichas(albergues, rng, fake):
    """Xera unha ficha con información variable para cada albergue."""
    fichas = []

    servizos_posibles = [
        "wifi",
        "lavadora",
        "cociña",
        "duchas",
        "consigna",
        "zona de descanso",
    ]

    paraxes = [
        "Nun entorno tranquilo",
        "Preto do centro",
        "Con vistas á natureza",
        "Nunha zona rural",
        "Preto dos servizos principais",
    ]

    for albergue in albergues:
        ficha = {
            "albergue_id": albergue["id"],
            "nome": albergue["nome"],
            "descricion": fake.paragraph(nb_sentences=3),
            "servizos": rng.sample(
                servizos_posibles,
                k=rng.randint(2, len(servizos_posibles))
            ),
            "contorna": rng.choice(paraxes),
        }

        # Algúns albergues teñen web e outros non.
        if rng.random() < 0.6:
            ficha["web"] = (
                f"https://albergue{albergue['id']}.exemplo.com"
            )

        # Só algúns dispoñen de garaxe para bicicletas.
        if rng.random() < 0.4:
            ficha["garaxe_bicis"] = True

        # As opinións son opcionais e poden variar entre albergues.
        if rng.random() < 0.7:
            ficha["opinions"] = [
                {
                    "puntuacion": rng.randint(3, 5),
                    "comentario": fake.sentence(),
                }
                for _ in range(rng.randint(1, 3))
            ]

        fichas.append(ficha)

    return fichas


# ------------------------------------------------------------------ carga

def carga_postgres(albergues, peregrinos, reservas):
    """Crea as táboas e insire os datos en PostgreSQL."""

    conexion = psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=int(os.getenv("PGPORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    cursor = None

    try:
        cursor = conexion.cursor()

        # Localizamos e executamos o esquema SQL.
        ruta_esquema = Path(__file__).resolve().parent / "esquema.sql"

        with open(ruta_esquema, "r", encoding="utf-8") as archivo:
            sql = archivo.read()

        cursor.execute(sql)

        # Limpamos as táboas antes de cargar os novos datos (para eliminar datos de probas x exemplo).
        cursor.execute("""
            TRUNCATE TABLE reservas, peregrinos, albergues
            RESTART IDENTITY CASCADE
        """)

        # Insertms os albergues.
        consulta = """
            INSERT INTO albergues (id, nome, camino, concello, prazas, prezo)
            VALUES %s
        """

        valores = [
            (a["id"], a["nome"], a["camino"], a["concello"], a["prazas"], a["prezo"])
            for a in albergues
        ]
        execute_values(cursor, consulta, valores)

        # Insertams os peregrinos.
        consulta = """
            INSERT INTO peregrinos
            (id, nome, apelidos, documento, email, pais, data_nacemento)
            VALUES %s
        """

        valores = [
            (p["id"], p["nome"], p["apelidos"], p["documento"],
             p["email"], p["pais"], p["data_nacemento"])
            for p in peregrinos
        ]
        execute_values(cursor, consulta, valores)

        # Insertamos as reservas relacionándoas cos albergs e peregrins.
        consulta = """
            INSERT INTO reservas (id, albergue_id, peregrino_id, noite)
            VALUES %s
        """

        valores = [
            (r["id"], r["albergue_id"], r["peregrino_id"], r["noite"])
            for r in reservas
        ]
        execute_values(cursor, consulta, valores)

        # Actualizamos as secuencias dos IDs automáticos.
        for tabla in ("albergues", "peregrinos", "reservas"):
            cursor.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{tabla}', 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM {tabla}
            """)

        # Confirmamos os cambios.
        conexion.commit()
        print("Datos cargados correctamente en PostgreSQL.")

    #Pechams o try
    except Exception as error:
        conexion.rollback()
        print(f"Erro ao cargar os datos: {error}")
        raise

    finally:
        if cursor:
            cursor.close()
        conexion.close()

def carga_mongo(fichas):
    """Garda as fichas dos albergues nunha colección de MongoDB."""

    cliente = MongoClient(
        host=os.getenv("MONGO_HOST"),
        port=int(os.getenv("MONGO_PORT")),
        username=os.getenv("MONGO_USER"),
        password=os.getenv("MONGO_PASSWORD"),
        authSource="admin"
    )

    try:
        # Comprobamos que podemos conectar con MongoDB.
        cliente.admin.command("ping")

        # Seleccionamos a base de datos e a colección.
        base_datos = cliente[os.getenv("MONGO_DB")]
        coleccion = base_datos["fichas"]

        # Borramos os datos anteriores para evitar duplicados.
        coleccion.delete_many({})

        # Inserimos as novas fichas.
        if fichas:
            coleccion.insert_many(fichas)

        print(f"Datos cargados correctamente en MongoDB: {coleccion.count_documents({})} fichas.")

    except Exception as error:
        print(f"Erro ao cargar os datos en MongoDB: {error}")
        raise

    finally:
        cliente.close()


# ------------------------------------------------------------------ main
def mostra(titulo, filas, cantas=2):
    print(f"\n{titulo}: {len(filas)}")
    for f in filas[:cantas]:
        print(f"  {f}")


def main():
    ap = argparse.ArgumentParser(description="Xera e carga datos de proba de Camiño Aberto")
    ap.add_argument("--albergues", type=int, default=40)
    ap.add_argument("--peregrinos", type=int, default=1500)
    ap.add_argument("--reservas", type=int, default=5000)
    ap.add_argument("--semente", type=int, default=42, help="mesma semente → mesmos datos")
    ap.add_argument("--desde", type=date.fromisoformat, default=date(2027, 5, 1),
                    help="primeira noite da tempada (AAAA-MM-DD)")
    ap.add_argument("--dias", type=int, default=30, help="número de noites da tempada")
    ap.add_argument("--sen-carga", action="store_true", help="xera e mostra, pero non carga nada")
    args = ap.parse_args()

    rng = random.Random(args.semente)
    fake = Faker("es_ES")
    fake.seed_instance(args.semente)


    print(f"Semente {args.semente} · tempada {args.desde} + {args.dias} noites")
    albergues = xera_albergues(args.albergues, rng)
    peregrinos = xera_peregrinos(args.peregrinos, rng, fake)
    reservas = xera_reservas(args.reservas, albergues, peregrinos, args.desde, args.dias, rng)
    fichas = xera_fichas(albergues, rng, fake)

    mostra("Albergues", albergues)
    mostra("Peregrinos", peregrinos)
    mostra("Reservas", reservas)
    mostra("Fichas", fichas, 1)

    if not args.sen_carga:
        carga_postgres(albergues, peregrinos, reservas)
        carga_mongo(fichas)


if __name__ == "__main__":
    main()
