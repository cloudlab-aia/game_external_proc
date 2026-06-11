# 📖 MANUAL DE USO PASO A PASO

## 🎯 **Cómo usar el sistema de análisis Real-ESRGAN híbrido**

Esta guía te llevará desde la instalación hasta la interpretación de resultados, **paso a paso**, sin asumir conocimiento previo.

---

## 🚀 **PASO 1: Preparación del Sistema**

### **1.1 Verificar Python**

```bash
# Verificar que tienes Python 3.7 o superior
python3 --version
# Resultado esperado: Python 3.9.x o superior
```

**Si no tienes Python:**
- **Ubuntu/Debian**: `sudo apt install python3 python3-pip`
- **Windows**: Descargar desde https://python.org
- **macOS**: `brew install python3`

### **1.2 Instalar dependencias**

```bash
# Opción 1: Instalación directa
pip3 install numpy pandas matplotlib seaborn openpyxl

# Opción 2: Usando requirements.txt (si lo tienes)
pip3 install -r requirements.txt

# Opción 3: Con conda (recomendado)
conda install numpy pandas matplotlib seaborn openpyxl
```

### **1.3 Verificar instalación**

Crea un archivo `test_dependencies.py`:

```python
#!/usr/bin/env python3

def test_imports():
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__} - OK")
        
        import pandas as pd  
        print(f"✓ Pandas {pd.__version__} - OK")
        
        import matplotlib.pyplot as plt
        print(f"✓ Matplotlib {plt.matplotlib.__version__} - OK")
        
        import seaborn as sns
        print(f"✓ Seaborn {sns.__version__} - OK")
        
        print("\n🎉 ¡Todas las dependencias funcionan correctamente!")
        
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("Ejecuta: pip3 install numpy pandas matplotlib seaborn openpyxl")

if __name__ == "__main__":
    test_imports()
```

```bash
python3 test_dependencies.py
```

---

## 📋 **PASO 2: Obtener el Script Principal**

### **2.1 Descargar el archivo**

Necesitas el archivo `comprehensive_glxgears_realesrgan_analysis.py`. 

**Si no lo tienes**, puedes crearlo copiando el código del script (ver documentación del script principal).

### **2.2 Verificar el archivo**

```bash
# Listar archivos en tu directorio
ls -la *.py

# Verificar que el archivo existe y tiene permisos
ls -la comprehensive_glxgears_realesrgan_analysis.py
```

### **2.3 Hacer el archivo ejecutable (opcional)**

```bash
chmod +x comprehensive_glxgears_realesrgan_analysis.py
```

---

## 🏃 **PASO 3: Ejecutar tu Primer Análisis**

### **3.1 Ejecución básica**

```bash
# Ejecutar con configuración por defecto
python3 comprehensive_glxgears_realesrgan_analysis.py
```

**Salida esperada:**
```
🚀 ANALIZADOR COMPLETO GLXGears + Real-ESRGAN
============================================================
🎯 Análisis exhaustivo desde baja resolución hasta 4K
📊 Generación completa de datos, tablas y gráficos
============================================================
📁 Análisis completo en: comprehensive_glxgears_analysis_20250919_004054

[ 1/18] 🔬 Analizando QQVGA (160x120) - Muy Baja
   🎮 FPS Nativo: 4968.1
   🤖 FPS Híbrido: 539.5
   ⚡ Inferencia: 0.1ms
   🏆 Viabilidad: Excelente

[ 2/18] 🔬 Analizando QVGA (320x240) - Baja
   🎮 FPS Nativo: 3924.5
   🤖 FPS Híbrido: 419.2
   ⚡ Inferencia: 0.5ms
   🏆 Viabilidad: Excelente

...

🎉 ANÁLISIS COMPLETADO EXITOSAMENTE
==================================================
📊 Configuraciones analizadas: 18
🎮 FPS nativo promedio: 822.7
🤖 FPS híbrido promedio: 112.6
⚡ Inferencia promedio: 429.5 ms
📁 Resultados en: comprehensive_glxgears_analysis_20250919_004054
```

### **3.2 ¿Qué hace exactamente?**

