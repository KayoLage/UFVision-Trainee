import cv2
import numpy as np
import os
import sys

# Configura o path para importar o vision.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vision

def nothing(x):
    pass

# Inicializa a captura da webcam
cap = cv2.VideoCapture(0)

# --- CONFIGURAÇÃO DO CLAHE (Onde a mágica acontece) ---
# clipLimit=5.0: Contraste bem forte (ajuda a clarear sombras escuras)
# tileGridSize=(4,4): Grid maior, trata áreas maiores de iluminação
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
# -----------------------------------------------------

# Cria uma janela para os controles
cv2.namedWindow("Controles")
cv2.resizeWindow("Controles", 300, 300)

# Cria trackbars (barras deslizantes)
cv2.createTrackbar("H Min", "Controles", 0, 179, nothing)
cv2.createTrackbar("S Min", "Controles", 0, 255, nothing)
cv2.createTrackbar("V Min", "Controles", 0, 255, nothing)

cv2.createTrackbar("H Max", "Controles", 179, 179, nothing)
cv2.createTrackbar("S Max", "Controles", 255, 255, nothing)
cv2.createTrackbar("V Max", "Controles", 255, 255, nothing)

print("Pressione 'q' para sair.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # 1. Converte para HSV
    hsv_original = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # --- APLICAÇÃO DO CLAHE ---
    # Separa os canais (Hue, Saturation, Value)
    h, s, v = cv2.split(hsv_original)
    
    # Aplica o CLAHE apenas no canal V (Brilho)
    v_corrected = clahe.apply(v)
    
    # Junta de volta criando o HSV Modificado
    hsv_clahe = cv2.merge([h, s, v_corrected])
    # --------------------------

    # Leitura dos valores atuais das barras
    h_min = cv2.getTrackbarPos("H Min", "Controles")
    s_min = cv2.getTrackbarPos("S Min", "Controles")
    v_min = cv2.getTrackbarPos("V Min", "Controles")
    
    h_max = cv2.getTrackbarPos("H Max", "Controles")
    s_max = cv2.getTrackbarPos("S Max", "Controles")
    v_max = cv2.getTrackbarPos("V Max", "Controles")

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])

    # 2. Cria a máscara bruta USANDO O HSV COM CLAHE
    mask_raw = cv2.inRange(hsv_clahe, lower, upper)

    # --- APLICAÇÃO DAS FUNÇÕES DO VISION.PY ---
    mask_limpa = vision.abertura(mask_raw)
    mask_final = vision.fechamento(mask_limpa)
    # ------------------------------------------

    # --- CONTAGEM E VISUALIZAÇÃO ---
    qtd_pixels = cv2.countNonZero(mask_final)
    mask_visualizacao = cv2.cvtColor(mask_final, cv2.COLOR_GRAY2BGR)

    THRESHOLD_PIXELS = 15000
    if qtd_pixels > THRESHOLD_PIXELS:
        cor_texto = (0, 255, 0) # Verde
        status = "DETECTADO (Solido)"
    else:
        cor_texto = (0, 0, 255) # Vermelho
        status = "RUIDO / MUITO LONGE"

    texto = f"Pixels: {qtd_pixels} | {status}"
    cv2.putText(mask_visualizacao, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, cor_texto, 2)

    # Aplica a máscara final na imagem original
    result = cv2.bitwise_and(frame, frame, mask=mask_final)
    
    # OPCIONAL: Para ver como o CLAHE está mudando a imagem, 
    # converte o HSV modificado de volta pra BGR para exibir
    frame_clahe_view = cv2.cvtColor(hsv_clahe, cv2.COLOR_HSV2BGR)

    # Mostra as janelas
    cv2.imshow("1. Original (Com CLAHE aplicado)", frame_clahe_view) # Mudei aqui para você ver o efeito
    cv2.imshow("2. Mascara Processada + Contagem", mask_visualizacao)
    cv2.imshow("3. Recorte Final", result)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()