import logging
from decimal import Decimal
from typing import Sequence

from app.models.alert import PriceAlert
from app.models.product import MonitoredProduct
from app.models.user import User

logger = logging.getLogger("notification_service")


class NotificationService:
    @staticmethod
    def _evaluate_condition(current_price: Decimal, target_price: Decimal, condition: str) -> bool:
        """Avalia se a condição do alerta foi satisfeita."""
        if condition in ("<=", "less_than_or_equal"):
            return current_price <= target_price
        elif condition in ("<", "less_than"):
            return current_price < target_price
        elif condition in (">=", "greater_than_or_equal"):
            return current_price >= target_price
        elif condition in (">", "greater_than"):
            return current_price > target_price
        return False

    async def send_price_alert(
        self,
        user_email: str,
        product_title: str,
        product_url: str,
        current_price: Decimal,
        target_price: Decimal,
        condition: str,
    ) -> bool:
        """
        Simula o envio de e-mail / webhook de notificação com log estruturado.
        Em ambiente de produção real, aqui se integraria a um provedor como SendGrid, AWS SES ou Resend.
        """
        logger.info(
            "[DISPARO DE ALERTA DE PREÇO] "
            f"Destinatário: {user_email} | "
            f"Produto: '{product_title}' | "
            f"Preço Atual: R$ {current_price:.2f} | "
            f"Meta: {condition} R$ {target_price:.2f} | "
            f"URL: {product_url}"
        )
        return True

    async def process_product_alerts(
        self,
        product: MonitoredProduct,
        current_price: Decimal,
        alerts: Sequence[PriceAlert],
    ) -> int:
        """
        Processa todos os alertas vinculados ao produto com política anti-spam:
        - Se a condição for atingida e is_triggered for False: dispara e marca is_triggered = True.
        - Se a condição deixar de ser satisfeita (preço subiu): rearma o alerta (is_triggered = False).
        Retorna a quantidade de alertas disparados nesta execução.
        """
        triggered_count = 0

        for alert in alerts:
            condition_met = self._evaluate_condition(
                current_price=current_price,
                target_price=alert.target_price,
                condition=alert.condition,
            )

            if condition_met and not alert.is_triggered:
                user_email = alert.user.email if alert.user else "usuario@exemplo.com"
                product_name = product.title or product.url

                await self.send_price_alert(
                    user_email=user_email,
                    product_title=product_name,
                    product_url=product.url,
                    current_price=current_price,
                    target_price=alert.target_price,
                    condition=alert.condition,
                )

                alert.is_triggered = True
                triggered_count += 1

            elif not condition_met and alert.is_triggered:
                alert.is_triggered = False
                logger.info(
                    f"Alerta #{alert.id} rearmado. "
                    f"Preço atual (R$ {current_price:.2f}) não atende mais a {alert.condition} R$ {alert.target_price:.2f}."
                )

        return triggered_count