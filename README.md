# Bagre.ai — Inteligência de Mercado no Futebol

Ferramenta de análise de transferências que identifica jogadores subvalorizados (**Pedigrees**) e contratações infladas por hype (**PediRatos**) usando dados reais de performance e valor de mercado.

## Rodando localmente

```bash
pip install -r requirements.txt
cp .env.example .env          # preencha RAPIDAPI_KEY e SECRET_KEY
python app.py
```

No primeiro start, o banco é criado automaticamente e as API keys de teste são impressas no terminal. Guarde-as para usar nos endpoints.

## Testando

1. Abra `http://localhost:8000` para o frontend.
2. Acesse `http://localhost:8000/docs` para a interface interativa (Swagger UI).
3. Use as API keys impressas no startup no header `X-API-Key`.

Exemplo rápido com curl:

```bash
curl -H "X-API-Key: <sua_key>" \
     "http://localhost:8000/v1/scout?nome=Vinicius+Jr"
```

## Tiers e funcionalidades

| Tier | Preço | Limite diário | Funcionalidades |
|------|-------|--------------|-----------------|
| **Várzea** | Grátis | 5 requests | Scout de jogador, Índice PediRato |
| **Olheiro** | R$ 29,90/mês | 50 requests | Várzea + Hype Index completo, Espelho Pedigree |
| **Diretor** | R$ 997,00/mês | Ilimitado | Olheiro + Coeficiente de Gini, Ciclo de Vida, Relatórios DOCX |

## Endpoints principais

| Método | Rota | Tier | Rate limit |
|--------|------|------|------------|
| GET | `/v1/scout` | Várzea | 10/min por IP |
| POST | `/v1/analytics/hype-index` | Olheiro | 5/min por IP |
| POST | `/v1/analytics/espelho-pedigree` | Olheiro | 5/min por IP |
| POST | `/v1/analytics/gini` | Diretor | 5/min por IP |
| POST | `/v1/analytics/ciclo-vida` | Diretor | 5/min por IP |
| POST | `/v1/reports/docx` | Diretor | 2/min por IP |

## Deploy no Render (free tier)

1. Faça fork/push do repositório para o GitHub.
2. Crie um novo **Web Service** no [Render](https://render.com) apontando para o repo.
3. O Render detecta o `render.yaml` automaticamente e configura build/start.
4. Adicione as variáveis de ambiente no painel do Render:
   - `RAPIDAPI_KEY` — sua chave da RapidAPI
   - `SECRET_KEY` — string aleatória segura
   - `DATABASE_PATH` já está configurado como `/tmp/bagre.db` no `render.yaml`

> **Nota:** O plano free do Render usa armazenamento efêmero. O banco SQLite em `/tmp` é resetado a cada deploy. Para persistência, substitua por um banco externo (ex: Supabase Postgres) ou use o Render Disk.

## Variáveis de ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `RAPIDAPI_KEY` | Chave de acesso às APIs esportivas | — |
| `DATABASE_PATH` | Caminho do arquivo SQLite | `./bagre.db` |
| `SECRET_KEY` | Chave para assinatura interna | — |
| `ENVIRONMENT` | `development` ou `production` | `development` |
