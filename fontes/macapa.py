import io
import json
import re
import tempfile
import time
from datetime import datetime
from urllib.parse import urljoin

import pdfplumber
import pytesseract
import requests
from bs4 import BeautifulSoup
from pdf2image import convert_from_path


URL_BASE = "https://macapa.ap.gov.br/diarios-oficiais/"


def extrair_texto_pdf(conteudo_pdf):
    # Tenta extrair texto via pdfplumber (PDFs digitais)
    texto_partes = []
    with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
        total_paginas = len(pdf.pages)
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto_partes.append(texto_pagina)

    texto = "\n".join(texto_partes)

    # Se não extraiu texto suficiente, aplica OCR em lotes pequenos (baixo uso de RAM)
    if len(texto.strip()) < 50:
        print(f"  -> PDF escaneado detectado ({total_paginas} págs). Aplicando OCR...")
        texto_partes = []
        tamanho_lote = 5

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(conteudo_pdf)
            tmp.flush()

            for inicio in range(1, total_paginas + 1, tamanho_lote):
                fim = min(inicio + tamanho_lote - 1, total_paginas)
                imagens = convert_from_path(
                    tmp.name,
                    dpi=150,
                    first_page=inicio,
                    last_page=fim,
                    grayscale=True,
                )
                for imagem in imagens:
                    try:
                        texto_pagina = pytesseract.image_to_string(imagem, lang="por")
                        texto_partes.append(texto_pagina)
                    finally:
                        imagem.close()

        texto = "\n".join(texto_partes)

    return texto


