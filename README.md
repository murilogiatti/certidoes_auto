# 🏛️ Automação de Certidões Negativas

Automação em Python para emissão de certidões negativas em múltiplos sites judiciais e governamentais brasileiros. O script preenche formulários automaticamente, gerencia CAPTCHAs com intervenção manual quando necessário, e salva todas as certidões organizadas por CPF.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)
![License](https://img.shields.io/badge/Licença-MIT-green)
![Platform](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## 📋 Certidões Suportadas

| # | Certidão | Site | Automação |
|---|----------|------|-----------|
| 1 | **Certidão de Protesto** | [protestosp.com.br](https://protestosp.com.br/) | ✅ 100% automático |
| 2 | **CEAT — Certidão Eletrônica de Ações Trabalhistas** | [trt15.jus.br](https://trt15.jus.br/servicos/certidoes/certidao-eletronica-de-acoes-trabalhistas-ceat) | ⚡ Semi (desafio manual) |
| 3 | **Certidão Negativa Trabalhista** | [tst.jus.br](https://www.tst.jus.br/certidao1) | ⚡ Semi (desafio manual) |
| 4 | **CRDA — Dívida Ativa PGE/SP** | [dividaativa.pge.sp.gov.br](https://www.dividaativa.pge.sp.gov.br/sc/pages/crda/emitirCrda.jsf) | ⚡ Semi (CAPTCHA manual) |
| 5 | **Distribuição Cível — TJSP** | [esaj.tjsp.jus.br](https://esaj.tjsp.jus.br/sco/abrirCadastro.do) | ✅ 100% automático |
| 6 | **Distribuição Criminal — TJSP** | [esaj.tjsp.jus.br](https://esaj.tjsp.jus.br/sco/abrirCadastro.do) | ✅ 100% automático |
| 7 | **Certidão Cível — TRF 3ª Região** | [web.trf3.jus.br](https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao) | ⚡ Semi (CAPTCHA manual) |
| 8 | **CND — Receita Federal** | [servicos.receitafederal.gov.br](https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cpf) | ✅ 100% automático |

> **✅ 100% automático** — O script faz tudo sozinho.  
> **⚡ Semi** — O script preenche os dados; você resolve o CAPTCHA/desafio no navegador e pressiona ENTER no terminal.

---

## 🚀 Início Rápido

### Pré-requisitos

- **Python 3.9+** — [Download](https://www.python.org/downloads/)
- **Git** (opcional) — [Download](https://git-scm.com/)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/certidoes-automaticas.git
cd certidoes-automaticas

# Instale as dependências
pip install playwright

# Instale o navegador Chromium
playwright install chromium
Execução
bashCopypython certidoes.py

📖 Como Funciona
1. Coleta de Dados
Ao executar, o script solicita no terminal:
Copy═══════════════════════════════════════════════════════
  📋  COLETA DE DADOS DA PESSOA
═══════════════════════════════════════════════════════

  Nome completo: JOÃO DA SILVA SANTOS
  CPF (somente números): 12345678901
  RG: 123456789
  Data de nascimento (DD/MM/AAAA): 15/03/1985
  Nome da mãe (obrigatório p/ TJSP Criminal): MARIA DA SILVA
  Email (obrigatório p/ TJSP): joao@email.com
2. Seleção de Certidões
Copy═══════════════════════════════════════════════════════
  📄  SELECIONE AS CERTIDÕES
═══════════════════════════════════════════════════════
  1. Protesto SP
  2. TRT 15 — CEAT
  3. TST
  4. Dívida Ativa PGE/SP
  5. TJSP — Distribuição Cível
  6. TJSP — Distribuição Criminal
  7. TRF 3ª Região
  8. Receita Federal — CND
  0. TODAS

  Opções (ex: 1,3,5 ou 0 para todas): 0
3. Execução Automática
O navegador Chrome abre automaticamente e processa cada site em sequência:
Copy━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1/8] Protesto SP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 [1/8] Protesto SP — Iniciando...
   🍪 Cookies aceitos.
   Selecionando tipo de documento: CPF
   Preenchendo CPF: 123.456.789-01
   Clicando em Consultar (1º clique)...
   Clicando em Consultar (2º clique)...
   📸 Screenshot salvo: downloads/12345678901/protesto_sp_20250625_143022.png
✅ [1/8] Protesto SP — Concluído!
4. Intervenção Manual (quando necessário)
Para sites com CAPTCHA/desafio, o script pausa e exibe:
Copy══════════════════════════════════════════════════════════
  ⚠️  TRT 15 (CEAT) — Resolva o desafio e clique em 'Emitir Certidão'.
  ➜  Pressione ENTER aqui quando concluir...
══════════════════════════════════════════════════════════

Basta resolver o CAPTCHA na janela do navegador e pressionar ENTER no terminal.

5. Relatório Final
Copy═══════════════════════════════════════════════════════
  📊  RELATÓRIO FINAL
═══════════════════════════════════════════════════════
  Pessoa: JOÃO DA SILVA SANTOS
  CPF:    123.456.789-01
  Data:   25/06/2025 14:38:45
  Pasta:  downloads/12345678901/
──────────────────────────────────────────────────────

  ✅  Protesto SP
      📄 protesto_sp_20250625_143022.png

  ✅  TRT 15 - CEAT
      📄 trt15_ceat_20250625_143155.pdf

  ✅  TST
      📄 tst_certidao_20250625_143301.pdf

  ✅  Dívida Ativa PGE/SP
      📄 divida_ativa_sp_20250625_143422.pdf

  ✅  TJSP Distribuição Cível
      📄 tjsp_dist_civil_20250625_143540.png

  ✅  TJSP Distribuição Criminal
      📄 tjsp_dist_criminal_20250625_143612.png

  ✅  TRF 3ª Região# 🏛️ Automação de Certidões Negativas

Automação em Python para emissão de certidões negativas em múltiplos sites judiciais e governamentais brasileiros. O script preenche formulários automaticamente, gerencia CAPTCHAs com intervenção manual quando necessário, e salva todas as certidões organizadas por CPF.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)
![License](https://img.shields.io/badge/Licença-MIT-green)
![Platform](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## 📋 Certidões Suportadas

| # | Certidão | Site | Automação |
|---|----------|------|-----------|
| 1 | **Certidão de Protesto** | [protestosp.com.br](https://protestosp.com.br/) | ✅ 100% automático |
| 2 | **CEAT — Certidão Eletrônica de Ações Trabalhistas** | [trt15.jus.br](https://trt15.jus.br/servicos/certidoes/certidao-eletronica-de-acoes-trabalhistas-ceat) | ⚡ Semi (desafio manual) |
| 3 | **Certidão Negativa Trabalhista** | [tst.jus.br](https://www.tst.jus.br/certidao1) | ⚡ Semi (desafio manual) |
| 4 | **CRDA — Dívida Ativa PGE/SP** | [dividaativa.pge.sp.gov.br](https://www.dividaativa.pge.sp.gov.br/sc/pages/crda/emitirCrda.jsf) | ⚡ Semi (CAPTCHA manual) |
| 5 | **Distribuição Cível — TJSP** | [esaj.tjsp.jus.br](https://esaj.tjsp.jus.br/sco/abrirCadastro.do) | ✅ 100% automático |
| 6 | **Distribuição Criminal — TJSP** | [esaj.tjsp.jus.br](https://esaj.tjsp.jus.br/sco/abrirCadastro.do) | ✅ 100% automático |
| 7 | **Certidão Cível — TRF 3ª Região** | [web.trf3.jus.br](https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao) | ⚡ Semi (CAPTCHA manual) |
| 8 | **CND — Receita Federal** | [servicos.receitafederal.gov.br](https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cpf) | ✅ 100% automático |

> **✅ 100% automático** — O script faz tudo sozinho.  
> **⚡ Semi** — O script preenche os dados; você resolve o CAPTCHA/desafio no navegador e pressiona ENTER no terminal.

---

## 🚀 Início Rápido

### Pré-requisitos

- **Python 3.9+** — [Download](https://www.python.org/downloads/)
- **Git** (opcional) — [Download](https://git-scm.com/)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/certidoes-automaticas.git
cd certidoes-automaticas

# Instale as dependências
pip install playwright

# Instale o navegador Chromium
playwright install chromium

      📄 trf3_civel_20250625_143730.pdf

  ✅  Receita Federal - CND
      📄 receita_federal_cnd_20250625_143845.pdf

──────────────────────────────────────────────────────
  Total: 8 | ✅ 8 | ❌ 0
═══════════════════════════════════════════════════════

  📋 Relatório salvo: downloads/12345678901/relatorio_20250625_143900.json

📁 Estrutura dos Arquivos
Copycertidoes-automaticas/
│
├── certidoes.py              # Script principal (arquivo único)
├── README.md                 # Este arquivo
├── requirements.txt          # Dependências
├── .gitignore                # Arquivos ignorados pelo Git
│
├── downloads/                # Gerado automaticamente
│   └── {CPF}/                # Pasta por pessoa (somente CPF)
│       ├── protesto_sp_20250625_143022.png
│       ├── trt15_ceat_20250625_143155.pdf
│       ├── tst_certidao_20250625_143301.pdf
│       ├── divida_ativa_sp_20250625_143422.pdf
│       ├── tjsp_dist_civil_20250625_143540.png
│       ├── tjsp_dist_criminal_20250625_143612.png
│       ├── trf3_civel_20250625_143730.pdf
│       ├── receita_federal_cnd_20250625_143845.pdf
│       └── relatorio_20250625_143900.json
│
└── certidoes_20250625_143022.log   # Log de execução

⚙️ Fluxo Detalhado por Site
1. Protesto SP — protestosp.com.br
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Seleciona CPF no dropdown]
    C --> D[Preenche CPF]
    D --> E[Clica Consultar]
    E --> F[Clica Consultar novamente]
    F --> G[📸 Screenshot]
Campos utilizados:

#TipoDocumento → valor 1 (CPF)
input[name="Documento"] → CPF


2. TRT 15 — CEAT
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Preenche CPF]
    C --> D[⏸️ Aguarda usuário]
    D --> E[Usuário resolve desafio + clica Emitir]
    E --> F[💾 Salva certidão]
Campo utilizado:

#certidaoActionForm:j_id23:doctoPesquisa → CPF


3. TST
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Clica 'Emitir Certidão']
    C --> D[Preenche CPF]
    D --> E[⏸️ Aguarda usuário]
    E --> F[Usuário resolve desafio + clica Emitir]
    F --> G[💾 Salva certidão]
Campo utilizado:

#gerarCertidaoForm:cpfCnpj → CPF


4. Dívida Ativa PGE/SP
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Preenche CPF]
    C --> D[⏸️ Aguarda CAPTCHA]
    D --> E[Usuário resolve CAPTCHA]
    E --> F[Script clica Emitir]
    F --> G[💾 Salva certidão]
Campo utilizado:

#emitirCrda:crdaInputCpf → CPF


5 & 6. TJSP — Distribuição Cível e Criminal
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Seleciona modelo]
    C --> D[Preenche campos obrigatórios]
    D --> E[Marca checkbox]
    E --> F[Clica Enviar]
    F --> G[💾 Salva certidão]
Campos utilizados:
CampoCívelCriminal#cdModelo526Nome✅✅CPF✅✅RG✅✅Data Nascimento✅✅Nome da Mãe—✅Email✅✅#confirmacaoInformacoes✅✅

7. TRF 3ª Região
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Seleciona CÍVEL + CPF + TRF]
    C --> D[Preenche CPF e Nome]
    D --> E[⏸️ Aguarda CAPTCHA]
    E --> F[Usuário resolve + clica Emitir]
    F --> G[💾 Salva certidão]
Campos utilizados:

#Tipo → CIVEL
#TipoDeDocumento → CPF
#TipoDeAbrangencia → TRF
Campos de CPF e Nome


8. Receita Federal — CND
mermaidCopyflowchart LR
    A[Acessa site] --> B[Aceita cookies]
    B --> C[Preenche CPF]
    C --> D[Preenche Data de Nascimento]
    D --> E[Clica Emitir Certidão]
    E --> F[💾 Salva certidão]
Campos utilizados:

input[name="niContribuinte"] → CPF
input[name="dataNascimento"] → Data de Nascimento


🔧 Configurações Avançadas
Alterar Timeout de Página
No código, a constante de timeout está em cada page.goto():
pythonCopyawait page.goto(url, wait_until="networkidle", timeout=60000)  # 60 segundos
Modo Headless (sem interface gráfica)

⚠️ Não recomendado — você precisa ver o navegador para resolver CAPTCHAs.

pythonCopybrowser = await p.chromium.launch(headless=True)  # Mude para True
Velocidade de Digitação
Cada campo usa delay em milissegundos entre teclas:
pythonCopyawait campo.type(pessoa.cpf_limpo, delay=80)  # 80ms entre teclas
Diminua para mais velocidade, aumente para parecer mais humano.

🛠️ Solução de Problemas
Erro: "Elemento não encontrado"
Os sites governamentais atualizam seus layouts periodicamente. Se um seletor parar de funcionar:

Acesse o site manualmente no Chrome
Pressione F12 → aba Elements
Clique no ícone de seletor (🔍) e clique no campo desejado
Copie o id ou name do elemento
Atualize o seletor correspondente no código

Erro: "Timeout"

Verifique sua conexão com a internet
O site pode estar fora do ar — tente novamente mais tarde
Aumente o timeout no page.goto()

CAPTCHA não aparece
Alguns sites detectam automação. O script já usa:

User-agent real do Chrome
Flag --disable-blink-features=AutomationControlled
Delays na digitação

Download não é capturado
Se a certidão abrir em nova aba ao invés de baixar:

O script tira screenshot da nova aba automaticamente
Você também pode salvar manualmente pelo navegador


📦 Dependências
Copyplaywright>=1.40.0
Arquivo requirements.txt
Copyplaywright>=1.40.0
Instalação:
bashCopypip install -r requirements.txt
playwright install chromium

📝 .gitignore
gitignoreCopy# Downloads e logs
downloads/
*.log

# Python
__pycache__/
*.pyc
*.pyo
.env
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

🤝 Contribuindo

Faça um fork do projeto
Crie uma branch para sua feature: git checkout -b minha-feature
Commit suas mudanças: git commit -m 'Adiciona nova feature'
Push para a branch: git push origin minha-feature
Abra um Pull Request

Ideias para contribuição

 Adicionar suporte a mais tribunais (TRT de outros estados)
 Integração com serviços de resolução automática de CAPTCHA (2Captcha, Anti-Captcha)
 Interface gráfica (GUI) com Tkinter ou PyQt
 Modo batch via arquivo CSV/JSON
 Notificação por email ao concluir
 Agendamento automático (cron/Task Scheduler)
 Validação de CPF antes de iniciar


⚖️ Aviso Legal
Este projeto é uma ferramenta de automação para uso legítimo na emissão de certidões públicas disponíveis gratuitamente nos sites oficiais.

✅ As certidões são públicas e de acesso livre
✅ O script apenas automatiza o preenchimento de formulários
✅ Nenhum dado é coletado, armazenado externamente ou compartilhado
⚠️ Use de acordo com os termos de uso de cada site
⚠️ O desenvolvedor não se responsabiliza por uso indevido


📄 Licença
Este projeto está sob a licença MIT.
CopyMIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

<div align="center">
Feito com ☕ e Python
⭐ Se este projeto foi útil, deixe uma estrela!
</div>
```Add to Conversation
