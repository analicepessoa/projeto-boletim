import sys
import types
import unittest


streamlit_falso = types.ModuleType("streamlit")
streamlit_falso.cache_resource = lambda func: func
streamlit_falso.secrets = {}
streamlit_falso.warning = lambda *_args, **_kwargs: None
sys.modules.setdefault("streamlit", streamlit_falso)

supabase_falso = types.ModuleType("supabase")
supabase_falso.Client = object
supabase_falso.create_client = lambda *_args, **_kwargs: None
sys.modules.setdefault("supabase", supabase_falso)

from src.supabase_client import _consolidar_notas_por_materia


class HistoricoMultiturmaTests(unittest.TestCase):
    def test_mantem_mesmo_modulo_separado_por_turma(self):
        notas = [
            {
                "id": "1",
                "materia_id": "basic",
                "nota": 0,
                "presencas": 4,
                "faltas": 1,
                "created_at": "2026-01-01",
                "turma_origem": "IQ15/0003",
                "detalhes_json": {
                    "frequencia": ["P", "P", "P", "P", "F"],
                    "notas": {},
                },
            },
            {
                "id": "2",
                "materia_id": "basic",
                "nota": 8.5,
                "presencas": 6,
                "faltas": 0,
                "created_at": "2026-02-01",
                "turma_origem": "IQ19/0013",
                "detalhes_json": {
                    "frequencia": ["P"] * 6,
                    "notas": {"Prova 001": 8.5},
                },
            },
        ]

        resultado = _consolidar_notas_por_materia(notas)

        self.assertEqual(len(resultado), 2)
        por_turma = {nota["turma_origem"]: nota for nota in resultado}
        self.assertEqual(por_turma["IQ15/0003"]["presencas"], 4)
        self.assertEqual(por_turma["IQ15/0003"]["faltas"], 1)
        self.assertEqual(por_turma["IQ15/0003"]["nota"], 0)
        self.assertEqual(por_turma["IQ19/0013"]["presencas"], 6)
        self.assertEqual(por_turma["IQ19/0013"]["faltas"], 0)
        self.assertEqual(por_turma["IQ19/0013"]["nota"], 8.5)

    def test_duplicata_na_mesma_turma_mantem_lancamento_mais_recente(self):
        notas = [
            {
                "id": "1",
                "materia_id": "basic",
                "turma_id": "turma-1",
                "turma_origem": "IQ15/0003",
                "nota": 7,
                "created_at": "2026-01-01",
            },
            {
                "id": "2",
                "materia_id": "basic",
                "turma_id": "turma-1",
                "turma_origem": "IQ15/0003",
                "nota": 9,
                "created_at": "2026-02-01",
            },
        ]

        resultado = _consolidar_notas_por_materia(notas)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], "2")
        self.assertEqual(resultado[0]["nota"], 9)

    def test_materias_diferentes_continuam_separadas(self):
        notas = [
            {"materia_id": "basic", "nota": 8, "presencas": 2, "faltas": 0},
            {"materia_id": "office", "nota": 9, "presencas": 3, "faltas": 1},
        ]

        resultado = _consolidar_notas_por_materia(notas)

        self.assertEqual(len(resultado), 2)


if __name__ == "__main__":
    unittest.main()

