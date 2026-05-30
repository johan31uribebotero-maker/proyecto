import streamlit as st
import pandas as pd
import numpy as np
import requests
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sqlite3

# ==========================================
# CONFIGURACIÓN STREAMLIT
# ==========================================

st.set_page_config(
    page_title="AMCO Dashboard Pro - Fase 5",
    layout="wide",
    initial_sidebar_state="expanded",
    theme="dark"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1a1f3a 100%);
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .heatmap-container {
        background: rgba(0,0,0,0.3);
        border-radius: 10px;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# RUTAS HARDCODEADAS (DEMO)
# ==========================================

RUTAS_METRO = [
    {
        'nombre': 'Ruta A - Circunvalar',
        'path': [[-75.7310, 4.7915], [-75.7200, 4.8000], [-75.7050, 4.8070], [-75.6942, 4.8135]],
        'color': [0, 255, 100]
    },
    {
        'nombre': 'Ruta B - Centro',
        'path': [[-75.6942, 4.8135], [-75.6910, 4.8140], [-75.6898, 4.8174]],
        'color': [100, 200, 255]
    },
    {
        'nombre': 'Ruta C - Norte',
        'path': [[-75.6942, 4.8135], [-75.6920, 4.8070], [-75.6885, 4.7945]],
        'color': [255, 150, 0]
    },
    {
        'nombre': 'Ruta D - Periferia',
        'path': [[-75.6942, 4.8135], [-75.6700, 4.8300], [-75.6500, 4.8500], [-75.6231, 4.8707]],
        'color': [255, 50, 50]
    }
]

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

@st.cache_data(ttl=2)
def obtener_telemetria():
    """Obtiene datos de telemetría del API"""
    try:
        response = requests.get('http://127.0.0.1:8000/telemetria', timeout=2)
        df = pd.DataFrame(response.json())
        
        # Limpiar datos GPS
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon'])
        
        return df[
            (df['lat'] >= 4.75) & (df['lat'] <= 5.40) &
            (df['lon'] >= -76.10) & (df['lon'] <= -75.50)
        ]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=5)
def obtener_congestion():
    """Obtiene datos de congestión por ruta"""
    try:
        response = requests.get('http://127.0.0.1:8000/congestión/por-ruta', timeout=2)
        return response.json()
    except:
        return {"congestiones": {}}

@st.cache_data(ttl=5)
def obtener_salud_flota():
    """Obtiene salud general de la flota"""
    try:
        response = requests.get('http://127.0.0.1:8000/salud/flota', timeout=2)
        return response.json()
    except:
        return {}

@st.cache_data(ttl=3)
def obtener_mapa_calor():
    """Obtiene mapa de calor de paradas"""
    try:
        response = requests.get('http://127.0.0.1:8000/mapa-calor/paradas', timeout=2)
        return response.json()
    except:
        return {"mapa_calor": []}

@st.cache_data(ttl=5)
def obtener_alertas():
    """Obtiene alertas activas"""
    try:
        response = requests.get('http://127.0.0.1:8000/alertas/activas', timeout=2)
        return response.json()
    except:
        return {"alertas": []}

def calcular_estado_salud(row):
    """Calcula estado de salud basado en velocidad"""
    if row['vel'] < 5:
        return '🔴 DETENIDO'
    elif row['vel'] < 20:
        return '🟡 LENTO'
    else:
        return '🟢 NORMAL'

# ==========================================
# HEADER Y NAVEGACIÓN
# ==========================================

st.title('🎛️ Centro Inteligente Metropolitano AMCO')
st.markdown('**FASE 4 & 5: Dashboard Avanzado con Mapas de Calor y Semáforos**')

# Sidebar
st.sidebar.markdown('## ⚙️ Control Central')
refresh_rate = st.sidebar.radio(
    "🔄 Velocidad de actualización",
    ["Manual", "2 segundos", "5 segundos"],
    index=1
)

view_mode = st.sidebar.radio(
    "📊 Vista",
    ["🗺️ Mapa en Tiempo Real", "🔥 Mapa de Calor", "🚦 Semáforo de Congestión", "📈 Analytics"]
)

