"""translate vendor names to english

Revision ID: 922ac3fa2764
Revises: beb54db85b7f
Create Date: 2026-09-11 17:46:28.688048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '922ac3fa2764'
down_revision: Union[str, Sequence[str], None] = 'beb54db85b7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Vendor name mapping: Chinese → English
VENDOR_RENAMES = [
    ("阿里云", "Alibaba Cloud"),
    ("华为云", "Huawei Cloud"),
    ("腾讯云", "Tencent Cloud"),
    ("火山引擎", "Volcengine"),
]


def upgrade() -> None:
    """Translate Chinese vendor names to English in database."""
    # aliyun_solutions.vendor
    for old, new in VENDOR_RENAMES:
        op.execute(
            f"UPDATE aliyun_solutions SET vendor = '{new}' WHERE vendor = '{old}'"
        )

    # competitor_news.vendor
    for old, new in VENDOR_RENAMES:
        op.execute(
            f"UPDATE competitor_news SET vendor = '{new}' WHERE vendor = '{old}'"
        )

    # cloud_vendor_news.vendor
    for old, new in VENDOR_RENAMES:
        op.execute(
            f"UPDATE cloud_vendor_news SET vendor = '{new}' WHERE vendor = '{old}'"
        )


def downgrade() -> None:
    """Revert English vendor names back to Chinese."""
    for old, new in VENDOR_RENAMES:
        op.execute(
            f"UPDATE aliyun_solutions SET vendor = '{old}' WHERE vendor = '{new}'"
        )
        op.execute(
            f"UPDATE competitor_news SET vendor = '{old}' WHERE vendor = '{new}'"
        )
        op.execute(
            f"UPDATE cloud_vendor_news SET vendor = '{old}' WHERE vendor = '{new}'"
        )
