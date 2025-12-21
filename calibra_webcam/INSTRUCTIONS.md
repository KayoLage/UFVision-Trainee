# Objetivo

O objetivo desse folder aqui é justamente fazer um script para calibração
da câmera no sentido de encontrar um bom intervalo de valor para cada cor de 
acordo com cada WebCam e ambiente de captura, assim podemos "facilmente" estender isso para 
diferentes setups de dispositivos.

# --- SUGESTÕES --- #

> Caso seu ambiente de captura seja um pouco "sujo" em relação aos objetos de fundo (sobretudo com tons de preto e marrom) é bem provável que você tenha que ajustar thresholds de área das máscaras.

Sobre os espaços de cor:
* Para cores como **vermelho**, **amarelo** e **laranja** recomendo usar **HSV** (ao menos foi testado este para elas e conseguiu separar bem)
* Para **preto e marrom pode ser** que o **LAB seja melhor** (mas o **HSV** costuma ser melhor também, inclusive recomendo ele)

## O que é esperado?

A seguir segue algumas imagens do que é esperado para as máscaras, se você conseguiu encontrar limiares que sejam próximos ou até melhores que isso você já consegue rodar o código de modo que ele seja robusto o suficiente para diferenciar todas as 6 cores!

> IMPORTANTE!!! => Para o laranja procure uma máscara que bruta que ela cubra o laranja, amarelo, vermelho e azul (não se preocupe que o código subtrai o amarelo e o vermelho depois deixando apenas o laranja)

## Validação da Máscara do Laranja

Para o **Laranja**, é esperado que a máscara bruta seja "gulosa", capturando também pixels de Amarelo, Vermelho e Azul. O sistema foi desenhado para realizar a limpeza automática via subtração booleana no script principal.

![Exemplo de máscara bruta para o Laranja](../images/mosaicos/mosaico_laranja_github.png)

*Figura: Exemplo da máscara bruta capturando (a) Amarelo, (b) Vermelho, (c) Azul e (d) Laranja antes da subtração lógica.*
