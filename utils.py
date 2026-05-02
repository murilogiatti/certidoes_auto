import os
from datetime import datetime

def timestamp() -> str:  # kept for ERRO/relatorio files
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def datestamp() -> str:
    """Somente data: YYYYMMDD — usado nos nomes dos arquivos de certidão."""
    return datetime.now().strftime("%Y%m%d")

def criar_pasta(nome_pessoa: str) -> str:
    """Cria e retorna o caminho: ./downloads/{Nome}/"""
    # Sanitiza o nome para uso como diretório
    nome_dir = nome_pessoa.strip().upper()
    # Remove caracteres inválidos em nomes de pasta
    for c in r'\/:*?"<>|':
        nome_dir = nome_dir.replace(c, "_")
    pasta = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "downloads", nome_dir
    )
    os.makedirs(pasta, exist_ok=True)
    return pasta

def _formatar_data(raw: str) -> str:
    """Tenta converter 28111988, 2811981, etc. em 28/11/1988."""
    raw = raw.replace("/", "").replace("-", "").replace(".", "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:2]}/{raw[2:4]}/{raw[4:]}"
    return raw  # devolve como está se não reconhecer
