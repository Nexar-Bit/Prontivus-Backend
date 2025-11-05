# Correção do Erro de Deploy - Greenlet

## Problema

O deploy está falhando porque o `greenlet==3.0.3` não é compatível com Python 3.13. O Render está usando Python 3.13.4 por padrão, mas o greenlet precisa ser compilado e não tem suporte para Python 3.13 na versão 3.0.3.

## Soluções Aplicadas

1. **Removida versão fixa do greenlet**: Mudado de `greenlet==3.0.3` para `greenlet` no `requirements.txt` para permitir que o pip instale a versão mais recente compatível.

2. **Criado `runtime.txt`**: Arquivo `runtime.txt` criado na raiz do backend para forçar Python 3.12.0.

## Próximos Passos

### Opção 1: Usar Python 3.12 (Recomendado)

No painel do Render:
1. Vá em **Settings** do seu Web Service
2. Em **Environment**, configure:
   - **Python Version**: `3.12.0` (ou deixe o `runtime.txt` fazer isso)

### Opção 2: Atualizar greenlet manualmente

Se ainda tiver problemas, você pode especificar uma versão mais recente do greenlet que suporte Python 3.13:

```txt
greenlet>=3.1.0
```

Ou remover completamente e deixar o SQLAlchemy gerenciar a dependência (ele já requer greenlet).

## Verificação

Após fazer push das alterações:
1. O Render deve detectar o `runtime.txt` e usar Python 3.12
2. O greenlet será instalado na versão mais recente compatível
3. O build deve completar com sucesso

## Nota

Se o Render ainda estiver usando Python 3.13, você pode:
- Configurar manualmente no dashboard do Render para usar Python 3.12
- Ou atualizar o greenlet para uma versão que suporte Python 3.13 (quando disponível)

