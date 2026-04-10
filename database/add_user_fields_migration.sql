-- Migration: Add missing fields to tbl_usuario
-- Date: 2026-04-09
-- Description: Add tipo_documento, documento, municipio fields to tbl_usuario table

USE granovital_ia;

-- Add tipo_documento column
ALTER TABLE tbl_usuario
ADD COLUMN tipo_documento VARCHAR(50) NULL COMMENT 'Tipo de documento: Cédula, Pasaporte' AFTER telefono;

-- Add documento column
ALTER TABLE tbl_usuario
ADD COLUMN documento VARCHAR(20) NOT NULL UNIQUE COMMENT 'Número de documento de identidad' AFTER tipo_documento;

-- Add municipio column
ALTER TABLE tbl_usuario
ADD COLUMN municipio VARCHAR(100) NULL COMMENT 'Municipio de residencia' AFTER documento;

-- Add index for documento for better performance
CREATE INDEX idx_usuario_documento ON tbl_usuario(documento);

COMMIT;