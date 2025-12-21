import cv2
import numpy as np
import os
import sys
import time 
from skimage.measure import label, regionprops
import settings as s

# adiciona automaticamente a pasta pai ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- CONFIGURAÇÕES GLOBAIS --- #
MORPHOLOGY_KERNEL = s.MORPHOLOGY_KERNEL
BLUR_KERNEL = s.BLUR_KERNEL

# Thresholds específicos por cor
THRESHOLD_PIXELS = s.THRESHOLD_PIXELS   # Azul, Vermelho, Amarelo
THRESHOLD_ORANGE = s.THRESHOLD_ORANGE   # Laranja
THRESHOLD_BLACK  = s.THRESHOLD_BLACK    # Preto
THRESHOLD_BROWN  = s.THRESHOLD_BROWN    # Marrom

# Define o tamanho mínimo de um "blob" para ser considerado objeto.
AREA_MINIMA_RUIDO = s.AREA_MINIMA_RUIDO 

# Thresholds para remoção de CC's
THRESHOLD_AREA_MIN_REMOVE_CC = s.THRESHOLD_AREA_MIN_REMOVE_CC
THRESHOLD_AREA_MAX_REMOVE_CC = s.THRESHOLD_AREA_MAX_REMOVE_CC

# --- Ranges HSV --- #
ranges = s.RANGES


def abertura(mascara):
    """Remove ruídos pequenos (pontos brancos isolados)."""
    return cv2.morphologyEx(mascara, cv2.MORPH_OPEN, MORPHOLOGY_KERNEL)

def fechamento(mascara):
    """Fecha buracos pretos dentro do objeto."""
    return cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, MORPHOLOGY_KERNEL)

def remove_componentes_por_area(
    binary_mask,
    min_area=None,
    max_area=None,
    connectivity=2
):
    """
    Remove componentes conexos de acordo com a área.
    """
    # Garante binário 0/1
    binary_mask = (binary_mask > 0).astype(np.uint8)

    labeled = label(binary_mask, connectivity=connectivity)
    output = np.zeros_like(binary_mask)

    for region in regionprops(labeled):
        area = region.area

        if min_area is not None and area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue

        output[labeled == region.label] = 1

    return output

def processar_mascara_completa(mascara, EhPraFazerAbertura=True):
    """
    Pipeline de limpeza atualizado com remove_componentes_por_area
    """
    # Abertura
    if EhPraFazerAbertura:
        m = abertura(mascara)
    else:
        m = mascara
    
    # Filtragem por Área
    m = remove_componentes_por_area(
        m, 
        min_area=THRESHOLD_AREA_MIN_REMOVE_CC, 
        max_area=THRESHOLD_AREA_MAX_REMOVE_CC 
    )
    
    # CONVERSÃO IMPORTANTE (garantir uint8)
    m = m * 255
    m = m.astype(np.uint8) 
    
    # Fechamento
    m = fechamento(m)
    
    return m

