# Agente de IA — Suporte a Professores

Assistente pedagógico com RAG (Retrieval-Augmented Generation): os professores
fazem login e perguntam coisas sobre os manuais/guias do programa; o agente
responde **só com base nesses documentos** e sempre cita a fonte.

## Como funciona, em uma frase

```
PDFs (manuais) --[scripts/ingest.py, roda 1x por atualização]--> Qdrant (AWS/EC2)
                                                                        │
professor faz login (JWT) --> POST /chat --> busca no Qdrant --> Gemini responde
                                                                  citando a fonte
```

- **Login**: FastAPI + JWT. Só entra quem você cadastrou manualmente
  (`scripts/create_teacher.py`) — não tem cadastro público.
- **Banco vetorial**: [Qdrant](https://qdrant.tech) rodando num container
  Docker numa instância EC2 `t3.micro` (free tier da AWS). Guarda os
  pedaços de texto dos PDFs já convertidos em vetor (embedding).
- **Orquestração**: [LangChain](https://python.langchain.com) — cuida da
  busca por similaridade no Qdrant e do encadeamento retriever → prompt → LLM.
- **LLM**: Google Gemini (`gemini-flash-latest` por padrão), via `langchain-google-genai`.
- **Embeddings**: também Gemini (`gemini-embedding-001`) — provedor único
  de propósito, pra simplificar cobrança/gestão de chave. Trocar de
  provedor (chat ou embeddings) é mudar só `app/rag/chain.py`,
  `app/rag/relatorios.py` e/ou `app/rag/vectorstore.py`.



## Estrutura do projeto

```
teacher_ai_agent/
├── .env.example              # copie pra .env e preencha
├── requirements.txt
├── docker-compose.yml        # só pra testar Qdrant localmente
├── app/
│   ├── main.py                # monta a API FastAPI
│   ├── config.py               # lê o .env
│   ├── database.py             # SQLAlchemy (banco de LOGIN, não o vetorial)
│   ├── models.py                # tabelas Teacher, Planilha, Conversa, Mensagem
│   ├── auth/
│   │   ├── security.py          # hash de senha, JWT
│   │   └── schemas.py
│   ├── rag/
│   │   ├── vectorstore.py       # conexão com o Qdrant
│   │   ├── chain.py             # busca + prompt + ferramentas + chamada ao Gemini
│   │   ├── relatorios.py        # relatório: API do Saldo+ ou última planilha
│   │   └── prompts.py           # system prompt do agente
│   ├── support/
│   │   └── tickets.py           # abre chamado no banco + envia e-mail
│   └── routers/
│       ├── auth_router.py       # POST /login, GET /me
│       ├── chat_router.py       # POST /chat (protegida) — cria/continua uma conversa
│       ├── conversas_router.py  # GET /conversas, GET /conversas/{id} (histórico)
│       └── relatorios_router.py # POST /planilhas (upload, protegida)
├── scripts/
│   ├── create_teacher.py       # cadastra professor (CLI)
│   ├── ingest.py                # PDFs -> embeddings -> Qdrant
│   └── upload_planilha.py      # envia planilha pra base (relatório de turma)
├── infra/
│   └── ec2_user_data.sh        # cole na criação da instância EC2
├── tests/
│   ├── test_auth.py             # teste de fumaça (login + chat)
│   └── test_ferramentas.py      # abrir_chamado, resumo de planilha, tool-calling do chain
└── documentos/                  # coloque os PDFs aqui pra ingerir
```

## Passo a passo

### 1. Preparar o ambiente local

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env`: gere o `SECRET_KEY` com
`python -c "import secrets; print(secrets.token_hex(32))"`, e preencha
`GOOGLE_API_KEY` (gere em https://aistudio.google.com/apikey — deixe
`QDRANT_URL`/`QDRANT_API_KEY` como estão por enquanto — o passo 2 resolve
isso pro teste local).

### 2. Testar localmente (sem AWS ainda)

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
docker compose up -d
```

Isso sobe um Qdrant local em `http://localhost:6333`. Ajuste o `.env`:
`QDRANT_URL=http://localhost:6333` e `QDRANT_API_KEY=chave-local-de-teste`
(mesma do `docker-compose.yml`).

Coloque um PDF de teste em `documentos/` e rode:

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
python scripts/ingest.py --pasta ./documentos
```

Cadastre um professor de teste:

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
python scripts/create_teacher.py --usuario maria.teste --nome "Maria Teste"
```

Suba a API:

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
uvicorn app.main:app --reload
```

Abra `http://localhost:8000/docs`, clique em "Authorize" (o esquema é
OAuth2PasswordBearer, então o próprio Swagger faz o login por você — não
precisa colar token manual): preencha `username`/`password` do professor
de teste, deixe `client_id`/`client_secret` em branco, e clique em
"Authorize". Depois teste `/api/v1/chat`.

**Nota pra quem for integrar um frontend**: `POST /login` recebe
`username`/`password` (nomes em inglês — exigência do padrão OAuth2 que o
FastAPI/Swagger espera), mas `GET /me` devolve os campos em português
(`usuario`, `nome_completo`, `escola`). Se for rodar um frontend local em
outra porta (ex.: Vite em `5173`), adicione a origem em `CORS_ORIGINS` no
`.env` — o `.env.example` já traz `http://localhost:5173` como exemplo.

### 3. Subir o Qdrant de verdade na AWS

1. No console da AWS, crie uma instância EC2 `t3.micro` (ou `t2.micro`),
   AMI **Amazon Linux 2023**.
2. Antes de lançar: abra "Advanced details" → "User data" e cole o
   conteúdo de `infra/ec2_user_data.sh`, **trocando a chave de API** pra
   uma senha forte sua.
3. Security Group: libere a porta `6333` (TCP) pra `0.0.0.0/0` — parece
   estranho liberar pro mundo todo, mas é necessário porque o Render (plano
   gratuito) não tem IP fixo de saída. Quem protege o acesso é a API key,
   não o firewall. **Não libere a porta 22 (SSH) publicamente** — prefira o
   AWS Systems Manager Session Manager pra acessar a instância sem abrir
   SSH nenhum (grátis, e mais seguro).
4. Depois que a instância estiver no ar, pegue o IP público dela e
   atualize o `.env`: `QDRANT_URL=http://SEU_IP:6333` e `QDRANT_API_KEY`
   com a chave que você definiu no user data.
5. Rode `python scripts/ingest.py` de novo, agora apontando pro Qdrant da AWS.

### 4. Deploy da API (Render, mesmo esquema do Saldo+)

1. Suba este projeto pro GitHub (com `.env` no `.gitignore` — não versione
   segredo).
2. No Render: New → Web Service → conecte o repositório.
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Em "Environment", cadastre as mesmas variáveis do `.env` (menos o
   `DATABASE_URL`, se quiser deixar o SQLite padrão — repare que no plano
   gratuito do Render o disco não é persistente entre deploys, então o
   banco de professores seria recriado a cada deploy; se isso for um
   problema, aponte `DATABASE_URL` pro mesmo Postgres/Supabase do Saldo+
   numa tabela separada).
4. Depois do deploy, cadastre os professores de verdade rodando
   `scripts/create_teacher.py` **localmente**, mas com o `.env` apontando
   pro `DATABASE_URL` de produção.

## Abertura de chamado e relatório de turma

Além de responder com base nos PDFs, o agente tem duas ferramentas que ele
mesmo decide quando usar (tool calling nativo do Gemini — `app/rag/chain.py`):

- **`abrir_chamado_de_suporte`**: quando o professor relata um problema real
  (acesso, erro no sistema, reclamação) que precisa de alguém da equipe
  entrando em contato. Grava um registro na tabela `tickets` e manda um
  e-mail pra `SUPPORT_EMAIL_TO`, com `Reply-To` já apontando pro e-mail do
  professor — quem responder o e-mail já fala direto com ele. **O chamado
  fica salvo no banco mesmo que o envio do e-mail falhe** (rede fora do ar,
  SMTP errado) — a IA nunca "engole" um chamado por causa de infra.
  Deliberadamente ela só abre chamado pra problema de verdade, não pra toda
  pergunta sem resposta nos materiais (senão o e-mail de suporte vira spam).
- **`gerar_relatorio`**: quando o professor pede um resumo de desempenho da
  turma. Tenta a API do Saldo+ primeiro (se `SALDO_API_BASE_URL` estiver
  configurada) e cai pra última planilha carregada no sistema como
  alternativa (`POST /api/v1/planilhas`, ou `scripts/upload_planilha.py`).

**Por que não escrevi um parser fixo pro formato exato dos dados**: nem o
schema da API do Saldo+ nem o de cada planilha são garantidos com
antecedência (cada planilha pode ter colunas diferentes, a API pode mudar
campo). Em vez disso, os dados são resumidos (estatísticas básicas — não
linha por linha) e entregues como JSON pro próprio modelo organizar num
texto legível. Isso é mais robusto a mudança de schema, mas também significa
que **vale revisar a primeira planilha real que você subir** — se as colunas
tiverem nomes muito diferentes do esperado (`turma`, `progresso` etc.), o
filtro por turma pode não funcionar e o relatório sai mais genérico. Me
mostre uma planilha de exemplo real quando tiver uma, que eu ajusto o
código de resumo pra ela.

Cadastre professores já com e-mail e turma (a turma é o que liga o
professor ao relatório certo):

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
python scripts/create_teacher.py --usuario maria.clara --nome "Maria Clara" --email maria@escola.com --turma "3A"
```

Pra carregar/atualizar a planilha usada no relatório:

```
cd "C:\Users\Cliente\Desktop\teacher_ai_agent"
python scripts/upload_planilha.py --arquivo ./relatorio_turmas.xlsx --usuario maria.clara
```

Configure o SMTP no `.env` (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM`, `SUPPORT_EMAIL_TO`) — qualquer provedor serve, inclusive Gmail
com uma "senha de app" (myaccount.google.com/apppasswords, não dá pra usar a
senha normal da conta).

