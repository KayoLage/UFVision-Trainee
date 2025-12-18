# UFVision Trainee – Detecção de Cor com ArduPilot + Gazebo

Este repositório contém todos os códigos desenvolvidos durante o **trabalho trainee do setor de Desenvolvimento de Software da equipe UFVision**, da **Universidade Federal de Viçosa (UFV)**.

O objetivo principal do projeto é a **detecção de cor aplicada à visão computacional para drones**, abrangendo desde o processamento de imagem até o controle de voo em ambiente simulado.

---

## 🎯 Objetivo do Projeto

Este repositório reúne implementações que cobrem:

- 📷 Calibração de câmera em diferentes espaços de cor:
  - HSV
  - YUV
  - LAB
- 🧠 Processamento de imagens para melhoria de máscaras:
  - Filtros de blur
  - Operações morfológicas
- 🚁 Controle de drone em simulação utilizando:
  - Gazebo Simulator
  - ArduPilot
  - Comunicação via `pymavlink`

---

## 🛠️ Pré-requisitos

Antes de executar o projeto, certifique-se de ter instalado:

- ArduPilot
- Gazebo Simulator
- Python 3.10 ou superior
- Conda (recomendado)
- Câmera (opcional, apenas para testes fora da simulação)

> ⚠️ Este projeto foi desenvolvido e testado utilizando Conda, por ser mais robusto que o uso exclusivo do `pip`.

---

## 📦 Instalação do Ambiente Python

Clone o repositório e crie o ambiente Conda a partir do arquivo `environment.yml`:

```conda env create -f environment.yml``` 

### 🚀 Executando o Projeto

O sistema é executado utilizando **três terminais**, conforme descrito abaixo.

## ▶️ Terminal 1 — Gazebo Simulator

``` 
conda activate ardupilot_gazebo # ambiente que tenha as dependências necessárias para rodar ardupilot + gazebo
gz sim -v4 -r iris_runway.sdf
```

## ▶️ Terminal 2 — ArduPilot (SITL)

``` 
cd ~/UFVision-Trainee/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON
```

## ▶️ Terminal 3 — Código Principal (Visão + Controle)

```
conda activate ardupilot_gazebo 
cd ~/UFVision-Traine
python3 main.py
```

### 📚 Guia de Instalação do ArduPilot e Gazebo

Caso você ainda não tenha o ArduPilot e o Gazebo instalados, consulte o guia abaixo:
[Guia empírico - ArduPilot e SITL via MAVProxy no Gazebo Harmonic](Guia%20emp%C3%ADrico%20-%20ArduPilot%20e%20SITL%20via%20MAVProxy%20no%20Gazebo%20Harmonic.pdf)

## Observações Finais

Desde já, agradeço à **Equipe UFVision** pela oportunidade de participar do projeto.
* **Contato:** kayo.lage@ufv.br

## 👨‍💻 Autor

Projeto desenvolvido por **Kayo de Melo Lage**

Equipe UFVision — Universidade Federal de Viçosa (UFV)