Durante la ejecución, el sistema:
1. **Crea carpeta única** con timestamp
2. **Simula 18 resoluciones** desde 160x120 hasta 4096x2160
3. **Calcula rendimiento** para cada configuración
4. **Genera archivos** de datos, gráficos y reportes
5. **Muestra resumen** de resultados principales

### **3.3 Tiempo de ejecución**

**Típicamente**: 10-30 segundos dependiendo de tu sistema.

---

## 📁 **PASO 4: Explorar los Resultados**

### **4.1 Navegar a la carpeta generada**

```bash
# El sistema crea una carpeta con timestamp único
cd comprehensive_glxgears_analysis_YYYYMMDD_HHMMSS

# Listar contenidos
ls -la
```

**Estructura esperada:**
```
📁 comprehensive_glxgears_analysis_20250919_004054/
├── 📊 data/         # Datos numéricos
├── 📈 graphics/     # Gráficos principales  
├── 🔍 comparatives/ # Gráficos comparativos
└── 📝 reports/      # Documentación
```

### **4.2 Primer vistazo: Gráfico principal**

**Ver la comparación FPS:**
```bash
# En Linux
xdg-open graphics/fps_comparison_complete.png

# En Windows
start graphics/fps_comparison_complete.png

# En macOS  
open graphics/fps_comparison_complete.png
```

**¿Qué verás?**
- 🟢 **Barras verdes**: FPS nativo (dGPU sola)
- 🟠 **Barras naranjas**: FPS híbrido (con Real-ESRGAN)
- **Diferencia**: Impacto del procesamiento IA

### **4.3 Segundo vistazo: Mapa de viabilidad**

```bash
# Ver el heatmap de viabilidad
xdg-open graphics/viability_heatmap.png
```

**¿Qué verás?**
- 🟢 **Verde**: Configuraciones viables
- 🟡 **Amarillo**: Configuraciones marginales  
- 🔴 **Rojo**: Configuraciones no viables

---

## 📊 **PASO 5: Analizar Datos Detallados**

### **5.1 Abrir la tabla principal**

**Opción A: CSV (recomendado para análisis)**
```bash
# Abrir con LibreOffice/Excel
libreoffice data/tabla_completa_resultados.csv
```

**Opción B: Excel nativo**
```bash
# Si tienes Excel
excel data/tabla_completa_resultados.xlsx
```

### **5.2 Interpretar las columnas clave**

**Enfócate en estas columnas:**

| **Columna** | **¿Qué significa?** | **¿Cómo interpretarla?** |
|-------------|---------------------|--------------------------|
| `FPS_Híbrido` | Tu FPS final real | **≥120**: Excelente, **60-119**: Bueno, **30-59**: Aceptable, **<30**: Insuficiente |
| `Inferencia_ms` | Tiempo por frame | **<16ms**: Imperceptible, **16-33ms**: Tolerable, **>33ms**: Problemático |
| `Caída_FPS_%` | Pérdida por IA | **<80%**: Impacto bajo, **80-90%**: Impacto alto, **>90%**: Impacto severo |
| `Valoración` | Evaluación global | **Excelente**: Úsala, **Bueno**: Viable, **Aceptable**: Límite, **Insuficiente**: No viable |

### **5.3 Buscar configuraciones óptimas**

**Filtrar por viabilidad:**
1. **Para gaming competitivo**: `Competitivo = True`
2. **Para gaming casual**: `Suave = True`  
3. **Para tiempo real**: `Tiempo_Real = True`

---

## 🎯 **PASO 6: Casos de Uso Comunes**

### **Caso A: "¿Qué resolución debo usar?"**

**Método rápido:**
1. Abrir `viability_heatmap.png`
2. Buscar filas completamente verdes
3. Esas resoluciones son tus mejores opciones

**Método detallado:**
1. Abrir `tabla_completa_resultados.csv`
2. Filtrar `Valoración = "Excelente"` 
3. Ordenar por `FPS_Híbrido` descendente
4. Las primeras filas son tus mejores opciones

### **Caso B: "¿Cuál es mi límite superior?"**

**Buscar el punto de ruptura:**
1. Abrir `tabla_completa_resultados.csv`
2. Buscar donde `Valoración` cambia de "Aceptable" a "Insuficiente"
3. La resolución anterior es tu límite superior

