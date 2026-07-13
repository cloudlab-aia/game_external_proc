import posix_ipc
import mmap
import numpy as np
import torch
import time

WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/framebuffer_shared"
device = torch.device("cuda:0")

# Crea o abre memoria compartida
try:
    shm = posix_ipc.SharedMemory(SHM_NAME, flags=0)  # Solo abrir si ya existe
except posix_ipc.ExistentialError:
    print("Memoria compartida no existe. Esperando...")
    while True:
        try:
            shm = posix_ipc.SharedMemory(SHM_NAME, flags=0)
            break
        except posix_ipc.ExistentialError:
            time.sleep(0.5)

# Mapea la región
mapfile = mmap.mmap(shm.fd, FRAME_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
shm.close_fd()

print("Proceso lector activo en GPU1...")

while True:
    mapfile.seek(0)
    raw = mapfile.read(FRAME_SIZE)
    frame_np = np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))

    tensor = torch.from_numpy(frame_np[:, :, :3].copy()).float().to(device) / 255.0
    processed = 1.0 - tensor  # Simula procesamiento
    print("Frame procesado en GPU1", processed.shape)
    time.sleep(1.0 / 60)
