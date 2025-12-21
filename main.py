import threading
import queue
import os
import sys

# Adiciona diretórios ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import controller as c
import vision as v

TAKEOFF_ALTITUDE_METTERS = 3

def main():
    # Cria a fila de comandos
    command_queue = queue.Queue()

    # Setup do Drone
    parser = c.argparse.ArgumentParser()
    parser.add_argument('--size', type=float, default=5.0)

    master = c.connect_drone()
    c.set_limits(master)

    # Thread de Telemetria
    threading.Thread(target=c.telemetry_reader, args=(master,), daemon=True).start()
    c.launch_emergency_ui(master)

    # Thread de Visão (Inicia agora para começar a procurar o Marrom)
    vision_thread = threading.Thread(
        target=v.start_vision_loop,
        args=(command_queue,),
        daemon=True
    )
    vision_thread.start()

    print("\n--- CONTROLE UFVision INICIADO ---")
    print("Main: SISTEMA EM STANDBY. Aguardando comando MARROM para decolar...")

    # Variável de Estado
    drone_esta_voando = False

    # Estados dos Toggles (Máquina de estados)
    toggle_state = {
        'Blue': 0, 'Red': 0, 'Yellow': 0, 'Black': 0
    }

    while True:
        # Consumo da Fila
        try:
            command = command_queue.get(timeout=1)
            print(f"🔍 Fila: '{command}' | Voando: {drone_esta_voando}")
        except queue.Empty:
            if c.e_emergency.is_set():
                c.land_drone(master)
                break
            continue

        # Checagem de Emergência
        if c.e_emergency.is_set():
            c.land_drone(master)
            break
        
        if command == "QUIT":
            break

        # --- LÓGICA DE ESTADOS --- #

        # CASO 1: DRONE NO CHÃO (Só aceita Marrom)
        if not drone_esta_voando:
            if command == "Brown":
                print(f"Main: [MARROM DETECTADO] Iniciando sequência de decolagem...")
                
                # Executa a decolagem
                c.arm_and_takeoff(master, TAKEOFF_ALTITUDE_METTERS)
                
                # Muda o estado
                drone_esta_voando = True
                
                print("Main: Decolagem concluída. Limpando fila de comandos antigos...")
                # Limpa comandos acumulados enquanto ele estava no chão
                with command_queue.mutex:
                    command_queue.queue.clear()
                print("Main: Fila limpa. Pronto para receber comandos de voo!")
            
            else:
                # Ignora Azul, Vermelho, etc. se estiver no chão
                print(f"Main: Ignorando comando '{command}' pois o drone ainda não decolou.")

        # CASO 2: DRONE VOANDO (Aceita movimentos, ignora Marrom)
        else:
            if command == "Brown":
                print("Main: Ignorando Marrom (Já estamos voando).")
                continue

            elif command == "Orange":
                print(f"Main: [LARANJA] Pousando...")    
                c.land_drone(master)
                break 

            # --- COMANDOS DE MOVIMENTO --- #
            elif command == "Blue":
                state = toggle_state['Blue']
                if state == 0:
                    print(f"Main: [AZUL 1/2] >> Avançar 1m")
                    c.move_increments(master, 1, 0, 0)
                    toggle_state['Blue'] = 1 
                else:
                    print(f"Main: [AZUL 2/2] << Retroceder 1m")
                    c.move_increments(master, -1, 0, 0)
                    toggle_state['Blue'] = 0 
                
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

            else:
                print(f"Main: Comando desconhecido '{command}'")
        
    print("Main: Encerrando...")
    master.close()
    os._exit(0)

if __name__ == "__main__":
    main()