**Ejemplo típico:**
- **VGA (640x480)**: Última resolución "Excelente"
- **SVGA (800x600)**: Primera resolución "Buena"  
- **HD (1280x720)**: Primera resolución "Aceptable"
- **Full HD (1920x1080)**: Primera resolución "Insuficiente"

### **Caso C: "¿Vale la pena el Real-ESRGAN?"**

**Análisis de trade-off:**
1. Ver `fps_comparison_complete.png`
2. Comparar altura de barras verdes vs naranjas
3. **Diferencia pequeña**: Vale la pena
4. **Diferencia enorme**: Tal vez no

**Métricas numéricas:**
- **Caída FPS < 85%**: Razonable
- **Caída FPS 85-95%**: Costoso pero posible
- **Caída FPS > 95%**: Probablemente no vale la pena

---

## 🔧 **PASO 7: Personalización Básica**

### **7.1 Modificar hardware simulado**

**Editar el script para tu hardware:**

```python
# Buscar HARDWARE_CONFIG en el script
HARDWARE_CONFIG = {
    "dgpu": {
        "name": "Tu GPU",                    # Cambiar nombre
        "vram_gb": 12,                       # Tu VRAM real
        "base_performance": 1.2,             # Si tienes GPU más potente
        "thermal_throttling": 0.90           # Si tienes problemas térmicos
    },
    "igpu": {
        "name": "Tu iGPU", 
        "base_inference_ms_per_mpixel": 8.0, # Si tu iGPU es más rápida
        "memory_bandwidth_factor": 1.1,     # Si tienes mejor memoria
        "thermal_factor": 1.3                # Si tu iGPU se calienta más
    }
}
```

### **7.2 Agregar resoluciones personalizadas**

**Agregar tu resolución específica:**

```python  
# Buscar RESOLUTION_CONFIGS en el script
RESOLUTION_CONFIGS = [
    # Resoluciones existentes...
    (1920, 1080, "FHD", "Full HD"),
    # Tu resolución personalizada:
    (2560, 1600, "WQXGA", "Mi Resolución Custom"),
    # Más resoluciones...
]
```

### **7.3 Cambiar umbrales de viabilidad**

**Si tus estándares son diferentes:**

```python
# Buscar _evaluate_viability en el script
def _evaluate_viability(self, fps: float) -> Dict:
    return {
        "realtime_gaming": fps >= 24,     # En lugar de 30
        "smooth_gaming": fps >= 50,       # En lugar de 60  
        "competitive_gaming": fps >= 100, # En lugar de 120
        "rating": self._get_rating(fps)
    }
```

---

## 📈 **PASO 8: Análisis Avanzado**

### **8.1 Usar datos JSON para análisis custom**

**Cargar datos en Python:**

```python
import json

# Cargar datos completos
with open('data/complete_analysis_data.json', 'r') as f:
    data = json.load(f)

# Acceder a un experimento específico  
first_experiment = data['experiments'][0]
fps_samples = first_experiment['dgpu_performance']['samples']

# Hacer análisis personalizado
import numpy as np
print(f"Variabilidad FPS: {np.std(fps_samples):.2f}")
```

### **8.2 Crear gráficos personalizados**

```python
import pandas as pd
import matplotlib.pyplot as plt

# Cargar tabla
df = pd.read_csv('data/tabla_completa_resultados.csv')

# Gráfico personalizado: Latencia vs Megapíxeles  
plt.figure(figsize=(12, 8))
plt.scatter(df['Megapíxeles'], df['Inferencia_ms'], alpha=0.7)
plt.xlabel('Megapíxeles')
plt.ylabel('Tiempo de Inferencia (ms)')  
plt.title('Escalado de Real-ESRGAN por Resolución')
plt.yscale('log')
plt.grid(True, alpha=0.3)
plt.show()
```

### **8.3 Comparar múltiples análisis**

**Para comparar diferentes configuraciones:**

```bash
# Ejecutar con diferentes configuraciones
python3 comprehensive_glxgears_realesrgan_analysis.py
# Cambiar hardware en el script
python3 comprehensive_glxgears_realesrgan_analysis.py

# Tendrás dos carpetas:
# comprehensive_glxgears_analysis_20250919_100000/
# comprehensive_glxgears_analysis_20250919_110000/
```

