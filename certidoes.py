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

from utils import timestamp, datestamp, criar_pasta, _formatar_data

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
        partes = self.nome.split()
        if not partes:
            return ""
        n = partes[0].lower()
        return ''.join(
            c for c in unicodedata.normalize('NFD', n)
            if unicodedata.category(c) != 'Mn'
        )


# ───────────────────────────────────────────────────────────────
#  FUNÇÕES UTILITÁRIAS
# ───────────────────────────────────────────────────────────────

from utils import timestamp, datestamp, criar_pasta, _formatar_data

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
    """Pausa e aguarda ENTER do usuário."""
    import sys
    print(f"\n[PAUSA] {mensagem}")
    print(f"➜ Aguardando interação manual no navegador...")
    if not sys.stdin.isatty():
        logger.warning("Ambiente sem TTY. Aguardando 15s automaticamente.")
        await asyncio.sleep(15)
        return
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input)
    except EOFError:
        logger.warning("EOF detectado. Aguardando 15s automaticamente.")
        await asyncio.sleep(15)
    return

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
    Salva o resultado da certidão com prioridade para PDF, nova aba ou print de página inteira.
    """
    await page.wait_for_timeout(3500)

    # 1) Verifica downloads capturados
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

    # 2) Verifica se o PDF abriu em nova aba (blob ou PDF viewer)
    for p in context.pages:
        if p != page:
            try:
                # Rolagem para garantir renderização antes do print
                await p.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await p.wait_for_timeout(500)
                await p.evaluate("window.scrollTo(0, 0)")
                
                arquivo = os.path.join(pasta, f"{nome_base}_{datestamp()}.jpg")
                await p.screenshot(path=arquivo, full_page=True, type="jpeg", quality=90)
                logger.info(f"   📸 Screenshot de nova aba (página inteira): {arquivo}")
                return arquivo
            except Exception:
                continue

    # 3) Print da página atual como último recurso
    # Rolagem para garantir renderização
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(500)
    await page.evaluate("window.scrollTo(0, 0)")
    
    arquivo = os.path.join(pasta, f"{nome_base}_{datestamp()}.jpg")
    await page.screenshot(path=arquivo, full_page=True, type="jpeg", quality=90)
    logger.info(f"   📸 Screenshot salvo (página inteira): {arquivo}")
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
        await aguardar_usuario("CENPROT — Resolva o CAPTCHA no navegador (se aparecer) e pressione ENTER aqui.")

        await page.wait_for_timeout(2000)
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

        # AGUARDA RESULTADO APARECER (Evita print da página de busca)
        logger.info("   Aguardando tabela de resultados...")
        try:
            await page.wait_for_selector(".table-responsive, #resultado-consulta, .card-body", timeout=15000)
        except Exception:
            pass
        
        await page.wait_for_timeout(4000)

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

    try:
        logger.info("🔄 [3/8] TST — Iniciando...")

        await goto_seguro(page, "https://www.tst.jus.br/certidao1")
        await aceitar_cookies(page)
        await page.wait_for_timeout(2000)

        # Clica em "Emitir Certidão" para abrir o formulário
        logger.info("   Abrindo formulário do TST...")
        for sel in ['a:has-text("Emitir Certidão")', 'button:has-text("Emitir Certidão")']:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=5000):
                    await el.click()
                    break
            except Exception:
                continue

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
            await campo_cpf.focus()
            await page.wait_for_timeout(500)
            await campo_cpf.press("Control+A")
            await campo_cpf.press("Backspace")
            await campo_cpf.type(pessoa.cpf_limpo, delay=120)
            await page.wait_for_timeout(1000)
            await campo_cpf.press("Tab")
        else:
            await aguardar_usuario("TST — Campo CPF não encontrado. Preencha o CPF no navegador e pressione ENTER.")

        downloads: List[Download] = []
        page.on("download", lambda d: downloads.append(d))

        await aguardar_usuario("TST — Resolva o desafio e pressione ENTER (o script clicará em Emitir Certidão).")

        # Clica em "Emitir Certidão" para gerar o PDF
        logger.info("   Clicando em 'Emitir Certidão'...")
        emitiu = False
        for frame in page.frames:
            for sel in [
                'a:has-text("Emitir Certidão")',
                'button:has-text("Emitir Certidão")',
                'button:has-text("Emitir")',
                'input[value*="Emitir"]',
            ]:
                try:
                    el = frame.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        logger.info(f"   Emitir clicado via iframe: {sel}")
                        emitiu = True
                        break
                except Exception:
                    continue
            if emitiu:
                break
                
        if not emitiu:
            # Fallback para tentar na página principal caso não ache no frame
            for sel in [
                'a:has-text("Emitir Certidão")',
                'button:has-text("Emitir Certidão")',
                'button:has-text("Emitir")',
                'input[value*="Emitir"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        await el.click()
                        logger.info(f"   Emitir clicado via página principal: {sel}")
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
                    def write_pdf():
                        with open(arquivo, "wb") as f:
                            f.write(bytes(pdf_bytes))
                    await asyncio.to_thread(write_pdf)
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
        
        # Tempo extra para o CAPTCHA carregar/estabilizar
        logger.info("   Aguardando carregamento do CAPTCHA...")
        await page.wait_for_timeout(4000)

        # Usuário resolve CAPTCHA
        await aguardar_usuario("Dívida Ativa PGE/SP — Resolva o CAPTCHA no navegador e pressione ENTER.")

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
            await page.evaluate("""(rgValue) => {
                const tds = document.querySelectorAll('td, th, label, span');
                for (const td of tds) {
                    if (/^\\s*RG\\s*\\*?\\s*$/.test(td.textContent)) {
                        // pega o próximo input no DOM
                        let el = td.nextElementSibling;
                        while (el && el.tagName !== 'INPUT') {
                            el = el.querySelector ? el.querySelector('input') : null;
                            if (!el) break;
                        }
                        if (!el) {
                            // tenta pelo parentRow
                            const row = td.closest('tr');
                            if (row) el = row.querySelector('input');
                        }
                        if (el) {
                            el.focus();
                            el.value = '';
                            el.value = rgValue;
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            el.dispatchEvent(new Event('change', {bubbles:true}));
                            el.dispatchEvent(new Event('blur', {bubbles:true}));
                        }
                        break;
                    }
                }
            }""", pessoa.rg)
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
    if not pessoa.data_nascimento or not pessoa.nome_mae:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("⏭️ [6/8] TJSP Criminal — Ignorada (Data de Nascimento ou Nome da Mãe não informados).")
        return {"site": "TJSP 1ª Instância (Criminal)", "sucesso": True, "arquivo": "IGNORADA", "erro": None}
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

        # Trata Cloudflare ou carregamento inicial
        logger.info("   Aguardando carregamento da página ou desafio Cloudflare...")
        tentativas = 0
        while True:
            try:
                await page.wait_for_selector("#Tipo", timeout=10000)
                break  # Elemento encontrado, sai do loop
            except Exception:
                tentativas += 1
                if tentativas > 3:
                    raise Exception("Falha repetida ao tentar contornar o Cloudflare ou carregar a página.")
                await aguardar_usuario("TRF 3ª Região — Desafio Cloudflare detectado. Resolva a verificação ('Sou Humano') no navegador, aguarde a página carregar e pressione ENTER aqui no terminal.")

        # Selects
        logger.info("   Selecionando tipo: CIVEL")
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

    if not pessoa.data_nascimento:
        logger.info("⏭️ [8/8] Receita Federal — Ignorada (Data de Nascimento não informada).")
        resultado.update({"sucesso": True, "arquivo": "IGNORADA", "erro": None})
        return resultado

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
        
        # Simula movimento de mouse aleatório para evitar detecção
        await page.mouse.move(100, 100)
        await page.mouse.move(200, 300, steps=10)
        
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
            await campo_cpf.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(400)
            
            # Digitação ainda mais lenta para a Receita
            for digito in pessoa.cpf_limpo:
                await page.keyboard.type(digito, delay=150)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(800)
        
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
            
            # Para campos Angular com máscara, fill() garante a inserção direta do valor sem conflitos
            await campo_data.fill(pessoa.data_nascimento)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(600)

        # Pausa obrigatória para CAPTCHA na Receita (sempre tem desafio de imagem/clique)
        await aguardar_usuario("Receita Federal — Resolva o desafio de segurança (CAPTCHA) no navegador e pressione ENTER.")
        
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


def coletar_dados() -> Pessoa:
    print("\n" + "═" * 62)
    print("  📋  COLETA DE DADOS DA PESSOA")
    print("═" * 62)

    # Injeção Orion Hub (Auto-preenchimento)
    env_nome = os.getenv("AUTO_NOME")
    env_cpf = os.getenv("AUTO_CPF")
    if env_nome and env_cpf:
        logger.info(f"🚀 [Orion Hub] Auto-preenchimento: {env_nome}")
        return Pessoa(
            nome=env_nome.upper(),
            cpf=env_cpf,
            rg=os.getenv("AUTO_RG", ""),
            data_nascimento=os.getenv("AUTO_NASC", ""),
            genero=os.getenv("AUTO_GENERO", "M").upper(),
            nome_mae=os.getenv("AUTO_MAE", "").upper() or None,
            email=os.getenv("AUTO_EMAIL", "").lower() or None
        )

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
            nome=nome.upper().upper(),
            cpf=cpf_raw,
            rg=rg.upper().upper(),
            data_nascimento=data_nasc,
            genero=genero_raw.upper(),
            nome_mae=nome_mae.upper() if nome_mae else None,
            email=email.lower().lower() if email else None,
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


async def exibir_relatorio(resultados: list, pessoa: Pessoa):
    """Gera o relatório final em JSON e exibe o resumo no terminal."""
    pasta = criar_pasta(pessoa.nome)
    relatorio = {
        "pessoa": {"nome": pessoa.nome, "cpf": pessoa.cpf_formatado},
        "data": datetime.now().isoformat(),
        "resultados": resultados,
        "totais": {
            "total": len(resultados), 
            "sucesso": sum(1 for r in resultados if r["sucesso"]),
            "erros": sum(1 for r in resultados if not r["sucesso"])
        },
    }
    json_path = os.path.join(pasta, f"relatorio_{timestamp()}.json")
    
    def salvar_json():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)
    
    await asyncio.to_thread(salvar_json)
    
    print("\n" + "═" * 62)
    print("  📊  RELATÓRIO FINAL")
    print("═" * 62)
    print(f"  Pessoa: {pessoa.nome}")
    print(f"  Pasta:  {pasta}")
    print("─" * 62)
    for r in resultados:
        icon = "✅" if r["sucesso"] else "❌"
        print(f"  {icon}  {r['site']}")
        if r["erro"]:
            print(f"      ⚠️  {r['erro'][:80]}...")
    print(f"{'═'*62}\n  📋 Relatório salvo em: {json_path}\n")

# ───────────────────────────────────────────────────────────────
#  DASHBOARD E PERSISTÊNCIA DE SESSÃO
# ───────────────────────────────────────────────────────────────

class GerenciadorSessao:
    def __init__(self, pessoa: Pessoa, status: dict):
        self.pessoa = pessoa
        self.pasta = criar_pasta(pessoa.nome)
        self.caminho_status = os.path.join(self.pasta, ".status_sessao.json")
        self.status = status

    @classmethod
    async def inicializar(cls, pessoa: Pessoa) -> 'GerenciadorSessao':
        pasta = criar_pasta(pessoa.nome)
        caminho_status = os.path.join(pasta, ".status_sessao.json")
        status = await cls._carregar_ou_criar_async(caminho_status)
        return cls(pessoa, status)

    @staticmethod
    async def _carregar_ou_criar_async(caminho_status: str) -> dict:
        def read_file():
            if os.path.exists(caminho_status):
                try:
                    with open(caminho_status, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return None
            
        status = await asyncio.to_thread(read_file)
        if status is not None:
            return status

        # Estado inicial se não existir
        return {
            "sites": {
                "1": {"nome": "Protesto SP", "status": "PENDENTE", "arquivo": None, "erro": None},
                "2": {"nome": "TRT 15 — CEAT", "status": "PENDENTE", "arquivo": None, "erro": None},
                "3": {"nome": "TST", "status": "PENDENTE", "arquivo": None, "erro": None},
                "4": {"nome": "Dívida Ativa PGE/SP", "status": "PENDENTE", "arquivo": None, "erro": None},
                "5": {"nome": "TJSP — Distribuição Cível", "status": "PENDENTE", "arquivo": None, "erro": None},
                "6": {"nome": "TJSP — Distribuição Criminal", "status": "PENDENTE", "arquivo": None, "erro": None},
                "7": {"nome": "TRF 3ª Região", "status": "PENDENTE", "arquivo": None, "erro": None},
                "8": {"nome": "Receita Federal — CND", "status": "PENDENTE", "arquivo": None, "erro": None},
            }
        }

    async def salvar(self):
        def write_file():
            with open(self.caminho_status, "w", encoding="utf-8") as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        await asyncio.to_thread(write_file)

    def obter_func_map(self):
        return {
            "1": site_protesto_sp,
            "2": site_trt15,
            "3": site_tst,
            "4": site_divida_ativa_sp,
            "5": site_tjsp_civil,
            "6": site_tjsp_criminal,
            "7": site_trf3,
            "8": site_receita_federal,
        }

class Dashboard:
    def __init__(self, sessao: GerenciadorSessao):
        self.sessao = sessao
        self.func_map = sessao.obter_func_map()

    def exibir(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "═" * 65)
        print("  📊  DASHBOARD DE CERTIDÕES (SESSÃO PERSISTENTE)")
        print("═" * 65)
        print(f"  Pessoa: {self.sessao.pessoa.nome}")
        print(f"  CPF:    {self.sessao.pessoa.cpf_formatado}")
        print(f"  Pasta:  {self.sessao.pasta}")
        print("─" * 65)
        
        for id, info in self.sessao.status["sites"].items():
            icon = "⚪" if info["status"] == "PENDENTE" else ("✅" if info["status"] == "OK" else "❌")
            status_color = info["status"]
            print(f"  {id}. [{icon}] {status_color:<9} | {info['nome']}")
            if info["erro"]:
                print(f"      ⚠️  Erro: {info['erro'][:70]}...")
        
        print("─" * 65)
        print("  0. 🚀 EXECUTAR TODAS AS PENDENTES (Lote)")
        print("  R. 🔄 REPETIR APENAS AS QUE FALHARAM")
        print("  S. 🏁 FINALIZAR E GERAR RELATÓRIO")
        print("═" * 65)

    async def executar_um(self, site_id, context):
        info = self.sessao.status["sites"][site_id]
        func = self.func_map[site_id]

        print(f"\n  ▶ Processando: {info['nome']}...")
        page = await context.new_page()
        
        try:
            res = await func(page, context, self.sessao.pessoa, self.sessao.pasta)
            arquivo_gerado = res.get("arquivo")
            # Valida se o arquivo existe e não está vazio/corrompido, ou se foi ignorado
            if arquivo_gerado == "IGNORADA":
                sucesso_real = True
            else:
                sucesso_real = res["sucesso"] and arquivo_gerado and os.path.exists(arquivo_gerado) and os.path.getsize(arquivo_gerado) > 5000

            if sucesso_real:
                info["status"] = "OK"
                info["arquivo"] = arquivo_gerado
                info["erro"] = None
            else:
                info["status"] = "ERRO"
                info["erro"] = res.get("erro") or "Arquivo não gerado ou inválido (muito pequeno)."
        except Exception as e:
            info["status"] = "ERRO"
            info["erro"] = str(e)
            logger.error(f"Falha fatal em {info['nome']}: {e}")
        finally:
            await page.close()
            await self.sessao.salvar()

    async def loop(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                executable_path="/usr/bin/google-chrome-stable",
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"],
            )
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                accept_downloads=True,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                permissions=["geolocation", "notifications"],
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False
            )

            while True:
                self.exibir()

                if os.getenv("AUTO_NOME"):
                    if os.getenv("AUTO_FORCE") == "1":
                        pendentes = [id for id, s in self.sessao.status["sites"].items()]
                    else:
                        pendentes = [id for id, s in self.sessao.status["sites"].items() if s["status"] != "OK"]
                        
                    if os.getenv("AUTO_SITES"):
                        permitidos = [s.strip() for s in os.getenv("AUTO_SITES").split(",")]
                        pendentes = [id for id in pendentes if id in permitidos]
                    
                    if pendentes:
                        opcao = "0"
                        print("\n  [Orion Hub] Auto-executando pendentes permitidos (Opção 0)...")
                    else:
                        opcao = "S"
                        print("\n  [Orion Hub] Concluído, finalizando sessão (Opção S)...")
                else:
                    opcao = input("\n  Escolha (ID, 0, R ou S): ").strip().upper()

                if opcao == "S":
                    break

                alvos = []
                if opcao == "0":
                    if os.getenv("AUTO_NOME") and os.getenv("AUTO_FORCE") == "1":
                        alvos = [id for id, s in self.sessao.status["sites"].items()]
                    else:
                        alvos = [id for id, s in self.sessao.status["sites"].items() if s["status"] != "OK"]
                        
                    if os.getenv("AUTO_NOME") and os.getenv("AUTO_SITES"):
                        permitidos = [s.strip() for s in os.getenv("AUTO_SITES").split(",")]
                        alvos = [id for id in alvos if id in permitidos]
                elif opcao == "R":
                    alvos = [id for id, s in self.sessao.status["sites"].items() if s["status"] == "ERRO"]
                elif opcao in self.sessao.status["sites"]:
                    alvos = [opcao]

                if alvos:
                    for id in alvos:
                        await self.executar_um(id, context)
                    if not os.getenv("AUTO_NOME"):
                        input("\n  ✅ Fim da sequência. ENTER para voltar ao Dashboard...")            
            await browser.close()
        
        await self.finalizar()

    async def finalizar(self):
        resultados = []
        for id, info in self.sessao.status["sites"].items():
            resultados.append({
                "site": info["nome"],
                "sucesso": info["status"] == "OK",
                "arquivo": info["arquivo"],
                "erro": info["erro"]
            })
        await exibir_relatorio(resultados, self.sessao.pessoa)

async def main():
    print("\n" + "═" * 62)
    print("  🏛️   AUTOMAÇÃO DE CERTIDÕES NEGATIVAS  v2.5")
    print("═" * 62)

    pessoa = coletar_dados()
    sessao = await GerenciadorSessao.inicializar(pessoa)
    dash = Dashboard(sessao)
    await dash.loop()

if __name__ == "__main__":
    asyncio.run(main())
