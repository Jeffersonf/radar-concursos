import datetime
import os
from typing import Any, Dict, List


class MarkdownReporter:
    """Gera relatórios executivos em Markdown organizados por prazo e salário."""

    def __init__(self, report_path: str):
        self.report_path = report_path
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)

    def generate(
        self,
        concursos: List[Dict[str, Any]],
        new_concursos: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> str:
        now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

        lines = [
            "# 📋 Relatório Consolidado de Concursos Públicos",
            f"*Gerado em: {now_str}*",
            "",
            "## 📊 Visão Geral",
            f"- **Total de Concursos Ativos Monitorados:** {stats.get('open', len(concursos))}",
            f"- **Novos Concursos Detectados nesta Rodada:** {len(new_concursos)}",
            f"- **Maior Salário Identificado:** R$ {stats.get('max_salary', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "",
        ]

        if new_concursos:
            lines.extend([
                "---",
                "## 🚀 Editais Recém-Publicados / Novidades",
                ""
            ])
            for c in new_concursos:
                sal = f"R$ {c['salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if c.get("salary") else "A combinar / Não divulgado"
                prazo = c.get("deadline_text") or "Não informado"
                lines.append(f"### ✨ [{c.get('uf', 'BR')}] [{c['title']}]({c['url']})")
                lines.append(f"- **Salário:** {sal} | **Vagas:** {c.get('vacancies_text', 'N/I')}")
                lines.append(f"- **Inscrições até:** `{prazo}`")
                lines.append(f"- **Resumo:** {c.get('details', '')}")
                lines.append("")

        lines.extend([
            "---",
            "## 🏆 Concursos em Destaque (Inscrições Abertas)",
            "",
            "| UF | Órgão / Concurso | Salário | Vagas | Inscrições Até | Link |",
            "|:---|:---|:---|:---|:---|:---|"
        ])

        for c in concursos[:50]:  # Top 50 ordenados
            sal_str = f"R$ {c['salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if c.get("salary") else "-"
            uf = c.get("uf", "-")
            title_clean = c["title"][:45] + ("..." if len(c["title"]) > 45 else "")
            vagas = c.get("vacancies_text", "-")
            prazo = c.get("deadline_text", "-")
            link = f"[Acessar]({c['url']})"
            lines.append(f"| **{uf}** | {title_clean} | {sal_str} | {vagas} | `{prazo}` | {link} |")

        lines.extend([
            "",
            "---",
            "💡 *Dica: Você pode pesquisar, filtrar por sua carreira e favoritar oportunidades no painel web local executando `python main.py dashboard`.*"
        ])

        content = "\n".join(lines)
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return content
