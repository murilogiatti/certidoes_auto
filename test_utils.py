import unittest
from certidoes import _formatar_data, criar_pasta, timestamp, datestamp
import os
import re

class TestUtils(unittest.TestCase):
    def test_formatar_data_valid(self):
        self.assertEqual(_formatar_data("28111988"), "28/11/1988")
        self.assertEqual(_formatar_data("28/11/1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28-11-1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28.11.1988"), "28/11/1988")
        self.assertEqual(_formatar_data(" 28111988 "), "28/11/1988")

    def test_formatar_data_invalid(self):
        # Should return raw if not recognized (length not 8 or not digits)
        self.assertEqual(_formatar_data("2811981"), "2811981")
        self.assertEqual(_formatar_data("abcdefgh"), "abcdefgh")
        self.assertEqual(_formatar_data("123"), "123")
        self.assertEqual(_formatar_data(""), "")

    def test_criar_pasta(self):
        pasta = criar_pasta(" João Silva ")
        self.assertTrue(pasta.endswith("JOÃO SILVA"))
        self.assertTrue(os.path.isdir(pasta))
        os.rmdir(pasta)

    def test_criar_pasta_invalid_chars(self):
        pasta = criar_pasta("Test <\\/:*?\"<>|> Name")
        expected_suffix = "TEST ___________ NAME"
        self.assertTrue(pasta.endswith(expected_suffix))
        self.assertTrue(os.path.isdir(pasta))
        os.rmdir(pasta)

    def test_timestamp(self):
        ts = timestamp()
        self.assertRegex(ts, r"^\d{8}_\d{6}$")

    def test_datestamp(self):
        ds = datestamp()
        self.assertRegex(ds, r"^\d{8}$")

if __name__ == "__main__":
    unittest.main()
