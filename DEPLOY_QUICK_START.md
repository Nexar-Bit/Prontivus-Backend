# Deploy Rápido - Render

## Checklist de Deploy

### 1. Preparar Variáveis de Ambiente

Execute para gerar uma SECRET_KEY:
```bash
python generate_secret_key.py
```

### 2. No Render Dashboard

#### Criar PostgreSQL Database:
- **Name**: `prontivus-database`
- **Database**: `prontivus_clinic`
- Copie a **Internal Database URL**

#### Criar Web Service:
- **Name**: `prontivus-backend`
- **Environment**: `Python 3`
- **Root Directory**: `backend`
- **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Variáveis de Ambiente no Render

Adicione estas variáveis no painel do Web Service:

```
DATABASE_URL=<Internal Database URL do PostgreSQL>
SECRET_KEY=<chave gerada pelo generate_secret_key.py>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=production
DEBUG=false
BACKEND_CORS_ORIGINS=https://seu-frontend.vercel.app
PYTHON_VERSION=3.12.0
```

### 4. Executar Migrações

No Shell do Render:
```bash
alembic upgrade head
```

### 5. Verificar

Acesse: `https://seu-backend.onrender.com/api/health`

---

**Nota**: Veja `RENDER_DEPLOY.md` para guia completo e detalhado.

