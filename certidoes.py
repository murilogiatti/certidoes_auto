#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  AUTOMAÇÃO DE CERTIDÕES NEGATIVAS  v2.0
  Downloads salvos em: ./downloads/{Nome}/
═══════════════════════════════════════════════════════════════
  Sites:
    1. Protesto SP
    2. TRT 15 — CEAT
    3. TST
    4. Dívida Ativa PGE/SP
    5. TJSP — Distribuição Cível
    6. TJSP — Distribuição Criminal
    7. TRF 3ª Região
    8. Receita Federal — CND
═══════════════════════════════════════════════════════════════
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
from playwright.async_api import (
    async_playwright,
    Page,
    BrowserContext,
    Download,
)

# ───────────────────────────────────────────────────────────────
#  LOGGING
# ───────────────────────────────────────────────────────────────

LOG_FILE = f"certidoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("certidoes")


# ───────────────────────────────────────────────────────────────
#  MODELO DE DADOS
# ───────────────────────────────────────────────────────────────

@dataclass
class Pessoa:
    nome: str
    cpf: str
    rg: str
    data_nascimento: str        # DD/MM/AAAA
    genero: str = "M"           # "M" ou "F"
    nome_mae: Optional[str] = None
    email: Optional[str] = None

    @property
    def cpf_limpo(self) -> str:
        return self.cpf.replace(".", "").replace("-", "").replace(" ", "")

    @property
    def cpf_formatado(self) -> str:
        c = self.cpf_limpo
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

    @property
    def data_nascimento_iso(self) -> str:
        """DD/MM/AAAA → AAAA-MM-DD"""
        parts = self.data_nascimento.split("/")
        if len(parts) != 3:
            raise ValueError("Data de nascimento inválida. Formato esperado: DD/MM/AAAA")
        d, m, a = parts
        return f"{a}-{m}-{d}"

    @property
    def primeiro_nome(self) -> str:
        """Retorna o primeiro nome em minúsculas, sem acentos."""
        import unicodedata
        n = self.nome.split()[0].lower()
        return ''.join(
            c for c in unicodedata.normalize('NFD', n)
            if unicodedata.category(c) != 'Mn'
        )

    @property
    def data_nascimento_compacta(self) -> str:
        """DD/MM/AAAA → DDMMAAAA (para campos numéricos)"""
        return self.data_nascimento.replace("/", "")


# ───────────────────────────────────────────────────────────────
#  FUNÇÕES UTILITÁRIAS
# ───────────────────────────────────────────────────────────────

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


async def aceitar_cookies(page: Page):
    """Tenta aceitar banners de cookies comuns."""
    await page.wait_for_timeout(2000)
    seletores = [
        "button:has-text('Aceitar')",
        "button:has-text('Aceito')",
        "button:has-text('Concordo')",
        "button:has-text('Entendi')",
        "button:has-text('Accept')",
        "button:has-text('OK')",
        "a:has-text('Aceitar')",
        "a:has-text('Aceito')",
        "#lgpd-button",
        "#cookieAccept",
        ".cookie-accept",
        ".accept-cookie",
        "[data-cookieconsent='accept']",
        "button.btn-accept-cookies",
        "#onetrust-accept-btn-handler",
        ".lgpd-accept",
        "button[aria-label*='cookie']",
        "button[aria-label*='Cookie']",
    ]
    for sel in seletores:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=600):
                await el.click()
                logger.info("   🍪 Cookies aceitos.")
                await page.wait_for_timeout(800)
                return
        except Exception:
            continue
    logger.debug("   Nenhum banner de cookies encontrado.")


async def aguardar_usuario(mensagem: str):
    """Pausa e aguarda ENTER do usuário no terminal."""
    print(f"\n{'═'*62}")
    print(f"  ⚠️  {mensagem}")
    print(f"  ➜  Pressione ENTER aqui quando concluir...")
    print(f"{'═'*62}\n")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input)


async def preencher_campo(page: Page, seletores: list, valor: str, delay: int = 60) -> bool:
    """Tenta preencher o primeiro campo visível dentre os seletores."""
    for sel in seletores:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=1500):
                await el.click()
                await el.fill("")
                await el.type(valor, delay=delay)
                return True
        except Exception:
            continue
    return False


async def salvar_resultado(
    page: Page,
    context: BrowserContext,
    downloads: List[Download],
    pasta: str,
    nome_base: str,
) -> Optional[str]:
    """
    Salva o resultado da certidão.
    Prioridade: 1) Downloads capturados  2) Nova aba com PDF  3) Screenshot
    """
    await page.wait_for_timeout(2500)

    # 1) Downloads capturados
    if downloads:
        dl = downloads[-1]
        try:
            await asyncio.wait_for(dl.path(), timeout=30)
            extensao = os.path.splitext(dl.suggested_filename or "")[1] or ".pdf"
            arquivo = os.path.join(pasta, f"{nome_base}_{datestamp()}{extensao}")
            await dl.save_as(arquivo)
            logger.info(f"   💾 Download salvo: {arquivo}")
            return arquivo
        except Exception as e:
            logger.warning(f"   Falha ao salvar download: {e}")

    # 2) Verifica novas abas (PDF pode ter aberto em nova aba)
    for p in context.pages:
        if p != page:
            try:
                url = p.url
                if ".pdf" in url.lower() or "blob:" in url:
                    arquivo = os.path.join(pasta, f"{nome_base}_{datestamp()}.jpg")
                    await p.screenshot(path=arquivo, full_page=True, type="jpeg")
                    logger.info(f"   📸 Screenshot de nova aba: {arquivo}")
                    return arquivo
            except Exception:
                continue

    # 3) Screenshot da página atual
    arquivo = os.path.join(pasta, f"{nome_base}_{datestamp()}.jpg")
    await page.screenshot(path=arquivo, full_page=True, type="jpeg")
    logger.info(f"   📸 Screenshot salvo: {arquivo}")
    return arquivo


