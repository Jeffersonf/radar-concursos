import os
import shutil
import tempfile
import unittest

from src.database import Database
from src.filter_engine import FilterEngine
from src.parsers.pci import PCIParser


class TestPCIParser(unittest.TestCase):
    def setUp(self):
        self.parser = PCIParser()

    def test_parse_salary(self):
        text = "10 vagas até R$ 14.850,50 para diversos cargos"
        salary = self.parser.parse_salary(text)
        self.assertEqual(salary, 14850.50)

        text_none = "Salário a combinar"
        self.assertIsNone(self.parser.parse_salary(text_none))

    def test_parse_vacancies(self):
        v1 = self.parser.parse_vacancies("145 vagas para Agente")
        self.assertEqual(v1["vacancies"], 145)
        self.assertFalse(v1["is_cr"])

        v2 = self.parser.parse_vacancies("Cadastro de reserva para Analista")
        self.assertIsNone(v2["vacancies"])
        self.assertTrue(v2["is_cr"])

    def test_parse_education(self):
        text = "Vagas para nível Médio e Superior completo"
        edu = self.parser.parse_education(text)
        self.assertIn("Médio", edu)
        self.assertIn("Superior", edu)

    def test_detect_banca_and_tipo(self):
        banca = self.parser.detect_banca("Concurso Receita Federal", "Organizado pela FGV")
        self.assertEqual(banca, "FGV")

        banca_cebraspe = self.parser.detect_banca("Polícia Federal", "Banca Cebraspe")
        self.assertEqual(banca_cebraspe, "Cebraspe")

        tipo_concurso = self.parser.detect_tipo("Concurso Público TJ-SP", "Vagas efetivas")
        self.assertEqual(tipo_concurso, "Concurso Público")

        tipo_seletivo = self.parser.detect_tipo("Processo Seletivo Simplificado", "Contratação temporária")
        self.assertEqual(tipo_seletivo, "Processo Seletivo")

    def test_detect_carreiras(self):
        carreiras_ti = self.parser.detect_carreiras("Analista em Tecnologia", "Desenvolvedor de software e dados")
        self.assertIn("TI & Dados", carreiras_ti)

        carreiras_juridico = self.parser.detect_carreiras("Tribunal Regional", "Advogado e Procurador")
        self.assertIn("Jurídico & Tribunais", carreiras_juridico)

    def test_parse_full_card(self):
        sample_html = """
        <div class="ca"><a href="https://www.pciconcursos.com.br/noticias/teste-tj-sp">Tribunal de Justiça - SP</a></div>
        <div class="cc">SP</div>
        <div class="cd">500 vagas até R$ 8.500,00<br><span>Escrevente Técnico Judiciário Vunesp<br><span>Médio</span></span></div>
        <div class="ce"><span>15/11/2026</span></div>
        """
        results = self.parser.parse(sample_html, uf="sp")
        self.assertEqual(len(results), 1)
        c = results[0]
        self.assertEqual(c["title"], "Tribunal de Justiça - SP")
        self.assertEqual(c["salary"], 8500.0)
        self.assertEqual(c["vacancies"], 500)
        self.assertIn("Médio", c["education"])
        self.assertEqual(c["uf"], "SP")
        self.assertEqual(c["banca"], "Vunesp")
        self.assertEqual(c["tipo"], "Concurso Público")


