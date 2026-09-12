"""
Barre 'distOffset' (la distancia de las lineas de muestreo de entrada/salida
respecto a los extremos del dominio, definida en system/sampleDict de
Difusor_piter_v2) y mide como cambia el error contra la solucion analitica
de Poiseuille plano, mostrando el resultado en una sola imagen
(error vs. distOffset).

Para cada offset en CONFIG["offsets"]:
  1. Edita distOffset en Difusor_piter_v2/system/sampleDict
  2. Corre 'postProcess -func sampleDict -latestTime' en el caso
  3. Lee inletProfile.xy / outletProfile.xy y calcula el error L2 relativo
     contra el perfil teorico (mismas funciones que compare_poiseuille.py)

Al terminar, deja distOffset en el primer valor de la lista (estado por
defecto conocido) y vuelve a correr el muestreo con ese valor.

Requiere que 'postProcess' este disponible en el PATH (entorno de OpenFOAM
cargado) y que compare_poiseuille.py este en la misma carpeta.

USO
---
    python error_vs_offset.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_poiseuille as cp  # noqa: E402  (reutiliza su logica de error)

# =========================== CONFIGURACION ==================================

CONFIG = {
    "caso_dir": "../Difusor_piter_v2",
    "H": 1.0,
    "offsets": list(range(1, 11)),  # metros (1..10)
    "carpeta_salida": "resultados_poiseuille",
    "nombre_imagen": "error_vs_offset.png",
}


# =========================== OPENFOAM =========================================

def fijar_dist_offset(sample_dict_path: Path, offset: float) -> None:
    texto = sample_dict_path.read_text()
    nuevo_texto, n = re.subn(
        r"^distOffset(\s+)[0-9.]+;",
        lambda m: f"distOffset{m.group(1)}{offset};",
        texto,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise RuntimeError(f"No se encontro/actualizo 'distOffset' en {sample_dict_path}")
    sample_dict_path.write_text(nuevo_texto)


def correr_postprocess(caso_dir: Path) -> None:
    resultado = subprocess.run(
        ["postProcess", "-func", "sampleDict", "-latestTime"],
        cwd=caso_dir, capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"postProcess fallo en {caso_dir}:\n{resultado.stdout[-2000:]}\n{resultado.stderr[-2000:]}"
        )


# =========================== ERROR (reusa compare_poiseuille.py) ============

def medir_error(caso_dir: Path, nombre_set: str, H_local: float) -> float:
    archivo = cp.resolver_archivo_set(caso_dir, nombre_set)
    y, u_sim = cp.cargar_perfil(archivo)
    y_local = y - y.min()  # coordenada local (pared inferior de esta seccion en 0)
    Q = cp.caudal(y_local, u_sim)
    u_teo = cp.perfil_poiseuille(y_local, H_local, Q)
    return cp.error_l2_relativo(u_sim, u_teo, y_local)


# =========================== FLUJO PRINCIPAL ==================================

def main() -> None:
    caso_dir = (Path(__file__).resolve().parent / CONFIG["caso_dir"]).resolve()
    sample_dict_path = caso_dir / "system" / "sampleDict"
    H = CONFIG["H"]
    offsets = CONFIG["offsets"]

    errores_entrada = []
    errores_salida = []

    for offset in offsets:
        print(f"--- distOffset = {offset} m ---")
        fijar_dist_offset(sample_dict_path, offset)
        correr_postprocess(caso_dir)
        e_in = medir_error(caso_dir, "inletProfile", H)
        e_out = medir_error(caso_dir, "outletProfile", 2 * H)
        errores_entrada.append(e_in)
        errores_salida.append(e_out)
        print(f"  Entrada: e = {e_in:.4f}   Salida: e = {e_out:.4f}")

    # Dejar el caso en un estado por defecto conocido (primer offset barrido)
    fijar_dist_offset(sample_dict_path, offsets[0])
    correr_postprocess(caso_dir)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(offsets, errores_entrada, "o-", color="#0072B2", lw=2, ms=7, label="Entrada")
    ax.plot(offsets, errores_salida, "o-", color="#E69F00", lw=2, ms=7, label="Salida")
    ax.set_xlabel("distOffset [m]  (distancia de la linea de muestreo al extremo del dominio)")
    ax.set_ylabel("Error $L_2$ relativo respecto a Poiseuille plano")
    ax.set_title("Como cambia el error teorico segun donde se mida")
    ax.set_xticks(offsets)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    carpeta_salida = (Path(__file__).resolve().parent / CONFIG["carpeta_salida"])
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_imagen = carpeta_salida / CONFIG["nombre_imagen"]
    fig.savefig(ruta_imagen, dpi=150)
    plt.close(fig)

    print("\nResumen:")
    print(f"{'offset [m]':>10}  {'e Entrada':>10}  {'e Salida':>10}")
    for offset, e_in, e_out in zip(offsets, errores_entrada, errores_salida):
        print(f"{offset:>10}  {e_in:>10.4f}  {e_out:>10.4f}")
    print(f"\nImagen guardada en: {ruta_imagen}")


if __name__ == "__main__":
    main()
