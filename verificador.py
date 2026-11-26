import csv
import sys
from datetime import datetime
import re

# Correção do bug de limite de 128KB do CSV
csv.field_size_limit(sys.maxsize)

def verificar():
    caminho_csv = "dados/diarios.csv"
    print(f"--- INICIANDO VERIFICAÇÃO: {caminho_csv} ---")
    
    try:
        with open(caminho_csv, mode='r', encoding='utf-8') as f:
            leitor = csv.DictReader(f)
            registros = list(leitor)
    except FileNotFoundError:
        print("ERRO FATAL: Arquivo CSV não encontrado. Rode o coletor primeiro.")
        sys.exit(1)

    erros = []
    vistos = set()
    
    if not registros:
        print("ERRO FATAL: O CSV está vazio.")
        sys.exit(1)

    # 1. Checa se as fontes esperadas estão presentes
    municipios = set(r['municipio'] for r in registros)
    if "Fortaleza" not in municipios:
        print("⚠️  AVISO: Nenhum dado de Fortaleza encontrado (bloqueio de WAF documentado).")
        # Não vamos falhar o script por causa do WAF, mas avisamos.
    
    numeros_macapa = []

    for i, linha in enumerate(registros, start=1):
        municipio = linha['municipio']
        numero = linha['numero_edicao']
        tipo = linha['tipo']
        data_pub = linha['data_publicacao']
        texto = linha['texto_completo']
        url = linha['url_documento']
        
        # 2. Valida Tipo
        if tipo not in ['normal', 'extra', 'suplemento']:
            erros.append(f"Linha {i}: Tipo inválido ({tipo}).")
            
        # 3. Valida URL
        if not url.startswith("http"):
            erros.append(f"Linha {i}: URL inválida ({url}).")

        # 4. Verifica duplicatas (incluindo o tipo na chave)
        chave = f"{municipio}-{numero}-{data_pub}-{tipo}"
        if chave in vistos:
            erros.append(f"Linha {i}: Edição duplicada ({chave}).")
        vistos.add(chave)
        
        # 5. Verifica texto
        if len(texto.strip()) < 500:
            erros.append(f"Linha {i}: Texto muito curto para a edição {numero} ({len(texto)} caracteres).")
        if "�" in texto:
            erros.append(f"Linha {i}: Texto contém caracteres ilegíveis (�) na edição {numero}.")
            
        # 6. Valida Data e Hora
        try:
            datetime.strptime(data_pub, "%Y-%m-%d")
            datetime.fromisoformat(linha['coletado_em'])
        except ValueError:
            erros.append(f"Linha {i}: Data ou Hora de coleta mal formatada.")

        if municipio == "Macapá" and tipo == "normal":
            numeros_macapa.append(int(numero))

    # 7. Verifica Lacunas na numeração de Macapá (Completude)
    if numeros_macapa:
        numeros_macapa.sort()
        for i in range(len(numeros_macapa) - 1):
            atual = numeros_macapa[i]
            proximo = numeros_macapa[i+1]
            if proximo - atual > 1:
                # Verifica se o buraco é maior que 3 (ex: fim de semana/feriado prolongado)
                if proximo - atual > 3:
                    erros.append(f"ALERTA DE COMPLETUDE: Salto na numeração de Macapá: da edição {atual} pulou para {proximo}.")

    print(f"Total de registros lidos: {len(registros)}")
    
    if erros:
        print("\n❌ PROBLEMAS ENCONTRADOS:")
        for erro in erros:
            print(f" - {erro}")
        print("\nVerificação FALHOU.")
        sys.exit(1)
    else:
        print("\n✅ Verificação passou! Sem duplicatas, textos legíveis e sem lacunas graves.")
        sys.exit(0)

if __name__ == "__main__":
    verificar()