def criar_mosaico(frame_original, mascaras_dict, comando_atual):
    """
    Cria um mosaico das máscaras de todas as cores para debug
    """
    scale = 0.5
    h, w = frame_original.shape[:2]
    new_dim = (int(w * scale), int(h * scale))
    
    thumb_orig = cv2.resize(frame_original, new_dim)
    cv2.putText(thumb_orig, f"CMD: {comando_atual}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    lista_imagens = [thumb_orig]
    ordem_cores = ["Blue", "Orange", "Red", "Yellow", "Brown", "Black"]
    
    for nome_cor in ordem_cores:
        mask = mascaras_dict.get(nome_cor)
        if mask is not None:
            thumb_mask = cv2.resize(mask, new_dim)
            thumb_color = cv2.cvtColor(thumb_mask, cv2.COLOR_GRAY2BGR)
            
            qtd = cv2.countNonZero(mask)
            
            # Lógica visual de Threshold
            if nome_cor == "Orange":
                limit = THRESHOLD_ORANGE
            elif nome_cor == "Brown":
                limit = THRESHOLD_BROWN
            elif nome_cor == "Black":
                limit = THRESHOLD_BLACK
            else:
                limit = THRESHOLD_PIXELS
            
            cor_texto = (0, 255, 0) if qtd > limit else (0, 0, 255)
            
            cv2.putText(thumb_color, f"{nome_cor}: {qtd}", (10, 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_texto, 1)
            
            lista_imagens.append(thumb_color)
            
    linhas = []
    chunk_size = 3
    for i in range(0, len(lista_imagens), chunk_size):
        chunk = lista_imagens[i:i + chunk_size]
        while len(chunk) < chunk_size:
            chunk.append(np.zeros_like(thumb_orig))
        linhas.append(np.hstack(chunk))
        
    return np.vstack(linhas)

def detectar_cor_e_retornar_mascaras(frame):
    mascaras = {}
    comando_final = None
    
    # --- PRÉ-PROCESSAMENTO (BLUR) --- #
    frame_blurred = cv2.medianBlur(frame, BLUR_KERNEL)

    # CLAHE e HSV
    hsv = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2HSV)
    
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)) 
    v = clahe.apply(v)
    hsv = cv2.merge([h, s, v])

    # --- CÁLCULO DAS MÁSCARAS --- #

    # 1⁰) Máscaras Independentes
    for cor in ["Blue", "Red", "Yellow"]:
        low, high = ranges[cor]
        m = cv2.inRange(hsv, low, high)
        mascaras[cor] = processar_mascara_completa(m)

    # 2⁰) Black
    low_k, high_k = ranges["Black"]
    mask_black = cv2.inRange(hsv, low_k, high_k)
    mascaras["Black"] = processar_mascara_completa(mask_black, EhPraFazerAbertura=False) # OBS.: coloque False se houver muitos objetos (sobretudo objetos menores)
                                                                                         # background no cenário de cor MARROM (já que subtraímos do preto a máscara do marrom,
                                                                                         # no geral False não muda muito, mude també o threshold de pixels para se detectar o preto 
                                                                                         # (aumentar)) se o ambiente de captura for "limpo", então por via das dúvidas False

    # 3⁰) Brown
    low_b, high_b = ranges["Brown"]
    mask_brown = cv2.inRange(hsv, low_b, high_b)
    
    if "Red" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Red"])
    if "Blue" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Blue"])
    if "Yellow" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Yellow"])
        
    mascaras["Brown"] = processar_mascara_completa(mask_brown, EhPraFazerAbertura=True)  # OBS.: coloque False se houver muitos objetos (sobretudo objetos menores)
                                                                                         # background no cenário de cor PRETA (já que subtraímos do marrom a máscara do preto,
                                                                                         # no geral False não muda muito, mude també o threshold de pixels para se detectar o preto 
                                                                                         # (aumentar)) se o ambiente de captura for "limpo", então por via das dúvidas False

    # Subtrai Brown do Black
    if "Black" in mascaras:
        mascaras["Black"] = cv2.subtract(mascaras["Black"], mascaras["Brown"])

    # 4⁰) Orange
    low_o, high_o = ranges["Orange"]
    mask_orange = cv2.inRange(hsv, low_o, high_o)
    if "Red" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Red"])
    if "Yellow" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Yellow"])
    if "Blue" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Blue"])

    mascaras["Orange"] = processar_mascara_completa(mask_orange)

    # --- LÓGICA DE DECISÃO --- #
    prioridade_verificacao = ["Blue", "Yellow", "Red", "Orange", "Black", "Brown"] # Da cor mais confiável para menos confiável (via empírica)
    
    for cor in prioridade_verificacao:
        qtd = cv2.countNonZero(mascaras[cor])
        
        if cor == "Orange":
            limite = THRESHOLD_ORANGE 
        elif cor == "Brown":
            limite = THRESHOLD_BROWN 
        elif cor == "Black":
            limite = THRESHOLD_BLACK 
        else:
            limite = THRESHOLD_PIXELS 
            
        if qtd > limite:
            comando_final = cor
            break 
                
    return comando_final, mascaras

def start_vision_loop(command_queue):
    # --- CONFIGURAÇÃO DE SALVAMENTO --- # (Só para colocar no relatório e no GitHub -> IGNORAR)
    HOME_DIR = os.path.expanduser("~")
    SAVE_DIR = os.path.join(HOME_DIR, "UFVision-Trainee", "images")
    
    if not os.path.exists(SAVE_DIR):
        try: os.makedirs(SAVE_DIR)
        except OSError: pass

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Visão: Erro webcam.")
        return

    cooldown = 0 
    
    print("--- SISTEMA DE VISÃO INICIADO ---")
    print(f"Pressione 's' na janela do Mosaico para salvar em: {SAVE_DIR}")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1) 
        
        cmd_detectado, mascaras_dict = detectar_cor_e_retornar_mascaras(frame)
        
        if cooldown == 0:
            if cmd_detectado:
                print(f"Visão: Detectado {cmd_detectado}!")
                command_queue.put(cmd_detectado)
                cooldown = 30
        else:
            cooldown -= 1
            
        mosaico = criar_mosaico(frame, mascaras_dict, cmd_detectado)
        cv2.imshow('Mosaico de Debug (Original + Mascaras)', mosaico)
        
        # --- CONTROLE DE TECLAS ---
        k = cv2.waitKey(1) & 0xFF
        
        if k == ord('q'):
            command_queue.put("QUIT")
            break
        
        elif k == ord('s'):
            # 1. Gera o timestamp para a pasta e arquivos
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Criamos uma subpasta específica para este "print"
            pasta_momento = os.path.join(SAVE_DIR, f"captura_{timestamp}")
            
            if not os.path.exists(pasta_momento):
                os.makedirs(pasta_momento)

            # 2. Salva o mosaico completo (opcional, mas bom para referência)
            cv2.imwrite(os.path.join(pasta_momento, "00_mosaico_completo.png"), mosaico)
            
            # 3. Salva o frame original (sem as máscaras em cima)
            cv2.imwrite(os.path.join(pasta_momento, "01_frame_original.png"), frame)

            # 4. Percorre o dicionário e salva cada máscara individualmente
            for nome_cor, mascara in mascaras_dict.items():
                nome_arquivo = f"mask_{nome_cor}_{timestamp}.png"
                caminho_final = os.path.join(pasta_momento, nome_arquivo)
                
                # Salvando a máscara
                cv2.imwrite(caminho_final, mascara)
            
            print(f"[VISION] Captura completa salva em: {pasta_momento}")
            
    cap.release()
    cv2.destroyAllWindows()