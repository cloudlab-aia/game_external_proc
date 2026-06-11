# 🛠️ TECNOLOGÍAS Y DEPENDENCIAS: Guía Completa

## 🎯 **¿Qué tecnologías usa el sistema y por qué?**

Este documento explica **cada tecnología** utilizada en el análisis, por qué fue elegida, y cómo se integra en el sistema híbrido.

---

## 🐍 **LENGUAJE BASE: Python 3**

### **¿Por qué Python?**
- **Ecosistema científico**: NumPy, SciPy, Pandas, Matplotlib
- **Facilidad de desarrollo**: Sintaxis clara y legible
- **Bibliotecas de IA**: TensorFlow, PyTorch, OpenVINO compatibles
- **Multiplataforma**: Linux, Windows, macOS
- **Comunidad**: Amplia comunidad científica y técnica

### **Versión requerida:**
```bash
Python 3.7+ (recomendado: Python 3.9-3.11)
```

---

## 📊 **BIBLIOTECAS PRINCIPALES**

### **📈 NumPy - Computación Numérica**

```python
import numpy as np
```

#### **¿Para qué se usa?**
- **Cálculos estadísticos**: Media, desviación, percentiles
- **Simulación matemática**: Generación de variabilidad realista
- **Operaciones vectorizadas**: Procesamiento eficiente de arrays

#### **Funciones clave utilizadas:**
```python
# Estadísticas
np.mean(fps_array)           # FPS promedio
np.std(fps_array)            # Desviación estándar
np.percentile(fps_array, 95) # Percentil 95

# Distribuciones aleatorias
np.random.normal(1.0, 0.12)  # Variabilidad térmica
np.random.uniform(0.9, 1.1)  # Variabilidad de carga

# Operaciones vectoriales
fps_array = np.array(fps_samples)  # Conversión para cálculos eficientes
```

#### **¿Por qué NumPy?**
- **Rendimiento**: 10-100x más rápido que Python puro
- **Precisión numérica**: Tipos de datos optimizados
- **Integración**: Base para todas las bibliotecas científicas
- **Memoria eficiente**: Arrays compactos vs listas Python

### **🗂️ Pandas - Manipulación de Datos**

```python
import pandas as pd
```

#### **¿Para qué se usa?**
- **Creación de tablas**: DataFrames estructurados
- **Exportación CSV/Excel**: Formatos compatibles
- **Análisis estadístico**: Agrupaciones y agregaciones

#### **Operaciones principales:**
```python
# Crear DataFrame desde resultados
df = pd.DataFrame({
    'Resolución': resolutions,
    'FPS_Nativo': native_fps,
    'FPS_Híbrido': hybrid_fps,
    # ... más columnas
})

# Exportar a diferentes formatos
df.to_csv('resultados.csv', index=False, encoding='utf-8')
df.to_excel('resultados.xlsx', index=False)

# Estadísticas descriptivas
df.describe()  # Min, max, media, percentiles automáticos
```

#### **¿Por qué Pandas?**
- **Versatilidad**: Múltiples formatos de salida
- **Facilidad**: Sintaxis intuitiva para manipulación
- **Compatibilidad**: Excel, CSV, JSON, SQL
- **Análisis**: Herramientas estadísticas integradas

### **📊 Matplotlib - Visualización Base**

```python
import matplotlib.pyplot as plt
```

#### **¿Para qué se usa?**
- **Gráficos científicos**: Barras, líneas, scatter plots
- **Configuración avanzada**: Escalas, colores, layouts
- **Exportación de alta calidad**: PNG, PDF, SVG

#### **Configuraciones clave:**
```python
# Configuración de figura
plt.figure(figsize=(16, 10))  # Tamaño optimizado
plt.dpi = 300                 # Alta resolución

# Gráficos de barras comparativas
plt.bar(x_pos - width/2, native_fps, width, 
        label='FPS Nativo', color='#2E8B57', alpha=0.8)
plt.bar(x_pos + width/2, hybrid_fps, width, 
        label='FPS Híbrido', color='#FF6B35', alpha=0.8)

# Escalas especializadas
plt.yscale('log')  # Escala logarítmica para rango amplio
plt.grid(True, alpha=0.3)  # Grid sutil para lectura

# Exportación profesional
plt.savefig(filename, dpi=300, bbox_inches='tight')
```

