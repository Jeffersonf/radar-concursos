#!/usr/bin/env python3
"""
export_static.py - Gerador de Versão Estática para GitHub Pages
Exporta todos os editais, estatísticas e cidades para arquivos JSON estáticos
e prepara a pasta `docs/` para publicação direta no GitHub Pages.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Suporte a UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ajusta path para importar módulos de src/
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.database import Database
from src.geo_engine import BRAZILIAN_CITIES, UF_CENTROIDS


def export_static(scan_first: bool = False, output_dir: str = "docs"):
    out_path = BASE_DIR / output_dir
    data_path = out_path / "data"
    data_path.mkdir(parents=True, exist_ok=True)

    db_path = BASE_DIR / "data" / "concursos.db"
    db = Database(str(db_path))

    if scan_first:
        print("🔍 Executando varredura prévia de concursos...")
        try:
            from src.monitor_engine import MonitorEngine
            engine = MonitorEngine(db=db)
            engine.scan()
        except Exception as e:
            print(f"⚠️ Aviso na varredura: {e}")

    print("📦 Exportando editais do banco SQLite...")
    # Consulta todos os concursos ativos e recentes
    concursos = db.query_concursos(limit=3000, only_active=False)
    stats = db.get_stats()
    analytics = db.get_analytics()

    # Prepara lista de cidades para autocompletar offline
    cities = []
    for city_key, (lat, lon, uf) in BRAZILIAN_CITIES.items():
        name = " ".join([w.capitalize() for w in city_key.split()])
        cities.append({"name": f"{name} - {uf}", "query": city_key, "lat": lat, "lon": lon})
    for uf, (lat, lon, cap) in UF_CENTROIDS.items():
        if uf != "NACIONAL":
            cities.append({"name": f"{cap} ({uf})", "query": cap.lower(), "lat": lat, "lon": lon})

    # 1. Salva concursos.json (no diretório docs/ e docs/data/)
    concursos_payload = {
        "concursos": concursos,
        "total": len(concursos),
        "exported_at": stats.get("last_updated") or ""
    }

    with open(data_path / "concursos.json", "w", encoding="utf-8") as f:
        json.dump(concursos_payload, f, ensure_ascii=False, indent=2)

    with open(out_path / "concursos.json", "w", encoding="utf-8") as f:
        json.dump(concursos_payload, f, ensure_ascii=False, indent=2)

    # 2. Salva stats.json
    with open(data_path / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 3. Salva analytics.json
    with open(data_path / "analytics.json", "w", encoding="utf-8") as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)

    # 4. Salva cities.json
    cities_payload = {"cities": cities}
    with open(data_path / "cities.json", "w", encoding="utf-8") as f:
        json.dump(cities_payload, f, ensure_ascii=False, indent=2)

    with open(out_path / "cities.json", "w", encoding="utf-8") as f:
        json.dump(cities_payload, f, ensure_ascii=False, indent=2)

    # 5. Copia os arquivos estáticos do front-end
    static_src = BASE_DIR / "src" / "web" / "static"
    for fname in ["index.html", "style.css", "app.js"]:
        src_file = static_src / fname
        if src_file.exists():
            shutil.copy2(src_file, out_path / fname)
            print(f"  ✓ Copiado: {fname} -> {output_dir}/{fname}")

    # 6. Cria arquivo .nojekyll para o GitHub Pages não barrar pastas
    nojekyll = out_path / ".nojekyll"
    nojekyll.touch(exist_ok=True)
    print("  ✓ Criado: .nojekyll")

    print(f"\n✅ Exportação estática concluída com sucesso!")
    print(f"   Total de editais: {len(concursos)}")
    print(f"   Destino: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta versão estática para GitHub Pages")
    parser.add_argument("--scan", action="store_true", help="Faz varredura no PCI Concursos antes de exportar")
    parser.add_argument("--out", default="docs", help="Pasta de saída (padrão: docs)")
    args = parser.parse_args()

    export_static(scan_first=args.scan, output_dir=args.out)
