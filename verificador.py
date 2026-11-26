import sys
import json
from datetime import datetime
import os


def verificar():
    caminho_jsonl = "dados/diarios.jsonl"
    print(f"--- INICIANDO VERIFICAÇÃO: {caminho_jsonl} ---")

    if not os.path.exists(caminho_jsonl):
        print("ERRO FATAL: Arquivo JSONL não encontrado. Rode o coletor primeiro.")
        sys.exit(1)

    registros = []
    try:
        with open(caminho_jsonl, mode="r", encoding="utf-8") as f:
            for linha in f:
                if linha.strip():
                    registros.append(json.loads(linha))
    except Exception as e:
        print(f"ERRO FATAL: Falha ao ler o JSONL. O arquivo está corrompido? Erro: {e}")
        sys.exit(1)

    erros = []
    vistos = set()

    if not registros:
        print("ERRO FATAL: O arquivo JSONL está vazio.")
        sys.exit(1)

    municipios = set(r.get("municipio") for r in registros)
    if "Fortaleza" not in municipios:
        print(
            "AVISO: Nenhum dado de Fortaleza encontrado (bloqueio de WAF documentado no README)."
        )

    numeros_macapa = []

    for i, linha in enumerate(registros, start=1):
        municipio = linha.get("municipio")
        numero = linha.get("numero_edicao")
        tipo = linha.get("tipo")
        data_pub = linha.get("data_publicacao")
        texto = linha.get("texto_completo")
        url = linha.get("url_documento")

        if tipo not in ["normal", "extra", "suplemento"]:
            erros.append(f"Registro {i}: Tipo inválido ({tipo}).")

        if not url or not url.startswith("http"):
            erros.append(f"Registro {i}: URL inválida ({url}).")

        chave = f"{municipio}-{numero}-{data_pub}-{tipo}"
        if chave in vistos:
            erros.append(f"Registro {i}: Edição duplicada ({chave}).")
        vistos.add(chave)

        if not texto or len(texto.strip()) < 500:
            erros.append(f"Registro {i}: Texto muito curto para a edição {numero}.")
        if texto and "�" in texto:
            erros.append(
                f"Registro {i}: Texto contém caracteres ilegíveis (�) na edição {numero}."
            )

        try:
            datetime.strptime(data_pub, "%Y-%m-%d")
            datetime.fromisoformat(linha.get("coletado_em"))
        except ValueError:
            erros.append(f"Registro {i}: Data ou Hora de coleta mal formatada.")

        if municipio == "Macapá" and tipo == "normal":
            numeros_macapa.append(int(numero))

    if numeros_macapa:
        numeros_macapa.sort()
        for i in range(len(numeros_macapa) - 1):
            atual = numeros_macapa[i]
            proximo = numeros_macapa[i + 1]
            if proximo - atual > 3:  # Pula mais de 3 dias (fins de semana/feriados)
                erros.append(
                    f"ALERTA DE COMPLETUDE: Salto na numeração de Macapá: da {atual} para {proximo}."
                )

    print(f"Total de registros lidos: {len(registros)}")

    if erros:
        print("\n PROBLEMAS ENCONTRADOS:")
        for erro in erros:
            print(f" - {erro}")
        print("\nVerificação FALHOU.")
        sys.exit(1)
    else:
        print(
            "\nVerificação passou! Sem duplicatas, textos legíveis e sem lacunas graves."
        )
        sys.exit(0)


if __name__ == "__main__":
    verificar()