#### **¿Por qué Matplotlib?**
- **Control total**: Personalización extrema de gráficos
- **Calidad científica**: Estándar en publicaciones
- **Escalas especializadas**: Logarítmica, semilog, etc.
- **Formatos múltiples**: PNG, PDF, SVG, EPS

### **🎨 Seaborn - Visualización Estadística**

```python
import seaborn as sns
```

#### **¿Para qué se usa?**
- **Mapas de calor (heatmaps)**: Viabilidad por resolución
- **Paletas de colores**: Científicamente optimizadas
- **Gráficos estadísticos**: Distribuciones, correlaciones

#### **Implementación principal:**
```python
# Heatmap de viabilidad
sns.heatmap(data_matrix, 
            xticklabels=col_labels,
            yticklabels=row_labels,
            annot=True,                    # Valores numéricos
            cmap='RdYlGn',                # Rojo→Amarillo→Verde
            cbar_kws={'label': 'Viabilidad'})
```

#### **¿Por qué Seaborn?**
- **Paletas optimizadas**: Colores científicamente válidos
- **Heatmaps avanzados**: Anotaciones automáticas
- **Integración Pandas**: DataFrames nativos
- **Estilo profesional**: Defaults optimizados

---

## 💾 **FORMATOS DE DATOS**

### **📝 JSON - Almacenamiento Estructurado**

```python
import json
```

#### **¿Para qué se usa?**
- **Datos completos**: Estructura jerárquica completa
- **Metadatos**: Configuración y timestamps
- **Interoperabilidad**: Lecturable por múltiples lenguajes

#### **Estructura típica:**
```python
complete_data = {
    "metadata": {
        "timestamp": "20250919_004054",
        "hardware_config": HARDWARE_CONFIG,
        "total_resolutions": 18
    },
    "experiments": [
        {
            "metadata": { /* resolución */ },
            "dgpu_performance": { /* métricas dGPU */ },
            "inference_performance": { /* métricas inferencia */ },
            "hybrid_performance": { /* métricas finales */ }
        }
        // ... para cada resolución
    ]
}

# Guardar con formato legible
json.dump(complete_data, f, indent=2, ensure_ascii=False)
```

#### **¿Por qué JSON?**
- **Estructura jerárquica**: Datos complejos organizados
- **Legibilidad humana**: Fácil inspección manual
- **Universalidad**: Compatible con todos los lenguajes
- **Preservación de tipos**: Números, strings, booleans

### **📊 CSV - Datos Tabulares**

```python
import csv
```

#### **¿Para qué se usa?**
- **Tablas simples**: Resultados principales
- **Compatibilidad Excel**: Fácil importación
- **Análisis externo**: R, MATLAB, etc.

#### **Ventajas del CSV:**
- **Simplicidad**: Formato de texto plano
- **Tamaño**: Compacto vs JSON/XML
- **Universalidad**: Soportado por todo software
- **Velocidad**: Carga rápida en herramientas

### **📈 Excel (.xlsx) - Presentación**

```python
# Via pandas
df.to_excel('resultados.xlsx', index=False)
```

#### **¿Para qué se usa?**
- **Presentaciones profesionales**: Formato empresarial
- **Análisis manual**: Filtros, ordenamiento nativo
- **Compatibilidad**: Office, LibreOffice, Google Sheets

---

## 🕰️ **UTILIDADES DEL SISTEMA**

### **📅 DateTime - Timestamps**

```python
from datetime import datetime
```

#### **¿Para qué se usa?**
- **Nombres únicos**: Carpetas sin conflictos
- **Trazabilidad**: Cuándo se ejecutó cada análisis
- **Metadatos**: Información temporal en reportes

#### **Formato utilizado:**
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# Resultado: "20250919_004054"

