#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

VALID_CATEGORIES = {
    "cryptography",
    "forensic",
    "miscellany",
    "osint",
    "pentesting",
    "steganography",
    "web",
}

REQUIRED_FIELDS = [
    "name",
    "author",
    "category",
    "description",
    "value",
    "type",
    "flags",
    "solution",
    "requirements",
    "state",
    "version",
]

FORCED_VALUES = {
    "type": "standard",
    "state": "hidden",
    "solution": "writeup/WRITEUP.md",
}

TEMPLATE_MARKERS = [
    "Example challenge",
    "Nombre del autor",
    "flag{example_flag}",
    "Describe aquí el reto",
    "Explica brevemente el objetivo",
    "Solución paso a paso",
]

MARKER = "<!-- ctf-validator-report -->"

INFRA_ALLOWLIST_PREFIXES = (".github/", "example/")
INFRA_ALLOWLIST_FILES = {"README.md"}



def is_infra_path(path: str) -> bool:
    return path in INFRA_ALLOWLIST_FILES or path.startswith(INFRA_ALLOWLIST_PREFIXES)


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def get_changed_files(base: str, head: str) -> list[str]:
    out = run(["git", "diff", "--name-only", f"{base}...{head}"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"YAML inválido en `{path}`: {exc}"

    if not isinstance(data, dict):
        return None, f"El archivo `{path}` debe contener un objeto YAML (mapa clave-valor)."
    return data, None


def is_under(root: str, rel_path: str) -> bool:
    return rel_path == root or rel_path.startswith(root + "/")


def detect_challenge_roots(changed_files: list[str]) -> tuple[set[str], list[str]]:
    roots: set[str] = set()
    outside: list[str] = []

    for rel_path in changed_files:
        parts = rel_path.split("/")
        if len(parts) < 2:
            outside.append(rel_path)
            continue
        category = parts[0]
        challenge_name = parts[1]
        if category not in VALID_CATEGORIES:
            outside.append(rel_path)
            continue
        roots.add(f"{category}/{challenge_name}")

    return roots, outside


def validate_writeup(writeup_path: Path) -> list[str]:
    errors: list[str] = []
    content = writeup_path.read_text(encoding="utf-8").strip()

    if not content:
        errors.append("`writeup/WRITEUP.md` existe pero está vacío.")
        return errors

    plain = " ".join(content.split())
    if len(plain) < 220:
        errors.append(
            "`writeup/WRITEUP.md` parece demasiado corto (< 220 caracteres útiles). "
            "Añade una explicación reproducible de la solución."
        )

    lower_plain = plain.lower()
    suspicious = [m for m in TEMPLATE_MARKERS if m.lower() in lower_plain]
    if suspicious:
        errors.append(
            "Se detectaron fragmentos de plantilla sin editar en el writeup: "
            + ", ".join(f"`{s}`" for s in suspicious)
            + "."
        )

    return errors


def validate_flags(flags: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(flags, list) or not flags:
        return ["`flags` debe ser una lista YAML con al menos una flag."]

    for idx, flag in enumerate(flags, start=1):
        if not isinstance(flag, dict):
            errors.append(
                f"La entrada `flags[{idx}]` debe ser un objeto YAML, no un string suelto."
            )
            continue

        if flag.get("type") != "static":
            errors.append(f"`flags[{idx}].type` debe ser `static`.")
        if flag.get("data") != "case_insensitive":
            errors.append(f"`flags[{idx}].data` debe ser `case_insensitive`.")

        content = flag.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"`flags[{idx}].content` debe ser un texto no vacío.")

    return errors


def validate_files_field(challenge_root: Path, files_field: Any) -> list[str]:
    errors: list[str] = []
    if files_field is None:
        return errors

    if not isinstance(files_field, list):
        return ["`files` debe ser una lista de rutas relativas (o `null` si no aplica)."]

    for idx, entry in enumerate(files_field, start=1):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(f"`files[{idx}]` debe ser una ruta de archivo válida.")
            continue

        rel = Path(entry)
        full = challenge_root / rel
        if full.is_dir():
            errors.append(f"`files[{idx}]` apunta a un directorio (`{entry}`), no a un archivo.")
        elif not full.exists():
            errors.append(
                f"`files[{idx}]` referencia `{entry}`, pero no existe en `{challenge_root}`."
            )

    return errors


def find_duplicate_names(current_root: str, current_name: str) -> list[str]:
    duplicates: list[str] = []
    for category in VALID_CATEGORIES:
        cat_dir = Path(category)
        if not cat_dir.exists():
            continue
        for challenge_yml in cat_dir.glob("*/challenge.yml"):
            data, err = load_yaml(challenge_yml)
            if err or not data:
                continue
            name = data.get("name")
            if not isinstance(name, str):
                continue

            root = str(challenge_yml.parent).replace("\\", "/")
            if name.strip().lower() == current_name.strip().lower() and root != current_root:
                duplicates.append(root)
    return duplicates


def build_report(errors: list[str], warnings: list[str], changed_files: list[str]) -> str:
    status = "✅ Validación superada" if not errors else "❌ Validación fallida"
    lines = [MARKER, f"## {status}", "", "### Archivos modificados detectados", ""]

    if changed_files:
        lines.extend([f"- `{f}`" for f in changed_files])
    else:
        lines.append("- _(sin cambios detectados)_")

    if errors:
        lines.extend(["", "### Errores que debes corregir", ""])
        lines.extend([f"- {e}" for e in errors])

    if warnings:
        lines.extend(["", "### Avisos", ""])
        lines.extend([f"- {w}" for w in warnings])

    if errors:
        lines.extend(
            [
                "",
                "### Qué se espera en una PR válida",
                "",
                "- 1 PR = 1 reto dentro de `categoria/nombre-del-reto/`.",
                "- Debe existir `challenge.yml` y `writeup/WRITEUP.md`.",
                "- `type: standard`, `state: hidden`, `solution: writeup/WRITEUP.md`.",
                "- `flags` en formato objeto YAML estático y case-insensitive.",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida PRs de retos CTF.")
    parser.add_argument("--base", required=True, help="SHA base de la PR")
    parser.add_argument("--head", required=True, help="SHA head de la PR")
    parser.add_argument(
        "--report-path",
        default="validation_report.md",
        help="Ruta de salida para el informe markdown",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    changed_files = get_changed_files(args.base, args.head)
    if not changed_files:
        errors.append("No se detectaron archivos modificados en la comparación base...head.")
        report = build_report(errors, warnings, changed_files)
        Path(args.report_path).write_text(report, encoding="utf-8")
        print(report)
        return 1

    roots, outside = detect_challenge_roots(changed_files)

    outside_infra = [p for p in outside if is_infra_path(p)]

    if len(roots) > 0 and outside:
        errors.append(
            "La PR del alumnado no debe modificar archivos ajenos al reto. "
            "Se detectaron cambios extra: "
            + ", ".join(f"`{p}`" for p in outside)
        )

    if len(roots) == 0:
        if outside and len(outside_infra) == len(outside):
            warnings.append(
                "Solo se detectaron cambios de infraestructura/documentación "
                "(`.github/`, `example/`, `README.md`). "
                "No se validó ningún reto en esta PR."
            )
        else:
            errors.append(
                "No se ha encontrado ninguna carpeta de reto válida. "
                "Crea tu entrega dentro de una categoría permitida, por ejemplo `cryptography/mi-reto/`."
            )
    elif len(roots) > 1:
        errors.append(
            "La PR contiene más de un reto. Se detectaron estas carpetas: "
            + ", ".join(f"`{r}`" for r in sorted(roots))
            + ". Recuerda: **1 PR = 1 reto**."
        )

    challenge_root = sorted(roots)[0] if len(roots) == 1 else None

    if challenge_root:
        root_path = Path(challenge_root)
        category = challenge_root.split("/")[0]

        challenge_yml = root_path / "challenge.yml"
        writeup_md = root_path / "writeup" / "WRITEUP.md"

        if not challenge_yml.exists():
            errors.append(f"Falta `{challenge_root}/challenge.yml`.")
        if not writeup_md.exists():
            errors.append(f"Falta `{challenge_root}/writeup/WRITEUP.md`.")

        data: dict[str, Any] | None = None
        if challenge_yml.exists():
            data, yaml_error = load_yaml(challenge_yml)
            if yaml_error:
                errors.append(yaml_error)

        if data is not None:
            missing = [field for field in REQUIRED_FIELDS if field not in data]
            if missing:
                errors.append(
                    "Faltan campos obligatorios en `challenge.yml`: "
                    + ", ".join(f"`{m}`" for m in missing)
                )

            for key, expected in FORCED_VALUES.items():
                if data.get(key) != expected:
                    errors.append(
                        f"`{key}` debe ser `{expected}` y actualmente es `{data.get(key)}`."
                    )

            if data.get("category") != category:
                errors.append(
                    f"`category` debe coincidir con la carpeta: se esperaba `{category}` "
                    f"y se encontró `{data.get('category')}`."
                )

            errors.extend(validate_flags(data.get("flags")))
            errors.extend(validate_files_field(root_path, data.get("files")))

            if isinstance(data.get("name"), str):
                duplicates = find_duplicate_names(challenge_root, data["name"])
                if duplicates:
                    errors.append(
                        "El valor de `name` ya existe en otros retos: "
                        + ", ".join(f"`{d}`" for d in duplicates)
                    )

            suspicious_values = []
            for key in ("name", "author", "description"):
                value = data.get(key)
                if isinstance(value, str):
                    for marker in TEMPLATE_MARKERS:
                        if marker.lower() in value.lower():
                            suspicious_values.append(f"{key} contiene `{marker}`")

            for idx, flag in enumerate(data.get("flags") or [], start=1):
                if isinstance(flag, dict):
                    content = flag.get("content")
                    if isinstance(content, str) and "example_flag" in content.lower():
                        suspicious_values.append(f"flags[{idx}].content contiene `example_flag`")

            if suspicious_values:
                errors.append(
                    "Parece que aún hay valores de plantilla sin editar: "
                    + ", ".join(suspicious_values)
                )

        if writeup_md.exists():
            errors.extend(validate_writeup(writeup_md))

    report = build_report(errors, warnings, changed_files)
    Path(args.report_path).write_text(report, encoding="utf-8")

    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(report)

    print(report)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
