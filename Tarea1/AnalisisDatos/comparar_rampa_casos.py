"""
Compara, en una sola imagen, los perfiles de velocidad (Ux) y presion (p)
justo ANTES y justo DESPUES de la rampa del difusor, para los 24 casos del
barrido LS in {1,2,3} x RS in {1..8} (carpetas DifusorLS<LS>RS<RS>/).

REQUISITO PREVIO
-----------------
Cada caso debe tener corrido:

    postProcess -func sampleDict -latestTime

usando el system/sampleDict que define los sets 'rampaAntes' y
'rampaDespues' (una linea vertical de muestreo a 'distRampa' metros antes
del inicio de la rampa y despues de su final, ver
Tarea1/DifusorLS2RS4/system/sampleDict). Cada set samplea U y p juntos,
generando un archivo <set>.xy por caso con columnas:

    y  U_x  U_y  U_z  p

USO
---
    python comparar_rampa_casos.py

Genera UNA sola imagen en resultados_rampa/comparacion_rampa_24_casos.png
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

# =========================== CONFIGURACION ==================================

CONFIG = {
    "casos_dir": "..",              # donde viven las carpetas DifusorLS<LS>RS<RS>/
    "LS_valores": [1, 2, 3],
    "RS_valores": list(range(1, 9)),  # 1..8
    "carpeta_salida": "resultados_rampa",
    "nombre_imagen": "comparacion_rampa_24_casos.png",
}

# Un color categorico (identidad) por LS, paleta segura para daltonismo
# (Okabe-Ito). Dentro de cada LS, RS se codifica como intensidad (claro=1,
# oscuro=8) del mismo color -> codificacion secuencial anidada dentro de la
# categorica.
COLOR_BASE_LS = {
    1: "#0072B2",  # azul
    2: "#E69F00",  # naranja
    3: "#009E73",  # verde azulado
}


# =========================== COLOR ===========================================

def color_por_ls_rs(ls: int, rs: int, rs_valores: list[int]) -> tuple[float, float, float]:
    """
    Mismo tono de color para todos los RS de un LS dado; la intensidad
    (mezcla con blanco) codifica RS: RS bajo = tono claro, RS alto = tono
    saturado. Evita el extremo casi-blanco para que la linea siga siendo
    visible.
    """
    base = np.array(mcolors.to_rgb(COLOR_BASE_LS[ls]))
    claro = np.array([1.0, 1.0, 1.0]) * 0.88 + base * 0.12

    idx = rs_valores.index(rs)
    frac = idx / (len(rs_valores) - 1) if len(rs_valores) > 1 else 1.0
    frac = 0.22 + 0.78 * frac  # nunca completamente claro

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

    for candidato in (f"{nombre_set}.xy", f"{nombre_set}_U_p.xy", f"{nombre_set}_p_U.xy"):
        ruta = carpeta_ultimo_tiempo / candidato
        if ruta.exists():
            return ruta

    raise FileNotFoundError(f"No se encontro '{nombre_set}.xy' en {carpeta_ultimo_tiempo}")


def cargar_perfil_u_p(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lee un archivo raw de sample con columnas y Ux Uy Uz p -> (y, Ux, p)."""
    datos = np.loadtxt(path)
    orden = np.argsort(datos[:, 0])
    datos = datos[orden]
    y = datos[:, 0]
    ux = datos[:, 1]
    p = datos[:, 4]
    return y, ux, p


# =========================== FLUJO PRINCIPAL ==================================

def main() -> None:
    # Relativo a la ubicacion del script, no al directorio desde donde se
    # invoque python (evita "no existe sampleDict" si se corre desde otro cwd).
    base_dir = (Path(__file__).resolve().parent / CONFIG["casos_dir"]).resolve()
    ls_valores = CONFIG["LS_valores"]
    rs_valores = CONFIG["RS_valores"]

    fig, ejes = plt.subplots(2, 2, figsize=(11, 9.5), sharey="row")
    ((ax_u_antes, ax_u_despues), (ax_p_antes, ax_p_despues)) = ejes

    casos_ok = 0
    casos_error = []

    for ls in ls_valores:
        for rs in rs_valores:
            caso_dir = base_dir / f"DifusorLS{ls}RS{rs}"
            color = color_por_ls_rs(ls, rs, rs_valores)
            try:
                archivo_antes = resolver_archivo_set(caso_dir, "rampaAntes")
                archivo_despues = resolver_archivo_set(caso_dir, "rampaDespues")
                y_a, u_a, p_a = cargar_perfil_u_p(archivo_antes)
                y_d, u_d, p_d = cargar_perfil_u_p(archivo_despues)
            except (FileNotFoundError, OSError, IndexError) as exc:
                casos_error.append((f"LS{ls}RS{rs}", str(exc)))
                continue

            ax_u_antes.plot(u_a, y_a, color=color, lw=1.3)
            ax_u_despues.plot(u_d, y_d, color=color, lw=1.3)
            ax_p_antes.plot(p_a, y_a, color=color, lw=1.3)
            ax_p_despues.plot(p_d, y_d, color=color, lw=1.3)
            casos_ok += 1

    ax_u_antes.set_title("Velocidad $u_x$ - antes de la rampa")
    ax_u_despues.set_title("Velocidad $u_x$ - despues de la rampa")
    ax_p_antes.set_title("Presion cinematica $p$ - antes de la rampa")
    ax_p_despues.set_title("Presion cinematica $p$ - despues de la rampa")

    for ax in (ax_u_antes, ax_u_despues):
        ax.set_xlabel("$u_x$ [m/s]")
    for ax in (ax_p_antes, ax_p_despues):
        ax.set_xlabel("$p$ [m$^2$/s$^2$]")
    for ax in (ax_u_antes, ax_p_antes):
        ax.set_ylabel("$y$ [m]")

    for ax in ejes.flat:
        ax.grid(alpha=0.3)

    # Leyenda: color = LS (categorico), intensidad = RS (secuencial, claro->oscuro)
    entradas_leyenda = [
        Line2D([0], [0], color=COLOR_BASE_LS[ls], lw=2.5, label=f"LS = {ls} m")
        for ls in ls_valores
    ]
    fig.legend(
        handles=entradas_leyenda,
        loc="lower center",
        ncol=len(ls_valores),
        bbox_to_anchor=(0.5, 0.005),
        frameon=False,
        title="Color = LS   |   Tono claro -> oscuro dentro de cada color = RS de 1 a 8 m",
    )

    fig.suptitle(
        f"Comparacion de perfiles cerca de la rampa - {casos_ok} casos "
        f"(LS in {ls_valores}, RS in {rs_valores[0]}..{rs_valores[-1]})",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.96))

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
