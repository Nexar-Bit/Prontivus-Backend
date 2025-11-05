# Guia de Deploy do Backend para Render

Este guia explica como fazer deploy do backend Prontivus no Render.

## Pré-requisitos

1. Conta no [Render.com](https://render.com)
2. Banco de dados PostgreSQL (pode criar no Render ou usar um existente)
3. Repositório Git do projeto

## Passo a Passo

### 1. Preparar o Banco de Dados

Se você ainda não tem um banco de dados PostgreSQL no Render:

1. No dashboard do Render, clique em **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `prontivus-database` (ou outro nome de sua escolha)
   - **Database**: `prontivus_clinic` (ou outro nome)
   - **User**: Deixe o padrão ou crie um usuário
   - **Region**: Escolha a região mais próxima (ex: Oregon)
   - **Plan**: Escolha o plano adequado

3. Após criar, copie a **Internal Database URL** (será usada nas variáveis de ambiente)

### 2. Criar o Web Service

1. No dashboard do Render, clique em **"New +"** → **"Web Service"**
2. Conecte seu repositório Git (GitHub, GitLab, etc.)
3. Configure as seguintes opções:

#### Configurações Básicas:
- **Name**: `prontivus-backend`
- **Environment**: `Python 3`
- **Region**: Mesma região do banco de dados
- **Branch**: `main` (ou sua branch principal)
- **Root Directory**: `backend` (se o backend estiver em uma subpasta)

#### Build & Deploy:
- **Build Command**: 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

### 3. Configurar Variáveis de Ambiente

No painel do Web Service, vá em **"Environment"** e adicione as seguintes variáveis:

#### Variáveis Obrigatórias:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```
*(Use a Internal Database URL do seu PostgreSQL no Render)*

```
SECRET_KEY=<gerar-uma-chave-secreta-forte>
```
*(Gere uma chave secreta forte. Você pode usar: `python generate_secret_key.py`)*

```
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Variáveis de Ambiente:
```
ENVIRONMENT=production
DEBUG=false
```

#### CORS (Importante!):
```
BACKEND_CORS_ORIGINS=https://seu-frontend.vercel.app,https://www.seu-dominio.com
```
*(Adicione todas as URLs do frontend que precisam acessar a API, separadas por vírgula)*

#### Python Version (Opcional):
```
PYTHON_VERSION=3.12.0
```

### 4. Executar Migrações do Banco de Dados

Após o primeiro deploy, você precisa executar as migrações do Alembic:

1. No painel do Web Service, vá em **"Shell"**
2. Execute:
   ```bash
   alembic upgrade head
   ```

Ou adicione ao build script (descomente no `render-build.sh`):
```bash
alembic upgrade head
```

### 5. Verificar o Deploy

1. Após o deploy, acesse: `https://seu-backend.onrender.com/api/health`
2. Deve retornar: `{"status": "healthy", "service": "Prontivus API", "version": "1.0.0"}`

### 6. Usando render.yaml (Alternativa)

Se preferir usar o arquivo `render.yaml`:

1. No dashboard do Render, clique em **"New +"** → **"Blueprint"**
2. Selecione seu repositório
3. Render detectará automaticamente o `render.yaml` e criará os serviços

**Nota**: Você ainda precisará configurar manualmente:
- `DATABASE_URL` (conectar ao banco de dados)
- `SECRET_KEY` (gerar uma chave forte)
- `BACKEND_CORS_ORIGINS` (URLs do frontend)

## Troubleshooting

### Erro: "ModuleNotFoundError"
- Verifique se todas as dependências estão no `requirements.txt`
- Verifique se o build está instalando corretamente

### Erro: "Database connection failed"
- Verifique se a `DATABASE_URL` está correta
- Use a **Internal Database URL** (não a External URL)
- Certifique-se de que o banco está na mesma região

### Erro: "CORS policy"
- Verifique se `BACKEND_CORS_ORIGINS` contém a URL do frontend
- URLs devem ser completas (com `https://`)

### Aplicação não inicia
- Verifique os logs no painel do Render
- Verifique se o `startCommand` está correto
- Verifique se a porta está usando `$PORT` (variável do Render)

## Estrutura de Arquivos Necessários

```
backend/
├── main.py              # Arquivo principal da aplicação
├── requirements.txt     # Dependências Python
├── Procfile            # Comando de start (opcional se usar render.yaml)
├── render.yaml         # Configuração do Render (opcional)
├── render-build.sh     # Script de build (opcional)
├── alembic.ini         # Configuração do Alembic
└── alembic/            # Migrações do banco de dados
```

## Monitoramento

- **Logs**: Acesse os logs em tempo real no painel do Render
- **Health Check**: Use `/api/health` para verificar o status
- **Metrics**: Render fornece métricas básicas no dashboard

## Atualizações Futuras

Após configurar, qualquer push para a branch principal (ou a configurada) irá:
1. Disparar um novo build automaticamente
2. Fazer deploy da nova versão
3. Manter a aplicação online durante o deploy (zero downtime com planos pagos)

## Suporte

Para mais informações, consulte:
- [Documentação do Render](https://render.com/docs)
- [FastAPI no Render](https://render.com/docs/deploy-fastapi)

