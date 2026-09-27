import json
import logging
import os
from typing import Any, Dict, List, Optional

from .collector import HTTPCollector
from .database import Database
from .filter_engine import FilterEngine
from .notifiers.console import ConsoleNotifier
from .notifiers.discord import DiscordNotifier
from .notifiers.markdown_report import MarkdownReporter
from .notifiers.telegram import TelegramNotifier
from .parsers.pci import PCIParser

logger = logging.getLogger("monitor.engine")


class ConcursosEngine:
    """Motor central que orquestra coleta, parseamento, persistência e notificações."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.base_dir = base_dir

        self.config_path = os.path.join(self.base_dir, "config", "settings.json")
        self.config = self.load_config()

        db_path = os.path.join(self.base_dir, self.config["general"].get("db_path", "data/concursos.db"))
        report_path = os.path.join(self.base_dir, self.config["general"].get("report_path", "data/relatorio_atual.md"))

        self.db = Database(db_path)
        self.collector = HTTPCollector(timeout=15)
        self.parser = PCIParser()
        self.filter_engine = FilterEngine(self.config.get("filters", {}))
        self.console = ConsoleNotifier()
        self.markdown_reporter = MarkdownReporter(report_path)

        # Notificadores remotos
        tg_conf = self.config.get("notifications", {}).get("telegram", {})
        self.telegram = TelegramNotifier(tg_conf.get("bot_token", ""), tg_conf.get("chat_id", ""))

        dc_conf = self.config.get("notifications", {}).get("discord", {})
        self.discord = DiscordNotifier(dc_conf.get("webhook_url", ""))

    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, new_config: Dict[str, Any]):
        self.config = new_config
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        self.filter_engine = FilterEngine(self.config.get("filters", {}))

    def run_scan(self, ufs_override: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Executa a varredura completa nas fontes configuradas (PCI Concursos por padrão).
        """
        pci_config = self.config.get("sources", {}).get("pci_concursos", {})
        if not pci_config.get("enabled", True):
            return {"total_scanned": 0, "new_count": 0, "new_items": []}

        base_url = pci_config.get("base_url", "https://www.pciconcursos.com.br/concursos/")
        target_ufs = ufs_override or pci_config.get("ufs", ["nacional"])

        all_scanned_items = []
        new_items = []
        updated_count = 0

        self.console.print_header(f"Iniciando varredura em {len(target_ufs)} regiões/estados")

        # Mapeamento de UFs para macro-regiões do PCI Concursos
        STATE_TO_REGION = {
            "sp": "sudeste", "rj": "sudeste", "mg": "sudeste", "es": "sudeste",
            "pr": "sul", "sc": "sul", "rs": "sul",
            "df": "centrooeste", "go": "centrooeste", "mt": "centrooeste", "ms": "centrooeste",
            "ba": "nordeste", "pe": "nordeste", "ce": "nordeste", "ma": "nordeste", "pb": "nordeste", "rn": "nordeste", "al": "nordeste", "se": "nordeste", "pi": "nordeste",
            "am": "norte", "pa": "norte", "ro": "norte", "to": "norte", "ac": "norte", "ap": "norte", "rr": "norte",
            "nacional": "nacional"
        }

        # Resolve quais URLs buscar (se tiver "todos", busca a página principal que contém todo o país)
        normalized_targets = [u.strip().lower() for u in target_ufs]
        if "todos" in normalized_targets or "brasil" in normalized_targets or len(normalized_targets) >= 5:
            urls_to_fetch = [("BRASIL (TODOS OS ESTADOS)", base_url.rstrip("/") + "/")]
        else:
            regions_needed = set()
            for u in normalized_targets:
                reg = STATE_TO_REGION.get(u, u)
                regions_needed.add(reg)
            urls_to_fetch = [(reg.upper(), f"{base_url.rstrip('/')}/{reg}/") for reg in regions_needed]

        self.console.print_header(f"Iniciando varredura em {len(urls_to_fetch)} fonte(s)")

        for label, url in urls_to_fetch:
            print(f"📡 Coletando editais de [{label}] em: {url} ...", end=" ", flush=True)
            status, html_content = self.collector.fetch(url)

            if status != 200 or not html_content:
                print(f"❌ Falha (HTTP {status})")
                continue

            parsed_list = self.parser.parse(html_content, uf="nacional" if "nacional" in url else "geral")
            print(f"✓ {len(parsed_list)} editais processados")

            for item in parsed_list:
                all_scanned_items.append(item)
                is_new, is_updated = self.db.upsert_concurso(item)
                if is_new:
                    new_items.append(item)
                elif is_updated:
                    updated_count += 1

        # Filtra os novos itens de acordo com as preferências do usuário
        matched_new_items = self.filter_engine.filter_list(new_items)

        # Notificações de novos itens compatíveis
        notified_ids = []
        for item in matched_new_items:
            # Console
            self.console.print_concurso_card(item, is_new=True)

            # Telegram
            if self.telegram.is_configured():
                self.telegram.notify_concurso(item)

            # Discord
            if self.discord.is_configured():
                self.discord.send_embed(item)

            notified_ids.append(item["external_id"])

        if notified_ids:
            self.db.mark_as_notified(notified_ids)

        # Estatísticas gerais do banco
        stats = self.db.get_stats()
        all_active_concursos = self.db.query_concursos(only_active=True, limit=50)

        # Atualiza relatório Markdown
        self.markdown_reporter.generate(
            concursos=all_active_concursos,
            new_concursos=matched_new_items,
            stats=stats
        )

        # Registra no log de auditoria
        self.db.log_check_run(
            total_found=len(all_scanned_items),
            new_found=len(new_items),
            details=f"Varredura em {len(target_ufs)} UFs. Itens filtrados: {len(matched_new_items)}"
        )

        self.console.print_summary(
            total_scanned=len(all_scanned_items),
            new_found=len(new_items),
            filtered_count=len(matched_new_items)
        )

        return {
            "total_scanned": len(all_scanned_items),
            "new_count": len(new_items),
            "filtered_new_count": len(matched_new_items),
            "new_items": matched_new_items
        }
