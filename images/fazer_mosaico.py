import cv2
import numpy as np
import os

def gerar_mosaico_github(caminhos, nome_saida="mosaico_laranja_github.png"):
    imgs = []
    # Carrega e padroniza o tamanho das 4 imagens
    for p in caminhos:
        img = cv2.imread(p)
        if img is None:
            print(f"Erro ao carregar: {p}")
            return
        imgs.append(cv2.resize(img, (640, 480)))

    # Organiza em 2x2 seguindo a lógica do vision.py
    linha_sup = np.hstack([imgs[0], imgs[1]])
    linha_inf = np.hstack([imgs[2], imgs[3]])
    mosaico = np.vstack([linha_sup, linha_inf])

    # Adiciona rótulos brancos (a, b, c, d) para o GitHub
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(mosaico, "(a)", (20, 40), font, 1, (255, 255, 255), 2)
    cv2.putText(mosaico, "(b)", (660, 40), font, 1, (255, 255, 255), 2)
    cv2.putText(mosaico, "(c)", (20, 520), font, 1, (255, 255, 255), 2)
    cv2.putText(mosaico, "(d)", (660, 520), font, 1, (255, 255, 255), 2)

    cv2.imwrite(nome_saida, mosaico)
    print(f"Mosaico salvo para o GitHub: {nome_saida}")

# Caminhos baseados na estrutura que você enviou
caminhos_fotos = [
    "mascara_laranja/laranja_amarelo/recorte_HSV_laranja_amarelo.png",
    "mascara_laranja/laranja_vermelho/recorte_HSV_laranja_vermelho.png",
    "mascara_laranja/laranja_azul/recorte_HSV_laranja_azul.png",
    "mascara_laranja/laranja_laranja/recorte_HSV_laranja_laranja.png"
]

gerar_mosaico_github(caminhos_fotos)
