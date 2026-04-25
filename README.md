# 🏛️ Certidões Auto v2.0

> **Automação de alta performance para emissão de Certidões Negativas brasileiras.**

O **Certidões Auto** é um motor de automação robusto desenvolvido em Python e Playwright, projetado para extrair certidões negativas de múltiplos portais governamentais e judiciais de forma resiliente, organizada e inteligente.

---

## 🚀 Diferenciais Técnicos

- **Navegação Resiliente**: Implementa estratégias de fallback (`networkidle`, `domcontentloaded`) para lidar com a instabilidade crônica de sites governamentais.
- **Engine Anti-Detecção**: Oculta flags de automação, utiliza User-Agents reais e simula comportamento humano (digitação rítmica e movimentos) para contornar bloqueios.
- **Gerenciador de Resultados Híbrido**: Captura inteligência de três formas:
  1. Downloads diretos monitorados.
  2. Detecção de PDFs em abas flutuantes ou objetos Blob.
  3. Screenshots de alta fidelidade (JPEG Full Page) como camada de segurança.
- **Orion Hub Ready**: Modo de automação via variáveis de ambiente para integração com outros sistemas e pipelines sem necessidade de TTY.
- **Estrutura de Dados Inteligente**: Sanitização e formatação automática de CPF/RG e nomes.

---

## 📂 Portais Suportados

| # | Portal | Escopo | Nível de Automação |
| :--- | :--- | :--- | :--- |
| 1 | **Protesto SP** | Nacional (CENPROT) | ✅ Full |
| 2 | **TRT 15** | CEAT (Trabalhista) | ⚡ Semi (Captcha) |
| 3 | **TST** | Nacional (Trabalhista) | ⚡ Semi (Captcha) |
| 4 | **PGE/SP** | Dívida Ativa Estadual | ⚡ Semi (Captcha) |
| 5 | **TJSP Cível** | Estadual (São Paulo) | ✅ Full |
| 6 | **TJSP Criminal** | Estadual (São Paulo) | ✅ Full |
| 7 | **TRF 3ª Região** | Federal (SP/MS) | ⚡ Semi (Captcha) |
| 8 | **Receita Federal** | CND (Nacional) | ✅ Full |

---

## 🛠️ Requisitos e Instalação

### Pré-requisitos
- Python 3.9+
- Pip (Gerenciador de pacotes)

### Instalação Rápida
```bash
# Clone o repositório
git clone https://github.com/murilogiatti/certidoes_auto.git
cd certidoes_auto

# Instale as dependências
pip install -r requirements.txt

# Instale os binários do navegador
playwright install chromium
```

---

## ⚙️ Modos de Uso

### 1. Modo Interativo (Padrão)
Basta rodar o script e seguir o assistente no terminal:
```bash
python certidoes.py
```

### 2. Modo Orion Hub (Automático)
Ideal para integração com scripts ou servidores. O script pula a coleta manual e executa tudo automaticamente:
```bash
export AUTO_NOME="NOME COMPLETO"
export AUTO_CPF="12345678900"
export AUTO_RG="123456789"
export AUTO_NASC="01/01/1990"
export AUTO_GENERO="M"
python certidoes.py
```

---

## 📊 Estrutura de Saída

Os arquivos são organizados por CPF na pasta `downloads/`, garantindo rastreabilidade:

```text
downloads/
└── 123.456.789-00/
    ├── protesto_sp_20260424.jpg
    ├── tjsp_civil_20260424.pdf
    ├── ...
    └── relatorio_20260424_230000.json  # Relatório estruturado do lote
```

---

## 🛡️ Aviso Legal
Esta ferramenta é um acelerador de produtividade para acesso a dados públicos. O uso deve respeitar os Termos de Serviço de cada órgão. O desenvolvedor não se responsabiliza pelo uso indevido da automação.

---
<div align="center">
  Desenvolvido com ☕ e precisão por <b>Murilo Giatti</b>
</div>
