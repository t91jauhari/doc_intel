"""Explicit private baseline import; requires migrated, explicitly named database."""
import argparse
import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .dataset_sources import import_bundled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-database', required=True)
    args = parser.parse_args()
    url = os.environ.get('REFACTOR_DATABASE_URL')
    if not url:
        parser.error('Set REFACTOR_DATABASE_URL explicitly.')
    engine = create_engine(url)
    try:
        if engine.dialect.name != 'postgresql':
            raise ValueError('Baseline import requires PostgreSQL.')
        with Session(engine) as session, session.begin():
            if session.scalar(text('SELECT current_database()')) != args.expected_database:
                raise ValueError('Connected database does not match the explicit target.')
            organizations = list(session.scalars(text('SELECT DISTINCT org FROM configurations ORDER BY org')))
            count = sum(len(import_bundled(session, organization)) for organization in organizations)
        print(json.dumps({'organizations': len(organizations), 'datasets_verified': count}))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
