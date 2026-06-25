from typing import Any

from sqlmodel import Session, select

from ...models import Cart
from ._helpers import auth_error


class ExecutorBase:
    def __init__(self, db: Session, user_id: int | None = None):
        self.db = db
        self.user_id = user_id

    def _require_auth(self) -> dict[str, Any] | None:
        if self.user_id is None:
            return auth_error()
        return None

    def _get_or_create_cart(self) -> Cart:
        cart = self.db.exec(select(Cart).where(Cart.user_id == self.user_id)).first()
        if not cart:
            cart = Cart(user_id=self.user_id)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart
