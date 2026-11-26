import argparse
import json
import os
from datetime import date, timedelta
from fontes import macapa, fortaleza


def salvar_jsonl(registros, caminho_arquivo):
    if not registros:
        print("Nenhum registro para salvar.")
        return

    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)

    with open(caminho_arquivo, mode="w", encoding="utf-8") as arquivo:
        for registro in registros:
            # ensure_ascii=False mantém os acentos (ex: "Macapá")
            linha_json = json.dumps(registro, ensure_ascii=False)
            arquivo.write(linha_json + "\n")

    print(f"Arquivo salvo com sucesso em: {caminho_arquivo}")


def main():
    parser = argparse.ArgumentParser(description="Coletor de Diários Oficiais")
    parser.add_argument(
        "--inicio", type=date.fromisoformat, help="Data inicial (AAAA-MM-DD)"
    )
    parser.add_argument(
        "--fim", type=date.fromisoformat, help="Data final (AAAA-MM-DD)"
    )
    args = parser.parse_args()

    fim = args.fim or date.today()
    inicio = args.inicio or (fim - timedelta(days=60))

    print(f"Iniciando coleta de {inicio} até {fim}...\n")

    registros = []

    print("=== COLETANDO MACAPÁ ===")
    registros.extend(macapa.coletar_macapa(inicio, fim))
    print("\n")

    print("=== COLETANDO FORTALEZA ===")
    registros.extend(fortaleza.coletar_fortaleza(inicio, fim))

    caminho_jsonl = "dados/diarios.jsonl"
    salvar_jsonl(registros, caminho_jsonl)

    print(f"\nColeta finalizada. Total de registros: {len(registros)}")


if __name__ == "__main__":
    main()
