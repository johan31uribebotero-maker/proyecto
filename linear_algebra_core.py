"""
LINEAR ALGEBRA CORE - Trabajo Final de Semestre
===============================================
Implementa operaciones de álgebra lineal pura para:
- Cálculos de distancias (norma de vectores)
- Análisis de conectividad (eigenvalores, autovectores)
- Algoritmo de Dijkstra con matrices ponderadas
- Descomposición SVD para análisis de congestión

Autor: AMCO System
Asignatura: Álgebra Lineal Aplicada
"""

import numpy as np
from scipy.linalg import eig, svd
from scipy.spatial.distance import cdist
from typing import Tuple, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlgebraLinealTransporte:
    """
    Motor de álgebra lineal para análisis de redes de transporte.
    Utiliza operaciones matriciales para optimización de rutas.
    """
    
    def __init__(self):
        self.matriz_adyacencia = None
        self.matriz_distancias = None
        self.coordenadas_paradas = None
        
    # ===============================================
    # 1. NORMAS Y DISTANCIAS EUCLIDIANAS
    # ===============================================
    
    @staticmethod
    def calcular_distancia_euclidiana(p1: np.ndarray, p2: np.ndarray) -> float:
        """
        Calcula la distancia euclidiana entre dos puntos.
        
        ||v|| = sqrt(sum((x2-x1)^2 + (y2-y1)^2))
        
        Args:
            p1: Punto 1 [lat, lon]
            p2: Punto 2 [lat, lon]
            
        Returns:
            Distancia en metros (aproximada)
        """
        diferencia = np.array(p2) - np.array(p1)
        
        # Convertir a metros (aproximado: 1 grado ≈ 111 km)
        diferencia_m = diferencia * 111000
        
        # Norma L2: sqrt(x^2 + y^2)
        distancia = np.linalg.norm(diferencia_m)
        
        return distancia
    
    @staticmethod
    def calcular_distancia_manhattan(p1: np.ndarray, p2: np.ndarray) -> float:
        """
        Distancia Manhattan (taxicab): |x2-x1| + |y2-y1|
        Útil para grillas urbanas.
        """
        diferencia = np.array(p2) - np.array(p1)
        diferencia_m = diferencia * 111000
        
        # Norma L1: sum(|x| + |y|)
        distancia = np.linalg.norm(diferencia_m, ord=1)
        
        return distancia
    
    # ===============================================
    # 2. MATRIZ DE DISTANCIAS (USANDO NORMAS)
    # ===============================================
    
    def construir_matriz_distancias(self, coordenadas: np.ndarray) -> np.ndarray:
        """
        Construye matriz de distancias entre todos los puntos.
        
        Entrada: matriz n×2 de coordenadas [lat, lon]
        Salida: matriz n×n de distancias
        
        Formula: D[i,j] = ||p_i - p_j||_2
        """
        self.coordenadas_paradas = coordenadas
        
        # Usar scipy para cálculo eficiente (versión vectorizada)
        coordenadas_m = coordenadas * 111000  # Convertir a metros
        
        # cdist calcula todas las distancias de forma matricial
        self.matriz_distancias = cdist(coordenadas_m, coordenadas_m, metric='euclidean')
        
        logger.info(f"Matriz de distancias construida: {self.matriz_distancias.shape}")
        
        return self.matriz_distancias
    
    # ===============================================
    # 3. ANÁLISIS DE AUTOVALORES (CENTRALIDAD)
    # ===============================================
    
    def calcular_centralidad_eigenvector(self, matriz_adyacencia: np.ndarray) -> Dict:
        """
        Calcula centralidad de eigenvector de la red.
        
        Las paradas más importantes tienen autovectores más grandes.
        Util para identificar HUBS de transporte.
        
        Formula: A*v = λ*v
        donde A es la matriz de adyacencia y v es el autovector.
        """
        self.matriz_adyacencia = matriz_adyacencia
        
        try:
            # Obtener autovalores y autovectores
            autovalores, autovectores = eig(matriz_adyacencia)
            
            # El autovector del mayor autovalor es la centralidad
            indice_max = np.argmax(np.real(autovalores))
            centralidad = np.abs(np.real(autovectores[:, indice_max]))
            
            # Normalizar a [0, 1]
            centralidad = centralidad / np.max(centralidad)
            
            return {
                'centralidad': centralidad,
                'autovalor_dominante': np.real(autovalores[indice_max]),
                'paradas_hub': np.argsort(centralidad)[::-1][:5]  # Top 5
            }
        except Exception as e:
            logger.error(f"Error en cálculo de autovalores: {e}")
            return {}
    
    # ===============================================
    # 4. DIJKSTRA CON MATRICES
    # ===============================================
    
    def dijkstra_matricial(self, origen: int, destino: int, 
                          matriz_distancias: np.ndarray) -> Tuple[float, List[int]]:
        """
        Implementa algoritmo de Dijkstra usando matrices.
        
        Complejidad: O(n²) con operaciones matriciales.
        
        Args:
            origen: índice de parada origen
            destino: índice de parada destino
            matriz_distancias: matriz n×n de distancias
            
        Returns:
            (distancia_total, camino_ids)
        """
        n = len(matriz_distancias)
        
        # Inicializar vectores
        distancias = np.full(n, np.inf)
        distancias[origen] = 0
        padres = np.full(n, -1, dtype=int)
        visitados = np.zeros(n, dtype=bool)
        
        # Algoritmo de Dijkstra (versión vectorizada)
        for _ in range(n):
            # Encontrar nodo no visitado con menor distancia (operación matricial)
            u = np.argmin(distancias + visitados * np.inf)
            
            if visitados[u] or distancias[u] == np.inf:
                break
            
            visitados[u] = True
            
            # Actualizar distancias (operación vectorial)
            nuevas_distancias = distancias[u] + matriz_distancias[u, :]
            actualizacion = nuevas_distancias < distancias
            
            distancias = np.where(actualizacion, nuevas_distancias, distancias)
            padres = np.where(actualizacion, u, padres)
        
        # Reconstruir camino
        camino = []
        actual = destino
        while actual != -1:
            camino.append(actual)
            actual = padres[actual]
        camino.reverse()
        
        return distancias[destino], camino
    
    # ===============================================
    # 5. DESCOMPOSICIÓN SVD PARA CONGESTIÓN
    # ===============================================
    
    def analizar_congestión_svd(self, matriz_flujo: np.ndarray) -> Dict:
        """
        Usa SVD para analizar patrones de flujo de pasajeros.
        
        Descomposición: M = U * Σ * V^T
        - U: direcciones principales de flujo
        - Σ: importancia de cada dirección
        - V^T: características de las paradas
        
        Args:
            matriz_flujo: matriz m×n de flujos (pasajeros por ruta)
            
        Returns:
            Análisis de componentes principales del flujo
        """
        try:
            U, valores_singulares, Vt = svd(matriz_flujo, full_matrices=False)
            
            # Varianza explicada por cada componente
            varianza_total = np.sum(valores_singulares ** 2)
            varianza_explicada = (valores_singulares ** 2) / varianza_total
            
            return {
                'componentes_principales': U[:, :3],  # Top 3 componentes
                'valores_singulares': valores_singulares[:3],
                'varianza_explicada': varianza_explicada[:3],
                'varianza_acumulada': np.cumsum(varianza_explicada[:3]),
                'interpretacion': 'Los mayores σ indican patrones dominantes de flujo'
            }
        except Exception as e:
            logger.error(f"Error en SVD: {e}")
            return {}
    
    # ===============================================
    # 6. PROYECCIÓN A LÍNEA (SNAP-TO-ROAD)
    # ===============================================
    
    @staticmethod
    def proyectar_punto_a_segmento(punto: np.ndarray, 
                                   p1: np.ndarray, 
                                   p2: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Proyecta un punto a su línea más cercana en un segmento.
        
        Usa proyección vectorial:
        proyección = p1 + t*(p2-p1)
        donde t = ((p-p1)·(p2-p1)) / ||p2-p1||²
        
        Args:
            punto: [lat, lon] a proyectar
            p1: inicio del segmento
            p2: fin del segmento
            
        Returns:
            (punto_proyectado, distancia_perpendicular)
        """
        # Vectores
        v = np.array(p2) - np.array(p1)  # Dirección del segmento
        w = np.array(punto) - np.array(p1)  # Vector del punto al inicio
        
        # Parámetro t (proyección)
        t = np.dot(w, v) / np.dot(v, v)
        t = np.clip(t, 0, 1)  # Limitar a [0, 1]
        
        # Punto proyectado
        proyeccion = np.array(p1) + t * v
        
        # Distancia perpendicular (usando norma)
        distancia = np.linalg.norm(np.array(punto) - proyeccion)
        
        return proyeccion, distancia
    
    @staticmethod
    def snap_to_road(punto: np.ndarray, 
                    ruta_puntos: np.ndarray,
                    distancia_max_m: float = 20) -> Tuple[np.ndarray, bool]:
        """
        Ajusta un punto GPS a la ruta más cercana (snap-to-road).
        
        Busca el segmento de ruta más cercano y proyecta el punto.
        Retorna el punto ajustado si está dentro de distancia_max_m.
        
        Args:
            punto: [lat, lon] a ajustar
            ruta_puntos: lista de [lat, lon] que definen la ruta
            distancia_max_m: distancia máxima permitida en metros
            
        Returns:
            (punto_ajustado, ajuste_aplicado)
        """
        mejor_proyeccion = punto
        mejor_distancia = np.inf
        
        # Probar cada segmento de la ruta
        for i in range(len(ruta_puntos) - 1):
            proyeccion, distancia = AlgebraLinealTransporte.proyectar_punto_a_segmento(
                punto, ruta_puntos[i], ruta_puntos[i + 1]
            )
            
            if distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_proyeccion = proyeccion
        
        # Ajustar solo si está dentro del rango
        if mejor_distancia <= (distancia_max_m / 111000):  # Convertir metros a grados
            return mejor_proyeccion, True
        else:
            return punto, False
    
    # ===============================================
    # 7. ANÁLISIS DE MATRIZ DE CONECTIVIDAD
    # ===============================================
    
    def calcular_rango_matriz(self, matriz: np.ndarray) -> int:
        """
        Calcula el rango de una matriz (información sobre conectividad).
        
        Rango = número de filas/columnas linealmente independientes
        Indica el número de "subredes" conectadas.
        """
        return np.linalg.matrix_rank(matriz)
    
    def calcular_determinante(self, matriz: np.ndarray) -> float:
        """
        Calcula el determinante (inversibilidad de la matriz).
        det = 0 → Matriz singular (red desconectada)
        det ≠ 0 → Matriz regular (red conectada)
        """
        return np.linalg.det(matriz)
    
    def calcular_condicion_matriz(self, matriz: np.ndarray) -> float:
        """
        Número de condición: mide estabilidad numérica.
        κ = ||M|| * ||M^-1||
        
        κ alto → Pequeños errores en entrada causan grandes errores en salida
        κ bajo → Sistema bien condicionado
        """
        return np.linalg.cond(matriz)

# ===============================================
# PRUEBAS Y DEMO
# ===============================================

if __name__ == "__main__":
    # Crear instancia
    motor = AlgebraLinealTransporte()
    
    # Coordenadas de ejemplo (paradas reales de Pereira)
    coordenadas = np.array([
        [4.8135, -75.6942],  # Centro
        [4.8200, -75.6900],  # Norte
        [4.8050, -75.6950],  # Sur
        [4.8150, -75.7000],  # Oeste
    ])
    
    # Construir matriz de distancias
    matriz_dist = motor.construir_matriz_distancias(coordenadas)
    print("Matriz de distancias (metros):")
    print(matriz_dist)
    
    # Calcular Dijkstra
    distancia, camino = motor.dijkstra_matricial(0, 3, matriz_dist)
    print(f"\nDistancia de 0→3: {distancia:.2f}m, Camino: {camino}")
    
    # Proyección
    punto_gps = np.array([4.815, -75.695])
    ruta = coordenadas[:3]
    punto_ajustado, ajustado = motor.snap_to_road(punto_gps, ruta)
    print(f"\nPunto original: {punto_gps}")
    print(f"Punto ajustado: {punto_ajustado}")
    print(f"Ajuste aplicado: {ajustado}")
