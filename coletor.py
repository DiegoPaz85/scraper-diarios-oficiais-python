import argparse
import csv
import os
from datetime import date, timedelta
from fontes import macapa
from fontes import fortaleza  # Vamos descomentar depois


def salvar_csv(registros, caminho_arquivo):
    if not registros:
        print("Nenhum registro para salvar.")
        return

    # Garante que a pasta dados existe
    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)

    # Pega as chaves (nomes das colunas) do primeiro registro
    colunas = registros[0].keys()

    with open(caminho_arquivo, mode="w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=colunas)
        writer.writeheader()
        writer.writerows(registros)

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

    # Se não passar datas, pega os últimos 60 dias a partir de hoje
    fim = args.fim or date.today()
    inicio = args.inicio or (fim - timedelta(days=60))

    print(f"Iniciando coleta de {inicio} até {fim}...\n")

    registros = []

    # Coleta Macapá
    print("=== COLETANDO MACAPÁ ===")
    registros.extend(macapa.coletar_macapa(inicio, fim))
    print("\n")

    # Coleta Fortaleza (no futuro)
    print("=== COLETANDO FORTALEZA ===")
    registros.extend(fortaleza.coletar_fortaleza(inicio, fim))

    # Salva tudo no CSV
    caminho_csv = "dados/diarios.csv"
    salvar_csv(registros, caminho_csv)

    print(f"\nColeta finalizada. Total de registros: {len(registros)}")


if __name__ == "__main__":
    main()
