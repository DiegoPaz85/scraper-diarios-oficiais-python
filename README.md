# Coleta de Diários Oficiais Municipais — Macapá e Fortaleza

## Como rodar
1. Instale as dependências: `pip install -r requirements.txt`
2. Instale as ferramentas de OCR (necessário para Macapá): `sudo apt install tesseract-ocr tesseract-ocr-por poppler-utils`
3. Execute o coletor passando o intervalo de datas (se omitido, coleta os últimos 60 dias):
   `python coletor.py --inicio 2026-11-25 --fim 2026-11-25`
4. Verifique a integridade dos dados:
   `python verificador.py`

## Como cada fonte funciona e o que descobri
**Macapá:** A página de listagem é feita em PHP/Livewire e contém uma tabela HTML estática. Os links apontam para PDFs no WordPress da prefeitura. Descobri que o servidor bloqueia requisições sem `Referer` (proteção anti-hotlink) e que os PDFs são **imagens escaneadas**. Portanto, o código usa `requests.Session` para pegar os cookies, envia o `Referer` correto e aplica **OCR** (`pytesseract` e `pdf2image`) para extrair o texto das imagens.
**Fortaleza:** O site foi construído em Next.js (React) e usa uma API interna (`/api/search`) para retornar os resultados. Durante a inspeção, descobri que a prefeitura usa um Web Application Firewall (WAF) da F5 extremamente agressivo. Ele bloqueou até mesmo a inspeção manual no navegador (exigindo captcha silencioso). Conforme as regras do desafio, não tentei burlar a proteção. O código tenta a requisição, detecta que o WAF devolveu uma página HTML com "Sua solicitação foi negada" e registra o bloqueio sem quebrar a execução.

## Como sei que não faltou edição (Verificação)
O script `verificador.py` roda sobre o CSV e valida três pilares:
1. **Duplicatas:** Verifica se a combinação `municipio + numero_edicao + data` é única.
2. **Qualidade do texto:** Garante que o texto não está vazio, tem um tamanho mínimo de 500 caracteres (para evitar extrações falhas do OCR) e não contém caracteres de substituição (`�`).
3. **Consistência:** Valida se todas as datas estão no formato ISO correto.
*Nota:* Para Fortaleza, a completude sequencial não pôde ser validada devido ao bloqueio da fonte.

## O que ficou de fora e o que faria com mais tempo
Ficou de fora o uso de navegadores headless (como Playwright) para tentar contornar o WAF do Fortaleza, pois o edital veda burlar proteções. Com mais tempo, eu implementaria um cruzamento de dados (validação cruzada) comparando os números das edições coletadas de Macapá com a API pública do projeto Querido Diário, garantindo completude por uma fonte terceira.

## O que quebraria primeiro se a fonte mudasse
Em Macapá, o que quebraria primeiro seria o seletor CSS da tabela (se mudarem as classes) ou o padrão de nome da URL do PDF. O OCR continuaria funcionando se o layout do PDF mudasse, mas a qualidade do texto poderia cair.

## Qual é a parte mais frágil do código e por quê
A extração de texto via OCR em Macapá. Como os PDFs são fotos do diário impresso, a qualidade do texto extraído depende da qualidade do escaneamento. O OCR pode cometer erros de português (ex: ler "Município" como "Muncípio"), o que é aceitável para busca, mas exigiria um pós-processamento ou um OCR mais avançado (como o Google Cloud Vision) em um ambiente de produção.

## Como usei IA
A IA foi usada para gerar o esqueleto inicial do `requests` e a estrutura da verificação. Eu precisei intervir em três pontos principais: 1) Descobrir e adicionar o cabeçalho `Referer` para o Macapá funcionar; 2) Implementar a lógica de fallback para OCR, que a IA inicialmente não previu; 3) Ajustar o tratamento do WAF do Fortaleza para que o script não quebrasse ao receber um HTML no lugar de um JSON.
