import logging
import urllib.error
import urllib.request
from typing import Optional, Tuple

logger = logging.getLogger("monitor.collector")


class HTTPCollector:
    """Coletor HTTP robusto baseado na biblioteca padrão do Python."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def fetch(self, url: str) -> Tuple[int, str]:
        """
        Executa requisição HTTP GET retornando (status_code, html_content).
        Trata automaticamente encodings como ISO-8859-1 e UTF-8 para preservar acentos em português.
        """
        req = urllib.request.Request(url, headers=self.DEFAULT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                raw_bytes = response.read()

                # Tenta identificar charset a partir dos headers
                content_type = response.headers.get("content-type", "").lower()
                encoding = "utf-8"
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].split(";")[0].strip()
                elif "iso-8859" in content_type or "latin" in content_type:
                    encoding = "iso-8859-1"
                else:
                    # Em portais como PCI Concursos, iso-8859-1 é o padrão se UTF-8 falhar
                    try:
                        decoded = raw_bytes.decode("utf-8")
                        return status_code, decoded
                    except UnicodeDecodeError:
                        encoding = "iso-8859-1"

                try:
                    decoded = raw_bytes.decode(encoding, errors="replace")
                except Exception:
                    decoded = raw_bytes.decode("iso-8859-1", errors="replace")

                return status_code, decoded

        except urllib.error.HTTPError as e:
            logger.warning(f"Erro HTTP {e.code} ao acessar {url}")
            return e.code, ""
        except urllib.error.URLError as e:
            logger.error(f"Erro de conexão ao acessar {url}: {e.reason}")
            return 500, ""
        except Exception as e:
            logger.error(f"Erro inesperado ao acessar {url}: {e}")
            return 500, ""
