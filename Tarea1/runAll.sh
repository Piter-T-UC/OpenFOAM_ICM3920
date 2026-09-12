#!/bin/bash
# Corre ./Allrun (blockMesh, checkMesh, foamRun) en serie para todos los
# casos DifusorLS<LS>RS<RS>/ generados por generar_casos_difusor.sh.
# Sigue con el siguiente caso aunque uno falle; el resultado de cada uno
# queda en runAll_resumen.log y en <caso>/log.blockMesh|checkMesh|foamRun.

cd "$(dirname "$0")" || exit 1
resumen="runAll_resumen.log"
: > "$resumen"

for d in DifusorLS*RS*/; do
    d="${d%/}"
    echo "=== $(date '+%F %T') : iniciando $d ===" | tee -a "$resumen"
    if (cd "$d" && ./Allrun); then
        echo "=== $(date '+%F %T') : $d OK ===" | tee -a "$resumen"
    else
        echo "=== $(date '+%F %T') : $d FALLO (ver $d/log.*) ===" | tee -a "$resumen"
    fi
done

echo "Todas las corridas finalizadas: $(date '+%F %T')" | tee -a "$resumen"
