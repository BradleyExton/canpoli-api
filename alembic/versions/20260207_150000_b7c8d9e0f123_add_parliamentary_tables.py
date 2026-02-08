"""Add parliamentary data tables."""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c8d9e0f123"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "representative_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("representative_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=200), nullable=False),
        sa.Column("role_type", sa.String(length=50), nullable=False),
        sa.Column("organization", sa.String(length=200), nullable=True),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["representative_id"], ["representatives.id"]),
    )
    op.create_index(
        "ix_representative_roles_representative_id",
        "representative_roles",
        ["representative_id"],
    )
    op.create_index(
        "ix_representative_roles_parl_session",
        "representative_roles",
        ["parliament", "session"],
    )
    op.create_index(
        "ix_representative_roles_is_current",
        "representative_roles",
        ["is_current"],
    )

    op.create_table(
        "party_standings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("party_id", sa.Integer(), nullable=True),
        sa.Column("party_name", sa.String(length=100), nullable=False),
        sa.Column("seat_count", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"]),
    )
    op.create_index("ix_party_standings_party_name", "party_standings", ["party_name"])
    op.create_index("ix_party_standings_parl_session", "party_standings", ["parliament", "session"])

    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legisinfo_id", sa.Integer(), nullable=True),
        sa.Column("bill_number", sa.String(length=20), nullable=False),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("title_fr", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=200), nullable=True),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("introduced_date", sa.Date(), nullable=True),
        sa.Column("latest_activity_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sponsor_hoc_id", sa.Integer(), nullable=True),
        sa.Column("sponsor_name", sa.String(length=200), nullable=True),
        sa.Column("sponsor_party", sa.String(length=100), nullable=True),
        sa.Column("summary_en", sa.Text(), nullable=True),
        sa.Column("summary_fr", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bills_bill_number", "bills", ["bill_number"])
    op.create_index("ix_bills_parl_session", "bills", ["parliament", "session"])
    op.create_index("ix_bills_latest_activity_date", "bills", ["latest_activity_date"])

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vote_number", sa.Integer(), nullable=False),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("vote_date", sa.Date(), nullable=True),
        sa.Column("subject_en", sa.Text(), nullable=True),
        sa.Column("subject_fr", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=100), nullable=True),
        sa.Column("yeas", sa.Integer(), nullable=True),
        sa.Column("nays", sa.Integer(), nullable=True),
        sa.Column("paired", sa.Integer(), nullable=True),
        sa.Column("bill_number", sa.String(length=20), nullable=True),
        sa.Column("motion_text", sa.Text(), nullable=True),
        sa.Column("sitting", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_votes_vote_number_parl_session",
        "votes",
        ["vote_number", "parliament", "session"],
    )
    op.create_index("ix_votes_vote_date", "votes", ["vote_date"])
    op.create_index("ix_votes_bill_number", "votes", ["bill_number"])

    op.create_table(
        "vote_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vote_id", sa.Integer(), nullable=False),
        sa.Column("representative_id", sa.Integer(), nullable=True),
        sa.Column("hoc_id", sa.Integer(), nullable=True),
        sa.Column("member_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=20), nullable=False),
        sa.Column("party_name", sa.String(length=100), nullable=True),
        sa.Column("riding_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vote_id"], ["votes.id"]),
        sa.ForeignKeyConstraint(["representative_id"], ["representatives.id"]),
    )
    op.create_index("ix_vote_members_vote_id", "vote_members", ["vote_id"])
    op.create_index(
        "ix_vote_members_representative_id",
        "vote_members",
        ["representative_id"],
    )

    op.create_table(
        "petitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("petition_number", sa.String(length=50), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=True),
        sa.Column("title_fr", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=200), nullable=True),
        sa.Column("presentation_date", sa.Date(), nullable=True),
        sa.Column("closing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signatures", sa.Integer(), nullable=True),
        sa.Column("sponsor_hoc_id", sa.Integer(), nullable=True),
        sa.Column("sponsor_name", sa.String(length=200), nullable=True),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_petitions_petition_number", "petitions", ["petition_number"])
    op.create_index("ix_petitions_presentation_date", "petitions", ["presentation_date"])

    op.create_table(
        "debates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parliament", sa.Integer(), nullable=True),
        sa.Column("session", sa.Integer(), nullable=True),
        sa.Column("sitting", sa.Integer(), nullable=True),
        sa.Column("debate_date", sa.Date(), nullable=True),
        sa.Column("language", sa.String(length=2), nullable=True),
        sa.Column("volume", sa.String(length=50), nullable=True),
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column("speaker_name", sa.String(length=200), nullable=True),
        sa.Column("document_url", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debates_parl_session", "debates", ["parliament", "session"])
    op.create_index("ix_debates_debate_date", "debates", ["debate_date"])
    op.create_index("ix_debates_sitting", "debates", ["sitting"])

    op.create_table(
        "debate_interventions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("debate_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("speaker_name", sa.String(length=200), nullable=True),
        sa.Column("speaker_affiliation", sa.String(length=300), nullable=True),
        sa.Column("floor_language", sa.String(length=2), nullable=True),
        sa.Column("timestamp", sa.String(length=5), nullable=True),
        sa.Column("order_of_business", sa.String(length=200), nullable=True),
        sa.Column("subject_title", sa.String(length=500), nullable=True),
        sa.Column("intervention_type", sa.String(length=50), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["debate_id"], ["debates.id"]),
    )
    op.create_index("ix_debate_interventions_debate_id", "debate_interventions", ["debate_id"])
    op.create_index("ix_debate_interventions_sequence", "debate_interventions", ["sequence"])

    op.create_table(
        "member_expenditures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("representative_id", sa.Integer(), nullable=True),
        sa.Column("hoc_id", sa.Integer(), nullable=True),
        sa.Column("member_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("fiscal_year", sa.String(length=9), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["representative_id"], ["representatives.id"]),
    )
    op.create_index(
        "ix_member_expenditures_representative_id",
        "member_expenditures",
        ["representative_id"],
    )
    op.create_index("ix_member_expenditures_fiscal_year", "member_expenditures", ["fiscal_year"])
    op.create_index(
        "ix_member_expenditures_period",
        "member_expenditures",
        ["period_start", "period_end"],
    )

    op.create_table(
        "house_officer_expenditures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("officer_name", sa.String(length=200), nullable=False),
        sa.Column("role_title", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("fiscal_year", sa.String(length=9), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_house_officer_expenditures_fiscal_year",
        "house_officer_expenditures",
        ["fiscal_year"],
    )
    op.create_index(
        "ix_house_officer_expenditures_period",
        "house_officer_expenditures",
        ["period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_house_officer_expenditures_period", table_name="house_officer_expenditures")
    op.drop_index("ix_house_officer_expenditures_fiscal_year", table_name="house_officer_expenditures")
    op.drop_table("house_officer_expenditures")

    op.drop_index("ix_member_expenditures_period", table_name="member_expenditures")
    op.drop_index("ix_member_expenditures_fiscal_year", table_name="member_expenditures")
    op.drop_index("ix_member_expenditures_representative_id", table_name="member_expenditures")
    op.drop_table("member_expenditures")

    op.drop_index("ix_debate_interventions_sequence", table_name="debate_interventions")
    op.drop_index("ix_debate_interventions_debate_id", table_name="debate_interventions")
    op.drop_table("debate_interventions")

    op.drop_index("ix_debates_sitting", table_name="debates")
    op.drop_index("ix_debates_debate_date", table_name="debates")
    op.drop_index("ix_debates_parl_session", table_name="debates")
    op.drop_table("debates")

    op.drop_index("ix_petitions_presentation_date", table_name="petitions")
    op.drop_index("ix_petitions_petition_number", table_name="petitions")
    op.drop_table("petitions")

    op.drop_index("ix_vote_members_representative_id", table_name="vote_members")
    op.drop_index("ix_vote_members_vote_id", table_name="vote_members")
    op.drop_table("vote_members")

    op.drop_index("ix_votes_bill_number", table_name="votes")
    op.drop_index("ix_votes_vote_date", table_name="votes")
    op.drop_index("ix_votes_vote_number_parl_session", table_name="votes")
    op.drop_table("votes")

    op.drop_index("ix_bills_latest_activity_date", table_name="bills")
    op.drop_index("ix_bills_parl_session", table_name="bills")
    op.drop_index("ix_bills_bill_number", table_name="bills")
    op.drop_table("bills")

    op.drop_index("ix_party_standings_parl_session", table_name="party_standings")
    op.drop_index("ix_party_standings_party_name", table_name="party_standings")
    op.drop_table("party_standings")

    op.drop_index("ix_representative_roles_is_current", table_name="representative_roles")
    op.drop_index("ix_representative_roles_parl_session", table_name="representative_roles")
    op.drop_index("ix_representative_roles_representative_id", table_name="representative_roles")
    op.drop_table("representative_roles")
