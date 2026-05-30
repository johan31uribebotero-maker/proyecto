"""OPERATIONAL INTELLIGENCE - Fase 6
====================================
Sistema inteligente de alertas y semáforos dinámicos.

Implementa:
- Semáforo de salud por ruta
- Detección de anomalías
- Predicción de problemas
- Alertas proactivas

Autor: AMCO System
Fecha: 30/05/2026
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# 1. ENUMERACIONES DE ESTADOS
# =====================================================

class EstadoSemaforoRuta(Enum):
    """Estados del semáforo de ruta."""
    VERDE = ("🟢 A TIEMPO", 0, 50)           # 0-50% ocupación
    AMARILLO = ("🟡 RETRASADO", 50, 75)      # 50-75% ocupación
    NARANJA = ("🟠 CRÍTICO", 75, 90)         # 75-90% ocupación
    ROJO = ("🔴 COLAPSADO", 90, 100)         # >90% ocupación
    
    def obtener_info(self):
        return {
            'emoji': self.value[0],
            'min': self.value[1],
            'max': self.value[2]
        }

class EstadoBus(Enum):
    """Estados del bus."""
    OPERATIVO = "🟢 OPERATIVO"
    ALERTA = "🟡 ALERTA"
    CRITICO = "🔴 CRÍTICO"
    MANTENIMIENTO = "⚫ MANTENIMIENTO"

# =====================================================
# 2. ANALIZADOR DE CONGESTIÓN DINÁMICO
# =====================================================

class AnalizadorCongestión:
    """Analiza congestión en tiempo real con predicción."""
    
    def __init__(self, ventana_minutos: int = 15):
        self.ventana = ventana_minutos
        self.historico = {}  # ruta_id -> lista de (timestamp, ocupacion%)
    
    def registrar_ocupacion(self, ruta_id: int, ocupacion_pct: float, 
                           pasajeros: int, capacidad: int):
        """Registra nivel de ocupación de una ruta."""
        if ruta_id not in self.historico:
            self.historico[ruta_id] = []
        
        self.historico[ruta_id].append({
            'timestamp': datetime.now(),
            'ocupacion': ocupacion_pct,
            'pasajeros': pasajeros,
            'capacidad': capacidad
        })
        
        # Limpiar datos antiguos (> ventana de tiempo)
        cutoff = datetime.now() - timedelta(minutes=self.ventana)
        self.historico[ruta_id] = [
            x for x in self.historico[ruta_id] 
            if x['timestamp'] > cutoff
        ]
    
    def obtener_estado_ruta(self, ruta_id: int, ocupacion_actual: float) -> Dict:
        """Retorna estado actual y tendencia de una ruta."""
        
        # Determinar semáforo
        if ocupacion_actual < 50:
            estado = EstadoSemaforoRuta.VERDE
        elif ocupacion_actual < 75:
            estado = EstadoSemaforoRuta.AMARILLO
        elif ocupacion_actual < 90:
            estado = EstadoSemaforoRuta.NARANJA
        else:
            estado = EstadoSemaforoRuta.ROJO
        
        # Calcular tendencia
        tendencia = self._calcular_tendencia(ruta_id)
        
        # Predicción
        prediccion = self._predecir_congestión(ruta_id)
        
        return {
            'ruta_id': ruta_id,
            'ocupacion': ocupacion_actual,
            'estado': estado.value[0],
            'tendencia': tendencia,
            'prediccion_5min': prediccion,
            'accion_recomendada': self._obtener_accion(estado, tendencia)
        }
    
    def _calcular_tendencia(self, ruta_id: int) -> str:
        """Calcula si la congestión sube, baja o se mantiene."""
        if ruta_id not in self.historico or len(self.historico[ruta_id]) < 2:
            return "📊 SIN DATOS"
        
        datos = self.historico[ruta_id][-5:]  # Últimos 5 registros
        if len(datos) < 2:
            return "📊 SIN DATOS"
        
        primera_ocupacion = datos[0]['ocupacion']
        ultima_ocupacion = datos[-1]['ocupacion']
        
        diferencia = ultima_ocupacion - primera_ocupacion
        
        if diferencia > 5:
            return "📈 EMPEORANDO (Sube +{:.1f}%)".format(diferencia)
        elif diferencia < -5:
            return "📉 MEJORANDO (Baja {:.1f}%)".format(abs(diferencia))
        else:
            return "➡️ ESTABLE"
    
    def _predecir_congestión(self, ruta_id: int) -> Dict:
        """Predice congestión en los próximos 5 minutos."""
        if ruta_id not in self.historico or len(self.historico[ruta_id]) < 3:
            return {'prediccion': 'Insuficientes datos', 'confianza': 0}
        
        datos = np.array([x['ocupacion'] for x in self.historico[ruta_id]])
        
        # Regresión lineal simple
        x = np.arange(len(datos)).reshape(-1, 1)
        y = datos
        
        # Coeficiente de pendiente
        pendiente = (len(datos) * np.sum(x.flatten() * y) - np.sum(x.flatten()) * np.sum(y)) / (
            len(datos) * np.sum(x.flatten() ** 2) - (np.sum(x.flatten())) ** 2
        )
        
        ocupacion_actual = datos[-1]
        ocupacion_predicha = ocupacion_actual + pendiente
        ocupacion_predicha = max(0, min(100, ocupacion_predicha))  # Limitar [0,100]
        
        return {
            'prediccion': f"{ocupacion_predicha:.1f}%",
            'confianza': 0.75,
            'sera_critica': ocupacion_predicha > 85
        }
    
    def _obtener_accion(self, estado: EstadoSemaforoRuta, tendencia: str) -> str:
        """Retorna acción recomendada basada en estado y tendencia."""
        if estado == EstadoSemaforoRuta.ROJO:
            return "🚨 URGENTE: Añadir buses inmediatamente"
        elif estado == EstadoSemaforoRuta.NARANJA and "EMPEORANDO" in tendencia:
            return "⚠️ PREVENTIVO: Preparar bus de apoyo"
        elif estado == EstadoSemaforoRuta.AMARILLO:
            return "📋 MONITOREAR: Incrementar frecuencia de chequeos"
        else:
            return "✅ NORMAL: Continuar operación regular"

# =====================================================
# 3. DETECTOR DE ANOMALÍAS
# =====================================================

class DetectorAnomalías:
    """Detecta comportamientos anómalos en buses."""
    
    @staticmethod
    def detectar_parada_prolongada(velocidad_kmh: float, 
                                   tiempo_parado_minutos: int) -> Tuple[bool, str]:
        """Detecta si un bus lleva demasiado tiempo parado."""
        if velocidad_kmh < 2 and tiempo_parado_minutos > 15:
            return True, f"⏸️ Bus parado {tiempo_parado_minutos} min (Posible falla o congestión)"
        return False, ""
    
    @staticmethod
    def detectar_exceso_velocidad(velocidad_kmh: float) -> Tuple[bool, str]:
        """Detecta exceso de velocidad."""
        if velocidad_kmh > 80:
            return True, f"🚨 EXCESO DE VELOCIDAD: {velocidad_kmh:.1f} km/h"
        if velocidad_kmh > 60:
            return True, f"⚠️ VELOCIDAD ELEVADA: {velocidad_kmh:.1f} km/h"
        return False, ""
    
    @staticmethod
    def detectar_bateria_critica(nivel_energia: float, tipo_motor: str) -> Tuple[bool, str]:
        """Detecta energía crítica."""
        if nivel_energia < 10:
            tipo = "Batería" if tipo_motor == "Electrico" else "Combustible"
            return True, f"🔴 {tipo} CRÍTICA: {nivel_energia:.1f}%"
        if nivel_energia < 20:
            tipo = "Batería" if tipo_motor == "Electrico" else "Combustible"
            return True, f"🟡 {tipo} BAJA: {nivel_energia:.1f}%"
        return False, ""
    
    @staticmethod
    def detectar_desviacion_ruta(distancia_ruta_m: float) -> Tuple[bool, str]:
        """Detecta desviación de ruta."""
        if distancia_ruta_m > 100:
            return True, f"⚠️ FUERA DE RUTA: {distancia_ruta_m:.1f}m de distancia"
        return False, ""
    
    @staticmethod
    def detectar_ocupacion_anormal(ocupacion_pct: float, 
                                   ocupacion_promedio: float) -> Tuple[bool, str]:
        """Detecta si ocupación es anormalmente alta/baja."""
        desviacion = abs(ocupacion_pct - ocupacion_promedio)
        
        if desviacion > 30:
            return True, f"🔴 OCUPACIÓN ANORMAL: {ocupacion_pct:.1f}% (Promedio: {ocupacion_promedio:.1f}%)"
        return False, ""

# =====================================================
# 4. DASHBOARD OPERACIONAL
# =====================================================

class DashboardOperacional:
    """Genera métricas operacionales consolidadas."""
    
    def __init__(self):
        self.analizador = AnalizadorCongestión()
        self.detector = DetectorAnomalías()
    
    def generar_reporte_salud(self, buses: List[Dict], rutas: List[Dict]) -> Dict:
        """Genera reporte consolidado de salud operacional."""
        
        alertas = []
        buses_criticos = []
        rutas_problematicas = []
        
        # Analizar cada bus
        for bus in buses:
            anomalias = []
            
            # Verificar exceso de velocidad
            es_anomalia, msg = self.detector.detectar_exceso_velocidad(bus['vel'])
            if es_anomalia:
                anomalias.append(msg)
            
            # Verificar batería
            es_anomalia, msg = self.detector.detectar_bateria_critica(bus['bateria_gasolina'], bus['tipo_motor'])
            if es_anomalia:
                anomalias.append(msg)
            
            if anomalias:
                buses_criticos.append({
                    'id': bus['vehiculo_id'],
                    'placa': bus['placa'],
                    'alertas': anomalias
                })
                alertas.extend(anomalias)
        
        # Analizar cada ruta
        for ruta in rutas:
            estado_ruta = self.analizador.obtener_estado_ruta(
                ruta['id'],
                ruta['ocupacion_pct']
            )
            
            if '🔴' in estado_ruta['estado'] or '🟠' in estado_ruta['estado']:
                rutas_problematicas.append(estado_ruta)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_alertas': len(alertas),
            'buses_criticos': buses_criticos,
            'rutas_problematicas': rutas_problematicas,
            'alertas': alertas,
            'salud_general': self._calcular_salud_general(buses, rutas)
        }
    
    def _calcular_salud_general(self, buses: List[Dict], rutas: List[Dict]) -> Dict:
        """Calcula salud general del sistema."""
        
        if not buses:
            return {'estado': '❓ SIN DATOS', 'porcentaje': 0}
        
        buses_problematicos = sum(1 for b in buses if b['bateria_gasolina'] < 20 or b['vel'] > 80)
        rutas_problematicas = sum(1 for r in rutas if r.get('ocupacion_pct', 0) > 85)
        
        porcentaje_salud = ((len(buses) - buses_problematicos) / len(buses)) * 100
        
        if porcentaje_salud >= 80:
            estado = "🟢 EXCELENTE"
        elif porcentaje_salud >= 60:
            estado = "🟡 ACEPTABLE"
        elif porcentaje_salud >= 40:
            estado = "🟠 CRÍTICO"
        else:
            estado = "🔴 COLAPSADO"
        
        return {
            'estado': estado,
            'porcentaje': porcentaje_salud,
            'buses_problematicos': buses_problematicos,
            'rutas_problematicas': rutas_problematicas
        }

if __name__ == "__main__":
    print("Operational Intelligence Module - AMCO Fase 6")
    print("Proporciona análisis inteligente de congestión y alertas")
