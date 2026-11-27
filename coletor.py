import argparse
import json
import os
from datetime import date, timedelta
from fontes import macapa, fortaleza


def carregar_urls_existentes(caminho_arquivo):
    """Lê o JSONL existente para evitar reprocessar edições já coletadas."""
    urls = set()
    if not os.path.exists(caminho_arquivo):
        return urls

    with open(caminho_arquivo, mode="r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            try:
                registro = json.loads(linha)
                url = registro.get("url_documento")
                if url:
                    urls.add(url)
            except json.JSONDecodeError:
                continue

    return urls


def anexar_registro_jsonl(registro, caminho_arquivo):
    """Grava um único registro imediatamente no JSONL."""
    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
    with open(caminho_arquivo, mode="a", encoding="utf-8") as arquivo:
        linha_json = json.dumps(registro, ensure_ascii=False)
        arquivo.write(linha_json + "\n")


def main():
    parser = argparse.ArgumentParser(description="Coletor de Diários Oficiais")
    parser.add_argument(
        "--inicio", type=date.fromisoformat, help="Data inicial (AAAA-MM-DD)"
    )
    parser.add_argument(
        "--fim", type=date.fromisoformat, help="Data final (AAAA-MM-DD)"
    )
    parser.add_argument(
        "--limpar",
        action="store_true",
        help="Apaga o JSONL anterior e refaz a coleta do zero",
    )
    args = parser.parse_args()

    fim = args.fim or date.today()
    inicio = args.inicio or (fim - timedelta(days=60))

    caminho_jsonl = "dados/diarios.jsonl"

    if args.limpar and os.path.exists(caminho_jsonl):
        os.remove(caminho_jsonl)
        print(f"Arquivo anterior removido: {caminho_jsonl}")

    urls_existentes = carregar_urls_existentes(caminho_jsonl)
    if urls_existentes:
        print(
            f"Retomando coleta: {len(urls_existentes)} registro(s) já salvos em {caminho_jsonl}."
        )

    print(f"Iniciando coleta de {inicio} até {fim}...\n")

    novos_registros = 0

    try:
        print("=== COLETANDO MACAPÁ ===")
        for registro in macapa.coletar_macapa(
            inicio, fim, urls_existentes=urls_existentes
        ):
            url = registro.get("url_documento")
            if url and url in urls_existentes:
                continue
            anexar_registro_jsonl(registro, caminho_jsonl)
            if url:
                urls_existentes.add(url)
            novos_registros += 1

        print("\n=== COLETANDO FORTALEZA ===")
        for registro in fortaleza.coletar_fortaleza(inicio, fim):
            url = registro.get("url_documento")
            if url and url in urls_existentes:
                continue
            anexar_registro_jsonl(registro, caminho_jsonl)
            if url:
                urls_existentes.add(url)
            novos_registros += 1

    except KeyboardInterrupt:
        print(
            "\nColeta interrompida pelo usuário. O progresso salvo até aqui foi preservado."
        )

    print(
        f"\nColeta finalizada. Novos registros salvos: {novos_registros} | Total no arquivo: {len(urls_existentes)}"
    )


if __name__ == "__main__":
    main()