async def goto_seguro(page: Page, url: str, timeout: int = 60000) -> bool:
    """
    Navega para a URL com fallback:
    1) networkidle  2) domcontentloaded  3) load
    """
    for estado in ["domcontentloaded", "load"]:
        try:
            await page.goto(url, wait_until=estado, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"   goto com '{estado}' falhou: {e}")
    logger.warning(f"   Não foi possível carregar {url} com nenhuma estratégia.")
    return False


# ───────────────────────────────────────────────────────────────
#  1. PROTESTO SP
# ───────────────────────────────────────────────────────────────

async def site_protesto_sp(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://protestosp.com.br/consulta-de-protesto
    Fluxo: Aguarda form → Seleciona CPF → Preenche CPF → Consultar 2x → Screenshot
    """
    nome = f"{pessoa.primeiro_nome}_cenprot"
    resultado = {"site": "Protesto SP", "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info("🔄 [1/8] Protesto SP — Iniciando...")

        await goto_seguro(page, "https://protestosp.com.br/consulta-de-protesto")

        # Aguarda o formulário aparecer diretamente
        logger.info("   Aguardando formulário...")
        await page.wait_for_selector("#TipoDocumento", timeout=30000)

        # Seleciona CPF (value="1")
        logger.info("   Selecionando tipo de documento: CPF")
        await page.select_option("#TipoDocumento", "1")
        await page.wait_for_timeout(600)

        # Preenche CPF
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        campo_doc = page.locator('input[name="Documento"], input.doc-validar').first
        await campo_doc.wait_for(timeout=10000)
        await campo_doc.click()
        await campo_doc.fill("")
        await campo_doc.type(pessoa.cpf_limpo, delay=80)
        await page.wait_for_timeout(600)

        # Usuário clica em Consultar (1º clique) manualmente
        sels_consultar = ['button:has-text("Consultar")', 'input[value="Consultar"]', 'a:has-text("Consultar")']
        await aguardar_usuario("CENPROT — Preenchi o CPF. Clique em CONSULTAR no navegador e pressione ENTER aqui.")

        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass

        # 2º clique em Consultar — script executa
        logger.info("   Clicando em Consultar (2º clique)...")
        for sel in sels_consultar:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=4000):
                    await el.click()
                    break
            except Exception:
                continue

        await page.wait_for_timeout(5000)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass

        # Screenshot do resultado
        arquivo = os.path.join(pasta, f"{nome}_{datestamp()}.jpg")
        await page.screenshot(path=arquivo, full_page=True, type="jpeg")
        logger.info(f"   📸 Screenshot salvo: {arquivo}")

        resultado["sucesso"] = True
        resultado["arquivo"] = arquivo
        logger.info("✅ [1/8] Protesto SP — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [1/8] Protesto SP — Erro: {e}")
        await aguardar_usuario(f"❌ Protesto SP — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True)
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  2. TRT 15ª REGIÃO (CEAT)
# ───────────────────────────────────────────────────────────────

async def site_trt15(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://trt15.jus.br → CEAT
    Fluxo: Preenche CPF → Usuário resolve desafio e clica Emitir → Salva
    """
    nome = f"{pessoa.primeiro_nome}_trt15"
    resultado = {"site": "TRT 15 - CEAT", "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info("🔄 [2/8] TRT 15 (CEAT) — Iniciando...")

        await goto_seguro(
            page,
            "https://trt15.jus.br/servicos/certidoes/certidao-eletronica-de-acoes-trabalhistas-ceat"
        )

        # Campo JSF (ID longo)
        campo_id = 'certidaoActionForm:j_id23:doctoPesquisa'
        campo_existe = await page.locator(f'[id="{campo_id}"]').count()

        if campo_existe == 0:
            logger.info("   Campo não encontrado na página, procurando link CEAT...")
            for sel in [
                'a[href*="ceat"]', 'a:has-text("CEAT")', 'a:has-text("Emitir")',
                'a:has-text("clique aqui")', 'a:has-text("Certidão Eletrônica")',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=1000):
                        href = await el.get_attribute("href")
                        if href and href.startswith("http"):
                            await goto_seguro(page, href)
                        else:
                            await el.click()
                            await page.wait_for_timeout(3000)
                        break
                except Exception:
                    continue

            # Fallback URL direta
            if await page.locator(f'[id="{campo_id}"]').count() == 0:
                await goto_seguro(page, "https://trt15.jus.br/ceat/certidaoAction.seam")
                await page.wait_for_timeout(3000)

        # Preenche CPF
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        campo_cpf = page.locator(f'[id="{campo_id}"]')
        try:
            await campo_cpf.wait_for(timeout=12000)
        except Exception:
            campo_cpf = page.locator(
                'input[name*="doctoPesquisa"], input[name*="cpf"], input[id*="doctoPesquisa"]'
            ).first

        await campo_cpf.click()
        await campo_cpf.fill("")
        await campo_cpf.type(pessoa.cpf_limpo, delay=80)
        await campo_cpf.evaluate("el => el.blur()")
        await page.wait_for_timeout(3000)

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        await aguardar_usuario("TRT 15 (CEAT) — Resolva o desafio e pressione ENTER (o script clicará em Emitir Certidão).")

        logger.info("   Clicando em 'Emitir Certidão'...")
        sels_emitir_trt15 = [
            'input[value*="Emitir"]', 'button:has-text("Emitir Certidão")',
            'button:has-text("Emitir")', 'a:has-text("Emitir Certidão")',
        ]
        for sel in sels_emitir_trt15:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    break
            except Exception:
                continue

        # Aguarda nova tela abrir após o clique em Emitir
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        # Clica em "Imprimir Certidão" na tela que abriu
        logger.info("   Clicando em 'Imprimir Certidão'...")
        for sel in [
            'a:has-text("Imprimir Certidão")',
            'button:has-text("Imprimir Certidão")',
            'input[value*="Imprimir Certidão"]',
            'button:has-text("Imprimir")',
            'a:has-text("Imprimir")',
            'input[value*="Imprimir"]',
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    logger.info(f"   Imprimir clicado via: {sel}")
                    break
            except Exception:
                continue

        await page.wait_for_timeout(6000)

        arquivo = await salvar_resultado(page, ctx, downloads, pasta, nome)
        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info("✅ [2/8] TRT 15 (CEAT) — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [2/8] TRT 15 — Erro: {e}")
        await aguardar_usuario(f"❌ TRT 15 — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True)
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  3. TST — TRIBUNAL SUPERIOR DO TRABALHO
# ───────────────────────────────────────────────────────────────

async def site_tst(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://www.tst.jus.br/certidao1
    Fluxo: Aceita cookies → 2x Emitir Certidão (abre form) → Preenche CPF
           → Usuário resolve desafio → Imprimir Certidão → Salva PDF
    """
    nome = f"{pessoa.primeiro_nome}_tst"
    resultado = {"site": "TST", "sucesso": False, "arquivo": None, "erro": None}

    sels_emitir_tst = [
        '[id="gerarCertidaoForm:j_id30"]',
        'input[value*="Emitir Certidão"]',
        'input[value*="Emitir"]',
        'button:has-text("Emitir Certidão")',
        'button:has-text("Emitir")',
        'a:has-text("Emitir Certidão")',
        'a:has-text("Emitir")',
        'a[href*="certidao"]',
    ]

    try:
        logger.info("🔄 [3/8] TST — Iniciando...")

        await goto_seguro(page, "https://www.tst.jus.br/certidao1")
        await aceitar_cookies(page)
        await page.wait_for_timeout(2000)

        # Usuário clica em "Emitir Certidão" manualmente (1º clique — navega para o form)
        await aguardar_usuario("TST — Clique em 'Emitir Certidão' no navegador e pressione ENTER aqui.")

        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # Preenche CPF
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        campo_cpf = None

        for frame in page.frames:
            for sel in [
                '[id="gerarCertidaoForm:cpfCnpj"]',
                'input[name*="cpfCnpj"]',
                'input[name*="cpf"]',
                'input[id*="cpfCnpj"]',
            ]:
                try:
                    el = frame.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        campo_cpf = el
                        break
                except Exception:
                    continue
            if campo_cpf:
                break

        if not campo_cpf:
            for sel in [
                '[id="gerarCertidaoForm:cpfCnpj"]',
                'input[name*="cpfCnpj"]',
                'input[id*="cpfCnpj"]',
                'input[name*="cpf"]',
                'input[placeholder*="CPF"]',
            ]:
                try:
                    el = page.locator(sel).first
                    await el.wait_for(timeout=8000)
                    if await el.is_visible():
                        campo_cpf = el
                        break
                except Exception:
                    continue

        if campo_cpf:
            await campo_cpf.click()
            await campo_cpf.fill("")
            await campo_cpf.type(pessoa.cpf_limpo, delay=60)
            await page.wait_for_timeout(1000)
        else:
            await aguardar_usuario("TST — Campo CPF não encontrado. Preencha o CPF no navegador e pressione ENTER.")

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        await aguardar_usuario("TST — Resolva o desafio e pressione ENTER (o script clicará em Imprimir Certidão).")

        # Clica em "Imprimir Certidão" para gerar o PDF
        logger.info("   Clicando em 'Imprimir Certidão'...")
        for sel in [
            'a:has-text("Imprimir Certidão")',
            'button:has-text("Imprimir Certidão")',
            'button:has-text("Imprimir")',
            'a:has-text("Imprimir")',
            'input[value*="Imprimir"]',
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    logger.info(f"   Imprimir clicado via: {sel}")
                    break
            except Exception:
                continue

        # Aguarda nova aba (PDF) abrir ou download disparar
        await page.wait_for_timeout(3000)
        nova_aba = None
        for _ in range(10):
            for p in ctx.pages:
                if p != page and p.url not in ("about:blank", ""):
                    nova_aba = p
                    break
            if nova_aba or downloads:
                break
            await page.wait_for_timeout(1000)

        if nova_aba:
            await nova_aba.wait_for_load_state("domcontentloaded", timeout=15000)
            await nova_aba.wait_for_timeout(2000)
            # Tenta capturar PDF da nova aba
            url_aba = nova_aba.url
            if ".pdf" in url_aba.lower() or "blob:" in url_aba:
                arquivo = os.path.join(pasta, f"{nome}_{datestamp()}.pdf")
                # Faz download via JS blob
                try:
                    pdf_bytes = await nova_aba.evaluate("""async () => {
                        const r = await fetch(document.URL);
                        const buf = await r.arrayBuffer();
                        return Array.from(new Uint8Array(buf));
                    }""")
                    with open(arquivo, "wb") as f:
                        f.write(bytes(pdf_bytes))
                    logger.info(f"   💾 PDF da nova aba salvo: {arquivo}")
                except Exception:
                    arquivo = os.path.join(pasta, f"{nome}_{datestamp()}.jpg")
                    await nova_aba.screenshot(path=arquivo, full_page=True, type="jpeg")
                    logger.info(f"   📸 Screenshot da nova aba: {arquivo}")
            else:
                arquivo = os.path.join(pasta, f"{nome}_{datestamp()}.jpg")
                await nova_aba.screenshot(path=arquivo, full_page=True, type="jpeg")
                logger.info(f"   📸 Screenshot da nova aba: {arquivo}")
        else:
            arquivo = await salvar_resultado(page, ctx, downloads, pasta, nome)

        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info("✅ [3/8] TST — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [3/8] TST — Erro: {e}")
        await aguardar_usuario(f"❌ TST — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True)
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  4. DÍVIDA ATIVA PGE/SP
# ───────────────────────────────────────────────────────────────

async def site_divida_ativa_sp(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://www.dividaativa.pge.sp.gov.br/sc/pages/crda/emitirCrda.jsf
    Fluxo: Preenche CPF → Usuário resolve CAPTCHA → Script clica Emitir → Salva
    """
    nome = f"{pessoa.primeiro_nome}_crda"
    resultado = {"site": "Dívida Ativa PGE/SP", "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info("🔄 [4/8] Dívida Ativa PGE/SP — Iniciando...")

        await goto_seguro(
            page,
            "https://www.dividaativa.pge.sp.gov.br/sc/pages/crda/emitirCrda.jsf"
        )
        await aceitar_cookies(page)
        await page.wait_for_timeout(2000)

        # Preenche CPF
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        campo_cpf = page.locator('[id="emitirCrda:crdaInputCpf"]')
        try:
            await campo_cpf.wait_for(timeout=12000)
        except Exception:
            campo_cpf = page.locator(
                'input[name="emitirCrda:crdaInputCpf"], input[id*="crdaInput"]'
            ).first

        await campo_cpf.click()
        await campo_cpf.fill("")
        await campo_cpf.type(pessoa.cpf_limpo, delay=60)
        await campo_cpf.evaluate("el => el.blur()")
        await page.wait_for_timeout(1000)

        # Usuário resolve CAPTCHA
        await aguardar_usuario("Dívida Ativa PGE/SP — Resolva o CAPTCHA no navegador.")

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        # Clica em Emitir
        logger.info("   Clicando em 'Emitir'...")
        for sel in [
            '[id*="btnEmitir"]',
            'input[value*="Emitir"]',
            'button:has-text("Emitir")',
            'a:has-text("Emitir")',
            'input[type="submit"]',
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    break
            except Exception:
                continue

        await page.wait_for_timeout(8000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        arquivo = await salvar_resultado(page, ctx, downloads, pasta, nome)
        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info("✅ [4/8] Dívida Ativa PGE/SP — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [4/8] Dívida Ativa PGE/SP — Erro: {e}")
        await aguardar_usuario(f"❌ Dívida Ativa — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True)
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  5 & 6. TJSP — DISTRIBUIÇÃO CÍVEL E CRIMINAL
# ───────────────────────────────────────────────────────────────

async def _site_tjsp(
    page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str, tipo: str
) -> dict:
    """
    https://esaj.tjsp.jus.br/sco/abrirCadastro.do
    tipo: "civil" (modelo 52) ou "criminal" (modelo 6)
    """
    if tipo == "civil":
        nome = f"{pessoa.primeiro_nome}_civil"
        valor_modelo = "52"
        etapa = "5/8"
        nome_display = "TJSP Distribuição Cível"
    else:
        nome = f"{pessoa.primeiro_nome}_criminal"
        valor_modelo = "6"
        etapa = "6/8"
        nome_display = "TJSP Distribuição Criminal"

    resultado = {"site": nome_display, "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info(f"🔄 [{etapa}] {nome_display} — Iniciando...")

        await goto_seguro(page, "https://esaj.tjsp.jus.br/sco/abrirCadastro.do")
        await aceitar_cookies(page)
        await page.wait_for_timeout(2000)

        # 1) Seleciona modelo e aguarda campos AJAX carregarem
        logger.info(f"   Selecionando modelo: {valor_modelo}")
        await page.wait_for_selector("#cdModelo", timeout=15000)
        await page.select_option("#cdModelo", valor_modelo)

        # Os campos são injetados por AJAX após a seleção — aguarda até 15 s
        logger.info("   Aguardando campos dinâmicos carregarem...")
        campos_carregados = False
        for _ in range(15):
            for sel_teste in [
                'input[name*="nmRequerente"]', 'input[name*="nome"]',
                'input[id*="nmRequerente"]', 'input[id*="nome"]',
            ]:
                try:
                    if await page.locator(sel_teste).first.is_visible(timeout=500):
                        campos_carregados = True
                        break
                except Exception:
                    continue
            if campos_carregados:
                break
            await page.wait_for_timeout(1000)

        if not campos_carregados:
            await aguardar_usuario("TJSP — Campos do formulário não carregaram em 15 s. Aguarde aparecerem no navegador e pressione ENTER.")
        else:
            logger.info("   ✅ Campos carregados.")
        await page.wait_for_timeout(500)

        async def tjsp_fill(label_texto: str, valor: str, delay: int = 40) -> bool:
            """Preenche campo pelo texto do label (get_by_label) com fallback por seletor."""
            try:
                el = page.get_by_label(label_texto, exact=False).first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    await el.fill("")
                    await el.type(valor, delay=delay)
                    return True
            except Exception:
                pass
            return False

        # 2) Nome
        logger.info(f"   Preenchendo nome: {pessoa.nome}")
        if not await tjsp_fill("Nome Completo", pessoa.nome):
            await preencher_campo(page, [
                'input[name*="nmRequerente"]', 'input[name*="nomeRequerente"]',
                'input[id*="nmRequerente"]', 'input[id*="nomeCompleto"]',
            ], pessoa.nome, delay=40)
        await page.wait_for_timeout(400)

        # 3) CPF
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        if not await tjsp_fill("CPF", pessoa.cpf_limpo):
            await preencher_campo(page, [
                'input[name*="nuDocumento"]', 'input[name*="nrCpf"]',
                'input[name*="cpf"]', 'input[id*="nuDocumento"]',
                'input[id*="cpf"]',
            ], pessoa.cpf_limpo, delay=40)
        await page.wait_for_timeout(400)

        # 4) RG — usa JavaScript para localizar o input logo após o label "RG"
        logger.info(f"   Preenchendo RG: {pessoa.rg}")
        rg_preenchido = False
        try:
            # Estratégia 1: JS busca o input cujo label contém "RG"
            await page.evaluate(f"""() => {{
                const tds = document.querySelectorAll('td, th, label, span');
                for (const td of tds) {{
                    if (/^\\s*RG\\s*\\*?\\s*$/.test(td.textContent)) {{
                        // pega o próximo input no DOM
                        let el = td.nextElementSibling;
                        while (el && el.tagName !== 'INPUT') {{
                            el = el.querySelector ? el.querySelector('input') : null;
                            if (!el) break;
                        }}
                        if (!el) {{
                            // tenta pelo parentRow
                            const row = td.closest('tr');
                            if (row) el = row.querySelector('input');
                        }}
                        if (el) {{
                            el.focus();
                            el.value = '';
                            el.value = '{pessoa.rg}';
                            el.dispatchEvent(new Event('input', {{bubbles:true}}));
                            el.dispatchEvent(new Event('change', {{bubbles:true}}));
                            el.dispatchEvent(new Event('blur', {{bubbles:true}}));
                        }}
                        break;
                    }}
                }}
            }}""")
            await page.wait_for_timeout(300)
            # Verifica se preencheu
            val = await page.evaluate("""() => {
                const inputs = document.querySelectorAll('input');
                for (const i of inputs) {
                    const row = i.closest('tr');
                    if (row && /RG/.test(row.textContent)) return i.value;
                }
                return '';
            }""")
            if val and val.strip():
                rg_preenchido = True
                logger.info(f"   RG preenchido via JS: '{val}'")
        except Exception as e:
            logger.debug(f"   JS RG falhou: {e}")

        if not rg_preenchido:
            # Estratégia 2: seletores diretos
            for sel_rg in [
                'input[name="entity.nrRg"]', 'input[id="nrRg"]',
                'input[name*="nrRg"]',       'input[id*="nrRg"]',
                'input[name*="Rg"]',         'input[id*="Rg"]',
            ]:
                try:
                    el = page.locator(sel_rg).first
                    if await el.is_visible(timeout=1500):
                        await el.click()
                        await el.fill("")
                        await el.type(pessoa.rg, delay=40)
                        rg_preenchido = True
                        logger.info(f"   RG preenchido via seletor: {sel_rg}")
                        break
                except Exception:
                    continue
        if not rg_preenchido:
            await aguardar_usuario("TJSP — Campo RG não encontrado. Preencha o RG no navegador e pressione ENTER.")
        await page.wait_for_timeout(400)

        # 4b) Gênero — clica no label do radio (ESAJ usa label clicável)
        genero_label = "Masculino" if pessoa.genero == "M" else "Feminino"
        logger.info(f"   Selecionando gênero: {genero_label}")
        genero_selecionado = False

        # Estratégia 1: clica no <label> cujo texto contém Masculino/Feminino
        try:
            lbl = page.locator(f'label:has-text("{genero_label}")').first
            if await lbl.is_visible(timeout=2000):
                await lbl.click()
                genero_selecionado = True
                logger.info(f"   Gênero clicado via label text: {genero_label}")
        except Exception:
            pass

        # Estratégia 2: clica no label associado ao radio via for=
        if not genero_selecionado:
            val_m = ["M", "m", "MASCULINO", "masculino", "1"]
            val_f = ["F", "f", "FEMININO",  "feminino",  "2"]
            vals_genero = val_m if pessoa.genero == "M" else val_f
            for val_g in vals_genero:
                try:
                    radio = page.locator(f'input[type="radio"][value="{val_g}"]').first
                    if await radio.is_visible(timeout=1000):
                        radio_id = await radio.get_attribute("id")
                        if radio_id:
                            lbl2 = page.locator(f'label[for="{radio_id}"]').first
                            if await lbl2.count() > 0:
                                await lbl2.click()
                            else:
                                await radio.click(force=True)
                        else:
                            await radio.click(force=True)
                        genero_selecionado = True
                        logger.info(f"   Gênero selecionado via radio value={val_g}")
                        break
                except Exception:
                    continue

        if not genero_selecionado:
            await aguardar_usuario(f"TJSP — Radio {genero_label} não encontrado. Selecione o gênero no navegador e pressione ENTER.")
        await page.wait_for_timeout(300)

        # 5) Data de nascimento — apenas para Criminal (modelo 6)
        if valor_modelo == "6":
            logger.info(f"   Preenchendo data nascimento: {pessoa.data_nascimento}")
            nascimento_preenchido = False
            for sel in [
                'input[name*="dtNascimento"]', 'input[name*="nascimento"]',
                'input[id*="dtNascimento"]', 'input[id*="nascimento"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=1500):
                        tipo_input = await el.get_attribute("type") or "text"
                        await el.click()
                        await el.fill("")
                        if tipo_input == "date":
                            await el.fill(pessoa.data_nascimento_iso)
                        else:
                            await el.type(pessoa.data_nascimento, delay=40)
                        nascimento_preenchido = True
                        break
                except Exception:
                    continue
            if not nascimento_preenchido:
                await aguardar_usuario("TJSP Criminal — Campo data de nascimento não encontrado. Preencha no navegador e pressione ENTER.")
            await page.wait_for_timeout(400)

        # 6) Nome da mãe
        if pessoa.nome_mae:
            logger.info(f"   Preenchendo nome da mãe: {pessoa.nome_mae}")
            await preencher_campo(page, [
                'input[name*="nmMae"]', 'input[name*="mae"]',
                'input[id*="nmMae"]', 'input[id*="mae"]',
                'input[name*="nomeMae"]',
            ], pessoa.nome_mae, delay=40)
        await page.wait_for_timeout(400)

        # 7) Email (obrigatório no TJSP)
        email_val = pessoa.email or ""
        if email_val:
            logger.info(f"   Preenchendo email: {email_val}")
            if not await tjsp_fill("E-Mail", email_val):
                await preencher_campo(page, [
                    'input[name*="nmEmail"]', 'input[name*="email"]',
                    'input[id*="nmEmail"]',   'input[id*="email"]',
                    'input[type="email"]',
                ], email_val, delay=40)
        else:
            await aguardar_usuario("TJSP — Email não informado mas é obrigatório. Preencha o email no navegador e pressione ENTER.")
        await page.wait_for_timeout(400)

        # 8) Checkbox confirmação
        logger.info("   Marcando checkbox de confirmação...")
        for sel_cb in ['#confirmacaoInformacoes', 'input[name="confirmacaoInformacoes"]']:
            try:
                cb = page.locator(sel_cb).first
                await cb.wait_for(timeout=5000)
                if not await cb.is_checked():
                    await cb.check()
                break
            except Exception:
                continue

        await page.wait_for_timeout(400)

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        # 9) Clica em Enviar
        logger.info("   Clicando em 'Enviar'...")
        for sel_enviar in [
            'input[value*="Enviar"]', 'button:has-text("Enviar")',
            'a:has-text("Enviar")', 'input[type="submit"]',
        ]:
            try:
                el = page.locator(sel_enviar).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    break
            except Exception:
                continue

        await page.wait_for_timeout(8000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        arquivo = await salvar_resultado(page, ctx, downloads, pasta, nome)
        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info(f"✅ [{etapa}] {nome_display} — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [{etapa}] {nome_display} — Erro: {e}")
        await aguardar_usuario(f"❌ {nome_display} — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(
                path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True
            )
        except Exception:
            pass

    return resultado


async def site_tjsp_civil(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    return await _site_tjsp(page, ctx, pessoa, pasta, "civil")


async def site_tjsp_criminal(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    return await _site_tjsp(page, ctx, pessoa, pasta, "criminal")


# ───────────────────────────────────────────────────────────────
#  7. TRF 3ª REGIÃO
# ───────────────────────────────────────────────────────────────

async def site_trf3(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao
    Fluxo: Selects (CIVEL, CPF, TRF) → Preenche CPF e Nome
           → Usuário resolve CAPTCHA e clica Emitir → Salva
    """
    nome = f"{pessoa.primeiro_nome}_trf3"
    resultado = {"site": "TRF 3ª Região", "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info("🔄 [7/8] TRF 3ª Região — Iniciando...")

        await goto_seguro(
            page,
            "https://web.trf3.jus.br/certidao-regional/CertidaoCivelEleitoralCriminal/SolicitarDadosCertidao"
        )
        await aceitar_cookies(page)
        await page.wait_for_timeout(2000)

        # Selects
        logger.info("   Selecionando tipo: CIVEL")
        await page.wait_for_selector("#Tipo", timeout=15000)
        await page.select_option("#Tipo", "CIVEL")
        await page.wait_for_timeout(800)

        logger.info("   Selecionando documento: CPF")
        await page.select_option("#TipoDeDocumento", "CPF")
        await page.wait_for_timeout(800)

        logger.info("   Selecionando abrangência: TRF")
        try:
            await page.select_option("#TipoDeAbrangencia", "TRF")
        except Exception:
            await page.select_option('select[name="Abrangencia"]', "TRF")
        await page.wait_for_timeout(800)

        # CPF — aguarda campo aparecer após os selects e tenta múltiplos seletores
        logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
        await page.wait_for_timeout(500)
        await preencher_campo(page, [
            'input[placeholder="Informe o documento"]',
            'input[placeholder*="documento"]',
            '#NumeroDocumento', 'input[name="NumeroDocumento"]',
            '#Documento', 'input[name="Documento"]',
            '#Cpf', 'input[name="Cpf"]',
            'input[id*="Cpf"]', 'input[id*="cpf"]',
            'input[placeholder*="CPF"]',
        ], pessoa.cpf_limpo, delay=60)
        await page.wait_for_timeout(400)

        # Nome
        logger.info(f"   Preenchendo nome: {pessoa.nome}")
        await preencher_campo(page, [
            '#Nome', 'input[name="Nome"]',
            '#NomeCompleto', 'input[name="NomeCompleto"]',
            'input[id*="Nome"]', 'input[placeholder*="Nome"]',
        ], pessoa.nome, delay=40)
        await page.wait_for_timeout(400)

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        await aguardar_usuario("TRF 3ª Região — Resolva o CAPTCHA e pressione ENTER (o script clicará em Emitir Certidão).")

        # Clica em "Emitir certidão"
        logger.info("   Clicando em 'Emitir certidão'...")
        for sel_emit in [
            'button:has-text("Emitir certidão")',
            'input[type="submit"][value*="Emitir"]',
            'button:has-text("Emitir")',
            'a:has-text("Emitir certidão")',
        ]:
            try:
                el = page.locator(sel_emit).first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    logger.info(f"   Emitir clicado via: {sel_emit}")
                    break
            except Exception:
                continue

        # Aguarda a página da certidão carregar
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # Tira print da tela da certidão
        arquivo = os.path.join(pasta, f"{nome}_{datestamp()}.jpg")
        await page.screenshot(path=arquivo, full_page=True, type="jpeg")
        logger.info(f"   📸 Screenshot salvo: {arquivo}")

        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info("✅ [7/8] TRF 3ª Região — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [7/8] TRF 3ª Região — Erro: {e}")
        await aguardar_usuario(f"❌ TRF 3ª Região — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(
                path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True
            )
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  8. RECEITA FEDERAL — CND
# ───────────────────────────────────────────────────────────────

async def site_receita_federal(page: Page, ctx: BrowserContext, pessoa: Pessoa, pasta: str) -> dict:
    """
    https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cpf
    Fluxo: Preenche CPF → Preenche Data de Nascimento → Clica Emitir → Salva
    ATENÇÃO: Site Angular — não usa networkidle; aguarda componentes aparecerem.
    """
    nome = f"{pessoa.primeiro_nome}_rf"
    resultado = {"site": "Receita Federal - CND", "sucesso": False, "arquivo": None, "erro": None}

    try:
        logger.info("🔄 [8/8] Receita Federal — Iniciando...")

        # Usa domcontentloaded: Angular nunca atinge networkidle
        await page.goto(
            "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cpf",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await aceitar_cookies(page)

        # ── CPF ──────────────────────────────────────────────────────
        logger.info("   Aguardando campo CPF...")
        campo_cpf = None
        for sel_cpf in [
            'input[name="niContribuinte"]',
            'input[placeholder*="CPF"]',
            'input[placeholder*="Informe o CPF"]',
            'input[maxlength="14"][type="text"]',
        ]:
            try:
                el = page.locator(sel_cpf).first
                await el.wait_for(state="visible", timeout=30000)
                campo_cpf = el
                logger.info(f"   Campo CPF encontrado via: {sel_cpf}")
                break
            except Exception:
                continue

        if not campo_cpf:
            await aguardar_usuario("Receita Federal — Campo CPF não encontrado. Preencha o CPF no navegador e pressione ENTER.")
        else:
            logger.info(f"   Preenchendo CPF: {pessoa.cpf_formatado}")
            # Clica, seleciona tudo via keyboard e apaga antes de digitar
            await campo_cpf.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(200)
            # Digita dígito a dígito — a máscara Angular aplica formatação
            for digito in pessoa.cpf_limpo:
                await page.keyboard.type(digito, delay=100)
            await page.keyboard.press("Tab")   # dispara blur/change do Angular
            await page.wait_for_timeout(600)
            val_cpf = await campo_cpf.input_value()
            logger.info(f"   CPF no campo: '{val_cpf}'")

        # ── Data de Nascimento ────────────────────────────────────────
        logger.info(f"   Preenchendo data nascimento: {pessoa.data_nascimento}")
        campo_data = None
        for sel_data in [
            'input[name="dataNascimento"]',
            'input[placeholder*="nascimento"]',
            'input[placeholder*="Informe a data"]',
            'input[maxlength="10"][autocomplete="off"]',
        ]:
            try:
                el = page.locator(sel_data).first
                if await el.is_visible(timeout=8000):
                    campo_data = el
                    logger.info(f"   Campo data encontrado via: {sel_data}")
                    break
            except Exception:
                continue

        if not campo_data:
            await aguardar_usuario("Receita Federal — Campo Data de Nascimento não encontrado. Preencha no navegador e pressione ENTER.")
        else:
            await campo_data.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(200)
            await page.keyboard.type(pessoa.data_nascimento, delay=80)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(600)

        # ── Emitir Certidão ───────────────────────────────────────────
        await page.wait_for_timeout(500)
        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        logger.info("   Clicando em 'Emitir Certidão'...")
        emitiu = False
        for sel_emit in [
            'button:has-text("Emitir Certidão")',
            'button:has-text("Emitir")',
            'a:has-text("Emitir Certidão")',
            'input[value*="Emitir Certidão"]',
        ]:
            try:
                el = page.locator(sel_emit).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    emitiu = True
                    logger.info(f"   Emitir clicado via: {sel_emit}")
                    break
            except Exception:
                continue

        if not emitiu:
            await aguardar_usuario("Receita Federal — Botão 'Emitir Certidão' não encontrado. Clique no navegador e pressione ENTER.")

        # Aguarda resposta
        await page.wait_for_timeout(10000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        arquivo = await salvar_resultado(page, ctx, downloads, pasta, nome)
        resultado.update({"sucesso": True, "arquivo": arquivo})
        logger.info("✅ [8/8] Receita Federal — Concluído!")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"❌ [8/8] Receita Federal — Erro: {e}")
        await aguardar_usuario(f"❌ Receita Federal — Erro: {e}\n  Resolva no navegador se possível e pressione ENTER para continuar.")
        try:
            await page.screenshot(
                path=os.path.join(pasta, f"ERRO_{nome}_{timestamp()}.png"), full_page=True
            )
        except Exception:
            pass

    return resultado


# ───────────────────────────────────────────────────────────────
#  COLETA DE DADOS
# ───────────────────────────────────────────────────────────────

def _ler_campo(prompt: str, atual: str = "") -> str:
    """Lê um campo, exibindo o valor atual entre colchetes para edição."""
    if atual:
        val = input(f"  {prompt} [{atual}]: ").strip()
        return val if val else atual
    return input(f"  {prompt}: ").strip()


def _formatar_data(raw: str) -> str:
    """Tenta converter 28111988, 2811981, etc. em 28/11/1988."""
    raw = raw.replace("/", "").replace("-", "").replace(".", "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:2]}/{raw[2:4]}/{raw[4:]}"
    return raw  # devolve como está se não reconhecer


def coletar_dados() -> Pessoa:
    print("\n" + "═" * 62)
    print("  📋  COLETA DE DADOS DA PESSOA")
    print("═" * 62)

    # Valores iniciais (vazios na primeira vez)
    nome = cpf_raw = rg = data_nasc = genero_raw = nome_mae = email = ""

    while True:
        print()
        # ── Nome
        novo = _ler_campo("Nome completo", nome).upper()
        if novo:
            nome = novo

        # ── CPF
        while True:
            novo = _ler_campo("CPF (somente números)", cpf_raw).replace(".", "").replace("-", "")
            if len(novo) == 11 and novo.isdigit():
                cpf_raw = novo
                break
            print("  ⚠️  CPF inválido — deve ter 11 dígitos numéricos.")

        # ── RG
        novo = _ler_campo("RG (somente números)", rg).replace(".", "").replace("-", "")
        if novo:
            rg = novo

        # ── Data de nascimento
        while True:
            raw_data = _ler_campo("Data de nascimento (DD/MM/AAAA)", data_nasc)
            raw_data = _formatar_data(raw_data)
            try:
                datetime.strptime(raw_data, "%d/%m/%Y")
                data_nasc = raw_data
                break
            except ValueError:
                print(f"  ⚠️  Data inválida ('{raw_data}') — use DD/MM/AAAA ou DDMMAAAA.")

        # ── Gênero
        while True:
            novo = _ler_campo("Gênero (M/F)", genero_raw).upper()
            if novo in ("M", "F"):
                genero_raw = novo
                break
            print("  ⚠️  Digite M para Masculino ou F para Feminino.")

        # ── Nome da mãe
        novo = _ler_campo("Nome da mãe (Enter para pular)", nome_mae).upper()
        if novo:
            nome_mae = novo

        # ── Email
        novo = _ler_campo("Email (Enter para pular)", email).lower()
        if novo:
            email = novo

        pessoa = Pessoa(
            nome=nome,
            cpf=cpf_raw,
            rg=rg,
            data_nascimento=data_nasc,
            genero=genero_raw,
            nome_mae=nome_mae if nome_mae else None,
            email=email if email else None,
        )

        print(f"\n  {'─'*58}")
        print(f"  Nome:   {pessoa.nome}")
        print(f"  CPF:    {pessoa.cpf_formatado}")
        print(f"  RG:     {pessoa.rg}")
        print(f"  Nasc:   {pessoa.data_nascimento}")
        print(f"  Gênero: {'Masculino' if pessoa.genero == 'M' else 'Feminino'}")
        print(f"  Mãe:    {pessoa.nome_mae or '(não informado)'}")
        print(f"  Email:  {pessoa.email or '(não informado)'}")
        print(f"  {'─'*58}")

        ok = input("\n  Dados corretos? (S/N): ").strip().upper()
        if ok == "S":
            return pessoa
        print("  Corrija os campos necessários (Enter mantém o valor atual).\n")


def selecionar_sites() -> list:
    opcoes = {
        "1": ("Protesto SP",                   site_protesto_sp),
        "2": ("TRT 15 — CEAT",                 site_trt15),
        "3": ("TST",                            site_tst),
        "4": ("Dívida Ativa PGE/SP",            site_divida_ativa_sp),
        "5": ("TJSP — Distribuição Cível",      site_tjsp_civil),
        "6": ("TJSP — Distribuição Criminal",   site_tjsp_criminal),
        "7": ("TRF 3ª Região",                  site_trf3),
        "8": ("Receita Federal — CND",          site_receita_federal),
    }

    print("\n" + "═" * 62)
    print("  📄  SELECIONE AS CERTIDÕES")
    print("═" * 62)
    for num, (desc, _) in opcoes.items():
        print(f"  {num}. {desc}")
    print("  0. TODAS")
    print()

    escolha = input("  Opções (ex: 1,3,5 ou 0 para todas): ").strip()

    if escolha == "0":
        return list(opcoes.values())

    selecionados = []
    for num in escolha.replace(" ", "").split(","):
        if num in opcoes:
            selecionados.append(opcoes[num])

    if not selecionados:
        print("  Nenhuma seleção válida. Emitindo todas.")
        return list(opcoes.values())

    print("\n  Selecionados:")
    for desc, _ in selecionados:
        print(f"    ✅ {desc}")

    return selecionados


# ───────────────────────────────────────────────────────────────
#  ORQUESTRADOR PRINCIPAL
# ───────────────────────────────────────────────────────────────

async def executar(pessoa: Pessoa, sites: list):
    pasta = criar_pasta(pessoa.nome)
    logger.info(f"📁 Pasta de downloads: {pasta}")

    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-maximized",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
            locale="pt-BR",
        )

        # Oculta o webdriver para reduzir detecção
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        total = len(sites)
        for i, (desc, func) in enumerate(sites, 1):
            print(f"\n{'━'*62}")
            print(f"  [{i}/{total}] {desc}")
            print(f"{'━'*62}")

            page = await context.new_page()

            try:
                resultado = await func(page, context, pessoa, pasta)
                resultados.append(resultado)
            except Exception as e:
                logger.error(f"Erro fatal em {desc}: {e}")
                resultados.append({
                    "site": desc,
                    "sucesso": False,
                    "arquivo": None,
                    "erro": str(e),
                })
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

            if i < total:
                await asyncio.sleep(2)

        await browser.close()

    return resultados


# ───────────────────────────────────────────────────────────────
#  RELATÓRIO FINAL
# ───────────────────────────────────────────────────────────────

def exibir_relatorio(resultados: list, pessoa: Pessoa):
    pasta = criar_pasta(pessoa.nome)

    print("\n" + "═" * 62)
    print("  📊  RELATÓRIO FINAL")
    print("═" * 62)
    print(f"  Pessoa: {pessoa.nome}")
    print(f"  CPF:    {pessoa.cpf_formatado}")
    print(f"  Data:   {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Pasta:  {pasta}")
    print("─" * 62)

    ok  = sum(1 for r in resultados if r["sucesso"])
    err = len(resultados) - ok

    for r in resultados:
        icone = "✅" if r["sucesso"] else "❌"
        print(f"\n  {icone}  {r['site']}")
        if r["arquivo"]:
            print(f"      📄 {os.path.basename(r['arquivo'])}")
        if r["erro"]:
            msg = r["erro"][:120] + "..." if len(r["erro"]) > 120 else r["erro"]
            print(f"      ⚠️  {msg}")

    print(f"\n{'─'*62}")
    print(f"  Total: {len(resultados)} | ✅ {ok} | ❌ {err}")
    print(f"{'═'*62}")

    relatorio = {
        "pessoa": {"nome": pessoa.nome, "cpf": pessoa.cpf_formatado},
        "data": datetime.now().isoformat(),
        "resultados": resultados,
        "totais": {"total": len(resultados), "sucesso": ok, "erros": err},
    }

    json_path = os.path.join(pasta, f"relatorio_{timestamp()}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    print(f"\n  📋 Relatório salvo: {json_path}\n")


# ───────────────────────────────────────────────────────────────
#  PONTO DE ENTRADA
# ───────────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 62)
    print("  🏛️   AUTOMAÇÃO DE CERTIDÕES NEGATIVAS  v2.0")
    print("═" * 62)

    pessoa = coletar_dados()
    sites  = selecionar_sites()

    print(f"\n  🚀 Iniciando automação para: {pessoa.nome}")
    print(f"  ⚠️  NÃO feche o navegador!")
    print(f"  ⚠️  Quando solicitado, resolva CAPTCHAs no navegador")
    print(f"      e pressione ENTER no terminal.\n")

    input("  Pressione ENTER para começar...")

    resultados = await executar(pessoa, sites)
    exibir_relatorio(resultados, pessoa)


if __name__ == "__main__":
    asyncio.run(main())
