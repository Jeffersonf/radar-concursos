import json
import logging
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict

from ..geo_engine import BRAZILIAN_CITIES, UF_CENTROIDS, resolve_user_location
from ..notifiers.discord import DiscordNotifier
from ..notifiers.telegram import TelegramNotifier
from ..parsers.pci import PCIParser

logger = logging.getLogger("monitor.web")


class DashboardHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP REST + arquivos estáticos para o painel de concursos."""

    db = None
    config = None
    engine = None
    scan_callback: Callable = None
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw)
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Rota de API: Concursos com filtros avançados e distância
        if path == "/api/concursos":
            uf = query.get("uf", [None])[0]
            search = query.get("search", [None])[0]
            min_salary = float(query.get("min_salary", [0.0])[0] or 0.0)
            education = query.get("education", [None])[0]
            area = query.get("area", [None])[0]
            banca = query.get("banca", [None])[0]
            tipo = query.get("tipo", [None])[0]
            sort_by = query.get("sort_by", ["default"])[0]
            only_active = query.get("only_active", ["false"])[0].lower() == "true"
            only_favs = query.get("only_favorites", ["false"])[0].lower() == "true"
            limit = int(query.get("limit", [250])[0])

            # Parâmetros de Geodistância
            user_lat = float(query.get("user_lat", [None])[0]) if query.get("user_lat", [None])[0] else None
            user_lon = float(query.get("user_lon", [None])[0]) if query.get("user_lon", [None])[0] else None
            max_dist = float(query.get("max_distance", [0.0])[0] or 0.0) if query.get("max_distance", [None])[0] else None

            results = self.db.query_concursos(
                uf=uf,
                search_query=search,
                min_salary=min_salary,
                education=education,
                area=area,
                banca=banca,
                tipo=tipo,
                only_active=only_active,
                only_favorites=only_favs,
                user_lat=user_lat,
                user_lon=user_lon,
                max_distance_km=max_dist,
                sort_by=sort_by,
                limit=limit
            )
            self._send_json({"total": len(results), "concursos": results})
            return

        # Rota de API: Detalhes Completos e Aprofundados do Concurso
        if path == "/api/concurso/details":
            ext_id = query.get("id", [None])[0]
            if not ext_id:
                self._send_json({"error": "ID é obrigatório"}, 400)
                return

            item = self.db.get_concurso_by_id(ext_id)
            if not item:
                self._send_json({"error": "Concurso não encontrado"}, 404)
                return

            # Se ainda não possui o resumo aprofundado ou taxa, faz o enriquecimento automático sob demanda
            if not item.get("full_summary") or not item.get("fee_text"):
                try:
                    enriched = PCIParser.enrich_concurso_details(item["url"])
                    if enriched:
                        self.db.update_concurso_details(ext_id, enriched)
                        item.update(enriched)
                except Exception as e:
                    logger.warning(f"Erro ao enriquecer detalhes do concurso {ext_id}: {e}")

            self._send_json(item)
            return

        # Rota de API: Estatísticas Rápidas
        if path == "/api/stats":
            stats = self.db.get_stats()
            self._send_json(stats)
            return

        # Rota de API: Analytics Completo com Gráficos
        if path == "/api/analytics":
            analytics_data = self.db.get_analytics()
            self._send_json(analytics_data)
            return

        # Rota de API: Resolução de Localização do Usuário (Nome da Cidade -> Coordenadas)
        if path == "/api/resolve-location":
            city_query = query.get("city", [""])[0]
            loc = resolve_user_location(city_query)
            if loc:
                name, lat, lon = loc
                self._send_json({"found": True, "name": name, "lat": lat, "lon": lon})
            else:
                self._send_json({"found": False, "error": "Cidade não localizada"}, 404)
            return

        # Rota de API: Lista de Cidades Sugeridas
        if path == "/api/cities":
            cities = []
            for city_key, (lat, lon, uf) in BRAZILIAN_CITIES.items():
                name = " ".join([w.capitalize() for w in city_key.split()])
                cities.append({"name": f"{name} - {uf}", "query": city_key, "lat": lat, "lon": lon})
            for uf, (lat, lon, cap) in UF_CENTROIDS.items():
                if uf != "NACIONAL":
                    cities.append({"name": f"{cap} ({uf})", "query": cap, "lat": lat, "lon": lon})
            self._send_json({"cities": cities})
            return

        # Rota de API: Exportar CSV
        if path == "/api/export":
            uf = query.get("uf", [None])[0]
            search = query.get("search", [None])[0]
            min_salary = float(query.get("min_salary", [0.0])[0] or 0.0)
            education = query.get("education", [None])[0]
            area = query.get("area", [None])[0]
            banca = query.get("banca", [None])[0]
            tipo = query.get("tipo", [None])[0]
            only_active = query.get("only_active", ["false"])[0].lower() == "true"
            only_favs = query.get("only_favorites", ["false"])[0].lower() == "true"

            user_lat = float(query.get("user_lat", [None])[0]) if query.get("user_lat", [None])[0] else None
            user_lon = float(query.get("user_lon", [None])[0]) if query.get("user_lon", [None])[0] else None
            max_dist = float(query.get("max_distance", [0.0])[0] or 0.0) if query.get("max_distance", [None])[0] else None

            results = self.db.query_concursos(
                uf=uf,
                search_query=search,
                min_salary=min_salary,
                education=education,
                area=area,
                banca=banca,
                tipo=tipo,
                only_active=only_active,
                only_favorites=only_favs,
                user_lat=user_lat,
                user_lon=user_lon,
                max_distance_km=max_dist,
                limit=1500
            )

            csv_content = self.db.export_csv(results)
            csv_bytes = csv_content.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="concursos_brasil.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        # Rota de API: Configuração
        if path == "/api/config":
            self._send_json(self.config)
            return

        # Servir Frontend Estático
        if path == "/" or path == "/index.html":
            file_path = os.path.join(self.static_dir, "index.html")
        else:
            rel_path = path.lstrip("/")
            file_path = os.path.join(self.static_dir, rel_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "text/plain"
            if mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json"):
                mime_type += "; charset=utf-8"

            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "Arquivo não encontrado")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Favoritar/Desfavoritar
        if path == "/api/favorite":
            data = self._read_json_body()
            ext_id = data.get("external_id")
            if not ext_id:
                self._send_json({"error": "external_id obrigatório"}, 400)
                return
            new_status = self.db.toggle_favorite(ext_id)
            self._send_json({"external_id": ext_id, "is_favorite": new_status})
            return

        # Salvar Anotações Pessoais do Concurseiro
        if path == "/api/notes":
            data = self._read_json_body()
            ext_id = data.get("external_id")
            notes = data.get("notes", "")
            if not ext_id:
                self._send_json({"error": "external_id obrigatório"}, 400)
                return
            ok = self.db.save_notes(ext_id, notes)
            self._send_json({"success": ok, "external_id": ext_id})
            return

        # Disparar varredura sob demanda
        if path == "/api/scan":
            if self.scan_callback:
                summary = self.scan_callback()
                self._send_json({"status": "success", "summary": summary})
            else:
                self._send_json({"error": "Scan callback indisponível"}, 500)
            return

        # Salvar configurações
        if path == "/api/settings":
            data = self._read_json_body()
            if self.engine:
                current_cfg = self.engine.config
                if "filters" in data:
                    current_cfg["filters"].update(data["filters"])
                if "notifications" in data:
                    current_cfg["notifications"].update(data["notifications"])
                self.engine.save_config(current_cfg)
                self._send_json({"status": "success", "config": current_cfg})
            else:
                self._send_json({"error": "Engine indisponível"}, 500)
            return

        # Testar Telegram
        if path == "/api/test-telegram":
            data = self._read_json_body()
            token = data.get("token") or self.config.get("notifications", {}).get("telegram", {}).get("bot_token")
            chat_id = data.get("chat_id") or self.config.get("notifications", {}).get("telegram", {}).get("chat_id")

            if not token or not chat_id:
                self._send_json({"success": False, "error": "Token e Chat ID são obrigatórios"}, 400)
                return

            tg = TelegramNotifier(token, chat_id)
            ok = tg.send_message("🔔 <b>Teste do Monitor de Concursos</b>\n\nSua integração com o Telegram está funcionando perfeitamente! 🎯")
            self._send_json({"success": ok})
            return

        # Testar Discord
        if path == "/api/test-discord":
            data = self._read_json_body()
            webhook = data.get("webhook_url") or self.config.get("notifications", {}).get("discord", {}).get("webhook_url")

            if not webhook:
                self._send_json({"success": False, "error": "Webhook URL é obrigatório"}, 400)
                return

            dc = DiscordNotifier(webhook)
            test_concurso = {
                "title": "Concurso Teste de Notificação",
                "url": "http://127.0.0.1:8090",
                "uf": "BR",
                "salary": 12500.0,
                "vacancies_text": "10 vagas",
                "deadline_text": "31/12/2026",
                "education": ["Superior"],
                "details": "Mensagem de teste de envio de webhook no Discord."
            }
            ok = dc.send_embed(test_concurso)
            self._send_json({"success": ok})
            return

        self.send_error(404, "Endpoint não encontrado")


def start_server(host: str, port: int, db, config, scan_callback=None, engine=None):
    """Inicia o servidor web local em uma porta dedicada."""
    DashboardHandler.db = db
    DashboardHandler.config = config
    DashboardHandler.scan_callback = scan_callback
    DashboardHandler.engine = engine

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, DashboardHandler)
    logger.info(f"Dashboard rodando em http://{host}:{port}/")
    return httpd
