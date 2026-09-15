from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.models.alert import PriceAlert
from app.models.product import MonitoredProduct
from app.services.notification_service import NotificationService, format_currency_brl


def test_format_currency_brl():
    assert format_currency_brl(Decimal("1299.90")) == "R$ 1.299,90"
    assert format_currency_brl(Decimal("45.00")) == "R$ 45,00"
    assert format_currency_brl(1000000.5) == "R$ 1.000.000,50"
    assert format_currency_brl(Decimal("0.99")) == "R$ 0,99"


def test_evaluate_condition():
    service = NotificationService()

    # Operador <= / less_than_or_equal
    assert service._evaluate_condition(Decimal("99.00"), Decimal("100.00"), "<=") is True
    assert service._evaluate_condition(Decimal("100.00"), Decimal("100.00"), "<=") is True
    assert service._evaluate_condition(Decimal("100.01"), Decimal("100.00"), "<=") is False

    # Operador < / less_than
    assert service._evaluate_condition(Decimal("99.99"), Decimal("100.00"), "<") is True
    assert service._evaluate_condition(Decimal("100.00"), Decimal("100.00"), "<") is False

    # Operador >= / greater_than_or_equal
    assert service._evaluate_condition(Decimal("100.00"), Decimal("100.00"), ">=") is True
    assert service._evaluate_condition(Decimal("105.00"), Decimal("100.00"), ">=") is True
    assert service._evaluate_condition(Decimal("99.00"), Decimal("100.00"), ">=") is False

    # Operador > / greater_than
    assert service._evaluate_condition(Decimal("100.01"), Decimal("100.00"), ">") is True
    assert service._evaluate_condition(Decimal("100.00"), Decimal("100.00"), ">") is False

    # Condição inválida
    assert service._evaluate_condition(Decimal("50.00"), Decimal("100.00"), "unknown") is False


async def test_send_price_alert_when_disabled():
    service = NotificationService()

    with patch.object(settings, "EMAILS_ENABLED", False):
        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            result = await service.send_price_alert(
                user_email="alvo@teste.com",
                product_title="Smartphone Pro",
                product_url="https://loja.com/smartphone",
                current_price=Decimal("1500.00"),
                target_price=Decimal("1600.00"),
                condition="<=",
            )
            assert result is True
            mock_send.assert_not_called()


async def test_send_price_alert_success_and_smtp_payload():
    service = NotificationService()

    with patch.object(settings, "EMAILS_ENABLED", True), \
         patch.object(settings, "SMTP_HOST", "mailpit"), \
         patch.object(settings, "SMTP_PORT", 1025), \
         patch.object(settings, "SMTP_USER", "user123"), \
         patch.object(settings, "SMTP_PASSWORD", "secret123"), \
         patch.object(settings, "SMTP_TLS", False):

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            result = await service.send_price_alert(
                user_email="consumidor@teste.com",
                product_title="Cadeira Ergonômica",
                product_url="https://loja.com/cadeira",
                current_price=Decimal("899.90"),
                target_price=Decimal("1000.00"),
                condition="<=",
            )

            assert result is True
            assert mock_send.await_count == 1

            # Inspeciona a chamada ao aiosmtplib.send
            args, kwargs = mock_send.call_args
            message = args[0]
            assert message["To"] == "consumidor@teste.com"
            assert "Cadeira Ergonômica" in message["Subject"]
            assert "R$ 899,90" in message["Subject"]
            assert kwargs["hostname"] == "mailpit"
            assert kwargs["port"] == 1025
            assert kwargs["username"] == "user123"
            assert kwargs["password"] == "secret123"

            # Inspeciona o corpo HTML renderizado via Jinja2
            html_payload = message.get_body(preferencelist=("html",)).get_content()
            assert "Cadeira Ergonômica" in html_payload
            assert "R$ 899,90" in html_payload
            assert "R$ 1.000,00" in html_payload
            assert "Economia: R$ 100,10" in html_payload
            assert "https://loja.com/cadeira" in html_payload


async def test_send_price_alert_smtp_failure_fallback():
    service = NotificationService()

    with patch.object(settings, "EMAILS_ENABLED", True):
        with patch("aiosmtplib.send", side_effect=ConnectionRefusedError("Connection refused")):
            result = await service.send_price_alert(
                user_email="consumidor@teste.com",
                product_title="Fone Bluetooth",
                product_url="https://loja.com/fone",
                current_price=Decimal("150.00"),
                target_price=Decimal("200.00"),
                condition="<=",
            )
            # Não deve propagar exceção que derrube o worker
            assert result is False


async def test_process_product_alerts_does_not_trigger_if_sending_fails():
    service = NotificationService()
    product = MagicMock(spec=MonitoredProduct, title="Monitor 4K", url="https://loja.com/monitor")
    alert = MagicMock(
        spec=PriceAlert,
        id=10,
        user=MagicMock(email="alerta@teste.com"),
        target_price=Decimal("2500.00"),
        condition="<=",
        is_triggered=False,
    )

    # Simula falha no envio do e-mail
    with patch.object(service, "send_price_alert", new_callable=AsyncMock, return_value=False):
        count = await service.process_product_alerts(product, Decimal("2400.00"), [alert])
        # Como o envio falhou, o alerta não deve ser marcado como disparado para tentar na próxima rodada
        assert count == 0
        assert alert.is_triggered is False

