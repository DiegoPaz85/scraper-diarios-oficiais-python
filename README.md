# Coleta de Diários Oficiais Municipais — Macapá e Fortaleza

## Como rodar
1. Instale as dependências: `pip install -r requirements.txt`
2. Instale as ferramentas de OCR (Macapá): `sudo apt install tesseract-ocr tesseract-ocr-por poppler-utils`
3. Execute o coletor: `python coletor.py` (O padrão coleta os últimos 60 dias. Para um período específico, use `--inicio AAAA-MM-DD --fim AAAA-MM-DD`).
4. Verifique a integridade dos dados: `python verificador.py`

## Intervalo Exato Coletado e Formato
A entrega foi executada em **26/11/2026**, cobrindo o intervalo exato de **27/09/2026 a 26/11/2026** (60 dias). Foram coletadas **[X] edições** de Macapá (substitua [X] pelo número final).
**Justificativa do Formato (JSONL):** Escolhi o JSONL (JSON Lines) em vez de CSV. O texto de um Diário Oficial é extenso e contém muitas quebras de linha. No CSV, isso esbarra no limite de 32.767 caracteres por célula do Excel e pode corromper a tabela. O JSONL trata cada linha como um objeto independente, ideal para *streaming*, indexação e integração direta com bancos NoSQL ou APIs de análise.

## Como cada fonte funciona e o que descobri
**Macapá:** A listagem em PHP/Livewire gera uma tabela HTML. Os PDFs ficam no WordPress da prefeitura, mas o servidor exige o cabeçalho `Referer` (proteção anti-hotlink). Descobri que os PDFs são **imagens escaneadas**. O código usa `requests.Session`, envia o `Referer` e aplica **OCR** (`pytesseract`).
**Fortaleza:** O site em Next.js (React) usa uma API interna (`POST /api/search`). Durante a inspeção, o WAF (F5) bloqueou até o uso manual do DevTools. O código envia o *payload* do mês, mas detecta que o WAF retorna uma página HTML ("Sua solicitação foi negada") no lugar do JSON. Conforme as regras, não tentei burlar a proteção; o script registra o bloqueio e aborta Fortaleza sem quebrar a execução.

## Mapeamento de Tipos
Em Macapá, o tipo é verificado na coluna de descrição da tabela e no início do texto usando Regex `\bedi[cç][aã]o\s+extra\b`. Isso evita falsos positivos com a palavra "EXTRATO" (comum em contratos). Se não houver menção, assume-se `normal`.

## Como sei que não faltou edição (Verificação)
O `verificador.py` é implacável e valida cinco pilares:
1. **Lacunas na numeração:** Ordena as edições de Macapá e acusa se houver saltos numéricos maiores que 3 dias (indicando feriados/fins de semana).
2. **Qualidade do texto:** Garante tamanho mínimo de 500 caracteres e ausência de caracteres ilegíveis (`�`).
3. **Duplicatas:** Usa a chave `município + número + data + tipo`, evitando conflitos entre edições normais e extras no mesmo dia.
4. **Consistência:** Valida se o tipo está no dicionário permitido, se a URL é válida e se a data/hora estão em ISO 8601.
5. **Presença de Fontes:** Emite alerta se a lista de Fortaleza estiver vazia.

## O que ficou de fora e o que faria com mais tempo
Não usei navegadores headless (Playwright) para burlar o WAF do Fortaleza. Com mais tempo, solicitaria acesso à API via LAI (Lei de Acesso à Informação) ou cruzaria os dados com o projeto Querido Diário. Em Macapá, não implementei o OSD (detecção de orientação), o que faria com que páginas horizontais fossem lidas com erros pelo OCR.

## O que quebraria primeiro se a fonte mudasse
Em Macapá, quebraria o seletor CSS da tabela ou a mudança na regra do `Referer`. No Fortaleza, qualquer alteração no *payload* da API ou a introdução de um captcha real (reCAPTCHA v3) impediria o acesso.

## Qual é a parte mais frágil do seu código e por quê
O OCR em Macapá. Como os PDFs são fotos do diário impresso, a qualidade do texto depende do escaneamento. O Tesseract pode falhar em páginas rotacionadas ou gerar erros ortográficos leves (ex: "Município" como "Muncípio"). O verificador pega textos vazios, mas não erros ortográficos.

## Como usei IA
A IA gerou o esqueleto do `requests` e a estrutura base da verificação. Eu precisei intervir em cinco pontos: 1) Adicionar o `Referer` no Macapá; 2) Implementar o *fallback* para OCR; 3) Tratar o "Falso 200" do WAF do Fortaleza; 4) Corrigir o falso positivo de "EXTRATO" com Regex; 5) Migrar o formato de saída de CSV para JSONL para evitar limites de célula e facilitar a indexação.