## Histórico de conversas

Cada pergunta feita em `POST /api/v1/chat` fica registrada, agrupada em
"conversas" (pra montar uma lateral de histórico no front, tipo ChatGPT):

- **Primeira pergunta**: mande `POST /api/v1/chat` sem `conversa_id`. O
  backend cria uma conversa nova (título = início da pergunta) e devolve o
  `conversa_id` junto da resposta.
- **Perguntas seguintes da mesma conversa**: mande esse `conversa_id` de
  volta no corpo da requisição pra continuar na mesma thread, em vez de
  abrir uma nova.
- **`GET /api/v1/conversas`**: lista as conversas do professor logado, mais
  recente primeiro — só o resumo (id, título, data).
- **`GET /api/v1/conversas/{id}`**: mensagens completas de uma conversa
  (pergunta, resposta, fontes citadas e `chamado_id` se aquela resposta
  abriu um chamado). Devolve 404 tanto se a conversa não existe quanto se
  pertence a outro professor — nunca revela qual dos dois é o caso.

Cada professor só enxerga as próprias conversas (`app/routers/conversas_router.py`
filtra por `teacher_username` do token JWT).

## Manutenção do dia a dia

- **Adicionar/atualizar um manual**: coloque o PDF em `documentos/` e rode
  `python scripts/ingest.py` de novo (aponta pro Qdrant da AWS). Se o
  arquivo mudou de nome, o pedaço antigo fica órfão no Qdrant — pra um
  projeto desse tamanho, o mais simples é aceitar isso por enquanto (não
  atrapalha a qualidade da resposta) em vez de implementar deleção
  seletiva.
- **Cadastrar um professor novo**: `python scripts/create_teacher.py --usuario ... --nome "..."`.
- **Custo esperado por mês** (depois do free tier acabar): EC2 t3.micro
  (~US$7-8). O consumo do Gemini (embeddings + chat com `gemini-flash-latest`)
  fica dentro do tier gratuito do Google AI Studio pra um uso do dia a dia
  desse tamanho — vale confirmar os limites atuais em
  https://ai.google.dev/pricing antes de escalar. Praticamente zero de
  infraestrutura fixa.

## Segurança — pontos de atenção

- O Qdrant fica exposto na internet (necessário, ver passo 3 acima) —
  **é a API key que protege os dados**, então trate ela como senha.
- O JWT expira em 8h (`ACCESS_TOKEN_EXPIRE_MINUTES`) — professor precisa
  logar de novo no dia seguinte.
- Não existe rota de "esqueci minha senha" nem de auto-cadastro, de
  propósito — pra esse tamanho de time, é mais simples e mais seguro você
  mesma trocar a senha de alguém rodando `create_teacher.py` de novo
  (apagando o registro antigo antes) do que manter fluxo de recuperação de
  senha por e-mail.
