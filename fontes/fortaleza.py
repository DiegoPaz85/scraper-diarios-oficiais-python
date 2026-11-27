import time
import requests


URL_HOME = "https://diariooficial.fortaleza.ce.gov.br/"
URL_API = "https://diariooficial.fortaleza.ce.gov.br/api/search"


def coletar_fortaleza(data_inicio, data_fim):
    print("Acessando a API de Fortaleza...")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://diariooficial.fortaleza.ce.gov.br",
            "Referer": URL_HOME,
        }
    )

    meses_busca = []
    ano, mes = data_inicio.year, data_inicio.month
    while (ano, mes) <= (data_fim.year, data_fim.month):
        meses_busca.append((ano, mes))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    try:
        resp_home = session.get(URL_HOME, timeout=30)
        if (
            resp_home.status_code != 200
            or "solicitação foi negada" in resp_home.text.lower()
        ):
            print(
                f"AVISO: Acesso inicial a Fortaleza bloqueado (HTTP {resp_home.status_code}). Abortando Fortaleza."
            )
            return []

        for ano_busca, mes_busca in meses_busca:
            print(f"Buscando diários de {mes_busca:02d}/{ano_busca}...")
            payload = {"ano": ano_busca, "mes": mes_busca}
            resposta = session.post(URL_API, json=payload, timeout=30)
            content_type = resposta.headers.get("Content-Type", "")

            if resposta.status_code != 200 or "text/html" in content_type.lower():
                print(
                    f"AVISO: WAF (F5) de Fortaleza bloqueou a requisição "
                    f"(HTTP {resposta.status_code}, Content-Type: {content_type})."
                )
                print(
                    "Conforme as regras do desafio, não tentaremos burlar a proteção. Abortando Fortaleza."
                )
                break

            time.sleep(1)

        return []

    except Exception as e:
        print(f"Erro ao coletar Fortaleza: {e}")
        return []
