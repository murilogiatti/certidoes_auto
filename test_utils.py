import unittest
import os
import shutil
from datetime import datetime
from utils import timestamp, datestamp, criar_pasta, _formatar_data

class TestUtils(unittest.TestCase):

    def test_timestamp_format(self):
        ts = timestamp()
        self.assertEqual(len(ts), 15)
        # Should parse back without error
        dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
        self.assertIsInstance(dt, datetime)

    def test_datestamp_format(self):
        ds = datestamp()
        self.assertEqual(len(ds), 8)
        dt = datetime.strptime(ds, "%Y%m%d")
        self.assertIsInstance(dt, datetime)

    def test_criar_pasta_valid_name(self):
        nome = "João da Silva"
        expected_dir_name = "JOAO DA SILVA"

        path = criar_pasta(nome)
        try:
            self.assertEqual(os.path.basename(path), expected_dir_name)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.isdir(path))
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_criar_pasta_invalid_chars(self):
        nome = "a/b:c*d?e\"f<g>h|i"
        expected_dir_name = "ABCDEFGHI"

        path = criar_pasta(nome)
        try:
            self.assertEqual(os.path.basename(path), expected_dir_name)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.isdir(path))
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_formatar_data_valid(self):
        self.assertEqual(_formatar_data("28111988"), "28/11/1988")
        self.assertEqual(_formatar_data("01012000"), "01/01/2000")

    def test_formatar_data_with_separators(self):
        self.assertEqual(_formatar_data("28/11/1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28-11-1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28.11.1988"), "28/11/1988")

    def test_formatar_data_invalid(self):
        # Should return exactly as is if not 8 digits
        self.assertEqual(_formatar_data("281188"), "281188")
        self.assertEqual(_formatar_data("invalid"), "invalid")

if __name__ == "__main__":
    unittest.main()
