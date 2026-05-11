import os
import re
import sys
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Configurações globais
EMAIL_PADRAO = "vgiattiimoveis@outlook.com"
CERTIDOES_SCRIPT = Path(__file__).parent / "certidoes.py"

def extract_sellers_from_txt(filepath):
    """
    Extrai as qualificações dos vendedores de um contrato padrão.
    Suporta arquivos .txt e .docx.
    Procura a seção "1. VENDEDORES" e para na próxima seção "2. COMPRADORES".
    """
    content = ""
    try:
        if filepath.lower().endswith('.docx'):
            with zipfile.ZipFile(filepath) as docx:
                xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                paras = []
                for p in tree.findall('.//w:p', namespaces):
                    texts = p.findall('.//w:t', namespaces)
                    if texts:
                        paras.append("".join([t.text for t in texts if t.text]))
                content = "\n".join(paras)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo: {e}")
        return []

    # Localiza a seção de vendedores
    match_vendedores = re.search(r'(?:1\.\s*)?VENDEDOR(?:ES|A)(.*?)(?:(?:2\.\s*)?COMPRADOR(?:ES|AS|A)|\Z)', content, re.IGNORECASE | re.DOTALL)
    if not match_vendedores:
        print("❌ Não foi possível encontrar a seção '1. VENDEDORES' no contrato.")
        return []
    
    texto_vendedores = match_vendedores.group(1)
    
    # Regex para capturar pessoas (Nome, RG, CPF)
    # Exemplo: VINICIUS DORIGON FAVORETTO, brasileiro, autônomo, portador do RG nº 35.150.104 e do CPF nº 326.602.878-30
    pattern_pessoa = re.compile(
        r'([A-ZÀ-Ú\s]+),\s*brasileir[oa],\s*[^,]+,\s*.*?RG.*?([\d\.\-]+)\s*e.*?CPF.*?([\d\.\-]+)',
        re.IGNORECASE | re.DOTALL
    )
    
    pessoas = []
    # Usando finditer para pegar múltiplas pessoas no texto (casais na mesma linha, etc)
    for match in pattern_pessoa.finditer(texto_vendedores):
        nome = match.group(1).strip()
        # Limpar quebras de linha e espaços extras no nome
        nome = re.sub(r'\s+', ' ', nome)
        # Limpar prefixos de casamento
        nome = re.sub(r'^.*?\bcom\s+', '', nome, flags=re.IGNORECASE).strip()
        rg = match.group(2).strip()
        cpf = match.group(3).strip()
        
        # Inferência simples de gênero pelo final do primeiro nome ou por palavras chave próximas
        genero = "F" if nome.split()[0].endswith("A") or nome.split()[0].endswith("IA") else "M"
        
        pessoas.append({
            "nome": nome,
            "rg": rg,
            "cpf": cpf,
            "genero": genero,
            "data_nascimento": "", # Precisamos coletar
            "email": EMAIL_PADRAO
        })
    
    # Remover duplicados caso o regex falhe de alguma forma
    seen_cpfs = set()
    unique_pessoas = []
    for p in pessoas:
        clean_cpf = re.sub(r'\D', '', p["cpf"])
        if clean_cpf not in seen_cpfs:
            seen_cpfs.add(clean_cpf)
            unique_pessoas.append(p)

    return unique_pessoas

