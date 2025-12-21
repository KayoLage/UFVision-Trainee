import cv2
import numpy as np

# --- CONFIGURAÇÕES DE KERNEL --- #
MORPHOLOGY_KERNEL = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)) 
BLUR_KERNEL = 7 # Tamanho do kernel deve ser ímpar (3, 5, 7, ...)

# --- THRESHOLDS DE CONTAGEM DE PIXELS --- #
THRESHOLD_PIXELS = 15000     # Azul, Vermelho, Amarelo (no geral não precisa ser ajustado)
THRESHOLD_ORANGE = 40000     # Laranja (no geral não precisa ser ajustado)
THRESHOLD_BLACK  = 30000     # Preto => Aumente se houver muitos objetos pretos que não são o de interesse na cena
THRESHOLD_BROWN  = 50000    # Marrom => Aumente se houver muitos objetos marrons que não são o de interesse na cena

# --- ÁREAS MÍNIMAS --- #
AREA_MINIMA_RUIDO = 10000        # Para filtrar contornos pequenos
THRESHOLD_AREA_MIN_REMOVE_CC = 30000 # Para a função remove_componentes
THRESHOLD_AREA_MAX_REMOVE_CC = None # Caso houver objetos muito grandes que não são o de interesse pode ser interessante

# --- RANGES HSV --- #
RANGES = {
    # Cores "Fáceis"
    "Blue":   (np.array([25, 100, 0]), np.array([140, 255, 255])),
    "Red":    (np.array([125, 100, 40]), np.array([179, 255, 255])),
    "Yellow": (np.array([15, 45, 105]), np.array([30, 255, 255])),
    
    # Cores "Difíceis"
    "Orange": (np.array([0, 180, 100]), np.array([179, 255, 255])), 
    "Brown":  (np.array([0, 100, 0]), np.array([179, 255, 125])), 
    "Black":  (np.array([0, 0, 0]), np.array([179, 255, 80]))
}