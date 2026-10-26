import unittest
from media_verification import build_media_evidence


class TestEvidence(unittest.TestCase):
    def test_ai_flag(self):
        r = build_media_evidence("image", "ai_generated", 88, "no_face_detected", 0,
                                 {"status": "unavailable"}, {"status": "no_local_matches", "matches": []})
        self.assertEqual(r["overall_status"], "potentially_synthetic_or_manipulated")

    def test_missing_c2pa_is_not_fake(self):
        r = build_media_evidence("image", "authentic", 80, "no_face_detected", 0,
                                 {"status": "not_found_or_unavailable"}, {"status": "no_local_matches", "matches": []})
        self.assertNotEqual(r["provenance"]["status"], "fake")


if __name__ == "__main__":
    unittest.main()