def main():
    print("="*60)
    print(" 🚀 VGIATTI - GERADOR DE CERTIDÕES EM LOTE (VENDEDORES) ")
    print("="*60)
    
    if len(sys.argv) != 2:
        print("Uso: python executar_lote_vendedores.py <caminho_do_contrato.txt>")
        sys.exit(1)
        
    contrato_path = sys.argv[1]
    if not os.path.exists(contrato_path):
        print(f"❌ Arquivo não encontrado: {contrato_path}")
        sys.exit(1)
        
    print(f"\n📄 Analisando contrato: {contrato_path}")
    vendedores = extract_sellers_from_txt(contrato_path)
    
    if not vendedores:
        print("⚠️ Nenhum vendedor encontrado com o padrão esperado.")
        sys.exit(0)
        
    print(f"\n✅ {len(vendedores)} vendedores identificados:")
    for i, v in enumerate(vendedores, 1):
        print(f"  {i}. Nome:   {v['nome']}")
        print(f"     CPF:    {v['cpf']}")
        print(f"     RG:     {v['rg']}")
        print(f"     Gênero: {'Masculino' if v['genero'] == 'M' else 'Feminino'}")
        print(f"     Email:  {v['email']}")
        print("     " + "-"*40)
        
    print("\n" + "="*60)
    print(" 👥 SELEÇÃO DE VENDEDORES ")
    print("="*60)
    print("Digite os NÚMEROS dos vendedores que deseja processar (ex: 1,3,4).")
    print("Para processar TODOS, apenas pressione ENTER.")
    
    escolha_vendedores = input("👉 Suas escolhas [TODOS]: ").strip()
    vendedores_selecionados = []
    
    if escolha_vendedores:
        indices = [int(s.strip()) for s in escolha_vendedores.split(",") if s.strip().isdigit()]
        for idx in indices:
            if 1 <= idx <= len(vendedores):
                vendedores_selecionados.append(vendedores[idx-1])
        if not vendedores_selecionados:
            print("⚠️ Nenhum vendedor válido selecionado. Encerrando.")
            sys.exit(0)
    else:
        vendedores_selecionados = vendedores
    
    # Coletar Datas de Nascimento e Nome da Mãe (Opcionais)
    print("\n⚠️ Se não informar a Data de Nascimento ou Nome da Mãe, a Criminal e a Receita Federal poderão ser IGNORADAS.")
    print("Por favor, informe os dados ou aperte ENTER para pular:")
    
    for v in vendedores_selecionados:
        while True:
            nasc = input(f"  [{v['cpf']}] {v['nome']} -> Nasc (opcional DD/MM/AAAA): ").strip()
            if not nasc:
                v["data_nascimento"] = ""
                break
            elif re.match(r'^\d{2}/\d{2}/\d{4}$', nasc):
                v["data_nascimento"] = nasc
                break
            else:
                print("  ❌ Formato inválido. Use DD/MM/AAAA ou aperte ENTER vazio.")
        
        mae = input(f"  [{v['cpf']}] {v['nome']} -> Nome da Mãe (opcional): ").strip()
        v["nome_mae"] = mae.upper() if mae else ""

    print("\n" + "="*60)
    print(" 🎯 SELEÇÃO DE CERTIDÕES ")
    print("="*60)
    print("  1. Protesto SP (CENPROT)")
    print("  2. TRT 15 (Trabalhista Interior)")
    print("  3. TST (Trabalhista Nacional)")
    print("  4. Dívida Ativa SP (PGE)")
    print("  5. TJSP Cível")
    print("  6. TJSP Criminal")
    print("  7. TRF 3ª Região")
    print("  8. Receita Federal")
    print("-" * 60)
    print("Digite os NÚMEROS das certidões desejadas separados por vírgula (ex: 1,5,7,8).")
    print("Para emitir TODAS, apenas pressione ENTER.")
    
    escolha_sites = input("👉 Suas escolhas [TODAS]: ").strip()
    if escolha_sites:
        # Limpar espaços e garantir que só tenham números válidos separados por vírgula
        permitidos = [s.strip() for s in escolha_sites.split(",") if s.strip().isdigit()]
        auto_sites = ",".join(permitidos)
    else:
        auto_sites = "1,2,3,4,5,6,7,8"
        
    print("\n" + "-" * 60)
    forcar = input("⚠️ Forçar re-emissão de certidões já concluídas anteriormente? (S/N) [N]: ").strip().upper()
    auto_force = "1" if forcar == "S" else "0"
                
    print("\n🚀 Iniciando processamento em lote via Orion Hub...")
    
    # Executar a automação para cada vendedor
    for idx, v in enumerate(vendedores_selecionados, 1):
        print("\n" + "="*60)
        print(f" ⏳ PROCESSANDO VENDEDOR ({idx}/{len(vendedores_selecionados)}) ")
        print(f" 👤 Nome: {v['nome']}")
        print(f" 🪪 CPF:  {v['cpf']}")
        print(f" 📅 Nasc: {v['data_nascimento'] if v['data_nascimento'] else 'Não informada'}")
        print(f" 👩 Mãe:  {v['nome_mae'] if v['nome_mae'] else 'Não informado'}")
        print("=" * 60)
        
        env_vars = os.environ.copy()
        env_vars["AUTO_NOME"] = v["nome"]
        env_vars["AUTO_CPF"] = v["cpf"]
        env_vars["AUTO_RG"] = v["rg"]
        env_vars["AUTO_NASC"] = v["data_nascimento"]
        env_vars["AUTO_MAE"] = v["nome_mae"]
        env_vars["AUTO_GENERO"] = v["genero"]
        env_vars["AUTO_EMAIL"] = v["email"]
        env_vars["AUTO_SITES"] = auto_sites
        env_vars["AUTO_FORCE"] = auto_force
        
        # Try to use local venv python if it exists
        venv_python = Path(__file__).parent / "venv" / "bin" / "python3"
        python_exec = str(venv_python) if venv_python.exists() else sys.executable
        
        try:
            # Roda o script de certidões original com o ambiente modificado
            subprocess.run([python_exec, str(CERTIDOES_SCRIPT)], env=env_vars, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro na automação de {v['nome']}. O processo retornou código {e.returncode}.")
            print("Pausando o lote para verificação.")
            input("Pressione ENTER para continuar para a próxima pessoa ou CTRL+C para abortar...")
            
    print("\n" + "="*60)
    print(" 🎉 PROCESSAMENTO EM LOTE CONCLUÍDO! ")
    print(" Verifique a pasta 'downloads/' para os resultados.")
    print("="*60)

if __name__ == "__main__":
    main()