class TestDatabaseAndFilters(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_concursos.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_upsert_and_analytics(self):
        item = {
            "external_id": "test_ti_123",
            "title": "Concurso TI Nacional",
            "url": "https://exemplo.com/edital",
            "uf": "DF",
            "details": "Vaga para Analista de TI até R$ 12.000,00",
            "salary": 12000.0,
            "vacancies": 10,
            "vacancies_text": "10 vagas",
            "education": ["Superior"],
            "deadline_date": "2026-12-01",
            "deadline_text": "01/12/2026",
            "days_remaining": 40,
            "is_expired": False,
            "is_extended": False,
            "banca": "Cebraspe",
            "tipo": "Concurso Público",
            "area": "TI & Dados"
        }

        is_new, is_up = self.db.upsert_concurso(item)
        self.assertTrue(is_new)

        # Test Analytics
        analytics = self.db.get_analytics()
        self.assertEqual(analytics["salary_brackets"]["R$ 10.001 a R$ 15.000"], 1)
        self.assertEqual(len(analytics["top_ufs"]), 1)
        self.assertEqual(analytics["top_ufs"][0]["uf"], "DF")

        # Test CSV Export
        csv_data = self.db.export_csv([item])
        self.assertIn("Concurso TI Nacional", csv_data)
        self.assertIn("12000,00", csv_data)
        self.assertIn("Cebraspe", csv_data)

    def test_filter_engine(self):
        item = {
            "title": "Receita Federal do Brasil",
            "details": "Auditor Fiscal da Receita Federal",
            "salary": 21000.0,
            "uf": "NACIONAL",
            "education": ["Superior"],
            "is_expired": False
        }

        rules = {
            "min_salary": 15000.0,
            "keywords": ["auditor", "fiscal"],
            "ufs": ["NACIONAL", "SP"],
            "education_levels": ["Superior"],
            "only_open_applications": True
        }

        engine = FilterEngine(rules)
        matches, reasons = engine.matches(item)
        self.assertTrue(matches)
        self.assertEqual(len(reasons), 4)


    def test_haversine_and_geo(self):
        from src.geo_engine import haversine_distance, extract_city_and_coords, resolve_user_location

        # Distância SP -> Campinas (~85 - 95 km em linha reta)
        sp_lat, sp_lon = -23.5505, -46.6333
        camp_lat, camp_lon = -22.9099, -47.0626
        dist = haversine_distance(sp_lat, sp_lon, camp_lat, camp_lon)
        self.assertTrue(80.0 <= dist <= 100.0)

        # Extração de cidade
        cidade, lat, lon = extract_city_and_coords("Prefeitura de Campinas", "Vagas diversas", "SP")
        self.assertIn("Campinas", cidade)
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)

        # Resolução de cidade do usuário
        res = resolve_user_location("São Paulo")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "Sao Paulo - SP")

        # Resolução de Buri
        res_buri = resolve_user_location("Buri")
        self.assertIsNotNone(res_buri)
        self.assertIn("Buri", res_buri[0])
        self.assertEqual(round(res_buri[1], 2), -23.8)

        # Resolução de CEP
        res_cep = resolve_user_location("18400-350")
        self.assertIsNotNone(res_cep)
        self.assertIn("Itapeva", res_cep[0])

    def test_database_enrichment_and_get_by_id(self):
        item = {
            "external_id": "item_detail_test",
            "title": "Concurso Tribunal Regional",
            "url": "https://pciconcursos.com.br/concurso/tribunal-123",
            "uf": "SP",
            "details": "Analista Judiciário",
            "salary": 13500.0,
            "vacancies": 5,
            "vacancies_text": "5 vagas",
            "education": ["Superior"],
            "deadline_date": "2026-11-20",
            "deadline_text": "20/11/2026",
            "days_remaining": 50,
            "is_expired": False,
            "is_extended": False,
            "banca": "FCC",
            "tipo": "Concurso Público",
            "area": "Jurídico & Tribunais"
        }
        self.db.upsert_concurso(item)

        # Update details
        details = {
            "exam_date": "A prova objetiva está prevista para ser aplicada em 15 de dezembro de 2026.",
            "fee_text": "A taxa de inscrição tem o valor de R$ 120,00.",
            "workload": "40 horas semanais",
            "regime": "Estatutário (Estabilidade)",
            "application_period": "De 10 a 30 de outubro de 2026.",
            "official_url": "https://www.concursosfcc.com.br/tribunal",
            "full_summary": "Edital completo publicado pelo Tribunal com regime estatutário."
        }
        self.db.update_concurso_details("item_detail_test", details)

        fetched = self.db.get_concurso_by_id("item_detail_test")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["exam_date"], details["exam_date"])
        self.assertEqual(fetched["fee_text"], details["fee_text"])
        self.assertEqual(fetched["workload"], "40 horas semanais")
        self.assertEqual(fetched["regime"], "Estatutário (Estabilidade)")
        self.assertEqual(fetched["official_url"], "https://www.concursosfcc.com.br/tribunal")
        self.assertIn("Edital completo", fetched["full_summary"])

    def test_enrich_concurso_details_parser(self):
        from unittest.mock import patch, MagicMock
        fake_html = """
        <html><body>
        <div class="ca">
          <p>O Tribunal de Justiça abre concurso sob o regime estatutário para novos servidores.</p>
          <p>A taxa de inscrição está no valor de R$ 95,00 para nível médio e R$ 140,00 para superior.</p>
          <p>A jornada é de 40 horas semanais.</p>
          <p>A prova objetiva tem data prevista para ser realizada no dia 22 de novembro de 2026.</p>
          <p>As inscrições estarão abertas entre 01/10/2026 e 25/10/2026.</p>
          <a href="https://www.vunesp.com.br/concurso/tj2026">Inscrição no Portal Vunesp</a>
        </div>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_html.encode("latin-1")
        mock_resp.__enter__.return_value = mock_resp

        parser = PCIParser()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = parser.enrich_concurso_details("https://fake.url/concurso")
            self.assertIn("22 de novembro", res["exam_date"])
            self.assertIn("R$ 95,00", res["fee_text"])
            self.assertEqual(res["workload"], "40 horas semanais")
            self.assertEqual(res["regime"], "Estatutário (Estabilidade)")
            self.assertIn("vunesp.com.br", res["official_url"])


if __name__ == "__main__":
    unittest.main()
