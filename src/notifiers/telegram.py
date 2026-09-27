import json
import logging
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("monitor.telegram")


class TelegramNotifier:
    """Envia notificações de editais novos diretamente para um Bot do Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str) -> bool:
        if not self.is_configured():
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False

    def notify_concurso(self, c: Dict[str, Any]) -> bool:
        sal = f"R$ {c['salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if c.get("salary") else "Não informado"
        prazo = c.get("deadline_text") or "Não informado"

        text = (
            f"🚨 <b>NOVO CONCURSO IDENTIFICADO!</b>\n\n"
            f"🏛 <b>{c['title']}</b>\n"
            f"📍 <b>UF:</b> {c.get('uf', 'BR')}\n"
            f"💰 <b>Salário:</b> {sal}\n"
            f"👥 <b>Vagas:</b> {c.get('vacancies_text', 'N/I')}\n"
            f"📅 <b>Inscrições até:</b> {prazo}\n"
            f"📝 <b>Detalhes:</b> {c.get('details', '')[:180]}\n\n"
            f"🔗 <a href=\"{c['url']}\">Clique aqui para ver o Edital</a>"
        )
        return self.send_message(text)
