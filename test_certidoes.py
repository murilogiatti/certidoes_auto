import unittest
from certidoes import Pessoa

class TestPessoa(unittest.TestCase):
    def setUp(self):
        self.pessoa = Pessoa(
            nome="João da Silva Santos",
            cpf="123.456.789-01",
            rg="12.345.678-9",
            data_nascimento="15/03/1985",
            genero="M",
            nome_mae="Maria da Silva",
            email="joao@email.com"
        )

    def test_cpf_limpo(self):
        self.assertEqual(self.pessoa.cpf_limpo, "12345678901")

    def test_cpf_formatado(self):
        self.assertEqual(self.pessoa.cpf_formatado, "123.456.789-01")

    def test_data_nascimento_iso(self):
        self.assertEqual(self.pessoa.data_nascimento_iso, "1985-03-15")

    def test_primeiro_nome(self):
        self.assertEqual(self.pessoa.primeiro_nome, "joao")

    def test_primeiro_nome_com_acentos(self):
        p = Pessoa(nome="Átila", cpf="123", rg="123", data_nascimento="01/01/2000")
        self.assertEqual(p.primeiro_nome, "atila")

if __name__ == "__main__":
    unittest.main()
