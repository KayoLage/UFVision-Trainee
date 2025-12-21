import cv2
import numpy as np
import os
import sys
import time

# --- CONFIGURAÇÃO DE CAMINHOS ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vision as v
import settings as s

def nothing(x):
    pass

# --- CONFIGURAÇÕES DE MODO (Escolha um para True) ---
MODO_PRETO   = False  # Subtrai Marrom
MODO_LARANJA = True  # Subtrai Red, Yellow, Brown e Blue
MODO_MARROM  = False   # Subtrai Red, Blue e Yellow [NOVO]

HOME_DIR = os.path.expanduser("~")
SAVE_DIR = os.path.join(HOME_DIR, "UFVision-Trainee", "images")

if not os.path.exists(SAVE_DIR):
    try: os.makedirs(SAVE_DIR)
    except OSError: pass

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERRO: Câmera não detectada.")
    sys.exit()

clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

cv2.namedWindow("Controles", cv2.WINDOW_AUTOSIZE)
cv2.createTrackbar("ESPACO COR", "Controles", 0, 3, nothing)
cv2.createTrackbar("C1 Min", "Controles", 0, 255, nothing)
cv2.createTrackbar("C2 Min", "Controles", 0, 255, nothing)
cv2.createTrackbar("C3 Min", "Controles", 0, 255, nothing)
cv2.createTrackbar("C1 Max", "Controles", 255, 255, nothing)
cv2.createTrackbar("C2 Max", "Controles", 255, 255, nothing)
cv2.createTrackbar("C3 Max", "Controles", 255, 255, nothing)

print("--- CALIBRADOR UFVision ATUALIZADO ---")
if MODO_MARROM:  print("[ATIVO] Modo Marrom: Subtraindo Red, Blue e Yellow")
if MODO_LARANJA: print("[ATIVO] Modo Laranja: Subtraindo Red, Yellow, Blue e Brown")

modo_anterior = -1

while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    frame_blurred = cv2.medianBlur(frame, s.BLUR_KERNEL)

    modo_cor = cv2.getTrackbarPos("ESPACO COR", "Controles")
    if modo_cor == -1: modo_cor = 0 

    # Ajuste de escala para o trackbar de Hue (HSV vai até 179)
    if modo_cor != modo_anterior:
        if modo_cor == 0: # HSV
            cv2.setTrackbarMax("C1 Min", "Controles", 179)
            cv2.setTrackbarMax("C1 Max", "Controles", 179)
        else:
            cv2.setTrackbarMax("C1 Min", "Controles", 255)
            cv2.setTrackbarMax("C1 Max", "Controles", 255)
        modo_anterior = modo_cor

    # Processamento de Imagem conforme espaço de cor
    if modo_cor == 0: # HSV com CLAHE
        temp = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2HSV)
        c1, c2, c3 = cv2.split(temp)
        c3 = clahe.apply(c3)
        img_processed = cv2.merge([c1, c2, c3])
        nome_espaco = "HSV"
    else:
        # Simplificado para outros espaços (LAB, YUV, BGR)
        img_processed = frame_blurred.copy() 
        nome_espaco = "Outro"

    # Máscara Bruta (dos Trackbars)
    c1_min, c2_min, c3_min = cv2.getTrackbarPos("C1 Min", "Controles"), cv2.getTrackbarPos("C2 Min", "Controles"), cv2.getTrackbarPos("C3 Min", "Controles")
    c1_max, c2_max, c3_max = cv2.getTrackbarPos("C1 Max", "Controles"), cv2.getTrackbarPos("C2 Max", "Controles"), cv2.getTrackbarPos("C3 Max", "Controles")
    
    mask_raw = cv2.inRange(img_processed, np.array([c1_min, c2_min, c3_min]), np.array([c1_max, c2_max, c3_max]))

    # --- LÓGICA DE SUBTRAÇÃO PARA CALIBRAÇÃO ---
    mask_final = mask_raw.copy()

    if modo_cor == 0: # Apenas para HSV onde temos os ranges salvos
        if MODO_MARROM:
            # Subtrai o que foi definido como Red, Blue e Yellow
            for cor in ["Red", "Blue", "Yellow"]:
                low, high = s.RANGES[cor]
                m_sub = cv2.inRange(img_processed, low, high)
                m_sub = v.processar_mascara_completa(m_sub)
                mask_final = cv2.subtract(mask_final, m_sub)

        elif MODO_LARANJA:
            for cor in ["Red", "Yellow", "Brown", "Blue"]:
                low, high = s.RANGES[cor]
                m_sub = cv2.inRange(img_processed, low, high)
                mask_final = cv2.subtract(mask_final, v.processar_mascara_completa(m_sub))

    # Processamento final (Morfologia e CC)
    mask_final = v.processar_mascara_completa(mask_final, EhPraFazerAbertura=(not MODO_PRETO))

    # Visualização
    scale = 0.6
    new_dim = (int(frame.shape[1] * scale), int(frame.shape[0] * scale))
    res_final = cv2.bitwise_and(frame, frame, mask=mask_final)
    
    cv2.imshow("Recorte (Marrom c/ Subtracao)", res_final)
    cv2.imshow("Mascara Final", cv2.resize(mask_final, new_dim))

    k = cv2.waitKey(1) & 0xFF
    if k == ord('q'):
        print(f"\n--- VALORES PARA O MARROM ({nome_espaco}) ---")
        print(f"LOWER = np.array([{c1_min}, {c2_min}, {c3_min}])")
        print(f"UPPER = np.array([{c1_max}, {c2_max}, {c3_max}])")
        break
    elif k == ord('s'):
        ts = time.strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(os.path.join(SAVE_DIR, f"calib_marrom_{ts}.png"), res_final)
        print(f"Imagem salva em: {SAVE_DIR}")

cap.release()
cv2.destroyAllWindows()