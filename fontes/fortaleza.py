import requests


def coletar_fortaleza(data_inicio, data_fim):
    print("Acessando a API do Fortaleza...")
    url_api = "https://diariooficial.fortaleza.ce.gov.br/api/search"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://diariooficial.fortaleza.ce.gov.br",
        "Referer": "https://diariooficial.fortaleza.ce.gov.br/",
    }

    session = requests.Session()
    session.headers.update(headers)

    # Gera a lista de meses (ex: (2026, 9), (2026, 10), (2026, 11))
    meses_busca = set()
    ano, mes = data_inicio.year, data_inicio.month
    while (ano, mes) <= (data_fim.year, data_fim.month):
        meses_busca.add((ano, mes))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    try:
        session.get("https://diariooficial.fortaleza.ce.gov.br/", timeout=30)

        for ano_busca, mes_busca in sorted(meses_busca):
            print(f"Tentando buscar diários de {mes_busca:02d}/{ano_busca}...")

            payload = {"ano": ano_busca, "mes": mes_busca}
            resposta = session.post(url_api, json=payload, timeout=30)

            # Detecção do WAF (F5)
            content_type = resposta.headers.get("Content-Type", "")
            if "text/html" in content_type:
                print(" AVISO: WAF do Fortaleza bloqueou a requisição.")
                print(" A resposta veio como HTML ('Sua solicitação foi negada').")
                print(
                    "Conforme as regras do desafio, não tentaremos burlar a proteção. Abortando Fortaleza."
                )
                break  # Interrompe o loop, pois o WAF bloqueou todas as chamadas

            # Se passou, tenta ler o JSON (Só rodaria se o WAF não bloqueasse)
            if resposta.status_code == 200:
                dados = resposta.json()
                # Aqui entraria o parse do JSON e download dos PDFs via 'api/nodes/...'
                print(
                    "Sucesso ao obter JSON! (Código para ler JSON não implementado pois foi bloqueado no teste)."
                )

        return []

    except Exception as e:
        print(f"Erro ao coletar Fortaleza: {e}")
        return []
