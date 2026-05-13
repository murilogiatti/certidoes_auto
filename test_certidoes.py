import unittest
from certidoes import Pessoa

class TestPessoa(unittest.TestCase):
    # Testes de Data de Nascimento (Base Main)
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

    # Testes de Primeiro Nome (PR #3)
    def test_standard_name(self):
        p = Pessoa(nome="João Silva", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "joao")

    def test_diacritics_agata(self):
        p = Pessoa(nome="Ágata", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "agata")

    def test_diacritics_muller(self):
        p = Pessoa(nome="Müller", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "muller")

    def test_diacritics_conceicao(self):
        p = Pessoa(nome="Conceição", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "conceicao")

    def test_whitespace_handling(self):
        p = Pessoa(nome="  João  ", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "joao")

    def test_single_name(self):
        p = Pessoa(nome="Joao", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "joao")

    def test_empty_name(self):
        p = Pessoa(nome="", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "")

    def test_whitespace_only_name(self):
        p = Pessoa(nome="   ", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.primeiro_nome, "")

    # Testes de CPF formatado
    def test_cpf_formatado_valid_unformatted(self):
        p = Pessoa(nome="TESTE", cpf="12345678901", rg="", data_nascimento="")
        self.assertEqual(p.cpf_formatado, "123.456.789-01")

    def test_cpf_formatado_already_formatted(self):
        p = Pessoa(nome="TESTE", cpf="123.456.789-01", rg="", data_nascimento="")
        self.assertEqual(p.cpf_formatado, "123.456.789-01")

    def test_cpf_formatado_mixed_formatting_spaces(self):
        p = Pessoa(nome="TESTE", cpf="  123 456 789-01  ", rg="", data_nascimento="")
        self.assertEqual(p.cpf_formatado, "123.456.789-01")

    def test_cpf_formatado_empty(self):
        p = Pessoa(nome="TESTE", cpf="", rg="", data_nascimento="")
        self.assertEqual(p.cpf_formatado, "..-")

    def test_cpf_formatado_short(self):
        p = Pessoa(nome="TESTE", cpf="123", rg="", data_nascimento="")
        self.assertEqual(p.cpf_formatado, "123..-")

if __name__ == "__main__":
    unittest.main()
