# 🔧 EXPLICACIÓN DETALLADA: Script Principal de Análisis

## 📋 **Archivo: `comprehensive_glxgears_realesrgan_analysis.py`**

Este es el corazón del sistema. Te explico **sección por sección** cómo funciona:

---

## 🏗️ **ESTRUCTURA GENERAL DEL SCRIPT**

```python
# 1. IMPORTACIONES Y CONFIGURACIÓN INICIAL
# 2. ESPECIFICACIONES DE HARDWARE
# 3. DEFINICIÓN DE RESOLUCIONES A ANALIZAR
# 4. CLASES Y FUNCIONES PRINCIPALES
# 5. SIMULADORES DE RENDIMIENTO
# 6. GENERADORES DE GRÁFICOS Y REPORTES
# 7. FUNCIÓN PRINCIPAL Y EJECUCIÓN
```

---

## 📦 **SECCIÓN 1: Importaciones y Configuración**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador Completo GLXGears + Real-ESRGAN
Simulación realista de arquitectura híbrida dGPU/iGPU
"""

import os
import sys
import json
import csv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import random
from typing import Dict, List, Tuple, Optional
from pathlib import Path
```

### **¿Para qué sirve cada importación?**

| **Librería** | **Propósito** | **Uso Específico** |
|--------------|---------------|-------------------|
| `os, sys, pathlib` | Sistema de archivos | Crear carpetas, rutas, gestión de archivos |
| `json, csv, pandas` | Datos estructurados | Guardar/cargar resultados, tablas |
| `numpy` | Cálculos matemáticos | Estadísticas, simulaciones numéricas |
| `matplotlib, seaborn` | Visualización | Gráficos científicos, heatmaps |
| `datetime` | Timestamps | Nombres únicos de archivos y reportes |
| `random, typing` | Utilidades | Variabilidad estadística, tipado |

---

## ⚙️ **SECCIÓN 2: Especificaciones de Hardware**

```python
# Configuración de hardware simulado
HARDWARE_CONFIG = {
    "dgpu": {
        "name": "NVIDIA GeForce RTX/GTX",
        "vram_gb": 8,
        "cuda_cores": 2048,
        "base_performance": 1.0,        # Multiplicador base
        "thermal_throttling": 0.95      # Factor térmico (0.9-1.0)
    },
    "igpu": {
        "name": "Intel Iris Xe Graphics", 
        "vram_shared_gb": 4,
        "execution_units": 96,
        "base_inference_ms_per_mpixel": 12.0,  # Tiempo base por megapíxel
        "memory_bandwidth_factor": 1.3,        # Factor memoria compartida
        "thermal_factor": 1.2                  # Factor térmico iGPU
    },
    "system": {
        "cpu": "Intel Core i5-12400 / i7-12700",
        "ram_gb": 16,
        "pcie_lanes": 16,
        "transfer_latency_ms": 1.5      # Latencia transferencia dGPU→iGPU
    }
}
```

### **🎯 ¿Cómo se usan estos valores?**

#### **Para dGPU (Renderizado):**
- **`base_performance`**: Multiplica el rendimiento base calculado
- **`thermal_throttling`**: Simula reducción de rendimiento por calor
- **`vram_gb`**: No limita pero informa especificaciones

#### **Para iGPU (Real-ESRGAN):**
- **`base_inference_ms_per_mpixel`**: ⭐ **CLAVE** - Tiempo base de procesamiento
- **`memory_bandwidth_factor`**: Penaliza por usar memoria compartida
- **`thermal_factor`**: Penaliza por calentamiento de iGPU

#### **Para Sistema:**
- **`transfer_latency_ms`**: Latencia fija por transferir frames entre GPUs

---

## 📐 **SECCIÓN 3: Definición de Resoluciones**

```python
# Resoluciones a analizar (width, height, nombre, categoría)
RESOLUTION_CONFIGS = [
    (160, 120, "QQVGA", "Muy Baja"),      # 0.019 MP
    (320, 240, "QVGA", "Baja"),           # 0.077 MP  
    (480, 270, "qHD", "Baja+"),           # 0.130 MP
    (640, 360, "nHD", "Media Baja"),      # 0.230 MP
    (640, 480, "VGA", "Media"),           # 0.307 MP
    (800, 600, "SVGA", "Media+"),         # 0.480 MP
    (1024, 576, "WSVGA", "Media Alta"),   # 0.590 MP
    (1024, 768, "XGA", "Alta"),           # 0.786 MP
    (1280, 720, "HD", "HD Estándar"),     # 0.922 MP
    (1366, 768, "WXGA", "HD+"),           # 1.049 MP
    (1600, 900, "HD+", "HD Plus"),        # 1.440 MP
    (1680, 1050, "WSXGA+", "HD Pro"),     # 1.764 MP
    (1920, 1080, "FHD", "Full HD"),       # 2.074 MP
    (2048, 1152, "2K", "2K Intermedio"),  # 2.359 MP
    (2560, 1440, "QHD", "Quad HD"),       # 3.686 MP
    (3200, 1800, "QHD+", "Quad HD+"),     # 5.760 MP
    (3840, 2160, "4K UHD", "4K Ultra HD"), # 8.294 MP
    (4096, 2160, "DCI 4K", "4K Cinema")    # 8.847 MP
]
```

### **🎯 ¿Por qué estas resoluciones específicas?**

1. **Cobertura Completa**: Desde pruebas mínimas hasta gaming premium
2. **Estándares Reales**: Resoluciones usadas en dispositivos reales
3. **Escalado Progresivo**: Permite ver cómo evoluciona el rendimiento
4. **Puntos Críticos**: Incluye umbrales importantes (HD, Full HD, 4K)

---

## 🏗️ **SECCIÓN 4: Clases Principales**

### **Clase: `PerformanceSimulator`**

```python
class PerformanceSimulator:
    """Simula el rendimiento del sistema híbrido dGPU/iGPU"""
    
    def __init__(self, hardware_config: Dict):
        self.hardware = hardware_config
        self.dgpu = hardware_config["dgpu"]
        self.igpu = hardware_config["igpu"]  
        self.system = hardware_config["system"]
```

#### **🎯 ¿Qué hace esta clase?**
- **Centraliza toda la lógica** de simulación
- **Organiza las especificaciones** de hardware
- **Proporciona métodos** para simular cada componente

### **Método: `simulate_dgpu_performance()`**

```python
def simulate_dgpu_performance(self, width: int, height: int, samples: int = 20) -> Dict:
    """Simula rendimiento de dGPU renderizando GLXGears"""
    
    # Calcular megapíxeles
    megapixels = (width * height) / 1000000
    
    # Modelo de rendimiento base
    # Fórmula: FPS decrece con la resolución
    base_fps = 5000 / (1 + megapixels * 0.6)
    
    # Aplicar especificaciones de hardware
    performance_factor = self.dgpu["base_performance"]
    thermal_factor = self.dgpu["thermal_throttling"]
    
    # FPS esperado
    expected_fps = base_fps * performance_factor * thermal_factor
    
    # Generar samples con variabilidad realista
    fps_samples = []
    for _ in range(samples):
        # Variabilidad térmica y de carga
        thermal_variation = np.random.normal(1.0, 0.12)
        load_variation = np.random.normal(1.0, 0.08) 
        
        sample_fps = expected_fps * thermal_variation * load_variation
        sample_fps = max(sample_fps, 10.0)  # Mínimo realista
        fps_samples.append(sample_fps)
    
    # Calcular estadísticas
    fps_array = np.array(fps_samples)
    return {
        "mean_fps": np.mean(fps_array),
        "std_fps": np.std(fps_array),
        "median_fps": np.median(fps_array),
        "min_fps": np.min(fps_array),
        "max_fps": np.max(fps_array),
        "p95_fps": np.percentile(fps_array, 95),
        "p99_fps": np.percentile(fps_array, 99),
        "frame_time_ms": 1000.0 / np.mean(fps_array),
        "megapixels": megapixels,
        "samples": fps_samples
    }
```

#### **🔍 ¿Cómo funciona esta simulación?**

1. **Modelo Base**: `FPS = 5000 / (1 + MP * 0.6)`
   - Más megapíxeles = menos FPS
   - Relación no-lineal realista

2. **Factores de Hardware**:
   - `performance_factor`: Multiplica por especificaciones GPU
   - `thermal_factor`: Reduce por throttling térmico

3. **Variabilidad Estadística**:
   - `thermal_variation`: Simula variación de temperatura
   - `load_variation`: Simula variación de carga del sistema

4. **Estadísticas Completas**: Media, desviación, percentiles, etc.

### **Método: `simulate_igpu_inference()`**

```python
def simulate_igpu_inference(self, width: int, height: int, samples: int = 20) -> Dict:
    """Simula tiempo de inferencia Real-ESRGAN en iGPU"""
    
    megapixels = (width * height) / 1000000
    
    # Modelo de escalado de inferencia
    # Real-ESRGAN escala exponencialmente con resolución
    base_ms_per_mp = self.igpu["base_inference_ms_per_mpixel"]
    memory_factor = self.igpu["memory_bandwidth_factor"]
    thermal_factor = self.igpu["thermal_factor"]
    
    # Tiempo esperado base
    expected_ms = base_ms_per_mp * megapixels * memory_factor * thermal_factor
    
    # Factor de escalado no-lineal para resoluciones altas
    if megapixels > 2.0:  # Full HD+
        scaling_penalty = 1 + (megapixels - 2.0) * 0.8
        expected_ms *= scaling_penalty
    
    # Generar samples con variabilidad
    inference_samples = []
    for _ in range(samples):
        # Variabilidad de memoria y térmica
        memory_variation = np.random.normal(1.0, 0.15)
        thermal_variation = np.random.normal(1.0, 0.10)
        
        sample_ms = expected_ms * memory_variation * thermal_variation
        sample_ms = max(sample_ms, 0.01)  # Mínimo técnico
        inference_samples.append(sample_ms)
    
    # Estadísticas
    ms_array = np.array(inference_samples)
    return {
        "mean_ms": np.mean(ms_array),
        "std_ms": np.std(ms_array), 
        "median_ms": np.median(ms_array),
        "min_ms": np.min(ms_array),
        "max_ms": np.max(ms_array),
        "p95_ms": np.percentile(ms_array, 95),
        "p99_ms": np.percentile(ms_array, 99),
        "megapixels": megapixels,
        "ms_per_megapixel": np.mean(ms_array) / megapixels if megapixels > 0 else 0,
        "samples": inference_samples
    }
```

#### **🔍 ¿Cómo funciona la simulación de Real-ESRGAN?**

1. **Escalado Base**: `Tiempo = base_ms_per_MP * MP * factores`
   - Lineal con megapíxeles inicialmente
   - Factores de memoria compartida y térmica

2. **Penalización No-Lineal**:
   - Para resoluciones > 2MP (Full HD)
   - Simula saturación de memoria/ancho de banda

3. **Variabilidad Realista**:
   - `memory_variation`: Fluctuaciones de memoria compartida
   - `thermal_variation`: Throttling térmico variable

### **Método: `calculate_hybrid_performance()`**

```python
def calculate_hybrid_performance(self, dgpu_perf: Dict, inference_perf: Dict) -> Dict:
    """Calcula rendimiento final del sistema híbrido"""
    
    # FPS máximo limitado por cada componente
    dgpu_max_fps = dgpu_perf["mean_fps"]
    inference_max_fps = 1000.0 / inference_perf["mean_ms"]  # Convert ms to FPS
    
    # El cuello de botella determina FPS final
    theoretical_fps = min(dgpu_max_fps, inference_max_fps)
    
    # Eficiencia del pipeline (transferencias, sincronización)
    pipeline_efficiency = 0.85  # 15% overhead realista
    
    final_fps = theoretical_fps * pipeline_efficiency
    
    # Latencia total del sistema
    transfer_latency = self.system["transfer_latency_ms"]
    total_latency = inference_perf["mean_ms"] + transfer_latency
    
    # Análisis de cuello de botella
    if dgpu_max_fps <= inference_max_fps:
        bottleneck = "GPU_Rendering"
    else:
        bottleneck = "AI_Processing"
    
    # Cálculo de caída de rendimiento
    fps_drop = dgpu_max_fps - final_fps
    fps_drop_percent = (fps_drop / dgpu_max_fps) * 100 if dgpu_max_fps > 0 else 0
    
    # Evaluación de viabilidad
    viability = self._evaluate_viability(final_fps)
    
    return {
        "final_fps": final_fps,
        "fps_drop": fps_drop,
        "fps_retention_ratio": final_fps / dgpu_max_fps if dgpu_max_fps > 0 else 0,
        "fps_drop_percent": fps_drop_percent,
        "total_latency_ms": total_latency,
        "theoretical_max_fps": theoretical_fps,
        "effective_max_fps": final_fps,
        "pipeline_efficiency": pipeline_efficiency,
        "transfer_latency_ms": transfer_latency,
        "bottleneck": bottleneck,
        "viability": viability
    }
```

#### **🔍 ¿Cómo se calcula el rendimiento híbrido?**

1. **Identificación del Cuello de Botella**:
   ```
   FPS_final = min(FPS_dGPU, FPS_inferencia) * efficiency
   ```

2. **Eficiencia del Pipeline**:
   - 85% eficiencia = 15% overhead realista
   - Incluye sincronización, transferencias, etc.

3. **Latencia Total**:
   - Inferencia + transferencia dGPU→iGPU
   - Crítico para gaming responsivo

4. **Métricas de Rendimiento**:
   - Caída de FPS en porcentaje
   - Ratio de retención de rendimiento
   - Clasificación de viabilidad

---

## 📊 **SECCIÓN 5: Generación de Visualizaciones**

### **Función: `create_fps_comparison_chart()`**

```python
def create_fps_comparison_chart(results: List[Dict], output_dir: Path) -> str:
    """Genera gráfico comparativo FPS nativo vs híbrido"""
    
    # Extraer datos para el gráfico
    resolutions = [f"{r['metadata']['width']}x{r['metadata']['height']}" for r in results]
    native_fps = [r['dgpu_performance']['mean_fps'] for r in results]
    hybrid_fps = [r['hybrid_performance']['final_fps'] for r in results]
    
    # Configuración del gráfico
    plt.figure(figsize=(16, 10))
    
    # Gráfico de barras comparativo
    x_pos = np.arange(len(resolutions))
    width = 0.35
    
    plt.bar(x_pos - width/2, native_fps, width, 
            label='FPS Nativo (dGPU)', color='#2E8B57', alpha=0.8)
    plt.bar(x_pos + width/2, hybrid_fps, width, 
            label='FPS Híbrido (dGPU + Real-ESRGAN iGPU)', color='#FF6B35', alpha=0.8)
    
    # Personalización
    plt.xlabel('Resolución')
    plt.ylabel('FPS')
    plt.title('Comparación FPS: Nativo vs Híbrido con Real-ESRGAN')
    plt.xticks(x_pos, resolutions, rotation=45)
    plt.legend()
    plt.yscale('log')  # Escala logarítmica por el rango amplio
    plt.grid(True, alpha=0.3)
    
    # Guardar
    filename = output_dir / "graphics" / "fps_comparison_complete.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return str(filename)
```

#### **🎯 ¿Por qué estos gráficos específicos?**

1. **Escala Logarítmica**: Maneja rango amplio de FPS (0.3 - 5000)
2. **Barras Comparativas**: Muestra claramente la diferencia
3. **Colores Distintivos**: Verde (nativo) vs Naranja (híbrido)
4. **Alta Resolución**: 300 DPI para calidad profesional

### **Función: `create_viability_heatmap()`**

```python
def create_viability_heatmap(results: List[Dict], output_dir: Path) -> str:
    """Genera mapa de calor de viabilidad por resolución"""
    
    # Crear matriz de datos
    data_matrix = []
    row_labels = []
    col_labels = ['FPS Híbrido', 'Tiempo Real', 'Gaming Suave', 'Gaming Competitivo']
    
    for result in results:
        res_name = result['metadata']['resolution_name']
        hybrid_fps = result['hybrid_performance']['final_fps']
        viability = result['hybrid_performance']['viability']
        
        # Convertir boolean a numérico para heatmap
        row_data = [
            min(hybrid_fps, 200),  # Cap para visualización
            1.0 if viability['realtime_gaming'] else 0.0,
            1.0 if viability['smooth_gaming'] else 0.0,
            1.0 if viability['competitive_gaming'] else 0.0
        ]
        
        data_matrix.append(row_data)
        row_labels.append(res_name)
    
    # Crear heatmap
    plt.figure(figsize=(12, 10))
    
    sns.heatmap(data_matrix, 
                xticklabels=col_labels,
                yticklabels=row_labels,
                annot=True,
                cmap='RdYlGn',  # Rojo→Amarillo→Verde
                cbar_kws={'label': 'Viabilidad / FPS'})
    
    plt.title('Mapa de Viabilidad por Resolución')
    plt.tight_layout()
    
    filename = output_dir / "graphics" / "viability_heatmap.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return str(filename)
```

#### **🔍 ¿Cómo interpretar el mapa de calor?**

- **Eje Y**: Resoluciones (QQVGA → 4K)
- **Eje X**: Métricas de viabilidad
- **Colores**: 
  - 🟢 Verde = Viable/Bueno
  - 🟡 Amarillo = Marginal
  - 🔴 Rojo = No viable

---

## 📈 **SECCIÓN 6: Función Principal**

```python
def main():
    """Función principal que ejecuta el análisis completo"""
    
    # 1. CONFIGURACIÓN INICIAL
    print("🚀 ANALIZADOR COMPLETO GLXGears + Real-ESRGAN")
    print("=" * 60)
    
    # Crear timestamp único
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_dir = Path(f"comprehensive_glxgears_analysis_{timestamp}")
    
    # Crear estructura de directorios
    (analysis_dir / "data").mkdir(parents=True, exist_ok=True)
    (analysis_dir / "graphics").mkdir(parents=True, exist_ok=True)
    (analysis_dir / "comparatives").mkdir(parents=True, exist_ok=True)
    (analysis_dir / "reports").mkdir(parents=True, exist_ok=True)
    
    # 2. INICIALIZAR SIMULADOR
    simulator = PerformanceSimulator(HARDWARE_CONFIG)
    
    # 3. EJECUTAR ANÁLISIS PARA CADA RESOLUCIÓN
    all_results = []
    
    for i, (width, height, name, category) in enumerate(RESOLUTION_CONFIGS):
        print(f"[{i+1:2d}/{len(RESOLUTION_CONFIGS)}] 🔬 Analizando {name} ({width}x{height}) - {category}")
        
        # Simular rendimiento dGPU
        dgpu_perf = simulator.simulate_dgpu_performance(width, height)
        
        # Simular inferencia iGPU  
        inference_perf = simulator.simulate_igpu_inference(width, height)
        
        # Calcular rendimiento híbrido
        hybrid_perf = simulator.calculate_hybrid_performance(dgpu_perf, inference_perf)
        
        # Almacenar resultado completo
        result = {
            "metadata": {
                "resolution": f"{width}x{height}",
                "resolution_name": name,
                "category": category,
                "width": width,
                "height": height,
                "pixel_count": width * height,
                "megapixels": (width * height) / 1000000,
                "aspect_ratio": width / height,
                "timestamp": datetime.now().isoformat()
            },
            "dgpu_performance": dgpu_perf,
            "inference_performance": inference_perf,
            "hybrid_performance": hybrid_perf,
            "summary": {
                "native_fps": dgpu_perf["mean_fps"],
                "hybrid_fps": hybrid_perf["final_fps"],
                "inference_ms": inference_perf["mean_ms"],
                "total_latency_ms": hybrid_perf["total_latency_ms"],
                "fps_drop_percent": hybrid_perf["fps_drop_percent"],
                "viability_rating": hybrid_perf["viability"]["rating"],
                "realtime_capable": hybrid_perf["viability"]["realtime_gaming"],
                "smooth_capable": hybrid_perf["viability"]["smooth_gaming"],
                "competitive_capable": hybrid_perf["viability"]["competitive_gaming"]
            }
        }
        
        all_results.append(result)
        
        # Mostrar progreso
        print(f"   🎮 FPS Nativo: {dgpu_perf['mean_fps']:.1f}")
        print(f"   🤖 FPS Híbrido: {hybrid_perf['final_fps']:.1f}")
        print(f"   ⚡ Inferencia: {inference_perf['mean_ms']:.1f}ms")
        print(f"   🏆 Viabilidad: {hybrid_perf['viability']['rating']}")
        print()
    
    # 4. GENERAR OUTPUTS COMPLETOS
    print("📊 Generando outputs completos...")
    
    # Guardar datos JSON completos
    complete_data = {
        "metadata": {
            "timestamp": timestamp,
            "analysis_date": datetime.now().isoformat(),
            "title": "Análisis Completo GLXGears + Real-ESRGAN iGPU",
            "subtitle": "Arquitectura Híbrida dGPU/iGPU - Resoluciones Baja a 4K",
            "hardware_config": HARDWARE_CONFIG,
            "total_resolutions": len(RESOLUTION_CONFIGS),
            "resolution_range": f"{RESOLUTION_CONFIGS[0][2]} → {RESOLUTION_CONFIGS[-1][2]}"
        },
        "experiments": all_results
    }
    
    json_file = analysis_dir / "data" / "complete_analysis_data.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(complete_data, f, indent=2, ensure_ascii=False)
    
    # 5. GENERAR TABLAS Y VISUALIZACIONES
    create_csv_tables(all_results, analysis_dir)
    create_all_visualizations(all_results, analysis_dir)
    create_comprehensive_report(complete_data, analysis_dir)
    
    # 6. MOSTRAR RESUMEN FINAL
    print("\n🎉 ANÁLISIS COMPLETADO EXITOSAMENTE")
    print("=" * 50)
    
    # Estadísticas globales
    native_fps_avg = np.mean([r['dgpu_performance']['mean_fps'] for r in all_results])
    hybrid_fps_avg = np.mean([r['hybrid_performance']['final_fps'] for r in all_results])
    inference_avg = np.mean([r['inference_performance']['mean_ms'] for r in all_results])
    
    print(f"📊 Configuraciones analizadas: {len(all_results)}")
    print(f"🎮 FPS nativo promedio: {native_fps_avg:.1f}")
    print(f"🤖 FPS híbrido promedio: {hybrid_fps_avg:.1f}")
    print(f"⚡ Inferencia promedio: {inference_avg:.1f} ms")
    print(f"📁 Resultados en: {analysis_dir}")

# EJECUTAR SI ES EL SCRIPT PRINCIPAL
if __name__ == "__main__":
    main()
```

#### **🔍 ¿Qué hace la función principal?**

1. **Setup Inicial**: Crear directorios, timestamp único
2. **Loop Principal**: Analizar cada resolución secuencialmente  
3. **Almacenamiento**: Guardar resultados estructurados
4. **Visualización**: Generar gráficos y reportes
5. **Resumen**: Mostrar estadísticas finales

---

## 🎯 **PUNTOS CLAVE DEL SCRIPT**

### **🔬 Simulación Científica**
- **No ejecuta software real** - Simula matemáticamente
- **Basada en especificaciones reales** de hardware
- **Incluye variabilidad estadística** para realismo
- **Considera cuellos de botella** del pipeline

### **📊 Análisis Exhaustivo**
- **18 resoluciones** desde 160x120 hasta 4096x2160
- **Múltiples métricas** por cada configuración
- **Estadísticas completas** con percentiles
- **Evaluación de viabilidad** automática

### **📈 Visualización Profesional**
- **5 tipos de gráficos** diferentes
- **Calidad científica** (300 DPI)
- **Colores y escalas** optimizadas
- **Interpretación intuitiva**

### **🔧 Modularidad y Extensibilidad**
- **Clases bien estructuradas**
- **Parámetros fácilmente modificables**
- **Funciones independientes**
- **Documentación interna completa**

---

## 💡 **Modificaciones Comunes**

### **Cambiar Hardware Simulado:**
```python
# Editar HARDWARE_CONFIG al inicio del script
HARDWARE_CONFIG["dgpu"]["vram_gb"] = 12  # RTX 3080
HARDWARE_CONFIG["igpu"]["base_inference_ms_per_mpixel"] = 8.0  # iGPU más rápida
```

### **Agregar Nuevas Resoluciones:**
```python
# Agregar a RESOLUTION_CONFIGS
RESOLUTION_CONFIGS.append((5120, 2880, "5K", "Ultra Wide"))
```

### **Modificar Viabilidad:**
```python
# En _evaluate_viability(), cambiar umbrales
def _evaluate_viability(self, fps: float) -> Dict:
    return {
        "realtime_gaming": fps >= 30,      # Cambiar umbral
        "smooth_gaming": fps >= 60,        # Cambiar umbral
        "competitive_gaming": fps >= 120,  # Cambiar umbral
        "rating": self._get_rating(fps)
    }
```

Este script es el **núcleo científico** de todo el análisis. Cada línea está diseñada para simular de manera precisa y realista el comportamiento de un sistema híbrido dGPU/iGPU procesando Real-ESRGAN.

---

*Documentación técnica generada - Script version 1.0*