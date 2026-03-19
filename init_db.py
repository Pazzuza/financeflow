#!/usr/bin/env python3
"""
Script de inicialização do banco de dados.
Cria todas as tabelas e opcionalmente insere dados de demonstração.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
import app.models  # noqa - registers all models


def init_db():
    print("Criando tabelas do banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("Banco de dados inicializado com sucesso!")
    print("Arquivo: financeflow.db")


def seed_demo():
    from app.core.database import SessionLocal
    from app.services.auth_service import create_user, authenticate_user
    from app.services.transaction_service import create_transaction
    from app.services.card_service import create_card
    from app.services.goal_service import create_goal
    from app.schemas import UserCreate, TransactionCreate, CreditCardCreate, GoalCreate
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    db = SessionLocal()
    try:
        # Create demo user
        from app.models.user import User
        existing = db.query(User).filter(User.email == "demo@financeflow.com").first()
        if existing:
            print("Aviso: Usuário demo já existe.")
            return

        print("Inserindo dados de demonstracao...")
        user = create_user(db, UserCreate(
            name="Demo User",
            email="demo@financeflow.com",
            password="demo1234",
            monthly_income=8000.0,
        ))

        from app.models.account import Account
        default_account = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id.desc()).first()
        if not default_account:
            raise RuntimeError("Default account not created for demo user")

        # Credit card
        card = create_card(db, CreditCardCreate(
            name="Nubank",
            limit=5000.0,
            closing_day=15,
            due_day=22,
            color="#8b5cf6",
            last_four="1234",
        ), user.id)

        # Get categories
        from app.models.category import Category
        cats = {c.name: c.id for c in db.query(Category).filter(Category.user_id == user.id).all()}

        today = datetime.utcnow()

        # Transactions
        sample_transactions = [
            ("Salário", 8000.0, "income", 0, cats.get("Salário"), None),
            ("Freelance projeto web", 1500.0, "income", 2, cats.get("Freelance"), None),
            ("Aluguel", 1800.0, "expense", 1, cats.get("Moradia"), None),
            ("Supermercado", 650.0, "expense", 3, cats.get("Alimentação"), None),
            ("iFood", 89.90, "expense", 5, cats.get("Alimentação"), None),
            ("Uber", 45.0, "expense", 7, cats.get("Transporte"), None),
            ("Gasolina", 180.0, "expense", 8, cats.get("Transporte"), None),
            ("Academia", 99.9, "expense", 4, cats.get("Saúde"), None),
            ("Netflix", 39.9, "expense", 6, cats.get("Lazer"), None),
            ("Spotify", 21.9, "expense", 6, cats.get("Lazer"), None),
            ("Conta de luz", 140.0, "expense", 9, cats.get("Contas"), None),
            ("Internet", 89.9, "expense", 9, cats.get("Contas"), None),
            ("Camiseta", 79.9, "expense", 10, cats.get("Vestuário"), card.id),
            ("Restaurante jantar", 120.0, "expense", 12, cats.get("Alimentação"), card.id),
            ("Curso Python", 297.0, "expense", 15, cats.get("Educação"), None),
        ]

        for desc, amount, ttype, day_offset, cat_id, card_id in sample_transactions:
            create_transaction(db, TransactionCreate(
                description=desc,
                amount=amount,
                type=ttype,
                date=today - relativedelta(days=day_offset),
                category_id=cat_id,
                credit_card_id=card_id,
                account_id=default_account.id,
            ), user.id)

        # Last month
        last_month = today - relativedelta(months=1)
        for desc, amount, ttype, cat_name in [
            ("Salário", 8000.0, "income", "Salário"),
            ("Aluguel", 1800.0, "expense", "Moradia"),
            ("Supermercado", 720.0, "expense", "Alimentação"),
            ("Transporte", 210.0, "expense", "Transporte"),
            ("Lazer", 350.0, "expense", "Lazer"),
        ]:
            create_transaction(db, TransactionCreate(
                description=desc,
                amount=amount,
                type=ttype,
                date=datetime(last_month.year, last_month.month, 5),
                category_id=cats.get(cat_name),
                account_id=default_account.id,
            ), user.id)

        # Goals
        create_goal(db, GoalCreate(
            name="Reserva de emergência",
            description="6 meses de despesas guardadas",
            target_amount=15000.0,
            current_amount=4200.0,
            icon="🛡️",
            color="#6366f1",
        ), user.id)

        create_goal(db, GoalCreate(
            name="Viagem para Europa",
            description="Visitando Portugal e Espanha",
            target_amount=12000.0,
            current_amount=2500.0,
            deadline=datetime(today.year + 1, 6, 1),
            icon="✈️",
            color="#f59e0b",
        ), user.id)

        create_goal(db, GoalCreate(
            name="Notebook novo",
            target_amount=5000.0,
            current_amount=1800.0,
            icon="💻",
            color="#10b981",
        ), user.id)

        print("Dados de demo inseridos!")
        print("Login: demo@financeflow.com")
        print("Senha: demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    if "--seed" in sys.argv or "-s" in sys.argv:
        seed_demo()
    else:
        print("\nPara inserir dados de demonstracao: python init_db.py --seed")
