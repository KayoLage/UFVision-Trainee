import cv2
import numpy as np
import os
import sys

# adiciona automaticamente a pasta pai ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- CONFIGURAÇÕES GLOBAIS --- #
KERNEL = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)) 

# Thresholds específicos por cor
THRESHOLD_PIXELS = 15000     # Azul, Vermelho, Amarelo
THRESHOLD_ORANGE = 40000     # Laranja
THRESHOLD_BLACK  = 70000     # Preto
THRESHOLD_BROWN  = 110000    # Marrom

# Define o tamanho mínimo de um "blob" para ser considerado objeto.
AREA_MINIMA_RUIDO = 10000 

def abertura(mascara):
    """Remove ruídos pequenos (pontos brancos isolados)."""
    return cv2.morphologyEx(mascara, cv2.MORPH_OPEN, KERNEL)

def fechamento(mascara):
    """Fecha buracos pretos dentro do objeto."""
    return cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, KERNEL)

def filtrar_ruido_por_contorno(mascara, area_minima):
    """
    Substitui a lógica de 'Abertura' agressiva.
    Usa componentes conexos (findContours) para remover APENAS objetos pequenos,
    sem alterar a forma dos objetos grandes (diferente da erosão).
    """
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Criamos uma nova máscara limpa (preta)
    mascara_limpa = np.zeros_like(mascara)
    
    for cnt in contornos:
        area = cv2.contourArea(cnt)
        
        if area > area_minima:
            cv2.drawContours(mascara_limpa, [cnt], -1, 255, thickness=cv2.FILLED)
            
    return mascara_limpa

def processar_mascara_completa(mascara, EhPraFazerAbertura = True):
    """
    Pipeline de limpeza atualizado:
    1. Abertura (limpa poeira de 1px)
    2. Filtro de Contorno (remove manchas pequenas/médias sem deformar o objeto)
    3. Fechamento (tapa buracos dentro do objeto)
    """
    if EhPraFazerAbertura:
        m = abertura(mascara)
    else:
        m = mascara
    
    m = filtrar_ruido_por_contorno(m, area_minima=AREA_MINIMA_RUIDO)
    m = fechamento(m)
    return m

def criar_mosaico(frame_original, mascaras_dict, comando_atual):
    """
    Cria um mosaico das máscaras de todas as cores para debug do código
    e fala se a máscara "foi ativada" ou não de acordo com seu threshold
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
            
            # --- LÓGICA DE COR DO TEXTO (VISUALIZAÇÃO) --- #
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
    
    # 1. CLAHE e HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    v = clahe.apply(v)
    hsv = cv2.merge([h, s, v])

    # --- DEFINIÇÃO DOS RANGES ---
    ranges = {
        # Cores "Fáceis"
        "Blue":   (np.array([25, 100, 0]), np.array([140, 255, 255])),
        "Red":    (np.array([125, 100, 40]), np.array([170, 255, 255])),
        "Yellow": (np.array([15, 45, 105]), np.array([30, 255, 255])),
        
        # Cores "Difíceis"
        "Orange": (np.array([0, 75, 140]), np.array([179, 255, 255])), 
        "Brown":  (np.array([0, 0, 0]), np.array([179, 130, 105])), 
        "Black":  (np.array([0, 0, 0]), np.array([179, 60, 110]))
    }
    
    # --- ORDEM DE CÁLCULO DAS MÁSCARAS (DEPENDÊNCIAS) --- #
    
    # 1. Independentes
    for cor in ["Blue", "Red", "Yellow"]:
        low, high = ranges[cor]
        m = cv2.inRange(hsv, low, high)
        mascaras[cor] = processar_mascara_completa(m)

    # 2. Black (Calculado primeiro para ser usado pelo Marrom)
    low_k, high_k = ranges["Black"]
    mask_black = cv2.inRange(hsv, low_k, high_k)
    mascaras["Black"] = processar_mascara_completa(mask_black, EhPraFazerAbertura=False)

    # 3. Brown (Subtrai Vermelho, Azul, Amarelo e PRETO)
    low_b, high_b = ranges["Brown"]
    mask_brown = cv2.inRange(hsv, low_b, high_b)
    
    if "Red" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Red"])
        
    if "Blue" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Blue"])
    if "Yellow" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Yellow"])
        
    # Subtrai o Preto inicial do Marrom
    if "Black" in mascaras:
        mask_brown = cv2.subtract(mask_brown, mascaras["Black"])
        
    # Processa o Marrom Final
    mascaras["Brown"] = processar_mascara_completa(mask_brown, EhPraFazerAbertura=True)

    # [NOVO] O PEDIDO: Subtrair a Máscara Marrom Final da Máscara Preta
    if "Black" in mascaras:
        mascaras["Black"] = cv2.subtract(mascaras["Black"], mascaras["Brown"])

    # 4. Orange (O "Guloso" - Subtrai todos os outros)
    low_o, high_o = ranges["Orange"]
    mask_orange = cv2.inRange(hsv, low_o, high_o)
    if "Red" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Red"])
    if "Yellow" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Yellow"])
    if "Brown" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Brown"])
    if "Blue" in mascaras:
        mask_orange = cv2.subtract(mask_orange, mascaras["Blue"])
    mascaras["Orange"] = processar_mascara_completa(mask_orange)

    # --- LÓGICA DE DECISÃO (PRIORIDADE) --- #
    prioridade_verificacao = ["Blue", "Yellow", "Red", "Orange", "Black", "Brown"]
    # Da máscara mais confiável para menos confiável

    for cor in prioridade_verificacao:
        qtd = cv2.countNonZero(mascaras[cor])
        
        # Seleciona o threshold correto para a cor atual
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
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Visão: Erro webcam.")
        return

    cooldown = 0 

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
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            command_queue.put("QUIT")
            break
            
    cap.release()
    cv2.destroyAllWindows()