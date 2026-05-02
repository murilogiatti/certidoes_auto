import unittest
import os
from utils import _formatar_data, criar_pasta, timestamp, datestamp

class TestUtils(unittest.TestCase):
    def test_formatar_data_valid_no_separators(self):
        self.assertEqual(_formatar_data("28111988"), "28/11/1988")

    def test_formatar_data_with_separators(self):
        self.assertEqual(_formatar_data("28/11/1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28-11-1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28.11.1988"), "28/11/1988")

    def test_formatar_data_with_whitespace(self):
        self.assertEqual(_formatar_data("  28111988  "), "28/11/1988")
        self.assertEqual(_formatar_data("  28 / 11 / 1988  "), "28/11/1988") # doesn't remove spaces within

    def test_formatar_data_invalid_length(self):
        self.assertEqual(_formatar_data("281188"), "281188")
        self.assertEqual(_formatar_data("281119881"), "281119881")

    def test_formatar_data_non_numeric(self):
        self.assertEqual(_formatar_data("2811198A"), "2811198A")

    def test_criar_pasta_sanitization(self):
        # We need to mock or just verify the behavior.
        # But we don't want to leave directories around in tests.
        import tempfile
        import shutil

        # Override the current working directory to not pollute the real repo too much
        # But `criar_pasta` uses `os.path.abspath(__file__)` which points to `utils.py`.
        # So it will create `downloads/` next to `utils.py`.

        # We can just test that the returned path is correct, and then delete it.
        nome = "João / Silva:*?"
        pasta = criar_pasta(nome)

        expected_dir_name = "JOÃO _ SILVA___"
        self.assertTrue(pasta.endswith(expected_dir_name))
        self.assertTrue(os.path.isdir(pasta))

        # Cleanup
        os.rmdir(pasta)

    def test_criar_pasta_whitespace(self):
        nome = "  Maria  "
        pasta = criar_pasta(nome)

        self.assertTrue(pasta.endswith("MARIA"))
        self.assertTrue(os.path.isdir(pasta))

        # Cleanup
        os.rmdir(pasta)

if __name__ == '__main__':
    unittest.main()
