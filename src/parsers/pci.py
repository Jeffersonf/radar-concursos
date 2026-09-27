import datetime
import hashlib
import html
import re
from typing import Any, Dict, List, Optional

from ..geo_engine import extract_city_and_coords


class PCIParser:
    """Parser especializado para as listagens do PCI Concursos (Nacional e regionais)."""

    ENTRY_PATTERN = re.compile(
        r'<div class="ca">\s*<a\s+href="(?P<link>[^"]+)"[^>]*>(?P<title>.*?)</a>(?P<extra_ca>.*?)</div>\s*'
        r'(?:<div class="cb">.*?</div>\s*)?'
        r'(?:<div class="cc">(?P<cc_uf>.*?)</div>\s*)?'
        r'<div class="cd">(?P<details>.*?)</div>\s*'
        r'<div class="ce">(?P<deadline>.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )

    BANCAS_MAP = {
        "cebraspe": "Cebraspe",
        "cespe": "Cebraspe",
        "fgv": "FGV",
        "fundação carlos chagas": "FCC",
        "fcc": "FCC",
        "vunesp": "Vunesp",
        "cesgranrio": "Cesgranrio",
        "instituto aocp": "Instituto AOCP",
        "aocp": "Instituto AOCP",
        "ibfc": "IBFC",
        "idecan": "Idecan",
        "quadrix": "Quadrix",
        "consulplan": "Consulplan",
        "fepese": "Fepese",
        "fundatec": "Fundatec",
        "avança sp": "Avança SP",
        "avancasp": "Avança SP",
        "nosso rumo": "Nosso Rumo",
        "instituto legatus": "Instituto Legatus",
        "legatus": "Instituto Legatus",
        "cotec": "Cotec / Unimontes",
        "objetiva": "Objetiva Concursos",
        "fadesp": "Fadesp",
        "iades": "Iades",
        "comperve": "Comperve",
        "fundep": "Fundep",
        "instituto mais": "Instituto Mais",
        "fapec": "FAPEC",
        "funrio": "Funrio",
        "selecon": "Selecon",
    }

    CAREER_MAP = {
        "TI & Dados": [
            "ti", "informática", "tecnologia", "computação", "desenvolvedor",
            "programador", "sistemas", "redes", "dados", "software",
            "analista de ti", "ciência de dados", "suporte técnico"
        ],
        "Jurídico & Tribunais": [
            "advogado", "direito", "procurador", "juiz", "promotor",
            "defensoria", "oab", "jurídico", "escrevente", "oficial de justiça",
            "tribunal", "judiciário", "magistratura"
        ],
        "Fiscal & Controle": [
            "auditor", "fiscal", "tributário", "controlador", "receita",
            "tce", "tcu", "cgm", "fazenda", "arrecadação", "contabilidade", "contador"
        ],
        "Segurança & Policial": [
            "guarda", "policial", "polícia", "perito", "bombeiro",
            "penitenciário", "vigilante", "investigador", "delegado",
            "agente de trânsito", "militar", "segurança pública"
        ],
        "Saúde": [
            "médico", "enfermeiro", "enfermagem", "dentista", "odontólogo",
            "farmacêutico", "psicólogo", "fisioterapeuta", "nutricionista",
            "biomédico", "saúde", "veterinário", "terapeuta", "fonoaudiólogo"
        ],
        "Educação": [
            "professor", "docente", "pedagogo", "educação", "educador",
            "orientador educacional", "magistério", "diretor de escola"
        ],
        "Administrativo": [
            "administrativo", "administração", "almoxarife", "auxiliar de escritório",
            "recepcionista", "secretário", "técnico legislativo", "recursos humanos",
            "atendente", "assistente administrativo"
        ]
    }

    def clean_html(self, raw_html: str) -> str:
        """Remove tags HTML, entidades e normaliza espaços."""
        if not raw_html:
            return ""
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def parse_salary(self, text: str) -> Optional[float]:
        """Extrai o maior valor monetário encontrado no texto."""
        matches = re.findall(r"R\$\s*([0-9\.,]+)", text)
        if not matches:
            return None

        salaries = []
        for m in matches:
            clean_str = m.strip().rstrip(".,")
            clean_num = clean_str.replace(".", "").replace(",", ".")
            try:
                val = float(clean_num)
                salaries.append(val)
            except ValueError:
                continue

        return max(salaries) if salaries else None

    def parse_vacancies(self, text: str) -> Dict[str, Any]:
        """Identifica número de vagas ou se é cadastro reserva."""
        match = re.search(r"(\d+)\s+vagas?", text, re.IGNORECASE)
        vacancies_num = int(match.group(1)) if match else None
        is_cr = bool(re.search(r"cadastro\s+de\s+reserva|cr\b", text, re.IGNORECASE))
        return {
            "vacancies": vacancies_num,
            "is_cr": is_cr,
            "text": f"{vacancies_num} vagas" if vacancies_num else ("Cadastro de Reserva" if is_cr else "Vagas não informadas")
        }

    def parse_education(self, text: str) -> List[str]:
        """Detecta níveis de escolaridade mencionados no edital."""
        levels = []
        text_lower = text.lower()
        if "superior" in text_lower or "gradua" in text_lower:
            levels.append("Superior")
        if "técnico" in text_lower or "tecnico" in text_lower:
            levels.append("Técnico")
        if "médio" in text_lower or "medio" in text_lower:
            levels.append("Médio")
        if "fundamental" in text_lower:
            levels.append("Fundamental")
        if "alfabetizado" in text_lower:
            levels.append("Alfabetizado")
        return levels

    def parse_deadline(self, raw_deadline: str) -> Dict[str, Any]:
        """Extrai data de encerramento das inscrições e calcula dias restantes."""
        clean_deadline = self.clean_html(raw_deadline)
        date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", clean_deadline)

        deadline_date = None
        days_remaining = None
        is_expired = False
        is_extended = "prorrogad" in clean_deadline.lower()

        if date_match:
            day, month, year = map(int, date_match.groups())
            try:
                deadline_date = datetime.date(year, month, day)
                today = datetime.date.today()
                diff = (deadline_date - today).days
                days_remaining = diff
                is_expired = diff < 0
            except ValueError:
                pass

        return {
            "raw_text": clean_deadline,
            "date": deadline_date.isoformat() if deadline_date else None,
            "days_remaining": days_remaining,
            "is_expired": is_expired,
            "is_extended": is_extended
        }

    def detect_banca(self, title: str, details: str) -> str:
        """Identifica a banca organizadora do concurso se mencionada."""
        combined = f"{title} {details}".lower()
        for key, name in self.BANCAS_MAP.items():
            if re.search(r'\b' + re.escape(key) + r'\b', combined):
                return name
        return "Órgão Próprio / A Definir"

    def detect_tipo(self, title: str, details: str) -> str:
        """Classifica entre Concurso Público Efetivo ou Processo Seletivo Simplificado."""
        combined = f"{title} {details}".lower()
        if any(term in combined for term in ["processo seletivo", "seletivo simplificado", "pss", "temporár", "contratação temporária"]):
            return "Processo Seletivo"
        if any(term in combined for term in ["estágio", "estagiário", "residente", "residência"]):
            return "Estágio / Residência"
        return "Concurso Público"

    def detect_carreiras(self, title: str, details: str) -> List[str]:
        """Classifica as áreas de atuação / carreiras profissionais do edital."""
        combined = f"{title} {details}".lower()
        matched_careers = []
        for career_name, keywords in self.CAREER_MAP.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', combined) for kw in keywords):
                matched_careers.append(career_name)
        return matched_careers or ["Geral / Administrativo"]

    def parse(self, html_content: str, uf: str = "nacional") -> List[Dict[str, Any]]:
        """Processa o HTML do PCI Concursos e extrai editais enriquecidos."""
        concursos = []
        for match in self.ENTRY_PATTERN.finditer(html_content):
            raw_title = match.group("title")
            link = match.group("link").strip()
            raw_details = match.group("details")
            raw_deadline = match.group("deadline")

            title = self.clean_html(raw_title)
            details = self.clean_html(raw_details)

            salary_val = self.parse_salary(details)
            vacancies_info = self.parse_vacancies(details)
            education_levels = self.parse_education(details)
            deadline_info = self.parse_deadline(raw_deadline)

            # Detecção semântica avançada
            banca = self.detect_banca(title, details)
            tipo = self.detect_tipo(title, details)
            carreiras = self.detect_carreiras(title, details)

            # Detecção de UF
            cc_raw = self.clean_html(match.group("cc_uf") or "")
            if cc_raw and len(cc_raw) == 2 and cc_raw.isalpha():
                detected_uf = cc_raw.upper()
            elif uf.lower() in ("todos", "geral"):
                detected_uf = "NACIONAL"
            else:
                detected_uf = uf.upper()

            # Resolução geoespacial da cidade e coordenadas
            cidade, lat, lon = extract_city_and_coords(title, details, detected_uf)

            # Hash único
            external_id = hashlib.md5(f"{title}_{link}".encode("utf-8")).hexdigest()[:14]

            concurso = {
                "external_id": external_id,
                "title": title,
                "url": link,
                "uf": detected_uf,
                "cidade": cidade,
                "lat": lat,
                "lon": lon,
                "details": details,
                "salary": salary_val,
                "vacancies": vacancies_info["vacancies"],
                "vacancies_text": vacancies_info["text"],
                "is_cr": vacancies_info["is_cr"],
                "education": education_levels,
                "deadline_date": deadline_info["date"],
                "deadline_text": deadline_info["raw_text"],
                "days_remaining": deadline_info["days_remaining"],
                "is_expired": deadline_info["is_expired"],
                "is_extended": deadline_info["is_extended"],
                "banca": banca,
                "tipo": tipo,
                "area": ", ".join(carreiras),
                "source": "PCI Concursos"
            }
            concursos.append(concurso)

        return concursos

    @classmethod
    def enrich_concurso_details(cls, url: str) -> Dict[str, Any]:
        """
        Acessa a página da notícia no PCI Concursos e extrai informações detalhadas:
        Data prevista da prova, taxa de inscrição, carga horária, regime de contratação,
        período de inscrições completo, link oficial da banca e resumo dos cargos.
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                raw_bytes = resp.read()
                try:
                    content = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw_bytes.decode('latin-1', errors='replace')
        except Exception:
            return {}

        # 1. Parágrafos do artigo
        paragraphs_raw = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        cleaned_paras = []
        for p in paragraphs_raw:
            txt = html.unescape(re.sub(r'<[^>]+>', ' ', p)).strip()
            txt = re.sub(r'\s+', ' ', txt)
            if any(ign in txt.lower() for ign in ["otimize sua preparação", "escutar o podcast", "complete a verificação abaixo", "apostilas digitais", "compartilhe no"]):
                continue
            if len(txt) > 20:
                cleaned_paras.append(txt)

        full_summary = "\n\n".join(cleaned_paras) if cleaned_paras else ""

        # 2. Data Prevista da Prova
        exam_date = ""
        prova_matches = re.findall(r'prova[^.]+?(?:prevista|marcada|aplicada|ocorrer|realizada)[^.]+?\.', full_summary, re.IGNORECASE)
        if prova_matches:
            exam_date = prova_matches[0].strip()

        # 3. Taxa de Inscrição & Isenção
        fee_text = ""
        taxa_matches = re.findall(r'(?:taxa|valor)[^.]+?R\$\s*[\d\.,]+[^.]+?\.', full_summary, re.IGNORECASE)
        if taxa_matches:
            fee_text = taxa_matches[0].strip()
        elif any(w in full_summary.lower() for w in ["não haverá cobrança de taxa", "sem cobrança de taxa", "inscrições gratuitas", "inscrição gratuita", "isento"]):
            fee_text = "Inscrição Gratuita (sem taxa)"

        # 4. Carga Horária Semanal
        workload = ""
        workload_match = re.search(r'(\d+\s*horas\s*semanais|\d+h\s*semanais|\d+\s*horas\s*diárias)', full_summary, re.IGNORECASE)
        if workload_match:
            workload = workload_match.group(1).strip()

        # 5. Regime de Contratação
        regime = ""
        if re.search(r'\bclt\b|consolidação das leis do trabalho', full_summary, re.IGNORECASE):
            regime = "CLT (Consolidação das Leis do Trabalho)"
        elif re.search(r'\bestatutário\b|estatutaria|regime jurídico único', full_summary, re.IGNORECASE):
            regime = "Estatutário (Estabilidade)"
        elif re.search(r'\btemporário\b|contratação temporária|prazo determinado', full_summary, re.IGNORECASE):
            regime = "Temporário (PSS)"

        # 6. Período Completo das Inscrições
        application_period = ""
        insc_match = re.search(r'inscriç[õo]es\s+(?:poderão\s+ser\s+realizadas|ocorrem|abertas|serão\s+feitas)\s+(?:de|entre|a\s+partir\s+de)\s+([^.]+?\.)', full_summary, re.IGNORECASE)
        if insc_match:
            application_period = f"De {insc_match.group(1).strip()}"

        # 7. Link Oficial da Banca / Inscrição
        official_url = ""
        all_links = re.findall(r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', content, re.DOTALL | re.IGNORECASE)
        for href, text in all_links:
            clean_text = text.lower()
            if any(ign in href for ign in ["pciconcursos", "google", "facebook", "twitter", "instagram", "youtube", "pci.app.br", "fonts.gstatic"]):
                continue
            if any(w in clean_text or w in href for w in ["cebraspe", "vunesp", "fgv", "fcc", "ibfc", "aocp", "quadrix", "concurso", "inscricao", "candidato", "avalia"]):
                official_url = href
                break
            if not official_url and href.startswith("http"):
                official_url = href

        return {
            "exam_date": exam_date,
            "fee_text": fee_text,
            "workload": workload,
            "regime": regime,
            "application_period": application_period,
            "official_url": official_url,
            "full_summary": full_summary
        }