**Comparar resultados:**
```python
import pandas as pd

# Cargar ambos análisis
df1 = pd.read_csv('analysis_1/data/tabla_completa_resultados.csv')
df2 = pd.read_csv('analysis_2/data/tabla_completa_resultados.csv')

# Comparar FPS híbrido
comparison = pd.DataFrame({
    'Resolución': df1['Resolución'],
    'Config_1': df1['FPS_Híbrido'],
    'Config_2': df2['FPS_Híbrido'],
    'Diferencia': df2['FPS_Híbrido'] - df1['FPS_Híbrido']
})

print(comparison)
```

---

## 🔍 **PASO 9: Troubleshooting Común**

### **Error 1: ModuleNotFoundError**

```
ImportError: No module named 'numpy'
```

**Solución:**
```bash
pip3 install numpy pandas matplotlib seaborn openpyxl
```

### **Error 2: Font warnings**

```
findfont: Font family 'Arial' not found.
```

**Solución (ignorar o arreglar):**
- **Ignorar**: No afecta funcionamiento, solo estética
- **Arreglar**: `sudo apt-get install ttf-mscorefonts-installer`

### **Error 3: Permissions**

```
PermissionError: [Errno 13] Permission denied
```

**Solución:**
```bash
# Verificar permisos del directorio actual
ls -la
# Cambiar al directorio home si es necesario
cd ~
```

### **Error 4: Memoria insuficiente**

```
MemoryError: Unable to allocate array
```

**Solución:**
```bash
# Reducir número de samples en el script
# Cambiar: samples: int = 20
# Por: samples: int = 10
```

---

## 📚 **PASO 10: Recursos para Profundizar**

### **10.1 Archivos de documentación**

Si ejecutaste el análisis, tienes estos archivos adicionales:
- `DOCUMENTACION_COMPLETA_ARQUITECTURA.md` - Arquitectura del sistema
- `EXPLICACION_SCRIPT_PRINCIPAL.md` - Código línea por línea  
- `GUIA_INTERPRETACION_ARCHIVOS.md` - Cómo leer cada archivo
- `TECNOLOGIAS_Y_DEPENDENCIAS.md` - Bibliotecas utilizadas

### **10.2 Comandos útiles para explorar**

```bash
# Ver todas las imágenes generadas
ls -la graphics/ comparatives/

# Ver tamaños de archivo  
du -h data/*

# Contar líneas del reporte
wc -l reports/ANALISIS_ARQUITECTONICO_COMPLETO.md

# Buscar configuraciones excelentes
grep "Excelente" data/tabla_completa_resultados.csv
```

### **10.3 Próximos pasos recomendados**

1. **Experimentar**: Cambiar parámetros y ver diferencias
2. **Validar**: Comparar con hardware real si tienes acceso
3. **Extender**: Agregar otros modelos de IA (DLSS, FSR)
4. **Optimizar**: Encontrar configuración perfecta para tu sistema

---

## 🎯 **RESUMEN EJECUTIVO**

### **Para usuarios básicos:**
1. `python3 comprehensive_glxgears_realesrgan_analysis.py`
2. Abrir `graphics/viability_heatmap.png`
3. Buscar filas verdes = resoluciones viables
4. ¡Listo!

### **Para usuarios avanzados:**
1. Personalizar `HARDWARE_CONFIG` por tu sistema
2. Ejecutar análisis
3. Analizar `data/tabla_completa_resultados.csv`
4. Crear análisis custom con `data/complete_analysis_data.json`

### **Para presentaciones:**
1. Usar `graphics/fps_comparison_complete.png` como gráfico principal
2. Complementar con `reports/ANALISIS_ARQUITECTONICO_COMPLETO.md`
3. Datos de apoyo en `data/tabla_completa_resultados.xlsx`

---

**¿Necesitas ayuda específica?** Consulta las secciones de troubleshooting y los archivos de documentación generados. El sistema está diseñado para ser autoexplicativo y generar toda la información necesaria para su interpretación.

---

*Manual de uso completo - Versión 1.0*