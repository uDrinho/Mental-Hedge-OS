"""Suíte de testes determinísticos para o motor quantitativo, schemas Pydantic e guardrails."""
import glob
import json
import unittest
from core.config import CALLS_DIR, MEMORY_PATH
from core.schemas import OperationalCall, ThesisAdvisoryReport, LeaderboardEntry
from risk_advisor import evaluate_investment_thesis, get_confluence_leaderboard


class TestMentalHedgeEngine(unittest.TestCase):
    def setUp(self):
        self.sample_snapshot = {
            "BTC": {"price": 80068.15, "variation_pct": 3.52, "variation_5d_pct": 2.95},
            "ETH": {"price": 2419.21, "variation_pct": 6.45, "variation_5d_pct": 7.54},
            "SPX": {"price": 7688.62, "variation_pct": 1.58, "variation_5d_pct": -0.44},
            "NDX": {"price": 28437.17, "variation_pct": 0.91, "variation_5d_pct": -4.1},
            "RUT": {"price": 2856.95, "variation_pct": 1.58, "variation_5d_pct": 1.35},
            "WTI": {"price": 88.56, "variation_pct": -7.84, "variation_5d_pct": -13.84},
            "UST30Y": {"price": 5.28, "variation_pct": -0.79, "variation_5d_pct": -0.43},
            "DXY": {"price": 101.52, "variation_pct": -0.34, "variation_5d_pct": -0.65},
            "USDBRL": {"price": 5.46, "variation_pct": 0.44, "variation_5d_pct": 1.63},
        }

    def test_all_extracted_jsonl_calls_match_pydantic_schema(self):
        """Garante que todas as 472 chamadas extraídas pelos subagentes respeitam o schema estrito."""
        jsonl_files = sorted(glob.glob(str(CALLS_DIR / "*.jsonl")))
        self.assertGreaterEqual(len(jsonl_files), 12, "Deve conter pelo menos 12 meses de arquivos .jsonl")

        total_validated = 0
        for file_path in jsonl_files:
            with open(file_path, "r", encoding="utf-8") as fp:
                for line_num, line in enumerate(fp, start=1):
                    if line.strip():
                        raw = json.loads(line)
                        call = OperationalCall.model_validate(raw)
                        self.assertTrue(call.tweet_id, f"tweet_id vazio em {file_path}:{line_num}")
                        total_validated += 1

        self.assertGreaterEqual(total_validated, 450)

    def test_episodic_error_memory_integrity(self):
        """Verifica se todas as regras duras anti-ruína estão presentes na memória episódica."""
        self.assertTrue(MEMORY_PATH.exists())
        with open(MEMORY_PATH, "r", encoding="utf-8") as fp:
            memory = json.load(fp)
        rule_ids = {r["id"] for r in memory.get("hard_rules", [])}
        expected_rules = {
            "RULE_NO_MINER_WITHOUT_HEDGE",
            "RULE_NO_TRADE_ON_MERE_EXPECTATION",
            "RULE_ETH_PREREQUISITE_FOR_ALTS",
            "RULE_MANDATORY_BREAKEVEN_AT_TARGET_1",
            "RULE_NEVER_SHORT_BLOWOFF",
        }
        self.assertTrue(expected_rules.issubset(rule_ids))

    def test_confluence_guardrails_and_pydantic_output(self):
        """Testa se o consultor bloqueia operações proibidas (RED) e aprova confluências prime (GREEN)."""
        # 1. SPX Long em topo de Onda 5 deve ser bloqueado (RED, score < 50)
        spx_long = ThesisAdvisoryReport.model_validate(
            evaluate_investment_thesis("SPX", "long", self.sample_snapshot)
        )
        self.assertEqual(spx_long.confluence_badge, "RED")
        self.assertLess(spx_long.confluence_score, 50)

        # 2. RUT Long no reteste de pivô secular deve ter Sinal Verde (GREEN, score >= 75)
        rut_long = ThesisAdvisoryReport.model_validate(
            evaluate_investment_thesis("RUT", "long", self.sample_snapshot)
        )
        self.assertEqual(rut_long.confluence_badge, "GREEN")
        self.assertGreaterEqual(rut_long.confluence_score, 75)

        # 3. Mineradoras Long devem acionar alerta de hedge obrigatório
        mara_long = ThesisAdvisoryReport.model_validate(
            evaluate_investment_thesis("MARA", "long", self.sample_snapshot)
        )
        self.assertEqual(mara_long.hard_rule_alert, "RULE_NO_MINER_WITHOUT_HEDGE")
        self.assertEqual(len(mara_long.setups_de_protecao), 3)

    def test_leaderboard_ordering_and_schema(self):
        """Verifica se o Leaderboard retorna todas as 11 teses ordenadas de forma decrescente."""
        board = get_confluence_leaderboard(self.sample_snapshot)
        self.assertEqual(len(board), 11)
        validated = [LeaderboardEntry.model_validate(item) for item in board]
        scores = [item.score for item in validated]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(validated[0].rank, 1)
        self.assertEqual(validated[-1].rank, 11)


if __name__ == "__main__":
    unittest.main()
