import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.scoring import analyze_message, aggregate_score, determine_status


class TestAnalyzeMessage(unittest.TestCase):
    def test_flags_lottery_urgency_and_sensitive_info(self):
        text = (
            "Congratulations! You have won K5,000. Send your PIN to claim "
            "your prize within 24 hours."
        )
        result = analyze_message(text)
        self.assertIn("Prize or lottery language", result.flags)
        self.assertIn("Urgency cues", result.flags)
        self.assertIn("Requests sensitive info", result.flags)
        self.assertGreaterEqual(result.score, 70)

    def test_detects_url(self):
        result = analyze_message("Claim your reward at http://bit.ly/reward-now")
        self.assertIn("Contains a link", result.flags)

    def test_clean_conversational_message_scores_zero(self):
        result = analyze_message("Hi, are we still meeting tomorrow at 2pm?")
        self.assertEqual(result.score, 0)
        self.assertEqual(result.flags, [])

    def test_score_never_exceeds_100(self):
        text = (
            "URGENT congratulations winner! Claim your jackpot cash prize now, "
            "send your PIN, OTP, password and account number via mobile money "
            "transfer fee before it expires at http://bit.ly/scam"
        )
        result = analyze_message(text)
        self.assertLessEqual(result.score, 100)

    def test_similarity_bonus_applied_for_near_duplicate(self):
        corpus = [
            "Congratulations! You have won a cash prize, send your PIN immediately to claim."
        ]
        result = analyze_message(
            "Congratulations you have won a cash prize, send your PIN immediately to claim now",
            corpus=corpus,
        )
        self.assertGreater(result.similarity, 0.5)
        self.assertTrue(any("Similar to a previously reported scam" in f for f in result.flags))

    def test_no_similarity_bonus_for_unrelated_corpus(self):
        corpus = ["Reminder: your dentist appointment is tomorrow at 9am."]
        result = analyze_message("Hi mom, running 10 minutes late.", corpus=corpus)
        self.assertEqual(result.similarity, 0.0)
        self.assertEqual(result.flags, [])

    def test_custom_patterns_override_defaults(self):
        patterns = {"lottery": ["totally not a scam"], "urgency": [], "money": [], "sensitive_info": []}
        result = analyze_message("This message contains totally not a scam wording.", patterns=patterns)
        self.assertIn("Prize or lottery language", result.flags)


class TestAggregateScore(unittest.TestCase):
    def test_empty_input_returns_zero(self):
        self.assertEqual(aggregate_score([]), 0.0)

    def test_single_high_score_report(self):
        agg = aggregate_score([(80.0, 1.0)])
        self.assertGreater(agg, 0)
        self.assertLessEqual(agg, 100)

    def test_more_reports_boosts_score(self):
        few = aggregate_score([(70.0, 1.0)])
        many = aggregate_score([(70.0, 1.0)] * 8)
        self.assertGreater(many, few)

    def test_low_trust_reporters_count_less(self):
        trusted = aggregate_score([(70.0, 1.0), (70.0, 1.0), (70.0, 1.0)])
        untrusted = aggregate_score([(70.0, 0.1), (70.0, 0.1), (70.0, 0.1)])
        self.assertGreater(trusted, untrusted)

    def test_score_capped_at_100(self):
        agg = aggregate_score([(100.0, 1.0)] * 8)
        self.assertLessEqual(agg, 100.0)


class TestDetermineStatus(unittest.TestCase):
    def test_flagged_when_thresholds_met(self):
        status = determine_status(effective_report_count=3.0, aggregate=80.0)
        self.assertEqual(status, "flagged")

    def test_monitoring_when_too_few_reports(self):
        status = determine_status(effective_report_count=1.0, aggregate=90.0)
        self.assertEqual(status, "monitoring")

    def test_monitoring_when_score_too_low(self):
        status = determine_status(effective_report_count=5.0, aggregate=20.0)
        self.assertEqual(status, "monitoring")

    def test_manual_override_wins_even_with_no_signal(self):
        status = determine_status(effective_report_count=0.0, aggregate=0.0, manual_override="cleared")
        self.assertEqual(status, "cleared")

    def test_manual_override_wins_over_flagging_conditions(self):
        status = determine_status(effective_report_count=10.0, aggregate=95.0, manual_override="cleared")
        self.assertEqual(status, "cleared")

    def test_custom_thresholds_respected(self):
        status = determine_status(
            effective_report_count=2.0, aggregate=40.0,
            report_threshold=2.0, score_threshold=40.0,
        )
        self.assertEqual(status, "flagged")


if __name__ == "__main__":
    unittest.main()
