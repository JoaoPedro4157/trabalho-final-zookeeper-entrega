#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p resultados

pids=()
for cliente in P1 P2 P3; do
    .venv/bin/python src/cliente.py "$cliente" --segundos 3 > "resultados/$cliente.log" &
    pids+=("$!")
done

falhou=0
for pid in "${pids[@]}"; do
    wait "$pid" || falhou=1
done

sort -n -k1,1 resultados/P1.log resultados/P2.log resultados/P3.log |
    tee resultados/concorrente.log

exit "$falhou"