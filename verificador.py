import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime


TIPOS_VALIDOS = {"normal", "extra", "suplemento"}
TAMANHO_MINIMO_TEXTO = 500
LIMITE_SALTO_GRAVE = 3


def verificar(caminho_jsonl: str = "dados/diarios.jsonl") -> None:
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
                    raise ValueError(
                        f"Linha {num_linha} não é um objeto JSON válido."
                    )
                registros.append(obj)
    except Exception as e:
        print(
            f"ERRO FATAL: Falha ao ler o JSONL (linha {num_linha}). Erro: {e}"
        )
        sys.exit(1)

    if not registros:
        print("ERRO FATAL: O arquivo JSONL está vazio.")
        sys.exit(1)

    erros = []
    avisos = []
    chaves_vistas = set()
    urls_vistas = set()
    contagem_municipios = Counter()
    numeros_normais_por_municipio = defaultdict(list)

    for i, registro in enumerate(registros, start=1):
        municipio = registro.get("municipio")
        numero = registro.get("numero_edicao")
        tipo = registro.get("tipo")
        data_pub = registro.get("data_publicacao")
        coletado_em = registro.get("coletado_em")
        texto = registro.get("texto_completo")
        url = registro.get("url_documento")

        if not isinstance(municipio, str) or not municipio.strip():
            erros.append(
                f"Registro {i}: Município ausente ou inválido ({municipio})."
            )
        else:
            contagem_municipios[municipio.strip()] += 1

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

        if not isinstance(texto, str) or len(texto.strip()) < TAMANHO_MINIMO_TEXTO:
            erros.append(
                f"Registro {i}: Texto ausente ou muito curto para a edição {numero}."
            )
        else:
            if "\ufffd" in texto or "\x00" in texto:
                erros.append(
                    f"Registro {i}: Texto contém caracteres corrompidos na edição {numero}."
                )

        try:
            if not isinstance(data_pub, str):
                raise TypeError("data_publicacao não é string")
            datetime.strptime(data_pub, "%Y-%m-%d")
        except (ValueError, TypeError):
            erros.append(
                f"Registro {i}: data_publicacao mal formatada ({data_pub})."
            )

        try:
            if not isinstance(coletado_em, str):
                raise TypeError("coletado_em não é string")
            datetime.fromisoformat(coletado_em)
        except (ValueError, TypeError):
            erros.append(
                f"Registro {i}: coletado_em mal formatado ({coletado_em})."
            )

        if (
            isinstance(municipio, str)
            and municipio.strip()
            and tipo == "normal"
            and numero is not None
        ):
            try:
                numeros_normais_por_municipio[municipio.strip()].append(
                    int(str(numero).strip())
                )
            except ValueError:
                avisos.append(
                    f"Registro {i}: Número de edição não numérico ({numero}) em {municipio}; ignorado na checagem sequencial."
                )

    if "Fortaleza" not in contagem_municipios:
        avisos.append(
            "Nenhum dado de Fortaleza encontrado (bloqueio de WAF documentado no README)."
        )

    for municipio, numeros in numeros_normais_por_municipio.items():
        numeros.sort()
        for atual, proximo in zip(numeros, numeros[1:]):
            diferenca = proximo - atual
            if diferenca == 0:
                erros.append(
                    f"DUPLICIDADE DE NUMERAÇÃO ({municipio}): Edição normal {atual} repetida."
                )
            elif 1 < diferenca <= LIMITE_SALTO_GRAVE:
                avisos.append(
                    f"Salto pequeno na numeração de {municipio}: da {atual} para {proximo} ({diferenca - 1} edição(ões) ausente(s))."
                )
            elif diferenca > LIMITE_SALTO_GRAVE:
                erros.append(
                    f"ALERTA DE COMPLETUDE ({municipio}): Salto grave na numeração de {atual} para {proximo} ({diferenca - 1} edições ausentes)."
                )

    for aviso in avisos:
        print(f"AVISO: {aviso}")

    print(f"Total de registros lidos: {len(registros)}")
    for municipio, total in sorted(contagem_municipios.items()):
        print(f" - {municipio}: {total} registro(s)")

    if erros:
        print("\nPROBLEMAS ENCONTRADOS:")
        for erro in erros:
            print(f" - {erro}")
        print("\nVerificação FALHOU.")
        sys.exit(1)

    print(
        "\nVerificação passou! Sem duplicatas, textos legíveis e sem lacunas graves."
    )
    sys.exit(0)


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "dados/diarios.jsonl"
    verificar(caminho)