iso_timestamp = datetime.now().isoformat()
# Resultado: "2025-09-19T00:40:54.880771"
```

### **🗃️ PathLib - Gestión de Archivos**

```python
from pathlib import Path
```

#### **¿Para qué se usa?**
- **Rutas multiplataforma**: Windows/Linux/macOS
- **Creación de directorios**: Estructura organizada
- **Operaciones de archivo**: Manejo moderno

#### **Operaciones principales:**
```python
# Crear estructura de directorios
analysis_dir = Path(f"comprehensive_glxgears_analysis_{timestamp}")
(analysis_dir / "data").mkdir(parents=True, exist_ok=True)
(analysis_dir / "graphics").mkdir(parents=True, exist_ok=True)

# Rutas seguras multiplataforma
json_file = analysis_dir / "data" / "complete_analysis_data.json"
```

### **🎲 Random - Variabilidad Estadística**

```python
import random
```

#### **¿Para qué se usa?**
- **Simulación realista**: Variaciones térmicas y de carga
- **Reproducibilidad**: Seeds para resultados consistentes
- **Distribuciones**: Normal, uniforme, exponencial

---

## 🔧 **CONCEPTOS DE HARDWARE SIMULADOS**

### **🎮 Especificaciones dGPU**

#### **NVIDIA GeForce Architecture:**
```python
dgpu_specs = {
    "name": "NVIDIA GeForce RTX/GTX",
    "vram_gb": 8,                    # VRAM dedicada
    "cuda_cores": 2048,              # Cores de procesamiento
    "base_performance": 1.0,         # Multiplicador de rendimiento
    "thermal_throttling": 0.95       # Factor de throttling térmico
}
```

#### **Modelado de rendimiento:**
- **Escalado por resolución**: FPS inversamente proporcional a megapíxeles
- **Variabilidad térmica**: Fluctuaciones por temperatura GPU
- **Factores de carga**: Variaciones del sistema operativo

### **🧠 Especificaciones iGPU**

#### **Intel Iris Xe Graphics:**
```python
igpu_specs = {
    "name": "Intel Iris Xe Graphics",
    "vram_shared_gb": 4,             # Memoria compartida con sistema
    "execution_units": 96,           # Unidades de ejecución paralela
    "base_inference_ms_per_mpixel": 12.0,  # Tiempo base por MP
    "memory_bandwidth_factor": 1.3,  # Penalización memoria compartida
    "thermal_factor": 1.2            # Factor térmico adicional
}
```

#### **Modelado de inferencia Real-ESRGAN:**
- **Escalado exponencial**: Tiempo crece no-linealmente
- **Limitaciones de memoria**: Factor de ancho de banda compartida
- **Throttling térmico**: Reducción por calentamiento iGPU

### **⚙️ Sistema de Interconexión**

#### **Especificaciones del sistema:**
```python
system_specs = {
    "cpu": "Intel Core i5-12400 / i7-12700",
    "ram_gb": 16,                    # RAM del sistema
    "pcie_lanes": 16,                # Carriles PCIe
    "transfer_latency_ms": 1.5       # Latencia dGPU→iGPU
}
```

#### **Pipeline híbrido:**
- **Transferencia de frames**: Latencia constante dGPU→memoria→iGPU
- **Sincronización**: Overhead del pipeline combinado
- **Eficiencia total**: 85% (15% overhead realista)

---

## 🔬 **METODOLOGÍA CIENTÍFICA**

### **📊 Modelado Estadístico**

#### **Distribuciones utilizadas:**
```python
# Variabilidad térmica (distribución normal)
thermal_variation = np.random.normal(1.0, 0.12)
# Media: 1.0, Desviación: 0.12 (12% variabilidad)

# Variabilidad de carga (distribución normal)  
load_variation = np.random.normal(1.0, 0.08)
# Media: 1.0, Desviación: 0.08 (8% variabilidad)

# Variabilidad de memoria (distribución normal)
memory_variation = np.random.normal(1.0, 0.15)  
# Media: 1.0, Desviación: 0.15 (15% variabilidad)
```

#### **¿Por qué estas distribuciones?**
- **Normal (Gaussiana)**: Modela variaciones naturales del hardware
- **Parámetros realistas**: Basados en mediciones reales de sistemas
- **Reproducibilidad**: Seeds permiten resultados consistentes

### **📈 Modelos de Escalado**

#### **Rendimiento dGPU:**
```python
base_fps = 5000 / (1 + megapixels * 0.6)
# Escalado hiperbólico: realista para renderizado 3D
```

#### **Inferencia iGPU:**
```python
expected_ms = base_ms_per_mp * megapixels * memory_factor * thermal_factor
# Escalado lineal base + factores multiplicativos

