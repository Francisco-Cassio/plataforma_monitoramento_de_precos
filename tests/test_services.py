from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis import get_url_lock_key
from app.models.alert import PriceAlert
from app.models.product import MonitoredProduct
from app.services.notification_service import NotificationService
from app.services.scraper_service import ScraperService, ScrapingError


# Conversão de formatos de moeda para Decimal
def test_clean_price_formats():
    service = ScraperService()

    # Padrão brasileiro com separador de milhar e centavos
    assert service._clean_price("R$ 1.999,90") == Decimal("1999.90")
    assert service._clean_price("R$ 89,50") == Decimal("89.50")

    # Padrão americano / meta tag
    assert service._clean_price("120.00") == Decimal("120.00")

    # Entradas inválidas
    assert service._clean_price("Indisponível") is None
    assert service._clean_price("") is None


# Extração de dados da página do Mercado Livre
async def test_scrape_mercado_livre_html():
    service = ScraperService()
    html = """
    <html>
      <head><meta property="og:title" content="Monitor Gamer 27"></head>
      <body>
        <div class="ui-pdp-price__second-line">
          <span class="andes-money-amount">
            <span class="andes-money-amount__fraction">1.299</span>
            <span class="andes-money-amount__cents">99</span>
          </span>
        </div>
      </body>
    </html>
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        data = await service.scrape_product("https://produto.mercadolivre.com.br/MLB-123")
        assert data.price == Decimal("1299.99")
        assert data.title == "Monitor Gamer 27"
        assert data.in_stock is True


# Extração de dados da página da Amazon
async def test_scrape_amazon_html():
    service = ScraperService()
    html = """
    <html>
      <head><title>Echo Dot 5 | Amazon.com.br</title></head>
      <body>
        <span class="a-offscreen">R$ 399,00</span>
        <div id="availability"><span>Em estoque</span></div>
      </body>
    </html>
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        data = await service.scrape_product("https://amazon.com.br/dp/B0123")
        assert data.price == Decimal("399.00")
        assert data.in_stock is True


# Deve levantar ScrapingError se o preço não for encontrado
async def test_scrape_missing_price_raises_error():
    service = ScraperService()
    html = "<html><body><h1>Página sem preço</h1></body></html>"

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ScrapingError):
            await service.scrape_product("https://exemplo.com/sem-preco")


# Controle anti-spam e rearmamento automático de alertas
async def test_notification_anti_spam_and_auto_rearm():
    service = NotificationService()
    product = MagicMock(spec=MonitoredProduct, title="Notebook", url="https://loja.com/notebook")
    user = MagicMock(email="comprador@teste.com")
    alert = MagicMock(
        spec=PriceAlert,
        id=1,
        user=user,
        target_price=Decimal("4000.00"),
        condition="<=",
        is_triggered=False,
    )

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        # 1. Bateu a meta -> dispara notificação
        count1 = await service.process_product_alerts(product, Decimal("3900.00"), [alert])
        assert count1 == 1
        assert alert.is_triggered is True
        assert mock_send.await_count == 1

        # 2. Preço continua baixo -> não dispara de novo
        count2 = await service.process_product_alerts(product, Decimal("3800.00"), [alert])
        assert count2 == 0
        assert alert.is_triggered is True
        assert mock_send.await_count == 1

        # 3. Preço subiu -> rearma o alerta
        count3 = await service.process_product_alerts(product, Decimal("4200.00"), [alert])
        assert count3 == 0
        assert alert.is_triggered is False
        assert mock_send.await_count == 1


# Geração de chave determinística no Redis a partir da URL
def test_url_lock_key_determinism():
    k1 = get_url_lock_key("https://mercadolivre.com.br/item-1")
    k2 = get_url_lock_key("https://mercadolivre.com.br/item-1 ")
    assert k1 == k2
    assert k1.startswith("lock:scrape:")