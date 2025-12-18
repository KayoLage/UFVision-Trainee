import time
import math
import argparse
import threading
import tkinter as tk
from collections import deque
from pymavlink import mavutil
import os
import sys

# adiciona automaticamente a pasta pai ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------
# CONFIGURAÇÕES GLOBAIS
# ---------------------------------------------------
MAX_INCREMENTO = 0.5  # distância máxima por comando (m)
PAUSA_ENTRE_MOVIMENTOS = 1.0  # tempo entre comandos (s)
TELEM_RATE_HZ = 5  # Hz para LOCAL_POSITION_NED
TOLERANCIA_POS = 0.1  # tolerância para chegada (m)

# evento para emergência
e_emergency = threading.Event()

# fila circular para última posição (x, y, z)
pos_queue = deque(maxlen=1)


# ---------------------------------------------------
# FUNÇÕES DE CONEXÃO E PARÂMETROS
# ---------------------------------------------------
def connect_drone():
    master = mavutil.mavlink_connection('udp:127.0.0.1:14550', baud=57600)
    master.wait_heartbeat()
    print("Conexão estabelecida!")

    # solicita telemetria LOCAL_POSITION_NED
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        TELEM_RATE_HZ,
        1
    )
    return master


def set_limits(master):
    params = {
        'MPC_XY_VEL_MAX': 1.0,
        'MPC_MAN_TILT_MAX': 15.0,
        'WP_YAW_BEHAVIOR': 0,
        'ARMING_CHECK': 0
    }

    for p, v in params.items():
        master.mav.param_set_send(
            master.target_system,
            master.target_component,
            p.encode(),
            v,
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32 if isinstance(v, float)
            else mavutil.mavlink.MAV_PARAM_TYPE_INT32
        )
    print("Parâmetros configurados:", params)


# ---------------------------------------------------
# THREAD DE TELEMETRIA
# ---------------------------------------------------
def telemetry_reader(master):
    while not e_emergency.is_set():
        msg = master.recv_match(type='LOCAL_POSITION_NED', blocking=True, timeout=1)
        if msg:
            pos_queue.append((msg.x, msg.y, -msg.z))


# ---------------------------------------------------
# FUNÇÕES DE VOO
# ---------------------------------------------------
def arm_and_takeoff(master, altitude):
    print("--- INICIANDO SEQUÊNCIA DE DECOLAGEM SEGURA ---")
    
    # 1. Desativa Checks (Segurança para simulação)
    master.mav.param_set_send(
        master.target_system, master.target_component,
        b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_INT32)
    print("Parâmetro ARMING_CHECK ajustado para 0.")

    # 2. ESPERA PELO GPS (Bloqueante com timeout)
    print("Aguardando Fixação do GPS (Isso pode levar até 1 minuto)...")
    gps_timeout = time.time() + 60  # 60 segundos de timeout
    
    while True:
        if time.time() > gps_timeout:
            print("⚠️ AVISO: Timeout do GPS. Continuando mesmo assim (modo simulação).")
            break
            
        msg = master.recv_match(type='GPS_RAW_INT', blocking=False, timeout=0.5)
        if msg:
            if msg.fix_type >= 3:
                print(f"GPS Fixado! (Satélites: {msg.satellites_visible})")
                break
            elif msg.fix_type < 3:
                if int(time.time()) % 2 == 0:
                    print(f"Aguardando Satélites... Fix Type: {msg.fix_type} (Necessário >= 3)")
                time.sleep(0.5)

    # 3. Garante Modo GUIDED
    print("Tentando entrar em modo GUIDED...")
    guided_timeout = time.time() + 10
    
    while master.flightmode != 'GUIDED':
        if time.time() > guided_timeout:
            print("⚠️ AVISO: Timeout para entrar em GUIDED. Tentando continuar...")
            break
        master.set_mode('GUIDED')
        time.sleep(1)
        print(f"Modo atual: {master.flightmode}. Aguardando GUIDED...")
    
    # 4. Arma os Motores
    print("Armando motores...")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1, 0, 0, 0, 0, 0, 0
    )
    
    # Espera ativa pela confirmação com timeout
    arm_timeout = time.time() + 10
    while not master.motors_armed():
        if time.time() > arm_timeout:
            print("⚠️ AVISO: Timeout ao armar. Verificando status...")
            break
        time.sleep(0.1)
    
    if master.motors_armed():
        print("!!! MOTORES ARMADOS !!!")
    else:
        print("⚠️ AVISO: Motores podem não estar armados corretamente!")
    
    time.sleep(2)  # Estabiliza hélices

    # 5. Decolagem
    print(f"Decolando para {altitude}m...")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, altitude
    )

    # 6. Monitora subida COM TIMEOUT
    print("Monitorando altitude...")
    takeoff_timeout = time.time() + 30  # 30 segundos para decolar
    last_alt_print = 0
    
    while True:
        # Verifica timeout
        if time.time() > takeoff_timeout:
            print(f"⚠️ AVISO: Timeout de decolagem atingido. Continuando...")
            break
        
        # Tenta receber mensagem com timeout curto
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=False, timeout=0.5)
        
        if msg:
            alt_atual = msg.relative_alt / 1000.0
            
            # Print a cada 0.5m para não poluir
            if abs(alt_atual - last_alt_print) >= 0.5:
                print(f"Altitude: {alt_atual:.1f}m / {altitude}m")
                last_alt_print = alt_atual
            
            if alt_atual >= altitude * 0.85:
                print(f"✅ Altitude alvo alcançada! ({alt_atual:.1f}m)")
                break
        else:
            # Se não receber mensagem, tenta LOCAL_POSITION_NED
            msg_local = master.recv_match(type='LOCAL_POSITION_NED', blocking=False, timeout=0.5)
            if msg_local:
                alt_atual = -msg_local.z  # Z é negativo no NED
                
                if abs(alt_atual - last_alt_print) >= 0.5:
                    print(f"Altitude (local): {alt_atual:.1f}m / {altitude}m")
                    last_alt_print = alt_atual
                
                if alt_atual >= altitude * 0.95:
                    print(f"✅ Altitude alvo alcançada! ({alt_atual:.1f}m)")
                    break
        
        time.sleep(0.1)  # Pequeno delay para não saturar CPU
    
    print("Decolagem concluída!")

