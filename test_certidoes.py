import unittest
from certidoes import Pessoa

class TestPessoa(unittest.TestCase):
    def test_data_nascimento_iso_valid(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="28/11/1988")
        self.assertEqual(p.data_nascimento_iso, "1988-11-28")

    def test_data_nascimento_iso_invalid_format(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="28-11-1988")
        with self.assertRaisesRegex(ValueError, "Data de nascimento inválida. Formato esperado: DD/MM/AAAA"):
            _ = p.data_nascimento_iso

    def test_data_nascimento_iso_missing_slashes(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="28111988")
        with self.assertRaisesRegex(ValueError, "Data de nascimento inválida. Formato esperado: DD/MM/AAAA"):
            _ = p.data_nascimento_iso

    def test_data_nascimento_iso_empty(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="")
        with self.assertRaisesRegex(ValueError, "Data de nascimento inválida. Formato esperado: DD/MM/AAAA"):
            _ = p.data_nascimento_iso

    def test_data_nascimento_iso_wrong_number_of_components(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="28/11")
        with self.assertRaisesRegex(ValueError, "Data de nascimento inválida. Formato esperado: DD/MM/AAAA"):
            _ = p.data_nascimento_iso

    def test_data_nascimento_iso_too_many_components(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="1234567", data_nascimento="28/11/1988/01")
        with self.assertRaisesRegex(ValueError, "Data de nascimento inválida. Formato esperado: DD/MM/AAAA"):
            _ = p.data_nascimento_iso

if __name__ == "__main__":
    unittest.main()
