import csv
import io
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.services.transaction_service import get_transactions


def export_transactions_csv(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> str:
    transactions = get_transactions(db, user_id, start_date, end_date, limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Data", "Tipo", "Descrição", "Valor", "Categoria", "Cartão", "Parcela", "Recorrente", "Notas"])
    for t in transactions:
        cat_name = t.category.name if t.category else ""
        card_name = t.credit_card.name if t.credit_card else ""
        parcel = f"{t.installment_current}/{t.installment_total}" if t.installment_total else ""
        writer.writerow([
            t.id,
            t.date.strftime("%d/%m/%Y"),
            "Receita" if t.type == "income" else "Despesa",
            t.description,
            f"{t.amount:.2f}",
            cat_name,
            card_name,
            parcel,
            "Sim" if t.is_recurring else "Não",
            t.notes or "",
        ])
    return output.getvalue()
