"""Script utilitário para popular dados de teste e demonstração no Vigia.

Uso:
    python -m app.scripts.seed_demo
    python -m app.scripts.seed_demo --reset
    python -m app.scripts.seed_demo --email usuario@exemplo.com
    python -m app.scripts.seed_demo --create-user
    python -m app.scripts.seed_demo --clean
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.alert import PriceAlert
from app.models.price_history import PriceHistory
from app.models.product import MonitoredProduct
from app.models.user import User, UserRole

DEMO_USER_EMAIL = "demo@vigia.com"
DEMO_USER_PASSWORD = "password123"

DEMO_CATALOG = [
    {
        "title": "Monitor Gamer LG UltraGear 27' Full HD 144Hz 1ms IPS",
        "url": "https://www.mercadolivre.com.br/monitor-gamer-lg-ultragear-27-ips-144hz",
        "platform": "mercadolivre",
        "last_price": Decimal("1199.00"),
        "in_stock": True,
        "target_price": Decimal("1250.00"),
        "history": [
            (6, Decimal("1499.00"), True),
            (5, Decimal("1449.90"), True),
            (4, Decimal("1399.00"), True),
            (3, Decimal("1419.00"), True),
            (2, Decimal("1299.00"), True),
            (1, Decimal("1249.00"), True),
            (0, Decimal("1199.00"), True),
        ],
    },
    {
        "title": "Kindle Paperwhite 16 GB Tela 6.8' com Temperatura de Luz",
        "url": "https://www.amazon.com.br/kindle-paperwhite-16gb",
        "platform": "amazon",
        "last_price": Decimal("699.00"),
        "in_stock": True,
        "target_price": None,
        "history": [
            (5, Decimal("799.00"), True),
            (3, Decimal("749.00"), True),
            (1, Decimal("719.00"), True),
            (0, Decimal("699.00"), True),
        ],
    },
    {
        "title": "Console PlayStation 5 Slim Edição Digital com 2 Jogos",
        "url": "https://www.amazon.com.br/playstation-5-slim-edicao-digital",
        "platform": "amazon",
        "last_price": Decimal("3699.00"),
        "in_stock": True,
        "target_price": Decimal("3299.00"),
        "history": [
            (4, Decimal("3999.00"), True),
            (3, Decimal("3849.00"), True),
            (2, Decimal("3799.00"), True),
            (1, Decimal("3749.00"), True),
            (0, Decimal("3699.00"), True),
        ],
    },
    {
        "title": "Placa de Vídeo RTX 4060 8GB GDDR6 128-bit Dual Fan",
        "url": "https://www.kabum.com.br/produto/placa-de-video-rtx-4060-8gb",
        "platform": "kabum",
        "last_price": Decimal("2199.00"),
        "in_stock": False,
        "target_price": Decimal("2000.00"),
        "history": [
            (3, Decimal("2399.00"), True),
            (2, Decimal("2299.00"), True),
            (1, Decimal("2199.00"), True),
            (0, Decimal("2199.00"), False),
        ],
    },
]


async def clean_demo_data(session: AsyncSession) -> int:
    """Remove os produtos e registros do catálogo de demonstração."""
    demo_urls = [item["url"] for item in DEMO_CATALOG]
    result = await session.execute(
        delete(MonitoredProduct).where(MonitoredProduct.url.in_(demo_urls))
    )
    await session.commit()
    return result.rowcount


async def ensure_demo_user(session: AsyncSession) -> User:
    """Retorna o usuário de demonstração existente ou cria um novo."""
    result = await session.execute(
        select(User).where(User.email == DEMO_USER_EMAIL)
    )
    user = result.scalars().first()

    if not user:
        user = User(
            email=DEMO_USER_EMAIL,
            hashed_password=get_password_hash(DEMO_USER_PASSWORD),
            role=UserRole.REGULAR,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"[seed] Usuario de demonstracao criado: {DEMO_USER_EMAIL} (senha: {DEMO_USER_PASSWORD})")

    return user


async def populate_user_catalog(session: AsyncSession, user: User) -> None:
    """Insere o catálogo de produtos e histórico para o usuário especificado."""
    now = datetime.now(timezone.utc)
    created_count = 0
    skipped_count = 0

    print(f"[seed] Processando usuario: {user.email} (id={user.id})")

    for item in DEMO_CATALOG:
        query = select(MonitoredProduct).where(
            MonitoredProduct.url == item["url"],
            MonitoredProduct.user_id == user.id,
        )
        res = await session.execute(query)
        product = res.scalars().first()

        if product:
            print(f"  - Existente: {item['title'][:45]}...")
            skipped_count += 1
            continue

        product = MonitoredProduct(
            user_id=user.id,
            title=item["title"],
            url=item["url"],
            platform=item["platform"],
            last_price=item["last_price"],
            in_stock=item["in_stock"],
        )
        session.add(product)
        await session.flush()

        for days_ago, price, in_stock in item["history"]:
            captured_at = now - timedelta(days=days_ago)
            session.add(
                PriceHistory(
                    product_id=product.id,
                    price=price,
                    in_stock=in_stock,
                    captured_at=captured_at,
                )
            )

        if item.get("target_price"):
            session.add(
                PriceAlert(
                    product_id=product.id,
                    user_id=user.id,
                    target_price=item["target_price"],
                    condition="<=",
                )
            )

        created_count += 1
        print(f"  + Cadastrado: {item['title'][:45]}... ({len(item['history'])} historicos)")

    await session.commit()
    print(f"[seed] Concluido para {user.email}: {created_count} criados, {skipped_count} mantidos.")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Utilitario de carga de dados para demonstracao e testes da plataforma Vigia."
    )
    parser.add_argument(
        "--email",
        "-e",
        type=str,
        help="E-mail do usuario alvo para popular os dados.",
    )
    parser.add_argument(
        "--create-user",
        action="store_true",
        help=f"Cria o usuario de demonstracao '{DEMO_USER_EMAIL}' caso nao exista.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Limpa os dados de demonstracao e recria todo o catalogo do zero.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove todos os produtos de demonstracao existentes.",
    )

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if args.clean or args.reset:
            count = await clean_demo_data(session)
            print(f"[seed] Limpeza concluida: {count} produto(s) de demonstracao removido(s).")
            if args.clean:
                return

        users: List[User] = []

        if args.email:
            result = await session.execute(
                select(User).where(User.email == args.email)
            )
            found = result.scalars().first()
            if not found:
                print(f"[seed] Erro: Usuario '{args.email}' nao encontrado no banco de dados.", file=sys.stderr)
                sys.exit(1)
            users = [found]
        else:
            result = await session.execute(select(User).order_by(User.id.asc()))
            users = list(result.scalars().all())

            if not users or args.create_user:
                demo_user = await ensure_demo_user(session)
                if demo_user not in users:
                    users.append(demo_user)

        if not users:
            print("[seed] Nenhum usuario disponivel. Use a flag --create-user para criar um usuario de teste.", file=sys.stderr)
            sys.exit(1)

        for user in users:
            await populate_user_catalog(session, user)


if __name__ == "__main__":
    asyncio.run(main())
