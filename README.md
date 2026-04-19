# AuthApp — Login & Cadastro com NiceGUI

App de exemplo com sistema completo de autenticação usando NiceGUI + SQLite.

## Funcionalidades

- ✅ Cadastro de usuário (username, email, senha)
- ✅ Login com sessão persistente
- ✅ Senhas criptografadas (SHA-256 + salt)
- ✅ Dashboard protegido por login
- ✅ App de notas pessoais por usuário
- ✅ Logout

## Estrutura

```
main.py          # App principal
requirements.txt # Dependências
Procfile         # Comando de start (Railway)
railway.toml     # Configuração Railway
```

## Como rodar localmente

```bash
pip install -r requirements.txt
python main.py
```

Acesse: http://localhost:8080

## Deploy no Railway

### 1. Suba para o GitHub
```bash
git init
git add .
git commit -m "feat: auth app"
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

### 2. No Railway
1. Crie um novo projeto → "Deploy from GitHub repo"
2. Selecione o repositório
3. O Railway detecta o `Procfile` automaticamente

### 3. Variáveis de ambiente (recomendado)
No Railway → Settings → Variables, adicione:

| Variável    | Valor                              |
|-------------|------------------------------------|
| `SECRET_KEY` | Uma string aleatória longa (ex: `openssl rand -hex 32`) |
| `DB_PATH`   | `/data/users.db` (se usar volume)  |

### ⚠️ Sobre persistência do banco de dados

O Railway reinicia os containers periodicamente, o que **apaga arquivos locais**.
Para manter os dados entre deploys, adicione um **Volume** no Railway:

1. Railway → seu serviço → **Volumes** → New Volume
2. Mount path: `/data`
3. Defina `DB_PATH=/data/users.db` nas variáveis de ambiente

Sem volume, os dados são perdidos a cada redeploy (ok para testes).

## Tecnologias

- **NiceGUI** — UI web em Python puro
- **SQLite** — banco de dados local
- **SHA-256 + salt** — hash de senhas (sem dependências extras)
- **Railway** — deploy e hospedagem
