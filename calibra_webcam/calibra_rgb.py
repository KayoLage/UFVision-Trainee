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

cap = cv2.VideoCapture(0)

# --- CONFIGURAÇÃO DO CLAHE (Igual ao código principal) ---
# Mantemos isso para garantir que a cor que você calibra aqui
# seja a mesma que o robô vai processar.
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
# ---------------------------------------------------------

cv2.namedWindow("Calibrador RGB")
cv2.resizeWindow("Calibrador RGB", 400, 350)

# --- TRACKBARS BGR (ATENÇÃO: OpenCV usa BGR, não RGB) ---
# Faixas iniciais para facilitar
cv2.createTrackbar("R Min", "Calibrador RGB", 0, 255, nothing)
cv2.createTrackbar("G Min", "Calibrador RGB", 0, 255, nothing)
cv2.createTrackbar("B Min", "Calibrador RGB", 0, 255, nothing)

cv2.createTrackbar("R Max", "Calibrador RGB", 255, 255, nothing)
cv2.createTrackbar("G Max", "Calibrador RGB", 255, 255, nothing)
cv2.createTrackbar("B Max", "Calibrador RGB", 255, 255, nothing)

print("Pressione 'q' para sair.")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    # 1. PRÉ-PROCESSAMENTO (CLAHE)
    # Convertemos BGR -> HSV -> Aplica CLAHE no V -> Converte volta pra BGR
    # Isso é CRUCIAL para simular a visão real do robô
    hsv_temp = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_temp)
    v_corrected = clahe.apply(v)
    hsv_corrected = cv2.merge([h, s, v_corrected])
    
    # Voltamos para BGR para fazer a calibração RGB
    frame_clahe = cv2.cvtColor(hsv_corrected, cv2.COLOR_HSV2BGR)

    # 2. LEITURA DOS TRACKBARS
    r_min = cv2.getTrackbarPos("R Min", "Calibrador RGB")
    g_min = cv2.getTrackbarPos("G Min", "Calibrador RGB")
    b_min = cv2.getTrackbarPos("B Min", "Calibrador RGB")
    
    r_max = cv2.getTrackbarPos("R Max", "Calibrador RGB")
    g_max = cv2.getTrackbarPos("G Max", "Calibrador RGB")
    b_max = cv2.getTrackbarPos("B Max", "Calibrador RGB")

    # 3. CRIAÇÃO DA MÁSCARA (ORDEM BGR!)
    lower = np.array([b_min, g_min, r_min])
    upper = np.array([b_max, g_max, r_max])
    
    mask_raw = cv2.inRange(frame_clahe, lower, upper)
    
    # 4. LIMPEZA (VISION.PY)
    mask_limpa = vision.abertura(mask_raw)
    mask_final = vision.fechamento(mask_limpa)

    # 5. ANÁLISE ESTATÍSTICA (PARA AJUDAR NA DIFERENÇA LARANJA vs AMARELO)
    qtd_pixels = cv2.countNonZero(mask_final)
    
    # Calcula a média das cores APENAS onde a máscara detectou algo
    # Isso te diz exatamente a cor média do objeto que você está segurando
    avg_color = cv2.mean(frame_clahe, mask=mask_final)
    avg_b, avg_g, avg_r = avg_color[:3]
    
    # O "Magic Number" para separar Laranja de Amarelo
    diff_r_g = avg_r - avg_g 

    # --- VISUALIZAÇÃO ---
    result = cv2.bitwise_and(frame_clahe, frame_clahe, mask=mask_final)
    
    # Info na tela
    cv2.putText(result, f"Pixels: {qtd_pixels}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Mostra a média RGB e a Diferença
    cv2.putText(result, f"Medias -> R:{int(avg_r)} G:{int(avg_g)} B:{int(avg_b)}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # ESTE É O NÚMERO QUE VOCÊ QUER OLHAR:
    cor_diff = (0, 0, 255) if diff_r_g > 30 else (0, 255, 255) # Vermelho se for alto (Laranja), Amarelo se for baixo
    cv2.putText(result, f"DIFF (R - G): {int(diff_r_g)}", (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_diff, 2)

    cv2.imshow("1. Original (CLAHE)", frame_clahe)
    cv2.imshow("2. Recorte Calibrado", result)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()