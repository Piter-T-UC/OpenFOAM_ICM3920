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
| `dx` | tamaño de celda de la malla de fondo (y espesor en z) | `D/10` |
| `wake*`, `wakeLevel` | caja de refinamiento en la estela y su nivel | `xc-1.5D … xc+8D`, `yc±1.5D`, nivel `2` |
| `cylLevelMin/Max` | **nivel de refinamiento en la superficie del cilindro (lo calculas tú)** | placeholder `3` |
| `nLayers`, `expansionRatio`, `firstLayerThickness` | **capas en la pared del cilindro (lo calculas tú)** | placeholder `10`, `1.2`, `0.0025D` |

## Malla (snappyHexMesh)
1. `blockMesh`: malla de fondo, el canal completo con celdas cúbicas de lado `dx` y 1 celda en z.
2. `snappyHexMesh`: recorta el cilindro, refina hasta el nivel `cylLevel` en su superficie
   (celda `dx/2^nivel`) y `wakeLevel` en la estela, y agrega `nLayers` capas en la pared.
3. `extrudeMesh`: snappy refina también en z, así que se toma la cara `front` y se extruye
   una sola celda para volver a una malla 2D (`front`/`back` de tipo `empty`).

Revisa en `log.snappyHexMesh` qué porcentaje de la pared quedó con capas.

## Correr
```bash
source /opt/openfoam14/etc/bashrc
cd Tarea2/Cilindro
./Allrun        # blockMesh, snappyHexMesh, extrudeMesh, checkMesh, foamRun
./Allclean      # limpiar
```

## Resultados
- `postProcessing/forceCoeffs/...`: `Cd(t)`, `Cl(t)`. La frecuencia de `Cl` da el Strouhal `St = f·D/Uin`.
- `postProcessing/probes/...`: `U` y `p` en un punto de la estela, `2D` aguas abajo del centro.
- Sobre `Re ≈ 47` el flujo desprende vórtices (calle de von Kármán); bajo eso converge a un estado estacionario.
