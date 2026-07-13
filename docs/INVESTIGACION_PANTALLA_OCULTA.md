# Investigación: pantalla oculta rápida para la arquitectura híbrida

Registro completo del estudio para conseguir que el juego renderice en una
**pantalla oculta** (no visible directamente) con **rendimiento nativo** de la
dGPU, de modo que el usuario vea una sola ventana (la salida reescalada por IA).
Incluye todas las vías probadas, los datos medidos y la conclusión.

Hardware: NVIDIA RTX 5060 (dGPU, PCI:1:0:0) + Intel Arrow Lake iGPU
(PCI:0:2:0). Sesión: KDE **Wayland**, escritorio renderizado por la NVIDIA
(PrimaryGPU). Monitor en la NVIDIA (DP-2/HDMI-A-3 conectados).

---

## CORRECCIÓN IMPORTANTE (2026-06-30)

La conclusión original de este documento,que la pantalla virtual (Xvfb) es
"50× más lenta" e "inviable para shaders" (8 FPS), **era errónea por
contaminación de la medida**. El 8 FPS se midió con procesos de estrés/consumo
de los experimentos aún corriendo en segundo plano, saturando la CPU.

**Medido en limpio (misma escena, sin procesos de fondo):**
- Pantalla virtual (Xvfb + PRIME) + Minecraft + Photon @854×480: **~27 FPS**,
 solo **~15 %** por debajo del single-window (~32 FPS). Jugable.
- Rebajando el render: 480×270 → **~38 FPS**; 640×360 → **~35 FPS**.

**Por qué glmark2 marca 50× pero Minecraft solo 15 %:** el sobrecoste de Xvfb es
~constante (~7 ms/frame de presentación). En un render trivial (glmark2,
0,15 ms/frame) eso supone 50×; en un render pesado (Minecraft+Photon,
~30 ms/frame) es solo ~15 %. Ambas cifras son coherentes con un coste fijo por
frame, no con un factor multiplicativo.

**Implicación:** la pantalla virtual oculta (Xvfb + PRIME + captura) **SÍ es
viable para el demo de una ventana con shaders**, a ~27–38 FPS según la
resolución de render. El muro del DRM master (secciones 3 y 6) sigue siendo real
, no se puede arrancar un 2.º servidor X acelerado, pero resulta **irrelevante**:
la pantalla virtual por software basta. Las secciones siguientes se conservan
como registro; donde citen "8 FPS" o "50× / inviable para shaders", aplíquese
esta corrección.

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
| **Single-window** (juego en `:1`, tapado por overlay) | ventana existe, invisible | 33 FPS | Funciona. El juego renderiza nativo en la sesión; el overlay lo cubre. |
| **Xvfb + PRIME** | | ~15 % (limpio) - ver corrección | Display software (CPU/llvmpipe), coste ~constante ~7 ms/frame. En limpio: Minecraft+Photon **~27 FPS** (jugable). El "8 FPS / 50×" fue contaminación de procesos de fondo. |
| **VirtualGL + Xvfb** | | (incompatible) | Crashea con Minecraft moderno (1.21, motor GL nuevo). 1.12.2 funciona pero no soporta shaders modernos (Iris/Photon necesitan ≥1.16). |
| **gamescope (con ventana)** | ventana visible | nativo | Captura OK (glxgears 144 FPS dentro de gamescope). Pero deja ventana visible (mismo caso que single-window). |
| **gamescope --headless** | | - | 0 FPS: sin salida no hay vblank, el juego no presenta → no se captura. Backend headless además crashea en esta NVIDIA. |
| **X headless en NVIDIA** | | | `drmSetMaster failed: Device or resource busy`. La NVIDIA la tiene la sesión. |
| **X headless en Intel** | | | GLAMOR (hardware) **inicializa bien**, pero también `drmSetMaster failed: busy`. La Intel (GPU de arranque) también la retiene la sesión. |

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
| Pantalla virtual (Xvfb + PRIME) - **medida contaminada** | ~8 |
| Pantalla virtual (Xvfb + PRIME) - **limpia** | **~27** |