def move_increments(master, dx, dy, dz):
    # aguarda posição inicial
    while not pos_queue:
        time.sleep(0.1)

    x0, y0, z0 = pos_queue[0]

    # yaw atual
    msg = master.recv_match(type='ATTITUDE', blocking=True, timeout=3)
    yaw = math.degrees(msg.yaw) % 360 if msg else 0.0
    print(f"Yaw atual: {yaw:.1f}°")

    # calcula passos
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    steps = max(1, int(dist / MAX_INCREMENTO))
    xi, yi, zi = dx / steps, dy / steps, dz / steps
    print(f"Movendo em {steps} passos: ΔX={dx}, ΔY={dy}, ΔZ={dz}")

    mask = 0b0000111111000000

    for i in range(1, steps + 1):
        if e_emergency.is_set():
            print("Movimento interrompido por emergência.")
            return

        tx = x0 + xi * i
        ty = y0 + yi * i
        tz = z0 + zi * i

        master.mav.send(
            mavutil.mavlink.MAVLink_set_position_target_local_ned_message(
                0,
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                mask,
                tx, ty, -tz,
                0, 0, 0, 0, 0, 0,
                math.radians(yaw), 0
            )
        )

        # espera alvo
        while True:
            if e_emergency.is_set():
                return
            rx, ry, rz = pos_queue[0]
            if abs(rx - tx) < TOLERANCIA_POS and abs(ry - ty) < TOLERANCIA_POS:
                break
            time.sleep(0.1)

        print(f"Alcançado => X={rx:.2f}, Y={ry:.2f}, Z={rz:.2f}")


def land_drone(master):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Pousando...")
    time.sleep(5)

    if pos_queue:
        fx, fy, fz = pos_queue[0]
        print(f"Posição final após pouso: X={fx:.2f}, Y={fy:.2f}, Z={fz:.2f}")

def condition_yaw(master, heading, relative=False):
    """
    Envia comando de Yaw (Giro).
    
    :param master: Conexão mavlink
    :param heading: Ângulo absoluto da bússola (0=Norte, 90=Leste).
    :param relative: Se True, soma ao ângulo atual. Se False (Padrão), aponta para o cardeal.
    """
    if relative:
        is_relative = 1 
        direction = 1 if heading >= 0 else -1 # 1=Horário, -1=Anti-horário
    else:
        is_relative = 0 # 0 = Absoluto (Global)
        direction = 0   # 0 = Shortest Path (O drone escolhe o lado mais curto para girar)

    # MAV_CMD_CONDITION_YAW
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_CONDITION_YAW,
        0,          # confirmation
        heading,    # param 1: Target Angle (0-360)
        0,          # param 2: Speed (0 = Default)
        direction,  # param 3: Direction
        is_relative,# param 4: Relative vs Absolute
        0, 0, 0     # param 5-7
    )
    
    modo = "RELATIVO" if relative else "GLOBAL/ABSOLUTO"
    print(f"Controller: Yaw {modo} para {heading}° enviado.")
    time.sleep(2) # Espera um pouco o drone girar

# ---------------------------------------------------
# INTERFACE DE EMERGÊNCIA
# ---------------------------------------------------
def start_emergency_ui(master):
    def on_land():
        print("EMERGÊNCIA acionada! Pouso imediato.")
        e_emergency.set()
        land_drone(master)
        root.destroy()

    root = tk.Tk()
    root.title("EMERGÊNCIA")
    root.geometry("220x100")

    btn = tk.Button(
        root,
        text="POUSAR AGORA",
        fg="white",
        bg="red",
        font=("Helvetica", 16, "bold"),
        command=on_land
    )
    btn.pack(expand=True, fill="both", padx=10, pady=10)
    root.mainloop()


def launch_emergency_ui(master):
    # Executa a interface de emergência em thread separada
    threading.Thread(
        target=start_emergency_ui,
        args=(master,),
        daemon=True
    ).start()

