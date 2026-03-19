from sqlalchemy.orm import Session
from app.models.goal import FinancialGoal, Alert
from app.schemas import GoalCreate, GoalUpdate


def create_goal(db: Session, data: GoalCreate, user_id: int) -> FinancialGoal:
    goal = FinancialGoal(**data.dict(), user_id=user_id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goals(db: Session, user_id: int):
    return db.query(FinancialGoal).filter(FinancialGoal.user_id == user_id).order_by(FinancialGoal.created_at.desc()).all()


def update_goal(db: Session, goal_id: int, user_id: int, data: GoalUpdate) -> FinancialGoal:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id).first()
    if not goal:
        return None
    if data.current_amount is not None:
        goal.current_amount = data.current_amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
            alert = Alert(
                title="Meta atingida! 🎉",
                message=f"Parabéns! Você atingiu a meta: {goal.name}",
                type="goal_reached",
                user_id=user_id,
            )
            db.add(alert)
    if data.is_completed is not None:
        goal.is_completed = data.is_completed
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int, user_id: int) -> bool:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id).first()
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True


def get_alerts(db: Session, user_id: int, unread_only: bool = False):
    q = db.query(Alert).filter(Alert.user_id == user_id)
    if unread_only:
        q = q.filter(Alert.is_read == False)
    return q.order_by(Alert.created_at.desc()).limit(20).all()


def mark_alerts_read(db: Session, user_id: int):
    db.query(Alert).filter(Alert.user_id == user_id, Alert.is_read == False).update({"is_read": True})
    db.commit()
