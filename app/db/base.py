from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# 👇 Import models AFTER Base is defined
from app.models.user import User
from app.models.school import School
