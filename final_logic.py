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

async def main():
    print("\n" + "═" * 62)
    print("  🏛️   AUTOMAÇÃO DE CERTIDÕES NEGATIVAS  v2.5")
    print("═" * 62)

    pessoa = coletar_dados()
    sessao = GerenciadorSessao(pessoa)
    dash = Dashboard(sessao)
    await dash.loop()

if __name__ == "__main__":
    asyncio.run(main())