import cv2
import numpy as np
import os
import sys

# Adiciona o diretório atual ao path para encontrar o arquivo vision.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vision # Importa seu módulo com as funções de morfologia

def nothing(x):
    pass

# Inicializa a captura da webcam
cap = cv2.VideoCapture(0)

# Cria uma janela para os controles
cv2.namedWindow("Calibrador LAB + Blur + Morfologia")
cv2.resizeWindow("Calibrador LAB + Blur + Morfologia", 400, 550)

# --- TRACKBARS LAB ---
cv2.createTrackbar("L Min", "Calibrador LAB + Blur + Morfologia", 0, 255, nothing)
cv2.createTrackbar("A Min", "Calibrador LAB + Blur + Morfologia", 0, 255, nothing)
cv2.createTrackbar("B Min", "Calibrador LAB + Blur + Morfologia", 0, 255, nothing)

cv2.createTrackbar("L Max", "Calibrador LAB + Blur + Morfologia", 255, 255, nothing)
cv2.createTrackbar("A Max", "Calibrador LAB + Blur + Morfologia", 255, 255, nothing)
cv2.createTrackbar("B Max", "Calibrador LAB + Blur + Morfologia", 255, 255, nothing)

# --- TRACKBAR DE BLUR ---
# Começa com 2 (que vira 5 no cálculo 2*x+1)
cv2.createTrackbar("Blur Size", "Calibrador LAB + Blur + Morfologia", 4, 10, nothing) 

print("--- CALIBRADOR COMPLETO (LAB + BLUR + MORFOLOGIA) ---")
print("1. Ajuste o 'Blur Size' para limpar ruído granulado.")
print("2. Ajuste L, A, B. Note que a máscara será limpa automaticamente.")
print("Pressione 'q' para sair.")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    # -----------------------------------------------------------
    # 1. TRATAMENTO DE IMAGEM (MEDIAN BLUR)
    # -----------------------------------------------------------
    k = cv2.getTrackbarPos("Blur Size", "Calibrador LAB + Blur + Morfologia")
    k = (k * 2) + 1 # Garante ímpar (1, 3, 5, 7...)
    
    # Aplica o blur para limpar "sujeira" antes de detectar cor
    frame_blurred = cv2.medianBlur(frame, k)
    
    # -----------------------------------------------------------
    # 2. CONVERSÃO E MÁSCARA (LAB)
    # -----------------------------------------------------------
    lab = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2Lab)

    l_min = cv2.getTrackbarPos("L Min", "Calibrador LAB + Blur + Morfologia")
    a_min = cv2.getTrackbarPos("A Min", "Calibrador LAB + Blur + Morfologia")
    b_min = cv2.getTrackbarPos("B Min", "Calibrador LAB + Blur + Morfologia")
    
    l_max = cv2.getTrackbarPos("L Max", "Calibrador LAB + Blur + Morfologia")
    a_max = cv2.getTrackbarPos("A Max", "Calibrador LAB + Blur + Morfologia")
    b_max = cv2.getTrackbarPos("B Max", "Calibrador LAB + Blur + Morfologia")

    lower = np.array([l_min, a_min, b_min])
    upper = np.array([l_max, a_max, b_max])

    # Cria a máscara bruta
    mask_raw = cv2.inRange(lab, lower, upper)
    
    # -----------------------------------------------------------
    # 3. PROCESSAMENTO MORFOLÓGICO (IMPORTADO DO VISION.PY)
    # -----------------------------------------------------------
    # Aqui usamos exatamente a mesma função que o robô usará.
    # Se funcionar aqui, funcionará no voo.
    mask_final = vision.processar_mascara_completa(mask_raw)
    
    # -----------------------------------------------------------
    # 4. CONTAGEM E VISUALIZAÇÃO
    # -----------------------------------------------------------
    qtd_pixels = cv2.countNonZero(mask_final)

    # Converte máscara para colorido (para podermos escrever texto colorido nela)
    mask_visualizacao = cv2.cvtColor(mask_final, cv2.COLOR_GRAY2BGR)

    THRESHOLD_PIXELS = 15000 # Seu limiar de detecção
    
    if qtd_pixels > THRESHOLD_PIXELS:
        cor_texto = (0, 255, 0) # Verde (BGR)
        status = "DETECTADO"
    else:
        cor_texto = (0, 0, 255) # Vermelho (BGR)
        status = "RUIDO / MUITO LONGE"

    texto = f"Pixels: {qtd_pixels} | {status}"
    
    # Escreve na parte superior da máscara
    cv2.putText(mask_visualizacao, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, cor_texto, 2)
    
    # Mostra o valor do Blur na tela também para referência
    cv2.putText(mask_visualizacao, f"Blur Kernel: {k}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

    # Aplica a máscara na imagem original (para ver o recorte)
    result = cv2.bitwise_and(frame_blurred, frame_blurred, mask=mask_final)

    # -----------------------------------------------------------
    # 5. EXIBIÇÃO
    # -----------------------------------------------------------
    cv2.imshow("1. Original (com Blur)", frame_blurred)
    cv2.imshow("2. Mascara Processada (Vision.py)", mask_visualizacao)
    cv2.imshow("3. Resultado Final", result)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()