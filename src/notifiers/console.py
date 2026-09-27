import sys
from typing import Any, Dict, List

# Suporte seguro a UTF-8 no console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ConsoleNotifier:
    """Exibição formatada e legível dos editais no terminal."""

    @staticmethod
    def print_header(title: str):
        print("\n" + "=" * 80)
        print(f" 🎯 {title.upper()}")
        print("=" * 80)

    @staticmethod
    def print_concurso_card(c: Dict[str, Any], is_new: bool = False):
        new_tag = " [✨ NOVO NO RADAR!]" if is_new else ""
        fav_tag = " ⭐" if c.get("is_favorite") else ""
        uf = c.get("uf", "BR")
        print(f"\n[{uf}]{fav_tag} {c['title']}{new_tag}")
        
        # Salário e Vagas
        salary_str = f"R$ {c['salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if c.get("salary") else "Não informado"
        vacancies_str = c.get("vacancies_text", "Não informado")
        print(f"   💰 Salário: {salary_str}  |  👥 Vagas: {vacancies_str}")

        # Escolaridade e Prazo
        education_str = ", ".join(c.get("education", [])) or "Geral"
        deadline_str = c.get("deadline_text", "Não informada")
        days = c.get("days_remaining")
        if days is not None:
            if days > 0:
                prazo_info = f"{deadline_str} (Restam {days} dias)"
            elif days == 0:
                prazo_info = f"{deadline_str} (ÚLTIMO DIA HOJE!)"
            else:
                prazo_info = f"{deadline_str} (Encerrado há {abs(days)} dias)"
        else:
            prazo_info = deadline_str

        print(f"   🎓 Escolaridade: {education_str}  |  📅 Inscrições até: {prazo_info}")
        print(f"   📝 Detalhes: {c.get('details', '')[:100]}...")
        print(f"   🔗 Link: {c.get('url')}")
        print("   " + "-" * 75)

    @staticmethod
    def print_summary(total_scanned: int, new_found: int, filtered_count: int):
        print("\n" + "=" * 80)
        print(" 📊 RESUMO DA EXECUÇÃO:")
        print(f"   • Total de editais varridos: {total_scanned}")
        print(f"   • Editais novos detectados: {new_found}")
        print(f"   • Editais correspondentes aos seus filtros: {filtered_count}")
        print("=" * 80 + "\n")
