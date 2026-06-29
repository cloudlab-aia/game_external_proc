# Investigación: pantalla oculta rápida para la arquitectura híbrida

Registro completo del estudio para conseguir que el juego renderice en una
**pantalla oculta** (no visible directamente) con **rendimiento nativo** de la
dGPU, de modo que el usuario vea una sola ventana (la salida reescalada por IA).
Incluye todas las vías probadas, los datos medidos y la conclusión.

Hardware: NVIDIA RTX 5060 (dGPU, PCI:1:0:0) + Intel Arrow Lake iGPU
(PCI:0:2:0). Sesión: KDE **Wayland**, escritorio renderizado por la NVIDIA
(PrimaryGPU). Monitor en la NVIDIA (DP-2/HDMI-A-3 conectados).

---

## 1. Objetivo y restricción

La arquitectura híbrida necesita: el juego renderiza en la dGPU (rápido) en una
pantalla **oculta**, se captura cada frame, la iGPU reescala con IA, y se muestra
**una sola ventana** con el resultado.

Requisito triple, en conflicto: **rápido (GPU nativa) + oculto + capturable**.
Capturar exige que el juego **presente** frames; presentar exige una **salida**;
una salida rápida es **GPU-hardware**; una salida GPU-hardware oculta requiere un
segundo servidor de pantalla.

---

## 2. Vías probadas (todas, con resultado y causa)

| Vía | Oculto | Rápido (shaders) | Resultado / causa |
|---|---|---|---|
| **Single-window** (juego en `:1`, tapado por overlay) | ⚠️ ventana existe, invisible | ✅ 33 FPS | Funciona. El juego renderiza nativo en la sesión; el overlay lo cubre. |
| **Xvfb + PRIME** | ✅ | ❌ 50× lento | El "display" es software (CPU/llvmpipe). Trasvase GPU→CPU + sincronización por frame. Mortal con muchas pasadas (shaders). |
| **VirtualGL + Xvfb** | ✅ | ❌ (incompatible) | Crashea con Minecraft moderno (1.21, motor GL nuevo). 1.12.2 funciona pero no soporta shaders modernos (Iris/Photon necesitan ≥1.16). |
| **gamescope (con ventana)** | ❌ ventana visible | ✅ nativo | Captura OK (glxgears 144 FPS dentro de gamescope). Pero deja ventana visible (mismo caso que single-window). |
| **gamescope --headless** | ✅ | — | 0 FPS: sin salida no hay vblank, el juego no presenta → no se captura. Backend headless además crashea en esta NVIDIA. |
| **X headless en NVIDIA** | ✅ | ✅ | ❌ `drmSetMaster failed: Device or resource busy`. La NVIDIA la tiene la sesión. |
| **X headless en Intel** | ✅ | ✅ | GLAMOR (hardware) **inicializa bien**, pero ❌ también `drmSetMaster failed: busy`. La Intel (GPU de arranque) también la retiene la sesión. |

---

## 3. La causa raíz (lo importante)

**El compositor de la sesión (KDE Wayland) retiene el DRM master de las DOS
GPUs.** No solo la que renderiza el escritorio (NVIDIA), sino también la Intel
(es la GPU de arranque / KMS primario).

`drmSetMaster` es el permiso para hacer *modesetting* (controlar una pantalla).
Solo un proceso por GPU y asiento puede tenerlo. La sesión activa lo tiene en
ambas → **ningún segundo servidor X con aceleración hardware puede arrancar
mientras el escritorio está abierto**, en ninguna de las dos GPUs.

Comprobado en logs:
- NVIDIA: `NVIDIA(GPU-0): Failed to acquire modesetting permission`.
- Intel: `modeset(0): drmSetMaster failed: Device or resource busy` (tras
  inicializar GLAMOR correctamente y con un conector forzado a "connected").

