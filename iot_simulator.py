import asyncio
import json
import random

import websockets
from sqlalchemy.orm import Session

from database import SessionLocal
from models import RutaDB

# ==========================================
# CONFIG
# ==========================================

TOTAL_BUSES = 200
WS_URL = "ws://127.0.0.1:8000/ws/telemetria_ingesta"

# ==========================================
# CARGAR RUTAS
# ==========================================

db: Session = SessionLocal()

rutas = db.query(RutaDB).all()

if not rutas:
    raise Exception(
        "No existen rutas. Ejecuta seed.py primero."
    )

# ==========================================
# ESTADO FLOTA
# ==========================================

estado_flota = {}

for bus_id in range(1, TOTAL_BUSES + 1):

    ruta = rutas[(bus_id - 1) % len(rutas)]

    geometria = json.loads(
        ruta.geometria_ruta
    )

    estado_flota[bus_id] = {
        "ruta_id": ruta.id,
        "path": geometria,
        "segmento": 0,
        "progreso": random.random(),
        "energia": random.uniform(50, 100),
        "salud": "VERDE"
    }

print(
    f"🚌 Simulador iniciado con {TOTAL_BUSES} buses"
)

# ==========================================
# FUNCIONES
# ==========================================

def interpolar(p1, p2, t):

    lon = p1[0] + (p2[0] - p1[0]) * t
    lat = p1[1] + (p2[1] - p1[1]) * t

    return lat, lon


def avanzar_bus(bus):

    path = bus["path"]

    seg = bus["segmento"]
    prog = bus["progreso"]

    prog += 0.03

    if prog >= 1.0:

        prog = 0.0
        seg += 1

        if seg >= len(path) - 1:
            seg = 0

    bus["segmento"] = seg
    bus["progreso"] = prog

    p1 = path[seg]
    p2 = path[seg + 1]

    lat, lon = interpolar(
        p1,
        p2,
        prog
    )

    return lat, lon


def calcular_estado_salud(velocidad):

    if velocidad < 5:
        return "ROJO"

    if velocidad < 20:
        return "AMARILLO"

    return "VERDE"


# ==========================================
# LOOP PRINCIPAL
# ==========================================

async def ejecutar():

    while True:

        try:

            async with websockets.connect(
                WS_URL
            ) as websocket:

                print(
                    "✅ Conectado a FastAPI"
                )

                while True:

                    for bus_id, bus in estado_flota.items():

                        lat, lon = avanzar_bus(bus)

                        velocidad = random.uniform(
                            10,
                            60
                        )

                        salud = calcular_estado_salud(
                            velocidad
                        )

                        energia = bus["energia"]
                        energia -= random.uniform(
                            0.02,
                            0.15
                        )

                        if energia < 10:
                            energia = 100

                        bus["energia"] = energia
                        bus["salud"] = salud

                        payload = {
                            "vehiculo_id": bus_id,
                            "latitud": lat,
                            "longitud": lon,
                            "velocidad_kmh": velocidad,
                            "nivel_energia": energia,
                            "pasajeros_a_bordo": random.randint(
                                5,
                                80
                            )
                        }

                        await websocket.send(
                            json.dumps(payload)
                        )

                        await asyncio.sleep(
                            0.005
                        )

                    print(
                        "📡 Telemetría enviada"
                    )

                    await asyncio.sleep(1)

        except Exception as e:

            print(
                f"⚠️ Error WS: {e}"
            )

            await asyncio.sleep(3)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    asyncio.run(
        ejecutar()
    )