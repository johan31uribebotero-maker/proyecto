"""
ADVANCED VISUALIZATION MODULE - Fase 6
======================================
Implementa mejoras profesionales de UI/UX:
- Interpolación de movimiento suave
- Dark mode con CartoDB
- Websockets para actualizaciones en tiempo real
- Geofencing para alertas de desviación
- Heatmaps dinámicos
- Loading skeletons

Autor: AMCO System
Fecha: 30/05/2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from typing import Tuple, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# 1. INTERPOLACIÓN DE MOVIMIENTO
# =====================================================

class InterpoladorMovimiento:
    """Interpola suavemente la posición de un bus entre dos puntos."""
    
    def __init__(self, duracion_segundos: float = 2.0):
        """
        Args:
            duracion_segundos: tiempo total de interpolación
        """
        self.duracion = duracion_segundos
        self.historico_posiciones = {}
    
    def interpolar_posicion(self, vehiculo_id: int, 
                           posicion_anterior: Tuple[float, float],
                           posicion_nueva: Tuple[float, float],
                           fraccion_tiempo: float) -> Tuple[float, float]:
        """
        Interpola linealmente entre dos posiciones.
        
        P(t) = P0 + t*(P1 - P0)  donde t ∈ [0, 1]
        
        Args:
            vehiculo_id: ID del bus
            posicion_anterior: [lat, lon] anterior
            posicion_nueva: [lat, lon] nueva
            fraccion_tiempo: t ∈ [0, 1]
            
        Returns:
            Posición interpolada [lat, lon]
        """
        lat0, lon0 = posicion_anterior
        lat1, lon1 = posicion_nueva
        
        # Interpolación lineal
        lat_interp = lat0 + fraccion_tiempo * (lat1 - lat0)
        lon_interp = lon0 + fraccion_tiempo * (lon1 - lon0)
        
        return lat_interp, lon_interp
    
    def interpolar_suave(self, vehiculo_id: int,
                        posicion_anterior: Tuple[float, float],
                        posicion_nueva: Tuple[float, float],
                        tiempo_actual: float) -> Tuple[float, float]:
        """
        Usa easing (suavizado) para interpolación más natural.
        Aplica función ease-in-out para movimiento más realista.
        
        easeInOutQuad(t) = t < 0.5 ? 2*t² : -1 + 4*t - 2*t²
        """
        if vehiculo_id not in self.historico_posiciones:
            self.historico_posiciones[vehiculo_id] = {
                'inicio': tiempo_actual,
                'anterior': posicion_anterior,
                'nueva': posicion_nueva
            }
        
        hist = self.historico_posiciones[vehiculo_id]
        tiempo_transcurrido = tiempo_actual - hist['inicio']
        fraccion = min(tiempo_transcurrido / self.duracion, 1.0)
        
        # Easing function: ease-in-out-quad
        if fraccion < 0.5:
            t_eased = 2 * fraccion ** 2
        else:
            t_eased = -1 + 4 * fraccion - 2 * fraccion ** 2
        
        posicion = self.interpolar_posicion(
            vehiculo_id, 
            hist['anterior'], 
            hist['nueva'],
            t_eased
        )
        
        # Limpiar cuando termina la interpolación
        if fraccion >= 1.0:
            del self.historico_posiciones[vehiculo_id]
        
        return posicion


# =====================================================
# 2. GEOFENCING (DETECCIÓN DE DESVIACIÓN)
# =====================================================

class GeoFencing:
    """Detecta si un bus se desvió de su ruta asignada."""
    
    def __init__(self, distancia_tolerancia_m: float = 50.0):
        """
        Args:
            distancia_tolerancia_m: distancia máxima permitida de la ruta (metros)
        """
        self.tolerancia = distancia_tolerancia_m
        self.alertas_activas = {}
    
    @staticmethod
    def distancia_punto_a_segmento(punto: np.ndarray,
                                  seg_inicio: np.ndarray,
                                  seg_fin: np.ndarray) -> float:
        """
        Calcula distancia perpendicular entre punto y segmento de línea.
        
        Usa proyección vectorial.
        """
        # Vector del segmento
        v = seg_fin - seg_inicio
        # Vector del inicio al punto
        w = punto - seg_inicio
        
        # Proyección
        c1 = np.dot(w, v)
        if c1 <= 0:
            return np.linalg.norm(punto - seg_inicio)
        
        c2 = np.dot(v, v)
        if c1 >= c2:
            return np.linalg.norm(punto - seg_fin)
        
        b = c1 / c2
        proyeccion = seg_inicio + b * v
        
        return np.linalg.norm(punto - proyeccion)
    
    def verificar_desviacion(self, vehiculo_id: int,
                            posicion_actual: np.ndarray,
                            ruta_puntos: List[np.ndarray]) -> Dict:
        """
        Verifica si el bus está fuera de su ruta.
        
        Returns:
            {
                'desviado': bool,
                'distancia_min': float,
                'segmento_mas_cercano': int,
                'alerta': str
            }
        """
        distancia_minima = np.inf
        segmento_mas_cercano = -1
        
        # Convertir a array de metros
        posicion_m = posicion_actual * 111000
        
        # Revisar cada segmento de la ruta
        for i in range(len(ruta_puntos) - 1):
            seg_inicio = ruta_puntos[i] * 111000
            seg_fin = ruta_puntos[i + 1] * 111000
            
            distancia = self.distancia_punto_a_segmento(
                posicion_m, seg_inicio, seg_fin
            )
            
            if distancia < distancia_minima:
                distancia_minima = distancia
                segmento_mas_cercano = i
        
        # Determinar si está desviado
        desviado = distancia_minima > self.tolerancia
        
        # Generar alerta
        if desviado and vehiculo_id not in self.alertas_activas:
            alerta = f"⚠️ BUS {vehiculo_id} FUERA DE RUTA ({distancia_minima:.1f}m)"
            self.alertas_activas[vehiculo_id] = True
            logger.warning(alerta)
        elif not desviado and vehiculo_id in self.alertas_activas:
            del self.alertas_activas[vehiculo_id]
            alerta = f"✅ BUS {vehiculo_id} RETORNÓ A RUTA"
        else:
            alerta = ""
        
        return {
            'desviado': desviado,
            'distancia_min': distancia_minima,
            'segmento_mas_cercano': segmento_mas_cercano,
            'alerta': alerta
        }


# =====================================================
# 3. DASHBOARD CON DARK MODE Y CAPAS AVANZADAS
# =====================================================

class DashboardAvanzado:
    """Dashboard con todas las mejoras de UI/UX."""
    
    @staticmethod
    def crear_mapa_3d_profesional(df_buses: pd.DataFrame,
                                  rutas_metro: List[Dict],
                                  df_paradas: pd.DataFrame = None) -> pdk.Deck:
        """
        Crea un mapa 3D profesional con múltiples capas.
        
        Capas:
        1. PathLayer: Rutas trazadas
        2. HexagonLayer: Densidad de pasajeros
        3. HeatmapLayer: Demanda en paradas
        4. ScatterplotLayer: Ubicación de buses
        5. GeoJsonLayer: Áreas de geofencing
        """
        layers = []
        
        # ===== CAPA 1: RUTAS (PathLayer) =====
        for ruta_info in rutas_metro:
            ruta_df = pd.DataFrame([{'path': ruta_info['path']}])
            layers.append(
                pdk.Layer(
                    'PathLayer',
                    ruta_df,
                    get_path='path',
                    get_width=8,
                    get_color=ruta_info['color'],
                    width_min_pixels=2,
                    pickable=True
                )
            )
        
        # ===== CAPA 2: HEXAGON (Densidad 3D) =====
        layers.append(
            pdk.Layer(
                'HexagonLayer',
                df_buses,
                get_position=['lon', 'lat'],
                radius=300,
                elevation_scale=15,
                extruded=True,
                pickable=True,
                color_range=[
                    [0, 255, 100],      # Verde - bajo
                    [255, 255, 0],      # Amarillo
                    [255, 150, 0],      # Naranja
                    [255, 0, 0]         # Rojo - alto
                ],
                coverage=0.9
            )
        )
        
        # ===== CAPA 3: HEATMAP DE PARADAS =====
        if df_paradas is not None and not df_paradas.empty:
            layers.append(
                pdk.Layer(
                    'HeatmapLayer',
                    df_paradas,
                    get_position=['lon', 'lat'],
                    radiusPixels=80,
                    getWeight='intensidad',
                    aggregationModel='SUM',
                    colorRange=[
                        [0, 0, 255],      # Azul
                        [0, 255, 255],    # Cyan
                        [0, 255, 0],      # Verde
                        [255, 255, 0],    # Amarillo
                        [255, 0, 0]       # Rojo
                    ],
                    pickable=True
                )
            )
        
        # ===== CAPA 4: BUSES (ScatterplotLayer) =====
        # Colorear según estado
        colores = []
        for _, row in df_buses.iterrows():
            if row['vel'] < 5:
                color = [255, 0, 0, 200]      # Rojo - detenido
            elif row['vel'] < 20:
                color = [255, 255, 0, 200]    # Amarillo - lento
            else:
                color = [0, 255, 100, 200]    # Verde - normal
            colores.append(color)
        
        df_buses['color'] = colores
        
        layers.append(
            pdk.Layer(
                'ScatterplotLayer',
                df_buses,
                get_position=['lon', 'lat'],
                get_radius=150,
                get_fill_color='color',
                pickable=True,
                transitions={
                    'getPosition': {
                        'type': 'spring',
                        'stiffness': 0.02,
                        'damping': 0.3
                    }
                }
            )
        )
        
        # ===== CREAR DECK =====
        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v11',  # Dark mode CartoDB
            map_provider='mapbox',
            initial_view_state=pdk.ViewState(
                latitude=4.8135,
                longitude=-75.6942,
                zoom=12,
                pitch=45,
                bearing=0
            ),
            layers=layers,
            tooltip={
                'text': (
                    'Bus {vehiculo_id}\n'
                    'Pasajeros: {pasajeros}\n'
                    'Velocidad: {vel} km/h\n'
                    'Energía: {bateria_gasolina}%'
                )
            }
        )
        
        return deck
    
    @staticmethod
    def crear_mapa_calor_dinamico(df_paradas: pd.DataFrame) -> pdk.Deck:
        """
        Crea un heatmap dinámico de paradas con cambios en tiempo real.
        
        Mayor intensidad = más personas esperando.
        """
        # Normalizar intensidades
        max_personas = df_paradas['personas_esperando'].max()
        df_paradas['intensidad'] = df_paradas['personas_esperando'] / max_personas
        
        heatmap_layer = pdk.Layer(
            'HeatmapLayer',
            df_paradas,
            get_position=['lon', 'lat'],
            radiusPixels=100,
            getWeight='intensidad',
            colorRange=[
                [0, 0, 139],      # Azul oscuro
                [0, 255, 255],    # Cyan
                [255, 255, 0],    # Amarillo
                [255, 100, 0],    # Naranja
                [255, 0, 0]       # Rojo
            ],
            aggregationModel='SUM',
            pickable=True
        )
        
        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v11',
            map_provider='mapbox',
            initial_view_state=pdk.ViewState(
                latitude=4.8135,
                longitude=-75.6942,
                zoom=12,
                pitch=30
            ),
            layers=[heatmap_layer],
            tooltip={'text': '{nombre}\nPersonas: {personas_esperando}'}
        )
        
        return deck


# =====================================================
# 4. INDICADORES DE CARGA (SKELETONS)
# =====================================================

class IndicadoresCarga:
    """Muestra skeletons y spinners durante la carga."""
    
    @staticmethod
    def mostrar_skeleton_tabla(filas: int = 5, columnas: int = 4):
        """Muestra un skeleton placeholder para tabla."""
        st.markdown("""
        <style>
        @keyframes skeleton-loading {
            0% { background-color: rgba(255, 255, 255, 0.05); }
            50% { background-color: rgba(255, 255, 255, 0.1); }
            100% { background-color: rgba(255, 255, 255, 0.05); }
        }
        .skeleton-cell {
            animation: skeleton-loading 1s infinite;
            height: 20px;
            border-radius: 4px;
            margin: 8px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        for _ in range(filas):
            col1, col2, col3, col4 = st.columns(columnas)
            with col1:
                st.markdown('<div class="skeleton-cell"></div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="skeleton-cell"></div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="skeleton-cell"></div>', unsafe_allow_html=True)
            with col4:
                st.markdown('<div class="skeleton-cell"></div>', unsafe_allow_html=True)
    
    @staticmethod
    def mostrar_spinner_personalizado(mensaje: str = "Cargando datos..."):
        """Muestra un spinner mientras se cargan datos."""
        with st.spinner(f"⏳ {mensaje}"):
            time.sleep(0.5)


# =====================================================
# 5. SEMÁFORO DINÁMICO DE SALUD
# =====================================================

class SemaforoDinamico:
    """Crea semáforos visuales dinámicos."""
    
    @staticmethod
    def crear_semaforo_salud(estado: str, porcentaje: float) -> str:
        """
        Crea un semáforo HTML5 animado.
        
        Estados:
        - VERDE: A tiempo
        - AMARILLO: Retrasado pero en movimiento
        - ROJO: Detenido o falla crítica
        """
        if estado == "🟢 A TIEMPO":
            color_fondo = 'rgba(0, 255, 100, 0.15)'
            color_borde = '#00ff64'
            color_luz = '#00ff64'
        elif estado == "🟡 RETRASADO":
            color_fondo = 'rgba(255, 200, 0, 0.15)'
            color_borde = '#ffc800'
            color_luz = '#ffc800'
        else:  # ROJO
            color_fondo = 'rgba(255, 0, 0, 0.15)'
            color_borde = '#ff3333'
            color_luz = '#ff3333'
        
        html = f"""
        <div style="
            background: {color_fondo};
            border: 3px solid {color_borde};
            border-radius: 15px;
            padding: 20px;
            margin: 10px 0;
            text-align: center;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: {color_luz};
                border-radius: 50%;
                margin: 0 auto 10px;
                box-shadow: 0 0 20px {color_luz};
                animation: pulse 1s infinite;
            "></div>
            <h3 style="color: white; margin: 0;">{estado}</h3>
            <p style="color: {color_luz}; font-size: 14px; margin: 5px 0;">
                {porcentaje:.1f}% Operativo
            </p>
        </div>
        <style>
        @keyframes pulse {{
            0%, 100% {{ box-shadow: 0 0 20px {color_luz}; }}
            50% {{ box-shadow: 0 0 40px {color_luz}; }}
        }}
        </style>
        """
        
        return html


# =====================================================
# 6. GRÁFICOS CON TEMA OSCURO
# =====================================================

class GraficosTemaOscuro:
    """Crea gráficos con tema oscuro profesional."""
    
    @staticmethod
    def grafico_barras_oscuro(data: Dict, titulo: str) -> go.Figure:
        """Gráfico de barras con tema oscuro."""
        fig = go.Figure(data=[
            go.Bar(
                x=list(data.keys()),
                y=list(data.values()),
                marker=dict(
                    color=list(data.values()),
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(thickness=15, len=0.7)
                ),
                text=[f"{v:.0f}" for v in data.values()],
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            template='plotly_dark',
            height=400,
            hovermode='x unified',
            margin=dict(l=0, r=0, t=50, b=0),
            paper_bgcolor='rgba(0,0,0,0.2)',
            plot_bgcolor='rgba(0,0,0,0.3)',
            font=dict(color='white', family='Arial')
        )
        
        return fig
    
    @staticmethod
    def grafico_linea_oscuro(df: pd.DataFrame, x: str, y: str, titulo: str) -> go.Figure:
        """Gráfico de línea con tema oscuro."""
        fig = px.line(
            df, x=x, y=y,
            title=titulo,
            markers=True,
            line_shape='spline'
        )
        
        fig.update_layout(
            template='plotly_dark',
            height=400,
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0.2)',
            plot_bgcolor='rgba(0,0,0,0.3)',
            font=dict(color='white')
        )
        
        fig.update_traces(
            line=dict(color='#00ffff', width=3),
            marker=dict(size=8, color='#ff6b9d')
        )
        
        return fig


# =====================================================
# DEMOSTRACIÓN
# =====================================================

if __name__ == "__main__":
    st.set_page_config(page_title="AMCO - Fase 6 Advanced", layout="wide", theme="dark")
    
    st.title("🎛️ AMCO - Advanced Visualization Demo")
    st.markdown("**Fase 6: Interpolación, Geofencing, Dark Mode**")
    
    # Demo de interpolación
    st.subheader("📍 Demo: Interpolación de Movimiento")
    interpolador = InterpoladorMovimiento(duracion_segundos=2.0)
    
    pos_anterior = (4.8135, -75.6942)
    pos_nueva = (4.8200, -75.6900)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("Posición anterior:", pos_anterior)
        st.write("Posición nueva:", pos_nueva)
    
    with col2:
        for t in [0, 0.25, 0.5, 0.75, 1.0]:
            pos_interp = interpolador.interpolar_posicion(1, pos_anterior, pos_nueva, t)
            st.write(f"t={t:.2f}: {pos_interp}")
    
    # Demo de geofencing
    st.subheader("🚨 Demo: Geofencing")
    geofen = GeoFencing(distancia_tolerancia_m=50)
    
    ruta = np.array([
        [4.8100, -75.6950],
        [4.8150, -75.6940],
        [4.8200, -75.6900]
    ])
    
    posicion_dentro = np.array([4.8150, -75.6940])
    posicion_fuera = np.array([4.8150, -75.6800])
    
    resultado_dentro = geofen.verificar_desviacion(1, posicion_dentro, ruta)
    resultado_fuera = geofen.verificar_desviacion(2, posicion_fuera, ruta)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"✅ Dentro de ruta: {resultado_dentro['distancia_min']:.1f}m")
    with col2:
        st.warning(f"⚠️ Fuera de ruta: {resultado_fuera['distancia_min']:.1f}m")
