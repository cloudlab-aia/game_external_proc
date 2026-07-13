#!/usr/bin/env python3
"""Carga sostenida sobre la CPU: ocupa todos los núcleos con bucles de cálculo
hasta recibir SIGTERM/SIGINT. Para el estado de carga 'cpu' de la matriz."""
import multiprocessing as mp
import os
import signal


def _burn():
    x = 1.0001
    while True:
        x = x * 1.0000001 + 0.0000001
        if x > 1e9:
            x = 1.0001


def main():
    n = os.cpu_count() or 4
    procs = [mp.Process(target=_burn, daemon=True) for _ in range(n)]
    for p in procs:
        p.start()

    def shutdown(*_):
        for p in procs:
            p.terminate()
        for p in procs:
            p.join(timeout=2)
            if p.is_alive():
                p.kill()
        os._exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    signal.pause()


if __name__ == "__main__":
    main()
