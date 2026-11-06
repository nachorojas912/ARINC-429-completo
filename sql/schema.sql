CREATE DATABASE IF NOT EXISTS arinc429
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE arinc429;

CREATE TABLE IF NOT EXISTS instrumentos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL UNIQUE,
  valor_minimo DECIMAL(12, 4) NOT NULL,
  valor_maximo DECIMAL(12, 4) NOT NULL,
  unidad VARCHAR(24) NOT NULL,
  label SMALLINT UNSIGNED NOT NULL,
  sdi TINYINT UNSIGNED NOT NULL DEFAULT 0,
  ssm TINYINT UNSIGNED NOT NULL DEFAULT 0,
  escala DECIMAL(16, 8) NOT NULL DEFAULT 1,
  `offset` DECIMAL(16, 8) NOT NULL DEFAULT 0,
  CONSTRAINT chk_instrumentos_rango CHECK (valor_minimo <= valor_maximo),
  CONSTRAINT chk_instrumentos_label CHECK (label BETWEEN 0 AND 255),
  CONSTRAINT chk_instrumentos_sdi CHECK (sdi BETWEEN 0 AND 3),
  CONSTRAINT chk_instrumentos_ssm CHECK (ssm BETWEEN 0 AND 3),
  CONSTRAINT chk_instrumentos_escala CHECK (escala > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS envios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  instrumento_id INT NOT NULL,
  valor DECIMAL(12, 4) NOT NULL,
  palabra_binaria CHAR(32) NOT NULL,
  palabra_hexadecimal CHAR(10) NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_envios_instrumento
    FOREIGN KEY (instrumento_id) REFERENCES instrumentos(id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transmisiones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  envio_id INT NULL,
  instrumento_nombre VARCHAR(120) NOT NULL,
  valor DECIMAL(12, 4) NOT NULL,
  puerto VARCHAR(32) NOT NULL,
  modo VARCHAR(16) NOT NULL,
  velocidad INT NOT NULL,
  orden_bytes VARCHAR(8) NOT NULL,
  palabra_binaria CHAR(32) NOT NULL,
  palabra_hexadecimal CHAR(10) NOT NULL,
  bytes_hexadecimales VARCHAR(11) NOT NULL,
  resultado VARCHAR(16) NOT NULL,
  mensaje TEXT NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_transmisiones_envio
    FOREIGN KEY (envio_id) REFERENCES envios(id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reproducciones_audio (
  id INT AUTO_INCREMENT PRIMARY KEY,
  envio_id INT NULL,
  instrumento_nombre VARCHAR(120) NOT NULL,
  valor DECIMAL(12, 4) NOT NULL,
  dispositivo VARCHAR(160) NOT NULL,
  modo VARCHAR(16) NOT NULL,
  amplitud DECIMAL(5, 4) NOT NULL,
  frecuencia_muestreo INT NOT NULL,
  muestras_por_bit INT NOT NULL,
  ritmo_demostracion DECIMAL(12, 4) NOT NULL,
  palabra_binaria CHAR(32) NOT NULL,
  resultado VARCHAR(16) NOT NULL,
  mensaje TEXT NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reproducciones_audio_envio
    FOREIGN KEY (envio_id) REFERENCES envios(id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;
