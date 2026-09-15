import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedData:
    price: Decimal
    in_stock: bool
    title: Optional[str] = None


class ScrapingError(Exception):
    """Exceção levantada quando ocorre falha temporária ou estrutural na coleta"""
    pass


class ScraperService:
    def _clean_price(self, price_str: str) -> Optional[Decimal]:
        if not price_str:
            return None

        match = re.search(r'[\d\.,]+', price_str)

        if not match:
            return None
        
        raw = match.group(0)

        if ',' in raw and '.' in raw:
            raw = raw.replace('.', '').replace(',', '.')
        elif ',' in raw:
            raw = raw.replace(',', '.')

        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return None

    async def scrape_product(self, url: str) -> ScrapedData:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning(f"Falha de rede ao acessar {url}: {exc}")
            raise ScrapingError(f"Erro ao acessar {url}: {exc}")

        soup = BeautifulSoup(response.text, "html.parser")

        title = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

        price = None

        # Tentativa 1: Meta tags
        meta_price = (
            soup.find("meta", property="product:price:amount")
            or soup.find("meta", property="og:price:amount")
            or soup.find("meta", itemprop="price")
        )
        if meta_price and meta_price.get("content"):
            price = self._clean_price(meta_price["content"])

        # Tentativa 2: Mercado Livre
        if not price:
            ml_elem = soup.find(class_="andes-money-amount__fraction")
            if ml_elem:
                ml_container = ml_elem.parent
                ml_cents = ml_container.find(class_="andes-money-amount__cents") if ml_container else None
                cents = f",{ml_cents.get_text(strip=True)}" if ml_cents else ",00"
                price = self._clean_price(f"{ml_elem.get_text(strip=True)}{cents}")

        # Tentativa 3: Amazon
        if not price:
            amz_offscreen = soup.find("span", class_="a-offscreen")
            if amz_offscreen:
                price = self._clean_price(amz_offscreen.get_text(strip=True))
            else:
                amz_whole = soup.find(class_="a-price-whole")
                if amz_whole:
                    amz_cents = soup.find(class_="a-price-fraction")
                    whole_clean = amz_whole.get_text(strip=True).rstrip(",.")
                    cents = f",{amz_cents.get_text(strip=True)}" if amz_cents else ",00"
                    price = self._clean_price(f"{whole_clean}{cents}")

        # Tentativa 4: Classe genérica
        if not price:
            generic_elem = soup.find(class_=re.compile(r"(price|preco|valor)", re.I))
            if generic_elem:
                price = self._clean_price(generic_elem.get_text())

        # Se não achar o preço, gera um log e lança ScrapingError
        if price is None:
            logger.warning(f"Preço não localizado na página: {url}")
            raise ScrapingError(f"Não foi possível extrair o preço da URL: {url}")

        # Verificação de disponibilidade/estoque
        in_stock = True
        avail_meta = (
            soup.find("link", itemprop="availability")
            or soup.find("meta", property="og:availability")
            or soup.find("meta", itemprop="availability")
        )
        if avail_meta:
            avail_val = (avail_meta.get("href") or avail_meta.get("content") or "").lower()
            if "outofstock" in avail_val or "discontinued" in avail_val:
                in_stock = False
            elif "instock" in avail_val:
                in_stock = True
        else:
            stock_container = (
                soup.find(id="availability")
                or soup.find(id="outOfStock")
                or soup.find(class_=re.compile(r"(ui-pdp-stock-information|out-of-stock|esgotado|indisponivel)", re.I))
            )
            if stock_container:
                container_text = stock_container.get_text().lower()
                out_of_stock_terms = ["indisponível", "esgotado", "out of stock", "sem estoque", "não temos previsão"]
                in_stock = not any(term in container_text for term in out_of_stock_terms)

        return ScrapedData(
            price=price,
            in_stock=in_stock,
            title=title,
        )