import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime


TIPOS_VALIDOS = {"normal", "extra", "suplemento"}
FONTES_ESPERADAS = {"Macapá", "Fortaleza"}
TAMANHO_MINIMO_TEXTO = 500
PROPORCAO_MINIMA_ALFANUM = 0.55
MAX_DIAS_BORDA = 7


def _texto_legivel(texto: str) -> tuple[bool, str]:
    limpo = texto.strip()
    if len(limpo) < TAMANHO_MINIMO_TEXTO:
        return False, f"texto muito curto ({len(limpo)} caracteres)"
    if "\ufffd" in limpo or "\x00" in limpo:
        return False, "contém caracteres corrompidos (\\ufffd ou \\x00)"

    sem_espacos = [c for c in limpo if not c.isspace()]
    if not sem_espacos:
        return False, "texto sem conteúdo visível"

    proporcao = sum(c.isalnum() for c in sem_espacos) / len(sem_espacos)
    if proporcao < PROPORCAO_MINIMA_ALFANUM:
        return False, f"baixa legibilidade ({proporcao:.0%} alfanumérico)"

    return True, ""


def verificar(
    caminho_jsonl: str,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    ignorar_fortaleza: bool = False,
) -> None:
    print(f"--- INICIANDO VERIFICAÇÃO: {caminho_jsonl} ---")

    if not os.path.exists(caminho_jsonl):
        print("ERRO FATAL: Arquivo JSONL não encontrado. Rode o coletor primeiro.")
        sys.exit(1)

    registros = []
    num_linha = 0
    try:
        with open(caminho_jsonl, mode="r", encoding="utf-8") as f:
            for num_linha, linha in enumerate(f, start=1):
                if not linha.strip():
                    continue
                obj = json.loads(linha)
                if not isinstance(obj, dict):
                    raise ValueError(f"Linha {num_linha} não é um objeto JSON válido.")
                registros.append(obj)
    except Exception as e:
        print(f"ERRO FATAL: Falha ao ler o JSONL (linha {num_linha}). Erro: {e}")
        sys.exit(1)

    if not registros:
        print("ERRO FATAL: O arquivo JSONL está vazio.")
        sys.exit(1)

    erros = []
    avisos = []
    chaves_vistas = set()
    urls_vistas = set()
    contagem_municipios = Counter()
    datas_por_municipio = defaultdict(list)
    numeros_todos_por_municipio = defaultdict(set)
    numeros_normais_por_municipio = defaultdict(list)

    for i, registro in enumerate(registros, start=1):
        municipio = registro.get("municipio")
        numero = registro.get("numero_edicao")
        tipo = registro.get("tipo")
        data_pub = registro.get("data_publicacao")
        coletado_em = registro.get("coletado_em")
        texto = registro.get("texto_completo")
        url = registro.get("url_documento")

        municipio_valido = isinstance(municipio, str) and bool(municipio.strip())
        if not municipio_valido:
            erros.append(f"Registro {i}: Município ausente ou inválido ({municipio}).")
        else:
            municipio = municipio.strip()
            contagem_municipios[municipio] += 1

        if numero is None or not str(numero).strip():
            erros.append(f"Registro {i}: Número da edição ausente ({numero}).")

        if tipo not in TIPOS_VALIDOS:
            erros.append(f"Registro {i}: Tipo inválido ({tipo}).")

        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            erros.append(f"Registro {i}: URL inválida ({url}).")
        else:
            if url in urls_vistas:
                erros.append(f"Registro {i}: URL duplicada ({url}).")
            urls_vistas.add(url)

        chave = f"{municipio}-{numero}-{data_pub}-{tipo}"
        if chave in chaves_vistas:
            erros.append(f"Registro {i}: Edição duplicada ({chave}).")
        chaves_vistas.add(chave)

        if not isinstance(texto, str):
            erros.append(f"Registro {i}: Texto ausente na edição {numero}.")
        else:
            ok, motivo = _texto_legivel(texto)
            if not ok:
                erros.append(f"Registro {i} (edição {numero}): {motivo}.")

        data_obj = None
        try:
            if not isinstance(data_pub, str):
                raise TypeError
            data_obj = date.fromisoformat(data_pub)
            if data_inicio and data_obj < data_inicio:
                erros.append(
                    f"Registro {i}: data_publicacao ({data_pub}) anterior ao início ({data_inicio})."
                )
            if data_fim and data_obj > data_fim:
                erros.append(
                    f"Registro {i}: data_publicacao ({data_pub}) posterior ao fim ({data_fim})."
                )
            if municipio_valido:
                datas_por_municipio[municipio].append(data_obj)
        except (ValueError, TypeError):
            erros.append(f"Registro {i}: data_publicacao mal formatada ({data_pub}).")

        try:
            if not isinstance(coletado_em, str):
                raise TypeError
            dt_coleta = datetime.fromisoformat(coletado_em)
            if dt_coleta.tzinfo is None:
                erros.append(
                    f"Registro {i}: coletado_em sem fuso horário ({coletado_em})."
                )
        except (ValueError, TypeError):
            erros.append(f"Registro {i}: coletado_em mal formatado ({coletado_em}).")

        if municipio_valido and numero is not None:
            try:
                num_int = int(str(numero).strip())
                numeros_todos_por_municipio[municipio].add(num_int)
                if tipo == "normal":
                    numeros_normais_por_municipio[municipio].append(num_int)
            except ValueError:
                avisos.append(
                    f"Registro {i}: Número não numérico ({numero}) em {municipio}; ignorado na checagem sequencial."
                )

    for fonte in sorted(FONTES_ESPERADAS):
        if fonte not in contagem_municipios:
            msg = f"Nenhum registro de {fonte} encontrado."
            if fonte == "Fortaleza" and ignorar_fortaleza:
                avisos.append(
                    f"{msg} (Ignorado via --ignorar-fortaleza; bloqueio WAF documentado no README)."
                )
            else:
                erros.append(f"INCOMPLETUDE: {msg}")

    for municipio, numeros_normais in numeros_normais_por_municipio.items():
        contagem_num = Counter(numeros_normais)
        for num, qtd in sorted(contagem_num.items()):
            if qtd > 1:
                erros.append(
                    f"DUPLICIDADE ({municipio}): Edição normal {num} aparece {qtd} vezes."
                )

    for municipio, conjunto_numeros in numeros_todos_por_municipio.items():
        ordenados = sorted(conjunto_numeros)
        for atual, proximo in zip(ordenados, ordenados[1:]):
            diferenca = proximo - atual
            if diferenca > 1:
                faltantes = list(range(atual + 1, proximo))
                erros.append(
                    f"LACUNA DE NUMERAÇÃO ({municipio}): saltou de {atual} para {proximo} (ausente(s): {faltantes})."
                )

    if data_inicio and data_fim:
        for municipio, datas in datas_por_municipio.items():
            menor, maior = min(datas), max(datas)
            if (menor - data_inicio).days > MAX_DIAS_BORDA:
                erros.append(
                    f"COBERTURA INCOMPLETA ({municipio}): primeira edição coletada em {menor}, distante de --inicio ({data_inicio})."
                )
            if (data_fim - maior).days > MAX_DIAS_BORDA:
                erros.append(
                    f"COBERTURA INCOMPLETA ({municipio}): última edição coletada em {maior}, distante de --fim ({data_fim})."
                )

    for aviso in avisos:
        print(f"AVISO: {aviso}")

    print(f"Total de registros lidos: {len(registros)}")
    for municipio, total in sorted(contagem_municipios.items()):
        datas = datas_por_municipio[municipio]
        faixa = f"{min(datas)} a {max(datas)}" if datas else "sem datas válidas"
        print(f" - {municipio}: {total} registro(s) ({faixa})")

    if erros:
        print("\nPROBLEMAS ENCONTRADOS:")
        for erro in erros:
            print(f" - {erro}")
        print("\nVerificação FALHOU.")
        sys.exit(1)

    print("\nVerificação passou! Dados íntegros, legíveis e sem lacunas.")
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verificador dos diários coletados")
    parser.add_argument(
        "arquivo", nargs="?", default="dados/diarios.jsonl", help="Caminho do JSONL"
    )
    parser.add_argument(
        "--inicio", type=date.fromisoformat, help="Data inicial esperada"
    )
    parser.add_argument("--fim", type=date.fromisoformat, help="Data final esperada")
    parser.add_argument(
        "--ignorar-fortaleza",
        action="store_true",
        help="Não falha por ausência de Fortaleza (WAF documentado)",
    )
    args = parser.parse_args()
    verificar(args.arquivo, args.inicio, args.fim, args.ignorar_fortaleza)
