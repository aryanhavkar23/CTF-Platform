from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class Category(TimeStampedModel):
    __tablename__ = "categories"

    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    challenges = relationship("Challenge", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category name={self.name!r}>"
