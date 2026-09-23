"""Initialize the PostgreSQL schema."""

from database import Database


if __name__ == '__main__':
    Database()
    print('PostgreSQL schema is ready.')
