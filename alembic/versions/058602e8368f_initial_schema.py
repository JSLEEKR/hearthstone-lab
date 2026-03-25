"""initial schema

Revision ID: 058602e8368f
Revises:
Create Date: 2026-03-24 21:47:17.657631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '058602e8368f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cards',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('card_id', sa.String(), nullable=False),
    sa.Column('dbf_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('name_ko', sa.String(), nullable=False),
    sa.Column('card_type', sa.String(), nullable=False),
    sa.Column('hero_class', sa.String(), nullable=False),
    sa.Column('mana_cost', sa.Integer(), nullable=False),
    sa.Column('attack', sa.Integer(), nullable=True),
    sa.Column('health', sa.Integer(), nullable=True),
    sa.Column('durability', sa.Integer(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('rarity', sa.String(), nullable=False),
    sa.Column('set_name', sa.String(), nullable=False),
    sa.Column('mechanics', sa.JSON(), nullable=True),
    sa.Column('collectible', sa.Boolean(), nullable=True),
    sa.Column('is_standard', sa.Boolean(), nullable=True),
    sa.Column('json_data', sa.JSON(), nullable=True),
    sa.Column('image_url', sa.String(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dbf_id')
    )
    op.create_index(op.f('ix_cards_card_id'), 'cards', ['card_id'], unique=True)
    op.create_index('ix_cards_class_cost', 'cards', ['hero_class', 'mana_cost'], unique=False)
    op.create_table('decks',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('hero_class', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('archetype', sa.String(), nullable=True),
    sa.Column('format', sa.String(), nullable=False),
    sa.Column('deckstring', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('deck_cards',
    sa.Column('deck_id', sa.Integer(), nullable=False),
    sa.Column('card_id', sa.Integer(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.CheckConstraint('count >= 1 AND count <= 2', name='ck_deck_cards_count'),
    sa.ForeignKeyConstraint(['card_id'], ['cards.id'], ),
    sa.ForeignKeyConstraint(['deck_id'], ['decks.id'], ),
    sa.PrimaryKeyConstraint('deck_id', 'card_id')
    )
    op.create_index('ix_deck_cards_card_id', 'deck_cards', ['card_id'], unique=False)
    op.create_table('simulations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('deck_a_id', sa.Integer(), nullable=False),
    sa.Column('deck_b_id', sa.Integer(), nullable=False),
    sa.Column('winner_id', sa.Integer(), nullable=True),
    sa.Column('turns', sa.Integer(), nullable=False),
    sa.Column('played_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['deck_a_id'], ['decks.id'], ),
    sa.ForeignKeyConstraint(['deck_b_id'], ['decks.id'], ),
    sa.ForeignKeyConstraint(['winner_id'], ['decks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_simulations_deck_a', 'simulations', ['deck_a_id'], unique=False)
    op.create_index('ix_simulations_deck_b', 'simulations', ['deck_b_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_simulations_deck_b', table_name='simulations')
    op.drop_index('ix_simulations_deck_a', table_name='simulations')
    op.drop_table('simulations')
    op.drop_index('ix_deck_cards_card_id', table_name='deck_cards')
    op.drop_table('deck_cards')
    op.drop_table('decks')
    op.drop_index('ix_cards_class_cost', table_name='cards')
    op.drop_index(op.f('ix_cards_card_id'), table_name='cards')
    op.drop_table('cards')
