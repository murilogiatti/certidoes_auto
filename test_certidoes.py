import unittest
from certidoes import Pessoa

class TestPessoaPrimeiroNome(unittest.TestCase):
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
        # This is expected to fail with IndexError initially
        self.assertEqual(p.primeiro_nome, "")

    def test_whitespace_only_name(self):
        p = Pessoa(nome="   ", cpf="", rg="", data_nascimento="")
        # This is expected to fail with IndexError initially
        self.assertEqual(p.primeiro_nome, "")

if __name__ == "__main__":
    unittest.main()