Detalle adicional: al arrancar el X sobre la Intel, Xorg intentaba auto-enganchar
la NVIDIA como GPU secundaria (PRIME) y fallaba el `drmSetMaster` de la NVIDIA;
con `Option "AutoBindGPU" "false"` se evitó eso, pero entonces falló el
`drmSetMaster` de la **propia Intel** → confirmando que ambas están ocupadas.

---

## 4. Datos medidos (clave para la memoria)

### 4.1 Aislar la culpa: glmark2 (escena pesada, reporta sus FPS)
Misma escena (`refract`), 800×600:

| Camino | FPS |
|---|---|
| `:1` nativo (sin wrapper) | **6683** |
| `:2` PRIME-Xvfb (sin wrapper) | **134** (50× más lento) |
| `:2` PRIME-Xvfb + wrapper de captura | **125** (el wrapper solo resta **−7%**) |

**Conclusión:** el wrapper de captura propio NO es el problema (−7%). El 100% de
la lentitud es el par **PRIME + Xvfb (software)**.

### 4.2 Minecraft + Photon (shaders pesados), render 854×480

| Configuración | FPS de render |
|---|---|
| Single-window (`:1`, NVIDIA nativo) | ~33 |
| Pantalla virtual (Xvfb + PRIME) | ~8 |

A 1080p nativo con Photon: **9,5 FPS** (GPU 97%, saturada).
Híbrida (render 854×480 + IA iGPU → 1080p): **29 FPS** → **3,1×** la nativa.

---

## 5. Por qué Xvfb se hunde con shaders pero no sin ellos

El sobrecoste de Xvfb es **por pasada de render**. Sin shaders, Minecraft hace
pocas pasadas → tolerable, jugable en una ventana. Photon hace **decenas de
pasadas** (sombras, GI, reflejos), y cada una sufre la sincronización
NVIDIA↔Xvfb → se acumula → 8 FPS. No es "todo o nada": existe un umbral de
calidad de shaders por debajo del cual la pantalla virtual sigue siendo jugable.

---

## 6. Conclusión

**En un escritorio de un solo asiento, no es posible una segunda pantalla oculta
acelerada por hardware mientras la sesión gráfica está activa**, porque el
compositor retiene el DRM master de todas las GPUs. La única pantalla oculta
disponible es por software (Xvfb), 50× más lenta y solo viable para contenido
ligero.

Para "oculto + rápido + separado" harían falta cambios inviables para una demo:
apagar la sesión gráfica (arranque headless/servidor), una GPU adicional dedicada
al escritorio, o reconfigurar PRIME y reiniciar.

### Implicación para la arquitectura
- **Rendimiento (beneficio 3×)**: se demuestra con captura directa en la sesión
  (single-window), render nativo. Validado.
- **Una sola ventana visible**: el overlay fullscreen cubre la ventana del juego
  → el usuario solo ve la salida IA (se cumple la intención del enunciado: no
  mostrar el render crudo).
- **Pantalla oculta de verdad (Xvfb)**: válida para contenido ligero/moderado
  (jugable en una ventana), pero no para shaders extremos.

### Valor para la memoria
Este estudio es un **análisis de viabilidad de sistemas** con datos: documenta
por qué la pantalla virtual rápida y oculta no es alcanzable en este hardware
(DRM master compartido), cuantifica el sobrecoste del render por software
(50×), y aísla que la captura propia es eficiente (−7%). Justifica con rigor la
decisión de arquitectura final.

---

## 7. Comandos/artefactos de referencia

- Diagnóstico glmark2 3 caminos: `/tmp/diag_glmark.py`.
- Config X headless (NVIDIA): `/tmp/headless_nvidia.conf` (falló: modesetting busy).
- Config X headless (Intel): `/tmp/headless_intel.conf` (falló: drmSetMaster busy
  pese a GLAMOR + conector forzado + AutoBindGPU=false).
- Forzar/revertir conector Intel: `echo on|detect | sudo tee /sys/class/drm/card1-HDMI-A-1/status`.
- Errores clave en `/var/log/Xorg.5.log` (NVIDIA) y `/var/log/Xorg.6.log` (Intel).
