"""
Comparación de perfiles de velocidad simulados en OpenFOAM contra la
solución analítica de Poiseuille plano, en las secciones de entrada y
salida de un difusor 2D.

CÓMO OBTENER LOS DATOS DESDE OPENFOAM
--------------------------------------
En system/sampleDict del caso (functionObject de tipo "sets", ejecutado con
'postProcess -func sampleDict'), se definen dos líneas verticales: una 1 m
aguas abajo del comienzo del dominio (x0=0) y otra 1 m aguas arriba del
final del dominio (x3=LS+Ldiff+RS). Ver Difusor_piter_v2/system/sampleDict:

    #include "${FOAM_CASE}/constant/Parametros"

    distOffset  1;
    xInlet      #calc "0 + $distOffset";
    xOutlet     #calc "$LS + $Ldiff + $RS - $distOffset";
    zMid        #calc "0.05 * $H";
    y0In        #calc "$Hout - $H";
    yTop        $Hout;

    type            sets;
    libs            ("libsampling.so");
    interpolationScheme cellPoint;
    setFormat       raw;

    sets
    (
        inletProfile
        {
            type    lineUniform;   // 'uniform' fue renombrado a 'lineUniform'
            axis    y;
            start   ($xInlet $y0In $zMid);
            end     ($xInlet $yTop $zMid);
            nPoints 200;
        }
        outletProfile
        {
            type    lineUniform;
            axis    y;
            start   ($xOutlet 0    $zMid);
            end     ($xOutlet $yTop $zMid);
            nPoints 200;
        }
    );

    fields (U);

Nota geométrica: la pared inferior del difusor NO esta en y=0 en la seccion
de entrada (esta en y=H=y0In), solo en la de salida. Este script lo tiene en
cuenta: para el modelo teorico usa la coordenada y relativa a la pared
inferior de cada seccion (y - y.min()), no la y absoluta de la malla.

Ejecuta (después de correr la simulación):

    postProcess -func sampleDict -latestTime

Esto genera archivos como:

    postProcessing/sampleDict/<tiempo>/inletProfile.xy
    postProcessing/sampleDict/<tiempo>/outletProfile.xy

(en versiones de OpenFOAM que samplean varios campos a la vez, el nombre
lleva el sufijo del campo, p. ej. inletProfile_U.xy; este script busca
ambas variantes automáticamente y detecta el <tiempo> más reciente).

Cada archivo tiene columnas separadas por espacios: y Ux Uy Uz (sin
encabezado) — el formato "raw" que este script lee de forma nativa. También
acepta CSV con encabezado (por ejemplo, exportado desde ParaView con "Plot
Over Line" -> Save Data), buscando columnas de coordenada y velocidad por
nombre.

USO
---
1. Edita la sección CONFIG más abajo: carpeta del caso ("caso_dir") y H.
2. Ejecuta:  python compare_poiseuille.py
3. Revisa la salida en consola y los gráficos en la carpeta de resultados.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

# Compatibilidad: numpy >= 2.0 renombro trapz -> trapezoid
_trapz = getattr(np, "trapezoid", None) or np.trapz

# =========================== CONFIGURACIÓN ================================

CONFIG = {
    # Carpeta del caso de OpenFOAM (relativa a este script), donde vive
    # postProcessing/sampleDict/<tiempo>/... generado por
    # 'postProcess -func sampleDict -latestTime'.
    "caso_dir": "../Difusor_piter_v2",
    # Altura física del canal de ENTRADA, en metros (= H en constant/Parametros).
    "H": 1.0,
    # Un set (definido en system/sampleDict) por sección a comparar.
    # "H_local_factor" multiplica a H para obtener la altura local de esa
    # sección (entrada = H, salida = 2H).
    "secciones": [
        {
            "nombre": "Entrada",
            "set": "inletProfile",
            "H_local_factor": 1.0,
        },
        {
            "nombre": "Salida",
            "set": "outletProfile",
            "H_local_factor": 2.0,
        },
    ],
    "carpeta_salida": "resultados_poiseuille",
}

# Umbrales del criterio de similitud (ver documento LaTeX adjunto)
UMBRAL_EXCELENTE = 0.05
UMBRAL_ACEPTABLE = 0.15


# =========================== LECTURA DE DATOS ==============================

def resolver_archivo_set(caso_dir: str | Path, nombre_set: str) -> Path:
    """
    Encuentra el archivo .xy de un set de sampleDict dentro de
    <caso_dir>/postProcessing/sampleDict/<ultimo_tiempo>/, sin necesidad de
    conocer de antemano el tiempo ni el sufijo exacto del nombre de archivo
    (algunas versiones de OpenFOAM escriben '<set>.xy', otras '<set>_U.xy').
    """
    base = Path(caso_dir) / "postProcessing" / "sampleDict"
    if not base.exists():
        raise FileNotFoundError(
            f"No existe {base}.\n"
            "Corre primero 'postProcess -func sampleDict -latestTime' en el "
            "caso de OpenFOAM."
        )

    carpetas_tiempo = [d for d in base.iterdir() if d.is_dir()]
    if not carpetas_tiempo:
        raise FileNotFoundError(f"No hay carpetas de tiempo dentro de {base}.")

    def como_numero(d: Path) -> float:
        try:
            return float(d.name)
        except ValueError:
            return -1.0

    carpeta_ultimo_tiempo = max(carpetas_tiempo, key=como_numero)

    for candidato in (f"{nombre_set}_U.xy", f"{nombre_set}.xy"):
        ruta = carpeta_ultimo_tiempo / candidato
        if ruta.exists():
            return ruta

    raise FileNotFoundError(
        f"No se encontro '{nombre_set}(_U).xy' en {carpeta_ultimo_tiempo}"
    )


def cargar_perfil(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Carga un perfil (y, Ux) desde un archivo exportado por OpenFOAM.

    Soporta:
      - formato "raw" de la utilidad sample (espacios, sin encabezado,
        columnas: y Ux Uy [Uz])
      - CSV con encabezado (p. ej. ParaView "Plot Over Line")

    Devuelve (y, Ux) ordenados por y creciente.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo: {path}\n"
            "Revisa la ruta en CONFIG['secciones'] o corre primero "
            "'postProcess -func sampleDict -latestTime' en tu caso de OpenFOAM."
        )

    with open(path, "r") as f:
        primera_linea = f.readline().strip()

    parece_csv = "," in primera_linea
    if parece_csv:
        y, ux = _cargar_csv(path)
    else:
        y, ux = _cargar_raw(path)

    orden = np.argsort(y)
    return y[orden], ux[orden]


def _cargar_raw(path: Path) -> tuple[np.ndarray, np.ndarray]:
    datos = np.loadtxt(path)
    if datos.ndim == 1:
        datos = datos.reshape(1, -1)
    if datos.shape[1] < 2:
        raise ValueError(
            f"{path} tiene menos de 2 columnas; se esperaba al menos y y Ux."
        )
    y = datos[:, 0]
    ux = datos[:, 1]
    return y, ux


def _cargar_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with open(path, newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        filas = [fila for fila in lector if fila]

    encabezado_lower = [c.strip().lower() for c in encabezado]

    def buscar_columna(candidatos: list[str]) -> int | None:
        for i, nombre in enumerate(encabezado_lower):
            if any(c in nombre for c in candidatos):
                return i
        return None

    # "points:1" es la columna Y en exportes de ParaView (points:0=x,1=y,2=z)
    col_y = buscar_columna(["points:1", "arc_length", "distance", "y"])
    col_ux = buscar_columna(["u:0", "ux", "u_x", "velocity:0"])

    if col_y is None or col_ux is None:
        raise ValueError(
            f"No se pudieron identificar las columnas y/Ux en {path}.\n"
            f"Encabezado encontrado: {encabezado}\n"
            "Ajusta manualmente la lista 'candidatos' en _cargar_csv()."
        )

    y = np.array([float(fila[col_y]) for fila in filas])
    ux = np.array([float(fila[col_ux]) for fila in filas])
    return y, ux


# =========================== MODELO TEÓRICO =================================

def caudal(y: np.ndarray, u: np.ndarray) -> float:
    """Caudal por unidad de profundidad: Q = integral de u dy (trapecio)."""
    return float(_trapz(u, y))


def perfil_poiseuille(y: np.ndarray, H_local: float, Q: float) -> np.ndarray:
    """
    Perfil teorico de Poiseuille plano:  u(y) = 6*Q/H^3 * y*(H-y)
    valido para y en [0, H_local], pared inferior en y=0.
    """
    return 6.0 * Q / H_local**3 * y * (H_local - y)


# =========================== MÉTRICA DE ERROR ================================

def norma_l2(f: np.ndarray, y: np.ndarray) -> float:
    return float(np.sqrt(_trapz(f ** 2, y)))


def error_l2_relativo(u_sim: np.ndarray, u_teo: np.ndarray, y: np.ndarray) -> float:
    """
    e = ||u_sim - u_teo||_2 / ||u_teo||_2
    Error relativo estandar respecto a la solucion teorica. No esta acotado
    en [0, 1]; se lee directamente como "e*100 % de error respecto al
    perfil de Poiseuille teorico".
    """
    num = norma_l2(u_sim - u_teo, y)
    den = norma_l2(u_teo, y)
    return 0.0 if den == 0 else num / den


def interpretar_error(e: float) -> str:
    if e < UMBRAL_EXCELENTE:
        return "Excelente concordancia con Poiseuille plano (flujo completamente desarrollado)."
    if e < UMBRAL_ACEPTABLE:
        return "Concordancia aceptable (posibles efectos residuales de la rampa o de malla)."
    return "Baja concordancia: revisar ubicacion de la linea de muestreo, malla o regimen de flujo."


# =========================== FLUJO PRINCIPAL =================================

def analizar_seccion(nombre: str, caso_dir: str, nombre_set: str, H_local: float) -> dict:
    archivo = resolver_archivo_set(caso_dir, nombre_set)
    y, u_sim = cargar_perfil(archivo)

    # perfil_poiseuille() asume la pared inferior en y=0; en este difusor la
    # pared inferior de la entrada esta en y=H (no en y=0, ver blockMeshDict:
    # y0In = Hout-H), asi que se usa la coordenada local (relativa a la
    # pared inferior de CADA seccion) solo para evaluar el modelo teorico.
    y_local = y - y.min()

    Q = caudal(y_local, u_sim)
    u_teo = perfil_poiseuille(y_local, H_local, Q)
    e = error_l2_relativo(u_sim, u_teo, y_local)
    return {
        "nombre": nombre,
        "archivo": archivo,
        "y": y,
        "u_sim": u_sim,
        "u_teo": u_teo,
        "Q": Q,
        "H_local": H_local,
        "error": e,
    }


def graficar(resultado: dict, carpeta_salida: Path) -> Path:
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(resultado["u_sim"], resultado["y"], "o", ms=3, label="OpenFOAM (simulado)")
    ax.plot(resultado["u_teo"], resultado["y"], "-", lw=2, label="Poiseuille plano (teorico)")
    ax.set_xlabel("$u_x$ [m/s]")
    ax.set_ylabel("$y$ [m]")
    ax.set_title(f"{resultado['nombre']}  (e = {resultado['error']:.3f})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    ruta = carpeta_salida / f"perfil_{resultado['nombre'].lower()}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def main() -> None:
    H = CONFIG["H"]
    # Relativo a la ubicacion del script, no al directorio desde donde se
    # invoque python (evita "no existe sampleDict" si se corre desde otro cwd).
    caso_dir = (Path(__file__).resolve().parent / CONFIG["caso_dir"]).resolve()
    carpeta_salida = Path(CONFIG["carpeta_salida"])
    resultados = []

    for seccion in CONFIG["secciones"]:
        H_local = seccion["H_local_factor"] * H
        resultado = analizar_seccion(
            seccion["nombre"], caso_dir, seccion["set"], H_local
        )
        resultados.append(resultado)

    print("=" * 60)
    print("COMPARACION CONTRA POISEUILLE PLANO")
    print("=" * 60)
    for r in resultados:
        print(f"\nSeccion: {r['nombre']}  ({r['archivo']})")
        print(f"  H_local = {r['H_local']:.5g} m")
        print(f"  Q_sim   = {r['Q']:.5g} m^2/s (por unidad de profundidad)")
        print(f"  Error e = {r['error']:.4f}")
        print(f"  -> {interpretar_error(r['error'])}")
        ruta = graficar(r, carpeta_salida)
        print(f"  Grafico guardado en: {ruta}")

    if len(resultados) >= 2:
        Q1, Q2 = resultados[0]["Q"], resultados[1]["Q"]
        diff_masa = abs(Q1 - Q2) / max(abs(Q1), abs(Q2), 1e-12)
        print(
            f"\nVerificacion de conservacion de masa: "
            f"|Q_{resultados[0]['nombre']} - Q_{resultados[1]['nombre']}| / Q_max "
            f"= {diff_masa:.4%}"
        )
        if diff_masa > 0.05:
            print("  Aviso: diferencia > 5%, revisar convergencia de la simulacion.")


if __name__ == "__main__":
    main()
