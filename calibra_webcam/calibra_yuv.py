import cv2
import numpy as np
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vision

def nothing(x):
    pass

# Inicializa a captura da webcam
cap = cv2.VideoCapture(0)

# Cria uma janela para os controles
cv2.namedWindow("Calibrador YCrCb + Blur")
cv2.resizeWindow("Calibrador YCrCb + Blur", 400, 500)

# --- TRACKBARS YCrCb ---
# Y = Luma (Brilho), Cr = Chroma Red (Vermelho), Cb = Chroma Blue (Azul)
cv2.createTrackbar("Y Min", "Calibrador YCrCb + Blur", 0, 255, nothing)
cv2.createTrackbar("Cr Min", "Calibrador YCrCb + Blur", 0, 255, nothing)
cv2.createTrackbar("Cb Min", "Calibrador YCrCb + Blur", 0, 255, nothing)

cv2.createTrackbar("Y Max", "Calibrador YCrCb + Blur", 255, 255, nothing)
cv2.createTrackbar("Cr Max", "Calibrador YCrCb + Blur", 255, 255, nothing)
cv2.createTrackbar("Cb Max", "Calibrador YCrCb + Blur", 255, 255, nothing)

# --- TRACKBAR DE BLUR ---
# Começa com 2 (que vira 5 no cálculo 2*x+1)
cv2.createTrackbar("Blur Size", "Calibrador YCrCb + Blur", 2, 10, nothing) 

print("--- MODO YCrCb (YUV) ---")
print("Dica: Cr alto (>140) isola VERMELHO.")
print("Dica: Cb alto (>140) isola AZUL.")
print("Ajuste o 'Blur Size' para limpar ruído.")

while True:
    ret, frame = cap.read()
    if not ret: break

    # -----------------------------------------------------------
    # 1. TRATAMENTO DE IMAGEM (BLUR)
    # -----------------------------------------------------------
    # Lê o valor do slider e garante que seja ímpar (1, 3, 5, 7...)
    k = cv2.getTrackbarPos("Blur Size", "Calibrador YCrCb + Blur")
    k = (k * 2) + 1 
    
    # Aplica o blur para limpar a imagem antes da conversão
    frame_blurred = cv2.medianBlur(frame, k)

    # -----------------------------------------------------------
    # 2. CONVERSÃO E MÁSCARA (YCrCb)
    # -----------------------------------------------------------
    ycrcb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2YCrCb)

    y_min = cv2.getTrackbarPos("Y Min", "Calibrador YCrCb + Blur")
    cr_min = cv2.getTrackbarPos("Cr Min", "Calibrador YCrCb + Blur")
    cb_min = cv2.getTrackbarPos("Cb Min", "Calibrador YCrCb + Blur")
    
    y_max = cv2.getTrackbarPos("Y Max", "Calibrador YCrCb + Blur")
    cr_max = cv2.getTrackbarPos("Cr Max", "Calibrador YCrCb + Blur")
    cb_max = cv2.getTrackbarPos("Cb Max", "Calibrador YCrCb + Blur")

    lower = np.array([y_min, cr_min, cb_min])
    upper = np.array([y_max, cr_max, cb_max])

    mask = cv2.inRange(ycrcb, lower, upper)
    
    # -----------------------------------------------------------
    # 3. CONTAGEM E VISUALIZAÇÃO
    # -----------------------------------------------------------
    qtd_pixels = cv2.countNonZero(mask)

    # Converte máscara para colorido (para texto colorido)
    mask_visualizacao = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    THRESHOLD_PIXELS = 15000 # Seu limiar alvo
    
    if qtd_pixels > THRESHOLD_PIXELS:
        cor_texto = (0, 255, 0) # Verde
        status = "DETECTADO"
    else:
        cor_texto = (0, 0, 255) # Vermelho
        status = "RUIDO / LONGE"

    texto = f"Pixels: {qtd_pixels} | {status}"
    
    cv2.putText(mask_visualizacao, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, cor_texto, 2)
    
    cv2.putText(mask_visualizacao, f"Blur Kernel: {k}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

    result = cv2.bitwise_and(frame_blurred, frame_blurred, mask=mask)

    # -----------------------------------------------------------
    # 4. EXIBIÇÃO
    # -----------------------------------------------------------
    cv2.imshow("1. Original (Blur)", frame_blurred)
    cv2.imshow("2. Mascara + Contagem", mask_visualizacao)
    cv2.imshow("3. Resultado", result)
    
    # Opcional: Ver como o computador vê os canais Y, Cr e Cb
    # cv2.imshow("4. Visao YCrCb", ycrcb) 

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()