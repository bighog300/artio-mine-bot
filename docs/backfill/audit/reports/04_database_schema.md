=== CHECKING DATABASE TABLES ===

⚠️ docker/compose not available; using static model inspection only.

Static model inspection:
186:    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
187:    completeness_details: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
220:        Index("ix_records_completeness_score", "completeness_score"),
679:    __tablename__ = "backfill_campaigns"
712:    __tablename__ = "backfill_jobs"
743:    __tablename__ = "backfill_schedules"
769:    __tablename__ = "backfill_policies"
186:    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
187:    completeness_details: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
220:        Index("ix_records_completeness_score", "completeness_score"),