# Penalización no-lineal para resoluciones altas
if megapixels > 2.0:
    scaling_penalty = 1 + (megapixels - 2.0) * 0.8
    expected_ms *= scaling_penalty
```

---

## 🚀 **INSTALACIÓN Y CONFIGURACIÓN**

### **📦 Dependencias requeridas:**

```bash
# Instalación via pip
pip install numpy pandas matplotlib seaborn openpyxl

# Instalación via conda (recomendado)
conda install numpy pandas matplotlib seaborn openpyxl
```

### **📋 Lista completa de dependencias:**

```txt
# requirements.txt
numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
seaborn>=0.11.0
openpyxl>=3.0.0
```

### **🔧 Verificación de instalación:**

```python
#!/usr/bin/env python3

# Script de verificación
def verify_dependencies():
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
        
        import pandas as pd
        print(f"✓ Pandas {pd.__version__}")
        
        import matplotlib
        print(f"✓ Matplotlib {matplotlib.__version__}")
        
        import seaborn as sns
        print(f"✓ Seaborn {sns.__version__}")
        
        print("\n🎉 Todas las dependencias están instaladas correctamente")
        
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("Instala las dependencias faltantes con:")
        print("pip install numpy pandas matplotlib seaborn openpyxl")

if __name__ == "__main__":
    verify_dependencies()
```

---

## 🎯 **ALTERNATIVAS Y EXTENSIONES**

### **📊 Alternativas de visualización:**

#### **Plotly** (Interactivo):
```python
# Para gráficos interactivos web
import plotly.graph_objects as go
import plotly.express as px
```

#### **Bokeh** (Dashboard):
```python
# Para dashboards interactivos
from bokeh.plotting import figure, show
from bokeh.layouts import column, row
```

### **🔢 Alternativas de cálculo:**

#### **SciPy** (Análisis avanzado):
```python
# Para estadísticas avanzadas
from scipy import stats
from scipy.optimize import curve_fit
```

#### **Scikit-learn** (Machine Learning):
```python
# Para análisis predictivo
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
```

### **💾 Alternativas de almacenamiento:**

#### **HDF5** (Datos grandes):
```python
# Para datasets masivos
import h5py
```

#### **Parquet** (Columnar):
```python
# Para análisis de big data
import pyarrow.parquet as pq
```

---

## 🔍 **DEBUGGING Y TROUBLESHOOTING**

### **🐛 Problemas comunes:**

#### **Fuentes no encontradas (Matplotlib):**
```
findfont: Font family 'Arial' not found.
```

**Solución:**
```python
# Usar fuente por defecto del sistema
plt.rcParams['font.family'] = 'DejaVu Sans'

# O instalar fuentes Arial
sudo apt-get install ttf-mscorefonts-installer  # Ubuntu/Debian
```

#### **Memoria insuficiente:**
```python
# Para datasets grandes, procesar en chunks
chunk_size = 1000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    process_chunk(chunk)
```

#### **Encoding de caracteres:**
```python
# Siempre especificar encoding UTF-8
with open(file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
```

---

## 📚 **RECURSOS ADICIONALES**

### **📖 Documentación oficial:**
- **NumPy**: https://numpy.org/doc/
- **Pandas**: https://pandas.pydata.org/docs/
- **Matplotlib**: https://matplotlib.org/stable/
- **Seaborn**: https://seaborn.pydata.org/

### **🎓 Tutoriales recomendados:**
- **Python científico**: https://scipy-lectures.org/
- **Visualización de datos**: https://python-graph-gallery.com/
- **Análisis estadístico**: https://www.statsmodels.org/

---

Cada tecnología en este sistema fue **cuidadosamente seleccionada** para un propósito específico. La combinación de NumPy + Pandas + Matplotlib + Seaborn forma el **stack científico estándar** de Python, garantizando compatibilidad, rendimiento y mantenibilidad a largo plazo.

---

*Documentación de tecnologías - Versión 1.0*