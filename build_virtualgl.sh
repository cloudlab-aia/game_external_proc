#!/bin/bash
set -e

# Colores ANSI profesionales
COLOR_INFO="\033[1;34m"    # Azul brillante
COLOR_WARN="\033[1;33m"    # Amarillo brillante
COLOR_SUCCESS="\033[1;32m" # Verde brillante
COLOR_RESET="\033[0m"      # Resetear color

echo -e "${COLOR_INFO}==> Construyendo VirtualGL desde el código fuente...${COLOR_RESET}"

cd "$(dirname "$0")/virtualgl"

mkdir -p build
cd build

cmake ..
make -j$(nproc)

echo -e "${COLOR_WARN}==> Instalando VirtualGL en el sistema (se solicitará contraseña sudo)...${COLOR_RESET}"
sudo make install

echo -e "${COLOR_SUCCESS}==> ¡VirtualGL se ha construido e instalado correctamente!${COLOR_RESET}"

echo -e "${COLOR_INFO}==> Para probar la instalación, ejecuta manualmente este comando:${COLOR_RESET}"
echo -e "    ${COLOR_WARN}./virtualgl/build/bin/vglrun glxgears${COLOR_RESET}"
