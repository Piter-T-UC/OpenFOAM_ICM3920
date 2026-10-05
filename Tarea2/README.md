# Tarea 2 — Flujo alrededor de un cilindro en un canal

Caso `Cilindro/`: canal recto 2D (paredes arriba y abajo) con un cilindro de diámetro `D`
centrado en altura (`yc = H/2`). Flujo laminar transiente (`foamRun` + `incompressibleFluid`, PIMPLE).

## Qué editar
Todo se controla desde `Cilindro/constant/Parametros`:

| Parámetro | Qué es | Default |
|---|---|---|
| `Lup` | **distancia del inlet al centro del cilindro (la eliges tú)** | `5D` |
| `Ldown` | distancia del centro del cilindro al outlet | `15D` |
| `H` | altura del canal | `4D` |
| `Re` | Reynolds basado en `D` y `Uin` (`Uin = Re·nu/D`) | `100` |
| `nTc` | duración en tiempos convectivos `D/Uin` | `200` |
| `B` | semilado del cuadrado de la O-grid alrededor del cilindro | `1D` |
| `nTheta` | celdas por cuarto de circunferencia | `40` |
| `nRad`, `gradRad` | **refinamiento radial en la pared del cilindro (lo calculas tú)** | placeholder `40`, `20` |
| `dx` | tamaño de celda lejos del cilindro | `D/20` |

Restricciones: `R < B < H/2` y `B < Lup`.

## Malla
12 bloques: una O-grid de 4 bloques entre el cilindro y el cuadrado de semilado `B`,
más 8 bloques rectangulares que completan el canal (ver el esquema en `system/blockMeshDict`).
En la O-grid la dirección radial se gradúa con `gradRad` (celdas finas junto al cilindro).

## Correr
```bash
source /opt/openfoam14/etc/bashrc
cd Tarea2/Cilindro
./Allrun        # blockMesh, checkMesh, foamRun
./Allclean      # limpiar
```

## Resultados
- `postProcessing/forceCoeffs/...`: `Cd(t)`, `Cl(t)`. La frecuencia de `Cl` da el Strouhal `St = f·D/Uin`.
- `postProcessing/probes/...`: `U` y `p` en un punto de la estela, `2D` aguas abajo del centro.
- Sobre `Re ≈ 47` el flujo desprende vórtices (calle de von Kármán); bajo eso converge a un estado estacionario.
