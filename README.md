# Coleta de Diários Oficiais Municipais — Macapá e Fortaleza

## Como rodar
1. Instale as dependências Python: `pip install -r requirements.txt`
2. Instale as dependências de sistema para OCR (Linux/Ubuntu):
   `sudo apt install tesseract-ocr tesseract-ocr-por poppler-utils`
3. Execute o coletor (padrão: últimos 60 dias):
   `python coletor.py --inicio 2026-09-27 --fim 2026-11-26 --limpar`
4. Execute a verificação completa (acusa a ausência de Fortaleza com código de saída 1):
   `python verificador.py --inicio 2026-09-27 --fim 2026-11-26`
   Para validar isoladamente a integridade de Macapá:
   `python verificador.py --inicio 2026-09-27 --fim 2026-11-26 --ignorar-fortaleza`

## Intervalo coletado, formato e mapeamento de tipos
A coleta foi executada em **26/11/2026**, cobrindo o intervalo de **27/09/2026 a 26/11/2026** (60 dias). Foram coletadas **40 edições** de Macapá (edições **5383** a **5422**, publicadas entre 28/09/2026 e 26/11/2026, todas classificadas como `normal`) e **0** de Fortaleza (bloqueio de WAF detalhado abaixo).

**Formato (JSONL):** Escolhi JSONL porque diários oficiais contêm textos extensos com múltiplas quebras de linha. Em CSV, isso ultrapassa facilmente limites de ferramentas de planilha e dificulta escape; JSONL permite gravação incremental (*append* seguro em caso de interrupção) e leitura linha a linha pronta para indexação.

**Mapeamento de tipos:** Em Macapá, o tipo é inferido pelo campo `title` retornado pelo portal e pelos primeiros 500 caracteres do texto extraído: expressões de edição extra/extraordinária viram `extra` (usando limites de palavra `\b` para não confundir com "extrato" de contratos), menções a suplemento viram `suplemento`, e o restante é classificado como `normal`.

## Como cada fonte funciona e o que descobri
**Macapá:** O portal usa Laravel/Livewire v3 e carrega inicialmente apenas o mês corrente. Os dados das edições vêm serializados no atributo `wire:snapshot` (`tabDiaries`), dentro do envelope interno `[valor, {"s": "..."}]`. Para cobrir 60 dias, o coletor extrai o token CSRF e chama `POST /livewire/update` (`changeYear` e `setMonth`) mês a mês. Os PDFs ficam hospedados no WordPress da prefeitura, exigem cabeçalho `Referer` (proteção anti-hotlink) e são majoritariamente imagens escaneadas. O extrator tenta `pdfplumber` primeiro e aplica OCR via Tesseract em lotes de 5 páginas (150 DPI, escala de cinza) quando a média cai abaixo de 50 caracteres por página.

**Fortaleza:** O portal em Next.js consulta `POST /api/search` por ano e mês. Durante a investigação — inclusive em acesso manual com DevTools — o WAF F5 BIG-IP bloqueou as chamadas retornando HTTP 200 com `Content-Type: text/html` ("Sua solicitação foi negada"). Seguindo as regras do desafio, não tentei burlar a proteção: o coletor detecta o bloqueio, registra o diagnóstico e encerra a fonte sem interromper Macapá.

## Como sei que não faltou nenhuma edição
O `verificador.py` encerra com erro (`exit 1`) diante de qualquer inconsistência:
1. **Completude por fonte:** falha por padrão se Macapá ou Fortaleza não tiverem registros.
2. **Sequência numérica:** como a numeração do diário não pula em fins de semana ou feriados, qualquer lacuna entre o menor e o maior número coletado dispara erro.
3. **Cobertura temporal:** valida se todas as datas estão dentro de `--inicio`/`--fim` e se não há lacuna maior que 7 dias nas bordas do intervalo.
4. **Duplicatas e metadados:** rejeita URLs repetidas, chaves `município + número + data + tipo` duplicadas, tipos inválidos ou `coletado_em` sem fuso horário ISO 8601.
5. **Legibilidade:** exige no mínimo 500 caracteres, ausência de `\ufffd`/`\x00` e ao menos 55% de caracteres alfanuméricos.

## O que ficou de fora e o que faria com mais tempo
Não usei automação de navegador para contornar o WAF de Fortaleza; em produção, solicitaria acesso institucional via LAI ou avaliaria fontes espelho (como o Querido Diário). Em Macapá, não implementei detecção automática de rotação de página (OSD) antes do OCR nem comparação direta entre a contagem exibida no portal e o total baixado.

## O que quebraria primeiro se a fonte mudasse
Em Macapá, qualquer renomeação dos métodos Livewire (`changeYear`/`setMonth`), da chave `tabDiaries` no snapshot ou da política de `Referer`. Em Fortaleza, mudanças no payload de `/api/search` ou exigência de desafio interativo (CAPTCHA) além do WAF atual.

## Qual é a parte mais frágil do código e por quê
O OCR de Macapá. Como os PDFs são digitalizações do impresso, páginas tortas, carimbos ou baixa resolução geram ruídos pontuais (ex.: `"Muncípio"` em vez de `"Município"`). O verificador detecta páginas vazias ou muito corrompidas, mas não erros ortográficos sutis que afetam buscas exatas.

## Como usei IA
Usei IA para estruturar o esqueleto inicial dos coletores, o desempacotamento recursivo do snapshot Livewire v3 e a revisão do verificador. Intervi manualmente para diagnosticar o bloqueio anti-hotlink (`Referer`) de Macapá, limitar o OCR em lotes para evitar estourar memória, tratar o falso HTTP 200 do WAF de Fortaleza, corrigir o falso positivo de "extrato" na classificação de tipos e endurecer as regras de fuso horário e completude no verificador.
