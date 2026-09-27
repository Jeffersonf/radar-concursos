import contextlib
import csv
import datetime
import io
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .geo_engine import haversine_distance


class Database:
    """Gerenciador do banco de dados SQLite para concursos monitorados."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS concursos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    uf TEXT NOT NULL,
                    cidade TEXT DEFAULT 'Nacional / Brasil',
                    lat REAL,
                    lon REAL,
                    details TEXT,
                    salary REAL,
                    vacancies INTEGER,
                    vacancies_text TEXT,
                    education TEXT,
                    deadline_date TEXT,
                    deadline_text TEXT,
                    days_remaining INTEGER,
                    is_expired INTEGER DEFAULT 0,
                    is_extended INTEGER DEFAULT 0,
                    banca TEXT DEFAULT 'Órgão Próprio / A Definir',
                    tipo TEXT DEFAULT 'Concurso Público',
                    area TEXT DEFAULT 'Geral',
                    user_notes TEXT DEFAULT '',
                    source TEXT DEFAULT 'PCI Concursos',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    is_favorite INTEGER DEFAULT 0,
                    notified INTEGER DEFAULT 0
                )
            """)

            # Verificação e migração de colunas
            cursor.execute("PRAGMA table_info(concursos)")
            existing_cols = {col["name"] for col in cursor.fetchall()}
            if "banca" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN banca TEXT DEFAULT 'Órgão Próprio / A Definir'")
            if "tipo" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN tipo TEXT DEFAULT 'Concurso Público'")
            if "area" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN area TEXT DEFAULT 'Geral'")
            if "cidade" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN cidade TEXT DEFAULT 'Nacional / Brasil'")
            if "lat" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN lat REAL")
            if "lon" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN lon REAL")
            if "user_notes" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN user_notes TEXT DEFAULT ''")
            if "exam_date" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN exam_date TEXT DEFAULT ''")
            if "fee_text" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN fee_text TEXT DEFAULT ''")
            if "workload" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN workload TEXT DEFAULT ''")
            if "regime" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN regime TEXT DEFAULT ''")
            if "application_period" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN application_period TEXT DEFAULT ''")
            if "official_url" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN official_url TEXT DEFAULT ''")
            if "full_summary" not in existing_cols:
                cursor.execute("ALTER TABLE concursos ADD COLUMN full_summary TEXT DEFAULT ''")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_concursos_uf ON concursos (uf)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_concursos_salary ON concursos (salary)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_concursos_deadline ON concursos (deadline_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_concursos_banca ON concursos (banca)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_concursos_cidade ON concursos (cidade)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checks_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checked_at TEXT NOT NULL,
                    total_found INTEGER NOT NULL,
                    new_found INTEGER NOT NULL,
                    details TEXT
                )
            """)
            conn.commit()

    def upsert_concurso(self, item: Dict[str, Any]) -> Tuple[bool, bool]:
        """Salva ou atualiza um concurso."""
        now_iso = datetime.datetime.now().isoformat()
        education_str = json.dumps(item.get("education", []), ensure_ascii=False)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, salary, deadline_date FROM concursos WHERE external_id = ?", (item["external_id"],))
            row = cursor.fetchone()

            if row is None:
                cursor.execute("""
                    INSERT INTO concursos (
                        external_id, title, url, uf, cidade, lat, lon, details, salary, vacancies,
                        vacancies_text, education, deadline_date, deadline_text,
                        days_remaining, is_expired, is_extended, banca, tipo, area, user_notes,
                        source, first_seen, last_seen, is_favorite, notified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (
                    item["external_id"],
                    item["title"],
                    item["url"],
                    item["uf"],
                    item.get("cidade", "Nacional / Brasil"),
                    item.get("lat"),
                    item.get("lon"),
                    item.get("details", ""),
                    item.get("salary"),
                    item.get("vacancies"),
                    item.get("vacancies_text", ""),
                    education_str,
                    item.get("deadline_date"),
                    item.get("deadline_text", ""),
                    item.get("days_remaining"),
                    1 if item.get("is_expired") else 0,
                    1 if item.get("is_extended") else 0,
                    item.get("banca", "Órgão Próprio / A Definir"),
                    item.get("tipo", "Concurso Público"),
                    item.get("area", "Geral"),
                    item.get("user_notes", ""),
                    item.get("source", "PCI Concursos"),
                    now_iso,
                    now_iso
                ))
                conn.commit()
                return True, False
            else:
                cursor.execute("""
                    UPDATE concursos SET
                        details = ?,
                        salary = COALESCE(?, salary),
                        vacancies = COALESCE(?, vacancies),
                        vacancies_text = ?,
                        education = ?,
                        deadline_date = ?,
                        deadline_text = ?,
                        days_remaining = ?,
                        is_expired = ?,
                        is_extended = ?,
                        banca = ?,
                        tipo = ?,
                        area = ?,
                        cidade = COALESCE(?, cidade),
                        lat = COALESCE(?, lat),
                        lon = COALESCE(?, lon),
                        last_seen = ?
                    WHERE external_id = ?
                """, (
                    item.get("details", ""),
                    item.get("salary"),
                    item.get("vacancies"),
                    item.get("vacancies_text", ""),
                    education_str,
                    item.get("deadline_date"),
                    item.get("deadline_text", ""),
                    item.get("days_remaining"),
                    1 if item.get("is_expired") else 0,
                    1 if item.get("is_extended") else 0,
                    item.get("banca", "Órgão Próprio / A Definir"),
                    item.get("tipo", "Concurso Público"),
                    item.get("area", "Geral"),
                    item.get("cidade"),
                    item.get("lat"),
                    item.get("lon"),
                    now_iso,
                    item["external_id"]
                ))
                conn.commit()
                return False, True

    def mark_as_notified(self, external_ids: List[str]):
        """Marca concursos como notificados."""
        if not external_ids:
            return
        with self._connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in external_ids)
            cursor.execute(f"UPDATE concursos SET notified = 1 WHERE external_id IN ({placeholders})", external_ids)
            conn.commit()

    def toggle_favorite(self, external_id: str) -> bool:
        """Alterna estado de favorito do concurso e retorna o novo status."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_favorite FROM concursos WHERE external_id = ?", (external_id,))
            row = cursor.fetchone()
            if not row:
                return False
            new_val = 0 if row["is_favorite"] else 1
            cursor.execute("UPDATE concursos SET is_favorite = ? WHERE external_id = ?", (new_val, external_id))
            conn.commit()
            return bool(new_val)

    def save_notes(self, external_id: str, notes: str) -> bool:
        """Salva anotações pessoais do candidato no edital."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE concursos SET user_notes = ? WHERE external_id = ?", (notes, external_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_concurso_details(self, external_id: str, details_dict: Dict[str, Any]) -> bool:
        """Salva os dados enriquecidos (data da prova, taxa, carga horária, resumo, etc.)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE concursos
                SET exam_date = ?,
                    fee_text = ?,
                    workload = ?,
                    regime = ?,
                    application_period = ?,
                    official_url = ?,
                    full_summary = ?
                WHERE external_id = ?
            """, (
                details_dict.get("exam_date", ""),
                details_dict.get("fee_text", ""),
                details_dict.get("workload", ""),
                details_dict.get("regime", ""),
                details_dict.get("application_period", ""),
                details_dict.get("official_url", ""),
                details_dict.get("full_summary", ""),
                external_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_concurso_by_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o edital completo pelo external_id."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM concursos WHERE external_id = ?", (external_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["education"] = json.loads(item["education"]) if item["education"] else []
            item["is_favorite"] = bool(item["is_favorite"])
            item["is_expired"] = bool(item["is_expired"])
            item["is_extended"] = bool(item["is_extended"])
            return item

    def query_concursos(
        self,
        uf: Optional[str] = None,
        search_query: Optional[str] = None,
        min_salary: Optional[float] = None,
        education: Optional[str] = None,
        area: Optional[str] = None,
        banca: Optional[str] = None,
        tipo: Optional[str] = None,
        only_active: bool = False,
        only_favorites: bool = False,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_distance_km: Optional[float] = None,
        sort_by: str = "default",
        limit: int = 150,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Busca concursos com filtros avançados, distância geodésica e ordenação flexível."""
        conditions = []
        params = []

        if uf and uf.upper() != "TODOS":
            conditions.append("UPPER(uf) = UPPER(?)")
            params.append(uf)

        if search_query:
            conditions.append("(LOWER(title) LIKE ? OR LOWER(details) LIKE ? OR LOWER(area) LIKE ? OR LOWER(cidade) LIKE ?)")
            term = f"%{search_query.lower()}%"
            params.extend([term, term, term, term])

        if min_salary and min_salary > 0:
            conditions.append("salary >= ?")
            params.append(min_salary)

        if education and education.upper() != "TODOS":
            conditions.append("LOWER(education) LIKE ?")
            params.append(f"%{education.lower()}%")

        if area and area.upper() != "TODOS":
            conditions.append("LOWER(area) LIKE ?")
            params.append(f"%{area.lower()}%")

        if banca and banca.upper() != "TODOS":
            conditions.append("LOWER(banca) LIKE ?")
            params.append(f"%{banca.lower()}%")

        if tipo and tipo.upper() != "TODOS":
            conditions.append("LOWER(tipo) LIKE ?")
            params.append(f"%{tipo.lower()}%")

        if only_active:
            conditions.append("is_expired = 0")

        if only_favorites:
            conditions.append("is_favorite = 1")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Definição de ordenação básica no SQL
        if sort_by == "salary_desc":
            order_clause = "is_favorite DESC, (salary IS NOT NULL) DESC, salary DESC"
        elif sort_by == "deadline_asc":
            order_clause = "is_favorite DESC, (deadline_date IS NOT NULL AND is_expired = 0) DESC, deadline_date ASC"
        elif sort_by == "vacancies_desc":
            order_clause = "is_favorite DESC, vacancies DESC"
        elif sort_by == "newest":
            order_clause = "is_favorite DESC, first_seen DESC"
        else:
            order_clause = """
                is_favorite DESC,
                (CASE WHEN deadline_date IS NOT NULL AND is_expired = 0 THEN 0 ELSE 1 END),
                deadline_date ASC,
                salary DESC
            """

        sql = f"""
            SELECT * FROM concursos
            {where_clause}
            ORDER BY {order_clause}
        """

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = []

            for r in rows:
                item = dict(r)
                item["education"] = json.loads(item["education"]) if item["education"] else []
                item["is_favorite"] = bool(item["is_favorite"])
                item["is_expired"] = bool(item["is_expired"])
                item["is_extended"] = bool(item["is_extended"])

                # Cálculo de distância caso o usuário tenha informado suas coordenadas
                dist = None
                if user_lat is not None and user_lon is not None and item.get("lat") is not None and item.get("lon") is not None:
                    dist = haversine_distance(user_lat, user_lon, item["lat"], item["lon"])
                item["distance_km"] = dist

                # Filtro por raio máximo de distância
                if max_distance_km and max_distance_km > 0:
                    if dist is None or dist > max_distance_km:
                        continue

                results.append(item)

            # Ordenação por distância
            if sort_by == "distance_asc":
                results.sort(key=lambda x: (not x["is_favorite"], x["distance_km"] is None, x["distance_km"] or 99999))

            return results[offset:offset + limit]

    def get_stats(self) -> Dict[str, Any]:
        """Calcula estatísticas dos concursos cadastrados."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM concursos")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM concursos WHERE is_expired = 0")
            open_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM concursos WHERE is_favorite = 1")
            favs = cursor.fetchone()[0]

            cursor.execute("SELECT MAX(salary) FROM concursos")
            max_salary = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT uf, COUNT(*) as count FROM concursos GROUP BY uf ORDER BY count DESC LIMIT 8")
            top_ufs = [{"uf": r["uf"], "count": r["count"]} for r in cursor.fetchall()]

            return {
                "total": total,
                "open": open_count,
                "favorites": favs,
                "max_salary": max_salary,
                "top_ufs": top_ufs
            }

    def get_analytics(self) -> Dict[str, Any]:
        """Gera dados analíticos estruturados para renderização de gráficos."""
        with self._connection() as conn:
            cursor = conn.cursor()

            salary_brackets = {
                "Até R$ 3.000": 0,
                "R$ 3.001 a R$ 6.000": 0,
                "R$ 6.001 a R$ 10.000": 0,
                "R$ 10.001 a R$ 15.000": 0,
                "Acima de R$ 15.000": 0,
            }
            cursor.execute("SELECT salary FROM concursos WHERE salary IS NOT NULL AND is_expired = 0")
            for row in cursor.fetchall():
                sal = row["salary"]
                if sal <= 3000:
                    salary_brackets["Até R$ 3.000"] += 1
                elif sal <= 6000:
                    salary_brackets["R$ 3.001 a R$ 6.000"] += 1
                elif sal <= 10000:
                    salary_brackets["R$ 6.001 a R$ 10.000"] += 1
                elif sal <= 15000:
                    salary_brackets["R$ 10.001 a R$ 15.000"] += 1
                else:
                    salary_brackets["Acima de R$ 15.000"] += 1

            cursor.execute("""
                SELECT uf, COUNT(*) as count, SUM(COALESCE(vacancies, 0)) as total_vagas
                FROM concursos WHERE is_expired = 0
                GROUP BY uf ORDER BY count DESC LIMIT 10
            """)
            top_ufs = [{"uf": r["uf"], "count": r["count"], "vagas": r["total_vagas"]} for r in cursor.fetchall()]

            cursor.execute("SELECT tipo, COUNT(*) as count FROM concursos WHERE is_expired = 0 GROUP BY tipo")
            tipos = [{"tipo": r["tipo"], "count": r["count"]} for r in cursor.fetchall()]

            cursor.execute("""
                SELECT banca, COUNT(*) as count FROM concursos
                WHERE banca != 'Órgão Próprio / A Definir' AND is_expired = 0
                GROUP BY banca ORDER BY count DESC LIMIT 8
            """)
            bancas = [{"banca": r["banca"], "count": r["count"]} for r in cursor.fetchall()]

            cursor.execute("SELECT area FROM concursos WHERE is_expired = 0")
            career_counts: Dict[str, int] = {}
            for row in cursor.fetchall():
                area_str = row["area"] or "Geral"
                for item in area_str.split(","):
                    name = item.strip()
                    if name:
                        career_counts[name] = career_counts.get(name, 0) + 1

            careers_list = [{"area": k, "count": v} for k, v in sorted(career_counts.items(), key=lambda x: x[1], reverse=True)[:8]]

            return {
                "salary_brackets": salary_brackets,
                "top_ufs": top_ufs,
                "tipos": tipos,
                "bancas": bancas,
                "careers": careers_list
            }

    def export_csv(self, concursos: List[Dict[str, Any]]) -> str:
        """Gera string CSV com BOM UTF-8 para compatibilidade perfeita com Excel."""
        output = io.StringIO()
        output.write("\ufeff")

        fieldnames = [
            "ID", "Órgão / Concurso", "UF", "Município / Polo", "Distância (Km)",
            "Salário (R$)", "Vagas", "Escolaridade", "Prazo Inscrição",
            "Dias Restantes", "Banca", "Tipo", "Área", "Minhas Anotações", "Link"
        ]
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)

        for c in concursos:
            sal_str = f"{c['salary']:.2f}".replace(".", ",") if c.get("salary") else "N/I"
            edu_str = ", ".join(c.get("education", []))
            dist_str = f"{c['distance_km']:.1f} km" if c.get("distance_km") is not None else "-"
            writer.writerow([
                c.get("external_id", ""),
                c.get("title", ""),
                c.get("uf", ""),
                c.get("cidade", ""),
                dist_str,
                sal_str,
                c.get("vacancies_text", ""),
                edu_str,
                c.get("deadline_text", ""),
                c.get("days_remaining", ""),
                c.get("banca", ""),
                c.get("tipo", ""),
                c.get("area", ""),
                c.get("user_notes", ""),
                c.get("url", "")
            ])

        return output.getvalue()

    def log_check_run(self, total_found: int, new_found: int, details: str = ""):
        """Registra no log a execução da varredura."""
        now_iso = datetime.datetime.now().isoformat()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO checks_log (checked_at, total_found, new_found, details)
                VALUES (?, ?, ?, ?)
            """, (now_iso, total_found, new_found, details))
            conn.commit()