> La fila de ~8 FPS quedó contaminada por procesos de estrés/consumo de los
> experimentos en segundo plano. En limpio, misma escena, la pantalla virtual da
> ~27 FPS (solo ~15 % bajo el single-window). Ver corrección al inicio.

A 1080p nativo con Photon: **9,5 FPS** (GPU 97%, saturada).
Híbrida (render 854×480 + IA iGPU → 1080p): **29 FPS** → **3,1×** la nativa.

---

## 5. El sobrecoste de Xvfb: un coste ~constante por frame

El sobrecoste de Xvfb es la **presentación por software** de cada frame: un coste
aproximadamente **constante** (~7 ms/frame), no un factor multiplicativo. Su
impacto relativo depende de cuánto tarde el render:
- Render trivial (glmark2, ~0,15 ms/frame): +7 ms domina → parece 50×.
- Render pesado (Minecraft+Photon, ~30 ms/frame): +7 ms es solo ~15 % → jugable.

Por eso los shaders **no** hunden la pantalla virtual: cuanto más pesado es el
render, menos pesa en proporción el sobrecoste fijo de Xvfb. Con Photon en limpio
se miden ~27 FPS (854×480), no 8. La cifra de 8 FPS provino de saturación de CPU
por procesos de fondo, no del Xvfb.

---

## 6. Conclusión

**En un escritorio de un solo asiento, no es posible una segunda pantalla oculta
acelerada por hardware mientras la sesión gráfica está activa**, porque el
compositor retiene el DRM master de todas las GPUs. La única pantalla oculta
disponible es por software (Xvfb); su sobrecoste es un coste **fijo por frame**
(~7 ms) que, en renders pesados como shaders, supone solo ~15 % → **jugable**
(~27 FPS con Photon, ~38 rebajando el render). No es, por tanto, un impedimento
para el demo de una ventana.

Para "oculto + rápido + separado" harían falta cambios inviables para una demo:
apagar la sesión gráfica (arranque headless/servidor), una GPU adicional dedicada
al escritorio, o reconfigurar PRIME y reiniciar.

### Implicación para la arquitectura
- **Rendimiento (beneficio 3×)**: se demuestra con captura directa en la sesión
 (single-window), render nativo. Validado.
- **Una sola ventana visible**: el overlay fullscreen cubre la ventana del juego
 → el usuario solo ve la salida IA (se cumple la intención del enunciado: no
 mostrar el render crudo).
- **Pantalla oculta de verdad (Xvfb)**: viable para el demo de una ventana con
 shaders (~27 FPS a 854×480, ~38 a 480×270). El sobrecoste fijo de Xvfb es
 asumible en renders pesados. (El "8 FPS / inviable" fue contaminación de fondo.)

### Valor para la memoria
Este estudio es un **análisis de viabilidad de sistemas** con datos: documenta
por qué la pantalla virtual rápida y oculta no es alcanzable en este hardware
(DRM master compartido), cuantifica el sobrecoste del render por software (coste
fijo ~7 ms/frame: 50× en renders triviales, solo ~15 % en shaders pesados), y
aísla que la captura propia es eficiente (−7%). Justifica con rigor la decisión
de arquitectura final.

---

## 7. Comandos/artefactos de referencia

- Diagnóstico glmark2 3 caminos: `/tmp/diag_glmark.py`.
- Config X headless (NVIDIA): `/tmp/headless_nvidia.conf` (falló: modesetting busy).
- Config X headless (Intel): `/tmp/headless_intel.conf` (falló: drmSetMaster busy
 pese a GLAMOR + conector forzado + AutoBindGPU=false).
- Forzar/revertir conector Intel: `echo on|detect | sudo tee /sys/class/drm/card1-HDMI-A-1/status`.
- Errores clave en `/var/log/Xorg.5.log` (NVIDIA) y `/var/log/Xorg.6.log` (Intel).
