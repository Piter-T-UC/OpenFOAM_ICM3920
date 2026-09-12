"""
Cuantifica la influencia de LS y RS sobre:
  - el error respecto a Poiseuille plano justo antes de la rampa (rampaAntes)
  - el error respecto a Poiseuille plano justo despues de la rampa (rampaDespues)
  - la presion al final del canal (presionCanal, ultimo punto = pared superior en x=xFinal)

Usa los archivos ya generados por 'postProcess -func sampleDict -latestTime'
en cada carpeta DifusorLS<LS>RS<RS>/.

Imprime una tabla y guarda un CSV para pegar en el informe.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_poiseuille as cp

CASOS_DIR = Path(__file__).resolve().parent / ".."
LS_VALORES = [1, 2, 3]
RS_VALORES = list(range(1, 9))
H = 1.0


def resolver_xy(caso_dir: Path, nombre: str) -> Path:
    base = caso_dir / "postProcessing" / "sampleDict"
    carpetas = [d for d in base.iterdir() if d.is_dir()]
    t = max(carpetas, key=lambda d: float(d.name))
    for cand in (f"{nombre}.xy", f"{nombre}_U_p.xy", f"{nombre}_p_U.xy"):
        p = t / cand
        if p.exists():
            return p
    raise FileNotFoundError(f"{nombre} no encontrado en {t}")


def cargar_u_p(path: Path):
    datos = np.loadtxt(path)
    orden = np.argsort(datos[:, 0])
    datos = datos[orden]
    return datos[:, 0], datos[:, 1], datos[:, 4]


def main():
    filas = []
    for ls in LS_VALORES:
        for rs in RS_VALORES:
            caso = (CASOS_DIR / f"DifusorLS{ls}RS{rs}").resolve()
            try:
                y_a, u_a, p_a = cargar_u_p(resolver_xy(caso, "rampaAntes"))
                y_d, u_d, p_d = cargar_u_p(resolver_xy(caso, "rampaDespues"))
                y_c, u_c, p_c = cargar_u_p(resolver_xy(caso, "presionCanal"))
            except (FileNotFoundError, OSError) as exc:
                print(f"AVISO: LS{ls}RS{rs} sin datos ({exc})")
                continue

            y_a_local = y_a - y_a.min()
            Q_a = cp.caudal(y_a_local, u_a)
            u_teo_a = cp.perfil_poiseuille(y_a_local, H, Q_a)
            e_a = cp.error_l2_relativo(u_a, u_teo_a, y_a_local)

            y_d_local = y_d - y_d.min()
            Q_d = cp.caudal(y_d_local, u_d)
            u_teo_d = cp.perfil_poiseuille(y_d_local, 2 * H, Q_d)
            e_d = cp.error_l2_relativo(u_d, u_teo_d, y_d_local)

            # x del final de la rampa (Ldiff = 3H) para medir posiciones relativas
            Ldiff = 3 * H
            x_fin_rampa = ls + Ldiff

            i_min = int(np.argmin(p_c))
            p_min = p_c[i_min]
            x_min_rel = y_c[i_min] - x_fin_rampa  # y_c aqui es en realidad 'x'

            # pico de recuperacion: maximo DESPUES del minimo, excluyendo el
            # ultimo 2% de puntos (ahi p decae forzado a 0 por la BC del outlet)
            corte = int(0.98 * len(p_c))
            tramo = p_c[i_min:corte]
            if len(tramo) > 0:
                i_max_rel = int(np.argmax(tramo))
                p_max = tramo[i_max_rel]
                x_max_rel = y_c[i_min + i_max_rel] - x_fin_rampa
            else:
                p_max, x_max_rel = np.nan, np.nan

            filas.append((ls, rs, e_a, e_d, p_min, x_min_rel, p_max, x_max_rel))

    print(f"{'LS':>3} {'RS':>3} {'e_antes':>9} {'e_despues':>10} "
          f"{'p_min':>12} {'x_min':>7} {'p_max':>12} {'x_max':>7}")
    for ls, rs, e_a, e_d, p_min, x_min, p_max, x_max in filas:
        print(f"{ls:>3} {rs:>3} {e_a:>9.4f} {e_d:>10.4f} "
              f"{p_min:>12.4e} {x_min:>7.2f} {p_max:>12.4e} {x_max:>7.2f}")

    # ---- Analisis de convergencia respecto a LS (a RS fijo) ----
    print("\n=== e_antes (antes de la rampa) por LS, a RS fijo ===")
    for rs in RS_VALORES:
        vals = [e_a for (ls, rs_, e_a, e_d, p_min, x_min, p_max, x_max) in filas if rs_ == rs]
        print(f"RS={rs}: e_antes(LS=1,2,3) = {[f'{v:.4f}' for v in vals]}")

    print("\n=== e_despues (despues de la rampa) por RS, a LS fijo ===")
    for ls in LS_VALORES:
        vals = [(rs, e_d) for (ls_, rs, e_a, e_d, p_min, x_min, p_max, x_max) in filas if ls_ == ls]
        print(f"LS={ls}: " + ", ".join(f"RS={rs}:{v:.4f}" for rs, v in vals))

    print("\n=== Pico de recuperacion de presion (p_max) por RS, a LS fijo ===")
    for ls in LS_VALORES:
        vals = [(rs, p_max, x_max) for (ls_, rs, e_a, e_d, p_min, x_min, p_max, x_max) in filas if ls_ == ls]
        for rs, p_max, x_max in vals:
            visible = "SI" if (rs - x_max) > 0.3 else "apenas/no"  # margen hasta el outlet
            print(f"LS={ls} RS={rs}: p_max={p_max:.4e} en x-xFinRampa={x_max:.2f} m "
                  f"(quedan {rs - x_max:.2f} m hasta el outlet) -> visible: {visible}")

    print("\n=== Minimo de presion (zona de separacion) por RS, a LS fijo ===")
    for ls in LS_VALORES:
        vals = [(rs, p_min, x_min) for (ls_, rs, e_a, e_d, p_min, x_min, p_max, x_max) in filas if ls_ == ls]
        for rs, p_min, x_min in vals:
            print(f"LS={ls} RS={rs}: p_min={p_min:.4e} en x-xFinRampa={x_min:.2f} m")

    # ---- guardar CSV ----
    out = Path(__file__).resolve().parent / "resultados_rampa" / "influencia_dominio.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write("LS,RS,e_antes,e_despues,p_min,x_min,p_max,x_max\n")
        for ls, rs, e_a, e_d, p_min, x_min, p_max, x_max in filas:
            f.write(f"{ls},{rs},{e_a:.6f},{e_d:.6f},{p_min:.6e},{x_min:.4f},{p_max:.6e},{x_max:.4f}\n")
    print(f"\nCSV guardado en: {out}")


if __name__ == "__main__":
    main()
