# Repositorio de retos CTF del centro

Este repositorio está diseñado para recoger retos propuestos por el alumnado con un flujo homogéneo basado en Pull Requests.

## Estructura de carpetas

Categorías válidas de retos:

- `cryptography/`
- `forensic/`
- `miscellany/`
- `osint/`
- `pentesting/`
- `steganography/`
- `web/`

Plantilla didáctica:

- `example/template-challenge/`

## Estructura mínima de un reto

Cada reto debe vivir en `categoria/nombre-del-reto/` y contener:

```text
categoria/nombre-del-reto/
├── challenge.yml
├── dist/
│   └── ...
└── writeup/
    └── WRITEUP.md
```

## Validación automática en PR

La GitHub Action `.github/workflows/validate-ctf-pr.yml` ejecuta el script `.github/scripts/validate_ctf_pr.py` en cada Pull Request para comprobar:

1. **1 PR = 1 reto** (una sola carpeta `categoria/nombre-del-reto`).
2. Categoría válida.
3. Existencia de `challenge.yml` y `writeup/WRITEUP.md`.
4. YAML sintácticamente válido.
5. Campos obligatorios en `challenge.yml`.
6. Valores fijos:
   - `type: standard`
   - `state: hidden`
   - `solution: writeup/WRITEUP.md`
7. Coherencia de `category` con la carpeta.
8. Formato de `flags`:
   - lista de objetos YAML
   - `type: static`
   - `data: case_insensitive`
9. Existencia real de los archivos listados en `files`.
10. Writeup no vacío, con contenido mínimo y sin plantilla sin editar.
11. Detección de valores de plantilla sin modificar.
12. Unicidad de `name` en el repositorio.
13. Prohibición de modificar archivos ajenos al reto en la misma PR.

## Feedback pedagógico

El validador publica un comentario en la PR (que se **actualiza** en cada ejecución, sin duplicar comentarios antiguos) con:

- archivos modificados detectados
- errores concretos y accionables
- guía breve de cómo debe quedar una PR válida

Además, sube un artefacto `ctf-validation-report` con el informe completo.

## Uso de la plantilla

1. Copia `example/template-challenge/`.
2. Renombra la carpeta dentro de una categoría válida, por ejemplo `cryptography/rsa-warmup/`.
3. Edita completamente `challenge.yml` y `writeup/WRITEUP.md`.
4. Añade los archivos de distribución en `dist/`.
5. Abre una PR con **solo ese reto**.


## Repositorio objetivo

Este proyecto está preparado para ejecutarse en el repositorio:

- `https://github.com/0xmrivas/ctfd-challenges-test`

La action incluye una comprobación de identidad (`github.repository`) para evitar ejecuciones en un repositorio equivocado.
