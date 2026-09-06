# OpenFOAM - Curso

Carpeta con las simulaciones de CFD del curso, sincronizada por Git/GitHub.

## Estructura
Cada simulación vive en su propia subcarpeta con la estructura estándar de OpenFOAM (0/, constant/, system/).

## Flujo de trabajo
1. Cargar el entorno: `source /opt/openfoam14/etc/bashrc`
2. Crear/copiar el caso dentro de esta carpeta.
3. Ejecutar el solver correspondiente.
4. `git add`, `git commit`, `git push` para respaldar (los resultados numéricos pesados quedan fuera por el .gitignore).
