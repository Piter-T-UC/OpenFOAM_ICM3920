#!/bin/bash
# Genera copias parametricas de Difusor_piter_v2 para un barrido en LS y RS.
#
# Por cada combinacion LS in {1,2,3} x RS in {1..8} crea una carpeta
# DifusorLS<LS>RS<RS>/ con un caso limpio (0/, constant/, system/, sin
# resultados previos ni polyMesh) y constant/Parametros parcheado con esos
# valores de LS y RS. Cada caso incluye un script Allrun que corre
# blockMesh, checkMesh y foamRun en serie.
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLANTILLA="$BASE_DIR/Difusor_piter_v2"

for LS in 1 2 3; do
  for RS in 1 2 3 4 5 6 7 8; do
    CASO="$BASE_DIR/DifusorLS${LS}RS${RS}"
    rm -rf "$CASO"
    mkdir -p "$CASO"/0 "$CASO"/constant "$CASO"/system

    cp -r "$PLANTILLA"/0/. "$CASO"/0/
    cp "$PLANTILLA"/constant/momentumTransport \
       "$PLANTILLA"/constant/MRFProperties \
       "$PLANTILLA"/constant/Parametros \
       "$PLANTILLA"/constant/physicalProperties \
       "$PLANTILLA"/constant/turbulenceProperties \
       "$CASO"/constant/
    cp "$PLANTILLA"/system/blockMeshDict \
       "$PLANTILLA"/system/controlDict \
       "$PLANTILLA"/system/fvSchemes \
       "$PLANTILLA"/system/fvSolution \
       "$CASO"/system/
    cp "$PLANTILLA"/Allclean "$CASO"/Allclean
    chmod +x "$CASO"/Allclean

    sed -i -E "s/^LS([[:space:]]+)[0-9.]+;/LS\\1${LS};/" "$CASO/constant/Parametros"
    sed -i -E "s/^RS([[:space:]]+)[0-9.]+;/RS\\1${RS};/" "$CASO/constant/Parametros"

    cat > "$CASO/Allrun" <<'EOF'
#!/bin/bash
cd "${0%/*}" || exit 1
set -e
blockMesh > log.blockMesh 2>&1
checkMesh > log.checkMesh 2>&1
foamRun > log.foamRun 2>&1
EOF
    chmod +x "$CASO/Allrun"
  done
done

echo "Se generaron $(ls -d "$BASE_DIR"/DifusorLS*RS*/ 2>/dev/null | wc -l) casos en $BASE_DIR."
