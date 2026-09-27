import json
import logging
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("monitor.discord")


class DiscordNotifier:
    """Envia notificações de editais novos via Webhook do Discord com Embeds estilizados."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("https://discord.com/api/webhooks/"))

    def send_embed(self, c: Dict[str, Any]) -> bool:
        if not self.is_configured():
            return False

        sal = f"R$ {c['salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if c.get("salary") else "Não informado"
        prazo = c.get("deadline_text") or "Não informado"

        embed = {
            "title": f"🚨 {c['title']}",
            "url": c["url"],
            "color": 3066993,  # Verde esmeralda (#2ecc71)
            "fields": [
                {"name": "📍 UF", "value": c.get("uf", "BR"), "inline": True},
                {"name": "💰 Salário", "value": sal, "inline": True},
                {"name": "👥 Vagas", "value": c.get("vacancies_text", "N/I"), "inline": True},
                {"name": "📅 Inscrições até", "value": prazo, "inline": True},
                {"name": "🎓 Escolaridade", "value": ", ".join(c.get("education", [])) or "Geral", "inline": True},
                {"name": "📝 Detalhes", "value": c.get("details", "")[:250], "inline": False}
            ],
            "footer": {
                "text": "Monitor de Concursos Públicos"
            }
        }

        payload = {
            "content": "✨ **Novo concurso encontrado no radar!**",
            "embeds": [embed]
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ConcursosMonitor/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Erro ao enviar webhook do Discord: {e}")
            return False
