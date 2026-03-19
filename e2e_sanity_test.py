import os
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient


def main() -> None:
    # Use a separate DB for e2e to avoid interference with dev runs.
    os.environ["DATABASE_URL"] = "sqlite:///./financeflow_test.db"

    from app.core.database import Base, SessionLocal, engine  # noqa: WPS433
    from app.models.user import User  # noqa: WPS433
    from app.models.category import Category  # noqa: WPS433
    from app.models.account import Account  # noqa: WPS433
    from app.models.credit_card import CreditCard  # noqa: WPS433
    from app.models.transaction import Transaction  # noqa: WPS433
    from app.models.goal import FinancialGoal  # noqa: WPS433
    from main import app  # noqa: WPS433

    Base.metadata.create_all(bind=engine)

    client = TestClient(app)

    email = f"u_{uuid.uuid4().hex[:10]}@example.com"
    password = "Pass1234!"

    # Register (creates default categories)
    resp = client.post(
        "/auth/register",
        data={
            "name": "Test User",
            "email": email,
            "password": password,
            "monthly_income": "5000.00",
        },
        allow_redirects=True,
    )
    assert resp.status_code == 200, f"register failed: {resp.status_code} {resp.text[:200]}"
    assert client.cookies.get("access_token"), "auth cookie not set"

    from jose import jwt  # noqa: WPS433
    from app.core.config import settings  # noqa: WPS433

    token = client.cookies.get("access_token")
    jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # Dashboard should load
    resp = client.get("/dashboard")
    assert resp.status_code == 200, f"dashboard failed: {resp.status_code}"

    # Categories should load (default + custom)
    resp = client.get("/categories")
    assert resp.status_code == 200, f"categories failed: {resp.status_code}"

    # Create a custom category
    resp = client.post(
        "/categories/new",
        data={
            "name": "Categoria E2E",
            "type": "expense",
            "color": "#ef4444",
            "icon": "🧪",
        },
        allow_redirects=True,
    )
    assert resp.status_code == 200, f"create category failed: {resp.status_code}"

    # Create a card
    resp = client.post(
        "/cards/new",
        data={
            "name": "Card E2E",
            "limit": "2000.00",
            "closing_day": "15",
            "due_day": "22",
            "color": "#8b5cf6",
            "last_four": "",
        },
        allow_redirects=True,
    )
    assert resp.status_code == 200, f"create card failed: {resp.status_code}"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user, "user not found in DB"

        expense_cat = (
            db.query(Category)
            .filter(Category.user_id == user.id, Category.type == "expense")
            .first()
        )
        assert expense_cat, "expense category not found"

        card = (
            db.query(CreditCard)
            .filter(CreditCard.user_id == user.id, CreditCard.is_active == True)  # noqa: E712
            .first()
        )
        assert card, "card not found"

        default_account = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id.desc()).first()
        assert default_account, "default account not found"

        # Create installments transaction (3 rows expected)
        today = datetime.now(timezone.utc).date().isoformat()
        resp = client.post(
            "/transactions/new",
            data={
                "description": "Compra parcelada E2E",
                "amount": "30.00",
                "type": "expense",
                "date": today,
                "notes": "",
                "category_id": str(expense_cat.id),
                "credit_card_id": str(card.id),
                "account_id": str(default_account.id),
                "installment_total": "3",
                "is_recurring": "false",
            },
            allow_redirects=False,
        )
        if resp.status_code not in (302, 303):
            lower = resp.text.lower()
            markers = ["falha", "dados inválidos".lower(), "inválid".lower(), "valor", "invalid account".lower()]
            idx = -1
            for m in markers:
                pos = lower.find(m)
                if pos != -1:
                    idx = pos
                    break
            snippet = resp.text[idx:idx+800] if idx != -1 else resp.text[:800]
            raise AssertionError(
                f"installments create failed: {resp.status_code}. Snippet: {snippet}"
            )

        txns_after_installments = (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id, Transaction.description.contains("Compra parcelada E2E"))
            .all()
        )
        assert len(txns_after_installments) == 3, f"expected 3 installments rows, got {len(txns_after_installments)}"

        # Create a single transaction (editable)
        resp = client.post(
            "/transactions/new",
            data={
                "description": "Compra avulsa E2E",
                "amount": "10.50",
                "type": "expense",
                "date": today,
                "notes": "",
                "category_id": str(expense_cat.id),
                "credit_card_id": str(card.id),
                "account_id": str(default_account.id),
                "installment_total": "",
                "is_recurring": "false",
            },
            allow_redirects=False,
        )
        assert resp.status_code in (302, 303), f"single create failed: {resp.status_code}"

        single_txn = (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id, Transaction.description == "Compra avulsa E2E")
            .first()
        )
        assert single_txn, "single transaction not created"

        # Edit it
        resp = client.get(f"/transactions/{single_txn.id}/edit")
        assert resp.status_code == 200, f"edit page failed: {resp.status_code}"

        resp = client.post(
            f"/transactions/{single_txn.id}/edit",
            data={
                "description": "Compra avulsa E2E (editada)",
                "amount": "12.00",
                "type": "expense",
                "date": today,
                "notes": "ok",
                "category_id": str(expense_cat.id),
                "credit_card_id": str(card.id),
                "account_id": str(default_account.id),
                "is_recurring": "false",
            },
            allow_redirects=False,
        )
        assert resp.status_code in (302, 303), f"edit post failed: {resp.status_code}"

        db.refresh(single_txn)
        edited = db.query(Transaction).filter(Transaction.id == single_txn.id).first()
        assert edited.description == "Compra avulsa E2E (editada)", "edit did not persist"

        # Delete it
        resp = client.post(f"/transactions/{single_txn.id}/delete", allow_redirects=False)
        assert resp.status_code in (302, 303), f"delete post failed: {resp.status_code}"
        deleted = db.query(Transaction).filter(Transaction.id == single_txn.id).first()
        assert deleted is None, "delete did not remove transaction"

        # Export CSV
        resp = client.get("/transactions/export")
        assert resp.status_code == 200, f"export failed: {resp.status_code}"
        assert "text/csv" in (resp.headers.get("content-type") or ""), "export content-type mismatch"
        assert "ID,Data" in resp.text, "export csv header missing"

        # Reports page should render
        resp = client.get("/reports?period=month")
        assert resp.status_code == 200, f"reports failed: {resp.status_code}"

        # Cards detail should render
        resp = client.get(f"/cards/{card.id}")
        assert resp.status_code == 200, f"card detail failed: {resp.status_code}"

        # Goals
        resp = client.post(
            "/goals/new",
            data={
                "name": "Meta E2E",
                "description": "",
                "target_amount": "1000.00",
                "current_amount": "0.00",
                "deadline": "",
                "icon": "🎯",
                "color": "#10b981",
            },
            allow_redirects=True,
        )
        assert resp.status_code == 200, f"goal create failed: {resp.status_code}"

        goal = db.query(FinancialGoal).filter(FinancialGoal.user_id == user.id, FinancialGoal.name == "Meta E2E").first()
        assert goal, "goal not created"

        resp = client.post(f"/goals/{goal.id}/deposit", data={"amount": "100.00"}, allow_redirects=False)
        assert resp.status_code in (302, 303), f"goal deposit failed: {resp.status_code}"

        db.expire_all()
        goal_after = db.query(FinancialGoal).filter(FinancialGoal.id == goal.id).first()
        assert goal_after.current_amount > 0, "goal deposit did not persist"

        resp = client.get("/goals")
        assert resp.status_code == 200, f"goals list failed: {resp.status_code}"
    finally:
        db.close()

    print("e2e_sanity_test: OK")


if __name__ == "__main__":
    main()

