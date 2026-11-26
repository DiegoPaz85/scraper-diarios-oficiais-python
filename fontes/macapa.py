import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import time
import io
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract

def extrair_texto_pdf(conteudo_pdf):
    # 1. Tenta extrair texto via pdfplumber (PDFs digitais)
    texto = ""
    with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto += texto_pagina + "\n"
    
    # 2. Se não extraiu nada, é porque é escaneado. Usa OCR.
    if len(texto.strip()) < 50:
        print("  -> PDF escaneado detectado. Aplicando OCR (pode demorar um pouco)...")
        imagens = convert_from_bytes(conteudo_pdf, dpi=200) # Converte páginas em imagens
        texto = ""
        for i, imagem in enumerate(imagens):
            texto_pagina = pytesseract.image_to_string(imagem, lang='por')
            texto += texto_pagina + "\n"
            
    return texto

def coletar_macapa(data_inicio, data_fim):
    url_base = "https://macapa.ap.gov.br/diarios-oficiais/"
    print(f"Acessando {url_base}...")
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    session.headers.update(headers)
    
    try:
        resposta = session.get(url_base, timeout=30)
        resposta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a página principal: {e}")
        return []

    soup = BeautifulSoup(resposta.text, "html.parser")
    tabela = soup.find("table")
    
    if not tabela:
        print("ERRO: Tabela não encontrada na página.")
        return []

    linhas = tabela.find("tbody").find_all("tr")
    registros = []

    for linha in linhas:
        colunas = linha.find_all("td")
        if len(colunas) < 4:
            continue 
            
        numero_edicao = colunas[0].text.strip()
        data_str = colunas[1].text.strip() 
        
        try:
            data_publicacao = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            continue

        if data_inicio <= data_publicacao <= data_fim:
            link_tag = colunas[3].find("a")
            if not link_tag:
                continue
                
            url_pdf = link_tag.get("href")
            print(f"Baixando edição {numero_edicao} de {data_str}...")
            
            try:
                headers_pdf = {"Referer": url_base}
                resp_pdf = session.get(url_pdf, headers=headers_pdf, timeout=60)
                resp_pdf.raise_for_status()
                
                if not resp_pdf.content.startswith(b'%PDF'):
                    print(f"  -> BLOQUEADO! O servidor não retornou um PDF para a edição {numero_edicao}.")
                    continue

                # Usa a nova função de extração
                texto_completo = extrair_texto_pdf(resp_pdf.content)
                            
                tipo = "normal"
                if "extra" in texto_completo.lower()[:500]:
                    tipo = "extra"
                elif "suplemento" in texto_completo.lower()[:500]:
                    tipo = "suplemento"

                registros.append({
                    "municipio": "Macapá",
                    "data_publicacao": data_publicacao.isoformat(),
                    "numero_edicao": numero_edicao,
                    "tipo": tipo,
                    "url_documento": url_pdf,
                    "texto_completo": texto_completo,
                    "coletado_em": datetime.now().astimezone().isoformat()
                })
                print(f"  -> Sucesso! {len(texto_completo)} caracteres extraídos.")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"  -> Erro ao baixar/ler o PDF {numero_edicao}: {e}")

    return registros

# --- Teste rápido ---
if __name__ == "__main__":
    # Vamos testar com apenas 1 dia para o OCR não demorar muito
    inicio = date(2026, 11, 25)
    fim = date(2026, 11, 25)
    
    resultados = coletar_macapa(inicio, fim)
    
    print(f"\n--- RESUMO ---")
    print(f"Total de diários coletados com sucesso: {len(resultados)}")
    if resultados:
        print("\n--- AMOSTRA DO TEXTO EXTRAÍDO (Edição " + resultados[0]['numero_edicao'] + ") ---")
        print(resultados[0]['texto_completo'][:1000])
