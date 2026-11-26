import requests

def coletar_fortaleza(data_inicio, data_fim):
    print("Acessando a API do Fortaleza...")
    url = "https://diariooficial.fortaleza.ce.gov.br/api/search"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://diariooficial.fortaleza.ce.gov.br",
        "Referer": "https://diariooficial.fortaleza.ce.gov.br/"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Pega o cookie inicial
        session.get("https://diariooficial.fortaleza.ce.gov.br/", timeout=30)
        
        payload = {"ano": data_inicio.year, "mes": data_inicio.month}
        resposta = session.post(url, json=payload, timeout=30)
        
        # Verifica se o WAF devolveu a página de bloqueio
        content_type = resposta.headers.get("Content-Type", "")
        if "text/html" in content_type:
            print("⚠️  AVISO: WAF do Fortaleza bloqueou a requisição.")
            print("A resposta veio como HTML ('Sua solicitação foi negada').")
            print("Conforme as regras, não tentaremos burlar a proteção.")
            return []
            
        # Se passou, tenta ler o JSON (só vai rodar se o WAF não bloquear)
        dados = resposta.json()
        # ... (aqui entraria o parse do JSON e download dos PDFs) ...
        return []
        
    except Exception as e:
        print(f"Erro ao coletar Fortaleza: {e}")
        return []
