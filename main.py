import threading
import queue
import time
import os
import sys

# Adiciona diretórios ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import controller as c
import vision as v

TAKEOFF_ALTITUDE_METTERS = 3

# Dicionário apenas para exibição no log
colors_display = {
    'Orange': 'Pousar',
    'Brown':  'Decolar',
    'Red':    'Esquerda <-> Direita',
    'Blue':   'Avançar <-> Retroceder',
    'Yellow': 'Subir <-> Descer',
    'Black':  'Girar Horário <-> Anti-horário'
}

def main():
    # 1. Cria a fila (FIFO pura)
    command_queue = queue.Queue()

    # 2. Setup do Drone
    parser = c.argparse.ArgumentParser()
    parser.add_argument('--size', type=float, default=5.0)
    args = parser.parse_args()

    master = c.connect_drone()
    c.set_limits(master)

    # Thread de Telemetria
    threading.Thread(target=c.telemetry_reader, args=(master,), daemon=True).start()
    c.launch_emergency_ui(master)

    # 3. Thread de Visão
    vision_thread = threading.Thread(
        target=v.start_vision_loop,
        args=(command_queue,),
        daemon=True
    )
    vision_thread.start()

    print("\n--- CONTROLE UFVision INICIADO ---")
    print(f"Main: Decolando para {TAKEOFF_ALTITUDE_METTERS}m...")
    
    # Decola ANTES do loop
    c.arm_and_takeoff(master, TAKEOFF_ALTITUDE_METTERS)

    print("Main: Limpando comandos detectados durante a decolagem...")
    with command_queue.mutex:
        command_queue.queue.clear()

    print("Main: Drone estabilizado. Aguardando cores...")

    # --- ESTADO DOS TOGGLES ---
    # 0 = Movimento Positivo/Ida
    # 1 = Movimento Negativo/Volta
    toggle_state = {
        'Blue': 0,   # 0=Frente, 1=Trás
        'Red': 0,    # 0=Esq, 1=Dir
        'Yellow': 0, # 0=Subir, 1=Descer
        'Black': 0   # 0=Horário, 1=Anti-horário
    }

    while True:
        # 4. Consumo da Fila
        try:
            command = command_queue.get(timeout=1)
            print(f"🔍 DEBUG: Comando recebido da fila: '{command}'")
            print(f"🔍 DEBUG: Fila atual tem {command_queue.qsize()} itens")
        except queue.Empty:
            if c.e_emergency.is_set():
                print("Main: Emergência detectada (Fila vazia)!")
                c.land_drone(master)
                break
            continue

        # Checagens
        if c.e_emergency.is_set():
            print("Main: Emergência detectada! Pousando.")
            c.land_drone(master)
            break
        
        if command == "QUIT":
            print("Main: Recebido QUIT da visão.")
            break

        # 6. Execução com Lógica Circular (Toggle)
        
        # --- AZUL: Eixo X (Avançar / Retroceder) ---
        if command == "Blue":
            state = toggle_state['Blue']
            if state == 0:
                print(f"Main: [AZUL 1/2] >> Avançar 1m")
                c.move_increments(master, 1, 0, 0)
                toggle_state['Blue'] = 1 # Prepara o próximo para ser retroceder
            else:
                print(f"Main: [AZUL 2/2] << Retroceder 1m")
                c.move_increments(master, -1, 0, 0)
                toggle_state['Blue'] = 0 # Reinicia o ciclo
            
        # --- VERMELHO: Eixo Y (Esquerda / Direita) ---
        elif command == "Red":
            state = toggle_state['Red']
            if state == 0:
                print(f"Main: [VERMELHO 1/2] <- Esquerda 1m")
                c.move_increments(master, 0, -1, 0) 
                toggle_state['Red'] = 1
            else:
                print(f"Main: [VERMELHO 2/2] -> Direita 1m")
                c.move_increments(master, 0, 1, 0)
                toggle_state['Red'] = 0
            
        # --- AMARELO: Eixo Z (Subir / Descer) ---
        elif command == "Yellow":
            state = toggle_state['Yellow']
            if state == 0:
                print(f"Main: [AMARELO 1/2] ^^ Subir 1m")
                c.move_increments(master, 0, 0, 1)
                toggle_state['Yellow'] = 1
            else:
                print(f"Main: [AMARELO 2/2] vv Descer 1m")
                c.move_increments(master, 0, 0, -1)
                toggle_state['Yellow'] = 0

        # --- PRETO: Rotação (Horário / Anti-Horário) ---
        elif command == "Black":
            state = toggle_state['Black']
            if state == 0:
                print(f"Main: [PRETO 1/2] Girar Horário 90°")
                c.condition_yaw(master, 90, relative=True) 
                toggle_state['Black'] = 1
            else:
                print(f"Main: [PRETO 2/2] Girar Anti-Horário 90°")
                c.condition_yaw(master, -90, relative=True)
                toggle_state['Black'] = 0

        # --- MARROM: Decolar (Segurança/Reset) ---
        elif command == "Brown":
            print(f"Main: [MARROM] Comando Decolar recebido.") # => A ideia é que o brown de o takeoff e o drone nao de o takeoff sozinho...
            # c.arm_and_takeoff(master, TAKEOFF_ALTITUDE_METTERS)

        # --- LARANJA: Pousar ---
        elif command == "Orange":
            print(f"Main: [LARANJA] Pousando...")    
            c.land_drone(master)
            break 
            
        else:
            print(f"Main: Comando '{command}' desconhecido.")
        
    print("Main: Encerrando conexão com o drone...")
    master.close()
    
    print("Main: Forçando saída...")
    os._exit(0)

if __name__ == "__main__":
    main()