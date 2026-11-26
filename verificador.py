import csv
import sys
from datetime import datetime, date


def verificar():
    caminho_csv = "dados/diarios.csv"
    print(f"--- INICIANDO VERIFICAÇÃO: {caminho_csv} ---")

    try:
        with open(caminho_csv, mode="r", encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            registros = list(leitor)
    except FileNotFoundError:
        print("ERRO FATAL: Arquivo CSV não encontrado. Rode o coletor primeiro.")
        sys.exit(1)

    erros = []
    vistos = set()

    if not registros:
        erros.append("O arquivo CSV está vazio.")

    for i, linha in enumerate(registros, start=1):
        municipio = linha["municipio"]
        numero = linha["numero_edicao"]
        data_pub = linha["data_publicacao"]
        texto = linha["texto_completo"]

        # 1. Verifica duplicatas
        chave = f"{municipio}-{numero}-{data_pub}"
        if chave in vistos:
            erros.append(f"Linha {i}: Edição duplicada ({chave}).")
        vistos.add(chave)

        # 2. Verifica texto vazio ou ilegível
        if len(texto.strip()) < 500:
            erros.append(
                f"Linha {i}: Texto muito curto ou vazio para a edição {numero} ({len(texto)} caracteres)."
            )

        if "�" in texto:
            erros.append(
                f"Linha {i}: Texto contém caracteres de substituição (ilegível) na edição {numero}."
            )

        # 3. Verifica Data
        try:
            datetime.strptime(data_pub, "%Y-%m-%d")
        except ValueError:
            erros.append(f"Linha {i}: Data mal formatada ({data_pub}).")

    print(f"Total de registros lidos: {len(registros)}")

    if erros:
        print("\n❌ PROBLEMAS ENCONTRADOS:")
        for erro in erros:
            print(f" - {erro}")
        print("\nVerificação FALHOU.")
        sys.exit(1)  # Termina com código de erro
    else:
        print(
            "\n✅ Verificação passou! Nenhuma duplicata, todos os textos estão legíveis e as datas são válidas."
        )
        sys.exit(0)


if __name__ == "__main__":
    verificar()
