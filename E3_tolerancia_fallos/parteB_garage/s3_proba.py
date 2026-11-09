"""Cliente S3 para probar Garage: subir, listar e verificar a integridade.

Variables de contorno: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
Uso:
  python s3_proba.py subir      --n 20 --tamano-kb 512
  python s3_proba.py listar
  python s3_proba.py verificar  [--porto 3910]
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import boto3
from botocore.config import Config

BUCKET = os.getenv("BUCKET", "albergues-docs")
MANIFESTO = Path("manifesto.json")       # sha256 de cada ficheiro subido


def cliente(porto):
    return boto3.client(
        "s3",
        endpoint_url=f"http://localhost:{porto}",
        region_name="garage",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 1},
                      connect_timeout=5, read_timeout=10),
    )


def sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def subir(s3, n, tamano_kb):
    """Xera n ficheiros aleatorios (como se fosen PDF de reservas), súbeos e garda o seu sha256."""
    manifesto = {}
    t0 = time.perf_counter()
    for i in range(1, n + 1):
        clave = f"reservas/2026/reserva_{i:04d}.pdf"
        datos = os.urandom(tamano_kb * 1024)
        s3.put_object(Bucket=BUCKET, Key=clave, Body=datos)
        manifesto[clave] = sha256(datos)
    MANIFESTO.write_text(json.dumps(manifesto, indent=2))
    print(f"Subidos {n} obxectos de {tamano_kb} KB en {time.perf_counter() - t0:.1f} s. Manifesto gardado.")


def listar(s3):
    total, tamano = 0, 0
    paxinas = s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET)
    for paxina in paxinas:
        for o in paxina.get("Contents", []):
            total += 1
            tamano += o["Size"]
    print(f"Bucket {BUCKET}: {total} obxectos, {tamano / 1e6:.1f} MB")


def verificar(s3):
    """Descarga cada obxecto e compara o seu sha256 co do manifesto."""
    manifesto = json.loads(MANIFESTO.read_text())
    ok, mal, erros = 0, 0, 0
    for clave, esperado in manifesto.items():
        try:
            datos = s3.get_object(Bucket=BUCKET, Key=clave)["Body"].read()
        except Exception as e:                       # nodo caído, sen quórum…
            erros += 1
            if erros == 1:
                print(f"Erro ao descargar {clave}: {type(e).__name__}: {e}")
            continue
        if sha256(datos) == esperado:
            ok += 1
        else:
            mal += 1
            print(f"CORRUPTO: {clave}")
    print(f"Verificados: {ok} correctos · {mal} corruptos · {erros} sen poder descargar")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("accion", choices=["subir", "listar", "verificar"])
    p.add_argument("--porto", type=int, default=3900, help="3900=garage1, 3910=garage2, 3920=garage3")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--tamano-kb", type=int, default=512)
    a = p.parse_args()
    s3 = cliente(a.porto)
    if a.accion == "subir":
        subir(s3, a.n, a.tamano_kb)
    elif a.accion == "listar":
        listar(s3)
    else:
        verificar(s3)
