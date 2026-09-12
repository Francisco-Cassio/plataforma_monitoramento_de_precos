import logging
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from typing import Sequence

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.models.alert import PriceAlert
from app.models.product import MonitoredProduct

logger = logging.getLogger("notification_service")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def format_currency_brl(value: Decimal | float) -> str:
    """Formata valores numéricos para a convenção brasileira: R$ 1.299,90."""
    formatted = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


class NotificationService:
    def __init__(self, template_env: Environment | None = None) -> None:
        self.jinja_env = template_env or jinja_env

    @staticmethod
    def _evaluate_condition(current_price: Decimal, target_price: Decimal, condition: str) -> bool:
        """Avalia se a condição de preço do alerta foi satisfeita."""
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
        Renderiza o template HTML e envia o e-mail de alerta via SMTP assíncrono,
        com fallback em texto puro e tratamento de exceções.
        """
        current_price_formatted = format_currency_brl(current_price)
        target_price_formatted = format_currency_brl(target_price)

        savings_formatted = None
        if target_price > current_price:
            savings = target_price - current_price
            savings_formatted = format_currency_brl(savings)

        if not settings.EMAILS_ENABLED:
            logger.info(
                f"[EMAIL DESATIVADO] Envio ignorado para {user_email} (Produto: '{product_title}')."
            )
            return True

        # Renderização do template HTML via Jinja2
        try:
            template = self.jinja_env.get_template("email/price_alert.html")
            html_content = template.render(
                product_title=product_title,
                current_price_formatted=current_price_formatted,
                target_price_formatted=target_price_formatted,
                savings_formatted=savings_formatted,
                product_url=product_url,
            )
        except Exception as e:
            logger.error(f"[ERRO TEMPLATE] Falha ao renderizar template de e-mail: {e}", exc_info=True)
            html_content = None

        # Fallback de texto simples
        plain_text = (
            f"Olá!\n\n"
            f"O produto que você está monitorando atingiu a meta no Vigia:\n"
            f"Produto: {product_title}\n"
            f"Preço Atual: {current_price_formatted}\n"
            f"Sua Meta: {target_price_formatted}\n"
        )
        if savings_formatted:
            plain_text += f"Economia estimada: {savings_formatted}\n"
        plain_text += f"\nAproveite a oferta acessando: {product_url}\n\nEquipe Vigia"

        message = EmailMessage()
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = user_email
        message["Subject"] = f"Meta Atingida: {product_title[:50]} por {current_price_formatted}"
        message.set_content(plain_text)

        if html_content:
            message.add_alternative(html_content, subtype="html")

        # Parâmetros de envio via aiosmtplib
        smtp_kwargs: dict = {
            "hostname": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "timeout": 15,
        }
        if settings.SMTP_TLS:
            smtp_kwargs["start_tls"] = True
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp_kwargs["username"] = settings.SMTP_USER
            smtp_kwargs["password"] = settings.SMTP_PASSWORD

        try:
            await aiosmtplib.send(message, **smtp_kwargs)
            logger.info(
                f"[EMAIL ENVIADO] Alerta disparado para {user_email} | "
                f"Produto: '{product_title}' | "
                f"Preço: {current_price_formatted} | "
                f"Meta: {condition} {target_price_formatted}"
            )
            return True
        except Exception as e:
            logger.error(
                f"[FALHA NO ENVIO DE EMAIL] Não foi possível enviar para {user_email} via SMTP ({settings.SMTP_HOST}:{settings.SMTP_PORT}): {e}"
            )
            return False

    async def process_product_alerts(
        self,
        product: MonitoredProduct,
        current_price: Decimal,
        alerts: Sequence[PriceAlert],
    ) -> int:
        """
        Processa os alertas vinculados ao produto com política anti-spam:
        - Condição atingida e não disparada: envia notificação e marca is_triggered = True.
        - Preço subiu acima da meta: rearma o alerta (is_triggered = False).
        Retorna o total de alertas disparados nesta execução.
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

                sent = await self.send_price_alert(
                    user_email=user_email,
                    product_title=product_name,
                    product_url=product.url,
                    current_price=current_price,
                    target_price=alert.target_price,
                    condition=alert.condition,
                )

                if sent:
                    alert.is_triggered = True
                    triggered_count += 1

            elif not condition_met and alert.is_triggered:
                alert.is_triggered = False
                logger.info(
                    f"Alerta #{alert.id} rearmado. "
                    f"Preço atual ({format_currency_brl(current_price)}) não atende mais a {alert.condition} {format_currency_brl(alert.target_price)}."
                )

        return triggered_count