def _desempacotar_livewire(valor):
    """Remove o envelope [valor, {"s": "..."}] usado nos snapshots do Livewire v3."""
    if (
        isinstance(valor, list)
        and len(valor) == 2
        and isinstance(valor[1], dict)
        and "s" in valor[1]
    ):
        return _desempacotar_livewire(valor[0])
    if isinstance(valor, list):
        return [_desempacotar_livewire(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _desempacotar_livewire(v) for k, v in valor.items()}
    return valor


def _listar_meses_no_intervalo(data_inicio, data_fim):
    """Retorna lista de (ano, mes) do mais recente ao mais antigo dentro do intervalo."""
    meses = []
    ano, mes = data_fim.year, data_fim.month
    while (ano, mes) >= (data_inicio.year, data_inicio.month):
        meses.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    return meses


def _chamar_livewire(session, url_update, csrf_token, snapshot_str, metodo, params):
    payload = {
        "_token": csrf_token,
        "components": [
            {
                "snapshot": snapshot_str,
                "updates": {},
                "calls": [
                    {
                        "path": "",
                        "method": metodo,
                        "params": params,
                    }
                ],
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Livewire": "true",
        "X-CSRF-TOKEN": csrf_token,
        "Referer": URL_BASE,
        "Origin": "https://macapa.ap.gov.br",
    }
    resp = session.post(url_update, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    dados_resp = resp.json()
    return dados_resp["components"][0]["snapshot"]


def listar_edicoes_macapa(session, data_inicio, data_fim):
    """Consulta o componente Livewire mês a mês e retorna as edições dentro do intervalo."""
    resposta = session.get(URL_BASE, timeout=30)
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    script_lw = soup.find("script", attrs={"data-csrf": True})
    comp_lw = soup.find(attrs={"wire:snapshot": True})

    if not script_lw or not comp_lw:
        raise RuntimeError(
            "Componente Livewire ou token CSRF não encontrado na página."
        )

    csrf_token = script_lw["data-csrf"]
    url_update = urljoin(URL_BASE, script_lw.get("data-update-uri", "/livewire/update"))
    snapshot_str = comp_lw["wire:snapshot"]
    snapshot_data = json.loads(snapshot_str)["data"]

    ano_atual = str(snapshot_data.get("year", ""))
    mes_atual = str(snapshot_data.get("month", "")).zfill(2)

    edicoes_filtradas = []
    urls_vistas = set()

    for ano, mes in _listar_meses_no_intervalo(data_inicio, data_fim):
        ano_str = str(ano)
        mes_str = f"{mes:02d}"

        if ano_str != ano_atual:
            print(f"Consultando ano {ano_str} no portal...")
            snapshot_str = _chamar_livewire(
                session, url_update, csrf_token, snapshot_str, "changeYear", [ano_str]
            )
            snapshot_data = json.loads(snapshot_str)["data"]
            ano_atual = str(snapshot_data.get("year", ano_str))
            mes_atual = str(snapshot_data.get("month", "")).zfill(2)
            time.sleep(0.5)

        if mes_str != mes_atual:
            print(f"Consultando mês {mes_str}/{ano_str} no portal...")
            snapshot_str = _chamar_livewire(
                session, url_update, csrf_token, snapshot_str, "setMonth", [mes_str]
            )
            snapshot_data = json.loads(snapshot_str)["data"]
            ano_atual = str(snapshot_data.get("year", ano_str))
            mes_atual = str(snapshot_data.get("month", mes_str)).zfill(2)
            time.sleep(0.5)

        diarios_mes = _desempacotar_livewire(snapshot_data.get("tabDiaries", []))

        for diario in diarios_mes:
            if not isinstance(diario, dict):
                continue

            numero_edicao = str(diario.get("id", "")).strip()
            data_str = str(diario.get("date", "")).strip()
            titulo = str(diario.get("title", "")).strip()
            url_pdf = str(diario.get("link", "")).strip()

            if not url_pdf or url_pdf in urls_vistas:
                continue

            try:
                data_publicacao = datetime.strptime(data_str, "%d/%m/%Y").date()
            except ValueError:
                continue

            if data_inicio <= data_publicacao <= data_fim:
                urls_vistas.add(url_pdf)
                edicoes_filtradas.append(
                    {
                        "numero_edicao": numero_edicao,
                        "data_str": data_str,
                        "data_publicacao": data_publicacao,
                        "titulo": titulo,
                        "url_pdf": url_pdf,
                    }
                )

    return edicoes_filtradas


def coletar_macapa(data_inicio, data_fim, urls_existentes=None):
    urls_existentes = urls_existentes or set()
    print(f"Acessando {URL_BASE}...")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    try:
        edicoes = listar_edicoes_macapa(session, data_inicio, data_fim)
    except Exception as e:
        print(f"Erro ao listar edições de Macapá: {e}")
        return

    print(f"Total de edições encontradas no período: {len(edicoes)}")

    for edicao in edicoes:
        numero_edicao = edicao["numero_edicao"]
        data_str = edicao["data_str"]
        data_publicacao = edicao["data_publicacao"]
        titulo = edicao["titulo"]
        url_pdf = edicao["url_pdf"]

        if url_pdf in urls_existentes:
            print(f"Pulando edição {numero_edicao} de {data_str} (já coletada).")
            continue

        print(f"Baixando edição {numero_edicao} de {data_str}...")

        try:
            resp_pdf = session.get(url_pdf, headers={"Referer": URL_BASE}, timeout=60)
            resp_pdf.raise_for_status()

            if not resp_pdf.content.startswith(b"%PDF"):
                print(
                    f"  -> BLOQUEADO! O servidor não retornou um PDF para a edição {numero_edicao}."
                )
                continue

            texto_completo = extrair_texto_pdf(resp_pdf.content)

            tipo = "normal"
            if re.search(r"\bextra(ordin[aá]ri[ao])?\b", titulo, re.I) or re.search(
                r"\bedi[cç][aã]o\s+extra(ordin[aá]ria)?\b",
                texto_completo[:1000],
                re.I,
            ):
                tipo = "extra"
            elif re.search(r"\bsuplemento\b", titulo, re.I) or re.search(
                r"\bsuplemento\b", texto_completo[:1000], re.I
            ):
                tipo = "suplemento"

            registro = {
                "municipio": "Macapá",
                "data_publicacao": data_publicacao.isoformat(),
                "numero_edicao": numero_edicao,
                "tipo": tipo,
                "url_documento": url_pdf,
                "texto_completo": texto_completo,
                "coletado_em": datetime.now().astimezone().isoformat(),
            }
            print(
                f"  -> Sucesso! {len(texto_completo)} caracteres extraídos (Tipo: {tipo})."
            )
            yield registro

            time.sleep(2)

        except Exception as e:
            print(f"  -> Erro ao baixar/ler o PDF {numero_edicao}: {e}")
