from typing import Any, Dict, List, Tuple


class FilterEngine:
    """Motor de filtragem e classificação de editais de acordo com o perfil do usuário."""

    def __init__(self, default_rules: Dict[str, Any] = None):
        self.rules = default_rules or {}

    def matches(self, concurso: Dict[str, Any], custom_rules: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """
        Avalia se um edital atende aos critérios configurados.
        Retorna (atende_criterios, lista_de_justificativas).
        """
        rules = custom_rules if custom_rules is not None else self.rules
        reasons = []

        # 1. Filtro de Inscrições Encerradas
        only_open = rules.get("only_open_applications", True)
        if only_open and concurso.get("is_expired"):
            return False, ["Inscrições já encerradas"]

        # 2. Filtro de UF
        target_ufs = rules.get("ufs", [])
        if target_ufs:
            normalized_target_ufs = [u.upper() for u in target_ufs]
            concurso_uf = concurso.get("uf", "").upper()
            if "TODOS" not in normalized_target_ufs and concurso_uf not in normalized_target_ufs:
                return False, [f"UF ({concurso_uf}) fora dos estados selecionados"]
            reasons.append(f"UF compatível ({concurso_uf})")

        # 3. Filtro de Salário Mínimo
        min_salary = rules.get("min_salary", 0.0)
        if min_salary and min_salary > 0:
            sal = concurso.get("salary")
            if sal is None or sal < min_salary:
                return False, [f"Salário (R$ {sal or 0:,.2f}) abaixo do mínimo exigido (R$ {min_salary:,.2f})"]
            reasons.append(f"Salário atrativo (R$ {sal:,.2f} >= R$ {min_salary:,.2f})")

        # 4. Filtro de Escolaridade
        req_education = rules.get("education_levels", [])
        if req_education:
            ed_levels = [e.lower() for e in concurso.get("education", [])]
            matched_ed = any(req.lower() in " ".join(ed_levels) for req in req_education)
            if not matched_ed:
                return False, ["Escolaridade não corresponde ao nível desejado"]
            reasons.append("Escolaridade compatível")

        # 5. Filtro de Palavras-Chave (Cargos, Áreas de Atuação, Órgãos)
        keywords = rules.get("keywords", [])
        if keywords:
            searchable_text = f"{concurso.get('title', '')} {concurso.get('details', '')}".lower()
            matched_keywords = [kw for kw in keywords if kw.lower() in searchable_text]
            if not matched_keywords:
                return False, ["Nenhuma palavra-chave de interesse encontrada"]
            reasons.append(f"Palavras-chave encontradas: {', '.join(matched_keywords)}")

        return True, reasons

    def filter_list(self, concursos: List[Dict[str, Any]], custom_rules: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Filtra uma lista de concursos, anexando as razões de combinação em cada item."""
        matched = []
        for c in concursos:
            is_match, reasons = self.matches(c, custom_rules)
            if is_match:
                item_copy = dict(c)
                item_copy["match_reasons"] = reasons
                matched.append(item_copy)
        return matched
