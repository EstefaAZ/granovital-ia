#!/usr/bin/env python3
"""
Script to run database migration for adding user fields.
"""

import os
from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    # Create engine
    database_url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(database_url)

    # SQL to add columns
    sql = """
    -- Add tipo_documento column
    ALTER TABLE tbl_usuario
    ADD COLUMN tipo_documento VARCHAR(50) NULL COMMENT 'Tipo de documento: Cédula, Pasaporte' AFTER telefono;

    -- Add documento column
    ALTER TABLE tbl_usuario
    ADD COLUMN documento VARCHAR(20) NOT NULL UNIQUE COMMENT 'Número de documento de identidad' AFTER tipo_documento;

    -- Add municipio column
    ALTER TABLE tbl_usuario
    ADD COLUMN municipio VARCHAR(100) NULL COMMENT 'Municipio de residencia' AFTER documento;

    -- Add index for documento
    CREATE INDEX idx_usuario_documento ON tbl_usuario(documento);
    """

    try:
        with engine.connect() as conn:
            for statement in sql.strip().split(';'):
                if statement.strip():
                    conn.execute(text(statement.strip()))
                    print(f"Executed: {statement.strip()[:50]}...")
            conn.commit()
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        # If columns already exist, ignore
        if "Duplicate column" in str(e):
            print("Columns already exist, skipping migration.")
        else:
            raise

if __name__ == "__main__":
    run_migration()