"""
Compara, en una sola imagen, la presion cerca de la pared superior a lo
largo de TODO el canal (desde la entrada x=0 hasta la salida x=LS+Ldiff+RS)
para los 24 casos del barrido LS in {1,2,3} x RS in {1..8}
(carpetas DifusorLS<LS>RS<RS>/).

La pared superior es plana en todo el dominio (yTop = Hout, constante en
los 3 bloques de blockMeshDict); la pared inferior es la que tiene el
escalon de la rampa. Por eso se samplea la presion cerca de la pared
SUPERIOR: es la unica linea recta que puede recorrer el canal completo sin
salirse del dominio en ningun caso.

REQUISITO PREVIO
-----------------
Cada caso debe tener corrido:

    postProcess -func sampleDict -latestTime

usando el system/sampleDict que define (entre otros) el set
'presionCanal' (ver Tarea1/DifusorLS2RS4/system/sampleDict), que genera
postProcessing/sampleDict/<tiempo>/presionCanal.xy con columnas:

    x  U_x  U_y  U_z  p

USO
---
    python comparar_presion_canal.py

Genera UNA sola imagen en resultados_rampa/comparacion_presion_canal.png
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# =========================== CONFIGURACION ==================================

CONFIG = {
    "casos_dir": "..",              # donde viven las carpetas DifusorLS<LS>RS<RS>/
    "LS_valores": [1, 2, 3],
    "RS_valores": list(range(1, 9)),  # 1..8
    "Ldiff": 3.0,                     # longitud de la rampa [m] (= 3*H, H=1 en todos los casos)
    "carpeta_salida": "resultados_rampa",
    "nombre_imagen": "comparacion_presion_canal.png",
}

# Un color categorico (identidad) por LS, paleta segura para daltonismo
# (Okabe-Ito). RS se codifica como intensidad (claro=1, oscuro=8) del mismo
# color de su LS.
COLOR_BASE_LS = {
    1: "#0072B2",  # azul
    2: "#E69F00",  # naranja
    3: "#009E73",  # verde azulado
}


# =========================== COLOR ===========================================

def color_por_ls_rs(ls: int, rs: int, rs_valores: list[int]) -> tuple[float, float, float]:
    base = np.array(mcolors.to_rgb(COLOR_BASE_LS[ls]))
    claro = np.array([1.0, 1.0, 1.0]) * 0.88 + base * 0.12

    idx = rs_valores.index(rs)
    frac = idx / (len(rs_valores) - 1) if len(rs_valores) > 1 else 1.0
    frac = 0.22 + 0.78 * frac

    return tuple(claro + (base - claro) * frac)


# =========================== LECTURA DE DATOS ================================

def resolver_archivo_set(caso_dir: Path, nombre_set: str) -> Path:
    base = caso_dir / "postProcessing" / "sampleDict"
    if not base.exists():
        raise FileNotFoundError(f"No existe {base}")

    carpetas_tiempo = [d for d in base.iterdir() if d.is_dir()]
    if not carpetas_tiempo:
        raise FileNotFoundError(f"No hay carpetas de tiempo en {base}")

    def como_numero(d: Path) -> float:
        try:
            return float(d.name)
        except ValueError:
            return -1.0

    carpeta_ultimo_tiempo = max(carpetas_tiempo, key=como_numero)

    ruta = carpeta_ultimo_tiempo / f"{nombre_set}.xy"
    if ruta.exists():
        return ruta

    raise FileNotFoundError(f"No se encontro '{nombre_set}.xy' en {carpeta_ultimo_tiempo}")


def cargar_perfil_x_p(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Lee un archivo raw de sample con columnas x Ux Uy Uz p -> (x, p)."""
    datos = np.loadtxt(path)
    orden = np.argsort(datos[:, 0])
    datos = datos[orden]
    return datos[:, 0], datos[:, 4]


# =========================== FLUJO PRINCIPAL ==================================

def main() -> None:
    # Relativo a la ubicacion del script, no al directorio desde donde se
    # invoque python (evita "no existe sampleDict" si se corre desde otro cwd).
    base_dir = (Path(__file__).resolve().parent / CONFIG["casos_dir"]).resolve()
    ls_valores = CONFIG["LS_valores"]
    rs_valores = CONFIG["RS_valores"]
    ldiff = CONFIG["Ldiff"]

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Franjas verticales muy tenues mostrando donde esta la rampa para cada LS
    for ls in ls_valores:
        ax.axvspan(
            ls, ls + ldiff,
            color=COLOR_BASE_LS[ls], alpha=0.07, lw=0, zorder=0,
        )

    casos_ok = 0
    casos_error = []
    p_lejos_de_entrada = []  # para fijar el ylim sin el pico de esquina en x=0

    for ls in ls_valores:
        for rs in rs_valores:
            caso_dir = base_dir / f"DifusorLS{ls}RS{rs}"
            color = color_por_ls_rs(ls, rs, rs_valores)
            try:
                archivo = resolver_archivo_set(caso_dir, "presionCanal")
                x, p = cargar_perfil_x_p(archivo)
            except (FileNotFoundError, OSError, IndexError) as exc:
                casos_error.append((f"LS{ls}RS{rs}", str(exc)))
                continue

            ax.plot(x, p, color=color, lw=1.3, zorder=2)
            p_lejos_de_entrada.append(p[x > 0.5])
            casos_ok += 1

    # x=0 tiene un pico de esquina (singularidad numerica entrada/pared,
    # sin significado fisico) cuyo efecto decae en la primera fraccion de
    # metro; se recorta el eje Y (con percentiles, robusto a la cola del
    # pico) para que no aplaste el resto de la curva, que es la parte
    # relevante para comparar casos.
    if p_lejos_de_entrada:
        p_ref = np.concatenate(p_lejos_de_entrada)
        p_lo, p_hi = np.percentile(p_ref, [1, 99])
        margen = 0.2 * (p_hi - p_lo)
        ax.set_ylim(p_lo - margen, p_hi + margen)
    ax.set_xlabel("$x$ [m] (0 = entrada del canal)")
    ax.set_ylabel("$p$ [m$^2$/s$^2$] (cerca de la pared superior)")
    ax.set_title(
        f"Presion a lo largo del canal - {casos_ok} casos "
        f"(LS in {ls_valores}, RS in {rs_valores[0]}..{rs_valores[-1]})"
    )
    ax.grid(alpha=0.3)

    entradas_leyenda = [
        Line2D([0], [0], color=COLOR_BASE_LS[ls], lw=2.5, label=f"LS = {ls} m")
        for ls in ls_valores
    ]
    entradas_leyenda.append(
        Patch(facecolor="gray", alpha=0.15, label="Zona de la rampa (por LS)")
    )
    ax.legend(
        handles=entradas_leyenda,
        loc="upper center",
        ncol=len(ls_valores) + 1,
        bbox_to_anchor=(0.5, -0.12),
        frameon=False,
        title="Color = LS   |   Tono claro -> oscuro dentro de cada color = RS de 1 a 8 m",
    )

    fig.tight_layout(rect=(0, 0.08, 1, 1))

    carpeta_salida = Path(CONFIG["carpeta_salida"])
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_imagen = carpeta_salida / CONFIG["nombre_imagen"]
    fig.savefig(ruta_imagen, dpi=150)
    plt.close(fig)

    print(f"Casos graficados: {casos_ok} / {len(ls_valores) * len(rs_valores)}")
    if casos_error:
        print("Casos con error:")
        for nombre, err in casos_error:
            print(f"  {nombre}: {err}")
    print(f"Imagen guardada en: {ruta_imagen}")


if __name__ == "__main__":
    main()