# ==========================================
# VISTA 1: MAPA EN TIEMPO REAL
# ==========================================

if view_mode == "🗺️ Mapa en Tiempo Real":
    
    @st.fragment(run_every='2s' if refresh_rate == "2 segundos" else ('5s' if refresh_rate == "5 segundos" else None))
    def render_mapa_realtime():
        
        df = obtener_telemetria()
        
        if df.empty:
            st.warning('⏳ Esperando telemetría... Asegúrate que el IoT Simulator está activo')
            return
        
        df['estado_ruta'] = df.apply(calcular_estado_salud, axis=1)
        
        # Métricas superiores
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric('🚌 Flota Activa', len(df), delta=f"{len(df)} buses")
        with col2:
            st.metric('👥 Pasajeros', int(df['pasajeros'].sum()), delta=f"+{int(df['pasajeros'].sum())} pax")
        with col3:
            st.metric('⚡ Vel. Promedio', f"{df['vel'].mean():.1f} km/h", delta=f"{df['vel'].std():.1f}σ")
        with col4:
            st.metric('🔋 Energía Promedio', f"{df['bateria_gasolina'].mean():.1f}%", delta=f"Min: {df['bateria_gasolina'].min():.0f}%")
        with col5:
            st.metric('📍 Cobertura GPS', f"{len(df)}/{len(df)} buses", delta="100% cobertura")
        
        st.divider()
        
        # Mapa 3D con capas
        left, right = st.columns([2.5, 1.2])
        
        with left:
            st.markdown('### 🗺️ Mapa 3D Interactivo - Flota y Rutas')
            
            # Construir capas
            layers = []
            
            # Capa 1: Rutas (PathLayer)
            for ruta_info in RUTAS_METRO:
                rutas_df = pd.DataFrame([{'path': ruta_info['path']}])
                layers.append(
                    pdk.Layer(
                        'PathLayer',
                        rutas_df,
                        get_path='path',
                        get_width=5,
                        get_color=ruta_info['color']
                    )
                )
            
            # Capa 2: Mapa de calor hexagonal (HexagonLayer)
            layers.append(
                pdk.Layer(
                    'HexagonLayer',
                    df,
                    get_position=['lon', 'lat'],
                    radius=250,
                    elevation_scale=12,
                    extruded=True,
                    pickable=True,
                    color_range=[
                        [0, 255, 100],      # Verde - bajo
                        [255, 200, 0],      # Amarillo
                        [255, 100, 0],      # Naranja
                        [255, 0, 0]         # Rojo - alto
                    ]
                )
            )
            
            # Capa 3: Buses (ScatterplotLayer)
            layers.append(
                pdk.Layer(
                    'ScatterplotLayer',
                    df,
                    get_position=['lon', 'lat'],
                    get_radius=100,
                    get_fill_color=[100, 200, 255],
                    pickable=True,
                    transitions={'getPosition': {'type': 'spring', 'stiffness': 0.03, 'damping': 0.4}}
                )
            )
            
            # Renderizar mapa
            st.pydeck_chart(
                pdk.Deck(
                    map_style='dark',
                    map_provider='carto',
                    initial_view_state=pdk.ViewState(
                        latitude=4.8135,
                        longitude=-75.6942,
                        zoom=11.5,
                        pitch=55
                    ),
                    layers=layers,
                    tooltip={'text': 'Bus {vehiculo_id}\nPasajeros: {pasajeros}\nVelocidad: {vel} km/h\nBatería: {bateria_gasolina}%'}
                )
            )
        
        with right:
            st.markdown('### 🎯 Estado Operativo')
            
            salud = df['estado_ruta'].value_counts()
            fig_salud = go.Figure(data=[
                go.Bar(y=salud.index, x=salud.values, orientation='h', marker_color=['#00ff64', '#ffc800', '#ff3333'])
            ])
            fig_salud.update_layout(
                height=250,
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_salud, use_container_width=True)
            
            st.markdown('### ⚡ Energía por Motor')
            energia = df.groupby('tipo_motor')['bateria_gasolina'].mean()
            fig_energia = px.bar(
                x=energia.index, y=energia.values,
                color=energia.values,
                color_continuous_scale=['#ff3333', '#ffc800', '#00ff64']
            )
            fig_energia.update_layout(
                height=250,
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_energia, use_container_width=True)
        
        # Tabla de datos
        st.divider()
        
        tabla_col1, tabla_col2 = st.columns(2)
        
        with tabla_col1:
            st.markdown('### 📋 Flota en Tiempo Real')
            st.dataframe(
                df[['vehiculo_id', 'tipo_motor', 'pasajeros', 'vel', 'bateria_gasolina', 'estado_ruta']]
                .rename(columns={'vehiculo_id': 'Bus ID', 'tipo_motor': 'Motor', 'pasajeros': 'Pax', 'vel': 'Vel (km/h)', 'bateria_gasolina': 'Energía %', 'estado_ruta': 'Estado'}),
                use_container_width=True,
                hide_index=True,
                height=400
            )
        
        with tabla_col2:
            st.markdown('### ⚠️ Alertas Activas')
            alertas = obtener_alertas()
            if alertas.get('alertas'):
                alertas_df = pd.DataFrame(alertas['alertas'][:10])
                st.dataframe(
                    alertas_df[['vehiculo_id', 'tipo_alerta', 'severidad', 'descripcion']],
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            else:
                st.info('✅ Sin alertas activas')
    
    render_mapa_realtime()

# ==========================================
# VISTA 2: MAPA DE CALOR
# ==========================================

elif view_mode == "🔥 Mapa de Calor":
    
    @st.fragment(run_every='3s' if refresh_rate == "2 segundos" else ('5s' if refresh_rate == "5 segundos" else None))
    def render_heatmap():
        
        datos_calor = obtener_mapa_calor()
        paradas = datos_calor.get('mapa_calor', [])
        
        if not paradas:
            st.warning('⏳ Cargando datos de paradas...')
            return
        
        st.markdown('### 🔥 Mapa de Calor de Demanda en Paradas')
        st.markdown('*Intensidad de calor = personas esperando en cada parada*')
        
        paradas_df = pd.DataFrame(paradas)
        max_personas = datos_calor.get('max_personas', 1)
        
        # Preparar datos para mapa
        map_data = pd.DataFrame([
            {
                'latitude': p['latitud'],
                'longitude': p['longitud'],
                'intensity': p['intensidad'],
                'personas': p['personas_esperando'],
                'nombre': p['nombre']
            }
            for p in paradas
        ])
        
        # Mapa de calor con Pydeck
        heatmap_layer = pdk.Layer(
            'HeatmapLayer',
            map_data,
            get_position=['longitude', 'latitude'],
            radiusPixels=50,
            getWeight='intensity',
            extruded=False,
            pickable=True
        )
        
        st.pydeck_chart(
            pdk.Deck(
                map_style='dark',
                map_provider='carto',
                initial_view_state=pdk.ViewState(
                    latitude=4.8135,
                    longitude=-75.6942,
                    zoom=12,
                    pitch=30
                ),
                layers=[heatmap_layer],
                tooltip={'text': '{nombre}\nPersonas: {personas}'}
            ),
            height=500
        )
        
        st.divider()
        
        # Gráficos de análisis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('### 📊 Top 10 Paradas - Mayor Demanda')
            top_paradas = paradas_df.nlargest(10, 'personas_esperando')
            fig = px.bar(
                top_paradas,
                x='personas_esperando',
                y='nombre',
                orientation='h',
                color='personas_esperando',
                color_continuous_scale='Hot'
            )
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('### 🎨 Distribución de Intensidad')
            fig = go.Figure(data=[
                go.Histogram(
                    x=paradas_df['personas_esperando'],
                    nbinsx=15,
                    marker_color='rgba(255, 100, 0, 0.7)'
                )
            ])
            fig.update_layout(
                title='Histograma de Personas Esperando',
                xaxis_title='Personas',
                yaxis_title='Frecuencia',
                height=400,
                margin=dict(l=0, r=0, t=50, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabla detallada
        st.markdown('### 📋 Detalle de Paradas')
        st.dataframe(
            paradas_df[['nombre', 'personas_esperando', 'intensidad', 'categoria']]
            .sort_values('personas_esperando', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    render_heatmap()

# ==========================================
# VISTA 3: SEMÁFORO DE CONGESTIÓN
# ==========================================

elif view_mode == "🚦 Semáforo de Congestión":
    
    @st.fragment(run_every='3s' if refresh_rate == "2 segundos" else ('5s' if refresh_rate == "5 segundos" else None))
    def render_semaforo():
        
        datos_congestion = obtener_congestion()
        datos_salud = obtener_salud_flota()
        
        # Header de salud general
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown('### 🏥 Salud General Flota')
            if datos_salud:
                salud_general = datos_salud.get('salud_general', '❓ N/A')
                porcentaje_verde = datos_salud.get('porcentaje_verde', 0)
                st.metric('Estado', salud_general, f"{porcentaje_verde}% operativo")
                
                estados = datos_salud.get('estados_resumido', {})
                fig = go.Figure(data=[
                    go.Pie(
                        labels=['🟢 Verde', '🟡 Amarillo', '🔴 Rojo'],
                        values=[estados.get('VERDE', 0), estados.get('AMARILLO', 0), estados.get('ROJO', 0)],
                        marker=dict(colors=['#00ff64', '#ffc800', '#ff3333'])
                    )
                ])
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('### 🚌 Flota por Estado')
            if datos_salud:
                detalle_buses = datos_salud.get('detalle_buses', [])
                estados_count = {}
                for bus in detalle_buses:
                    estado = bus['estado']
                    estados_count[estado] = estados_count.get(estado, 0) + 1
                
                st.metric('Total Buses', len(detalle_buses))
                for estado, count in estados_count.items():
                    st.write(f"{estado}: {count} buses")
        
        with col3:
            st.markdown('### ⏰ Último Refresco')
            st.metric('Timestamp', datetime.now().strftime("%H:%M:%S"))
        
        st.divider()
        
        # Semáforos por ruta
        st.markdown('### 🚦 Semáforo de Congestión por Ruta')
        
        congestiones = datos_congestion.get('congestiones', {})
        
        if congestiones:
            # Crear grid de semáforos
            cols = st.columns(2)
            
            for idx, (nombre_ruta, datos_ruta) in enumerate(sorted(congestiones.items())):
                with cols[idx % 2]:
                    congestion_pct = datos_ruta.get('congestion_porcentaje', 0)
                    estado = datos_ruta.get('estado', 'N/A')
                    
                    # Semáforo visual
                    if '🟢' in estado:
                        color = '#00ff64'
                        fondo = 'rgba(0, 255, 100, 0.1)'
                    elif '🟡' in estado:
                        color = '#ffc800'
                        fondo = 'rgba(255, 200, 0, 0.1)'
                    else:
                        color = '#ff3333'
                        fondo = 'rgba(255, 50, 50, 0.1)'
                    
                    st.markdown(f"""
                    <div style="background: {fondo}; border: 2px solid {color}; border-radius: 10px; padding: 15px; margin: 10px 0;">
                        <h4 style="color: white; margin: 0;">{nombre_ruta}</h4>
                        <p style="color: {color}; font-size: 20px; margin: 10px 0;">{estado}</p>
                        <p style="color: white; margin: 5px 0;">
                            <strong>Congestión:</strong> {congestion_pct}% 
                            ({datos_ruta.get('pasajeros_total', 0)}/{datos_ruta.get('capacidad_total', 0)} pax)
                        </p>
                        <p style="color: white; margin: 5px 0;">
                            <strong>Buses:</strong> {datos_ruta.get('num_buses', 0)} en operación
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Gráfico de comparación
            st.divider()
            st.markdown('### 📊 Comparativa de Congestión')
            
            rutas_lista = list(congestiones.keys())
            congestion_valores = [c.get('congestion_porcentaje', 0) for c in congestiones.values()]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=rutas_lista,
                    y=congestion_valores,
                    marker=dict(
                        color=congestion_valores,
                        colorscale='RdYlGn_r',
                        showscale=True
                    )
                )
            ])
            fig.update_layout(
                title='Porcentaje de Congestión por Ruta',
                xaxis_title='Ruta',
                yaxis_title='Congestión %',
                height=400,
                margin=dict(l=0, r=0, t=50, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning('⏳ Cargando datos de congestión...')
    
    render_semaforo()

# ==========================================
# VISTA 4: ANALYTICS
# ==========================================

elif view_mode == "📈 Analytics":
    
    @st.fragment(run_every='5s' if refresh_rate == "2 segundos" else ('10s' if refresh_rate == "5 segundos" else None))
    def render_analytics():
        
        df = obtener_telemetria()
        datos_salud = obtener_salud_flota()
        
        if df.empty:
            st.warning('⏳ Esperando datos de telemetría...')
            return
        
        st.markdown('### 📈 Análisis Detallado de Flota')
        
        tab1, tab2, tab3, tab4 = st.tabs(['🚌 Rendimiento', '⚡ Energía', '👥 Pasajeros', '🎯 Alertas'])
        
        with tab1:
            st.markdown('#### Velocidad y Rendimiento')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Vel. Promedio', f"{df['vel'].mean():.1f} km/h", f"Max: {df['vel'].max():.0f}")
            with col2:
                st.metric('Vel. Mínima', f"{df['vel'].min():.1f} km/h", f"Buses detenidos: {(df['vel'] < 5).sum()}")
            with col3:
                st.metric('Desv. Estándar', f"{df['vel'].std():.1f} km/h")
            
            # Gráfico de distribución
            fig = px.histogram(df, x='vel', nbins=20, title='Distribución de Velocidades',
                              color_discrete_sequence=['#00ff64'])
            fig.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown('#### Análisis de Energía')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Energía Promedio', f"{df['bateria_gasolina'].mean():.1f}%")
            with col2:
                st.metric('Energía Crítica', f"{(df['bateria_gasolina'] < 15).sum()} buses")
            with col3:
                st.metric('Energía Aceptable', f"{((df['bateria_gasolina'] >= 30) & (df['bateria_gasolina'] <= 70)).sum()} buses")
            
            # Gráfico por motor
            fig = px.box(df, x='tipo_motor', y='bateria_gasolina', title='Energía por Tipo de Motor',
                        color='tipo_motor')
            fig.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.markdown('#### Capacidad y Ocupación')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Pasajeros Total', int(df['pasajeros'].sum()))
            with col2:
                st.metric('Promedio por Bus', f"{df['pasajeros'].mean():.1f}")
            with col3:
                st.metric('Bus Lleno', f"{(df['pasajeros'] > 80).sum()} buses")
            
            # Scatter plot
            fig = px.scatter(df, x='pasajeros', y='vel', size='bateria_gasolina',
                           color='tipo_motor', title='Relación: Pasajeros vs Velocidad',
                           hover_data=['vehiculo_id', 'placa'])
            fig.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            st.markdown('#### Alertas y Problemas')
            alertas = obtener_alertas()
            
            if alertas.get('alertas'):
                alertas_df = pd.DataFrame(alertas['alertas'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric('Alertas Totales', len(alertas_df))
                with col2:
                    criticas = (alertas_df['severidad'] == '🔴 CRÍTICA').sum()
                    st.metric('Críticas', criticas)
                with col3:
                    info = (alertas_df['severidad'] != '🔴 CRÍTICA').sum()
                    st.metric('Informativas', info)
                
                # Tabla de alertas
                st.dataframe(
                    alertas_df[['vehiculo_id', 'tipo_alerta', 'descripcion', 'severidad']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success('✅ Sin alertas activas')
    
    render_analytics()

# ==========================================
# FOOTER
# ==========================================

st.divider()
st.markdown("""
---
<div style="text-align: center; color: #888; font-size: 12px;">
    <p>🚌 <strong>AMCO - Centro Inteligente Metropolitano</strong></p>
    <p>Fase 5: Dashboard Avanzado con Mapas de Calor y Semáforos de Congestión</p>
    <p>Actualización: 30/05/2026 | API: FastAPI 7.0 | DB: SQLite</p>
</div>
""", unsafe_allow_html=True)
