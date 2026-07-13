import pandas as pd
import matplotlib.pyplot as plt

# Cargar los resultados
df = pd.read_csv("benchmark_results.csv")

# Graficar tiempo medio vs resolución de entrada para cada modelo y dispositivo
for device in df['device'].unique():
    plt.figure(figsize=(10,6))
    for model in df['model'].unique():
        subset = df[(df['device'] == device) & (df['model'] == model)]
        # Eje X: número de píxeles de entrada
        x = subset['input_w'] * subset['input_h']
        y = subset['avg_time_ms']
        plt.plot(x, y, marker='o', label=model)
    plt.title(f"Tiempo de inferencia vs Resolución de entrada ({device})")
    plt.xlabel("Resolución de entrada (píxeles)")
    plt.ylabel("Tiempo medio (ms/frame)")
    plt.legend()
    plt.grid(True)
    plt.show()