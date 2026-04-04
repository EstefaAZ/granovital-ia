-- =============================================================
-- Migración: Agregar campos OAuth a tabla usuario
-- Fecha: $(date)
-- Descripción: Agrega campos para soporte de Google OAuth
-- =============================================================

-- Agregar columnas para OAuth
ALTER TABLE tbl_usuario
ADD COLUMN google_id VARCHAR(50) NULL UNIQUE COMMENT 'ID único de Google para usuarios OAuth',
ADD COLUMN provider VARCHAR(20) NOT NULL DEFAULT 'local' COMMENT 'Proveedor de autenticación: local, google',
ADD COLUMN avatar_url VARCHAR(500) NULL COMMENT 'URL del avatar del usuario (Google profile picture)';

-- Crear índices para mejor rendimiento
CREATE INDEX idx_usuario_google_id ON tbl_usuario(google_id);
CREATE INDEX idx_usuario_provider ON tbl_usuario(provider);

-- Agregar comentario a la tabla
ALTER TABLE tbl_usuario COMMENT 'Tabla de usuarios del sistema GranoVital IA - Soporta autenticación local y OAuth';

-- Verificar que el rol 'Consumidor' existe (necesario para usuarios OAuth)
INSERT IGNORE INTO tbl_rol (nombre_rol, descripcion, fecha_creacion)
VALUES ('Consumidor', 'Usuario final consumidor del sistema', NOW());

-- =============================================================
-- Script de rollback (en caso de ser necesario)
-- =============================================================
/*
-- Para hacer rollback de esta migración:
ALTER TABLE tbl_usuario
DROP COLUMN google_id,
DROP COLUMN provider,
DROP COLUMN avatar_url;

DROP INDEX idx_usuario_google_id ON tbl_usuario;
DROP INDEX idx_usuario_provider ON tbl_usuario;
*/