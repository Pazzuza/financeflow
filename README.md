# 💎 FinanceFlow

Sistema completo de gestão financeira pessoal com potencial SaaS. Desenvolvido com FastAPI, SQLAlchemy, SQLite e TailwindCSS.

## ✨ Funcionalidades

- **Dashboard** com resumo financeiro do mês, gráficos e alertas
- **Transações** — receitas e despesas com filtros por período, categoria, tipo
- **Categorias** — personalizáveis com ícone e cor, com suporte a subcategorias
- **Relatórios** — análise por dia, semana, mês, trimestre, ano ou período customizado
- **Cartões de crédito** — controle de limite, fatura e parcelamentos
- **Metas financeiras** — acompanhamento de progresso com depósitos
- **Alertas** — notificações quando gastos atingem o limite configurado
- **Exportação CSV** — com filtros de período
- **Interface responsiva** — funciona perfeitamente no celular

## 🏗️ Arquitetura

```
financeflow/
├── main.py                    # Entry point FastAPI
├── init_db.py                 # Script de inicialização do banco
├── requirements.txt
├── app/
│   ├── core/
│   │   ├── config.py          # Settings / variáveis de ambiente
│   │   ├── database.py        # SQLAlchemy engine e sessão
│   │   └── security.py        # JWT, hash de senha, auth
│   ├── models/
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── transaction.py
│   │   ├── credit_card.py     # CreditCard + Invoice
│   │   └── goal.py            # FinancialGoal + Alert
│   ├── schemas/
│   │   └── __init__.py        # Pydantic schemas
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── transaction_service.py
│   │   ├── card_service.py
│   │   ├── goal_service.py
│   │   └── export_service.py
│   └── routes/
│       ├── auth.py
│       ├── dashboard.py
│       ├── transactions.py
│       ├── categories.py
│       ├── cards.py
│       ├── goals.py
│       ├── reports.py
│       └── settings.py
├── templates/
│   ├── base.html
│   ├── auth/       (login.html, register.html)
│   ├── dashboard/  (index.html)
│   ├── transactions/ (list.html, form.html, categories.html)
│   ├── cards/      (list.html, form.html, detail.html)
│   ├── goals/      (list.html)
│   ├── reports/    (index.html)
│   └── settings/   (index.html)
└── static/
    ├── css/
    ├── js/
    └── img/
```

## 🚀 Instalação e execução

### 1. Clone ou extraia o projeto

```bash
cd financeflow
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv

# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Inicialize o banco de dados

```bash
# Apenas criar as tabelas:
python init_db.py

# Criar tabelas + dados de demonstração:
python init_db.py --seed
```

### 5. Execute o servidor

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Acesse: **http://localhost:8000**

Se usou `--seed`, entre com:
- **Email:** demo@financeflow.com
- **Senha:** demo1234

## 🗄️ Migrar para PostgreSQL

1. Instale o driver: `pip install psycopg2-binary`
2. No `.env`, defina:
   ```
   DATABASE_URL=postgresql://usuario:senha@localhost/financeflow
   ```
3. Remova o `connect_args` de `database.py` (já preparado com comentário)
4. Execute `python init_db.py`

## 🛠️ Stack técnica

| Camada      | Tecnologia                          |
|-------------|-------------------------------------|
| Backend     | Python 3.10+ / FastAPI              |
| ORM         | SQLAlchemy 2.0                      |
| Banco       | SQLite (pronto para PostgreSQL)     |
| Auth        | JWT via python-jose + bcrypt        |
| Frontend    | HTML5 + TailwindCSS CDN             |
| Gráficos    | Chart.js 4.4                        |
| Templates   | Jinja2                              |

## 📱 Mobile-first

Interface 100% responsiva com sidebar colapsável, layout em grid adaptativo e touch-friendly.

## 🔐 Segurança

- Senhas hasheadas com bcrypt
- Autenticação via JWT em cookie httpOnly
- Todas as rotas verificam ownership do usuário (multi-tenant ready)
- Pronto para adicionar rate limiting e HTTPS

## 📦 Variáveis de ambiente (.env)

```env
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///./financeflow.db
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

## 🗺️ Roadmap SaaS

- [ ] Planos de assinatura (Stripe)
- [ ] Multi-usuário com times/família
- [ ] Importação de extratos bancários (OFX/CSV)
- [ ] App mobile (React Native / PWA)
- [ ] Integração com Open Banking Brasil
- [ ] IA para categorização automática
- [ ] Notificações por e-mail/WhatsApp

## 📦 Deploy (Render / Railway)

Defina as variáveis de ambiente no painel da plataforma:

`DATABASE_URL` (Postgres recomendado) e `SECRET_KEY`.

O `Procfile` já inicia o app com `uvicorn` escutando em `0.0.0.0:$PORT`.
