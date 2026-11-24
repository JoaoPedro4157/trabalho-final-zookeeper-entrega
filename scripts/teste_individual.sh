#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p resultados
.venv/bin/python src/cliente.py P1 --segundos 2 | tee resultados/individual.log