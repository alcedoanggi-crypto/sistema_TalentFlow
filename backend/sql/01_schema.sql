-- =====================================================================
-- TalentFlow · Esquema PostgreSQL (fuente de verdad del modelo de datos)
-- Los modelos SQLAlchemy en app/models reflejan estas tablas.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configuración de búsqueda full-text en español que ignora tildes:
-- "programación" y "programacion" producen el mismo lexema.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'tf_es') THEN
    CREATE TEXT SEARCH CONFIGURATION tf_es (COPY = spanish);
    ALTER TEXT SEARCH CONFIGURATION tf_es
      ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- Organización y usuarios internos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS empresas (
  id            SERIAL PRIMARY KEY,
  nombre        VARCHAR(150) NOT NULL,
  slug          VARCHAR(80)  NOT NULL UNIQUE,
  descripcion   TEXT,
  sitio_web     VARCHAR(255),
  color_marca   VARCHAR(7) NOT NULL DEFAULT '#4f46e5',
  creada_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usuarios (
  id             SERIAL PRIMARY KEY,
  empresa_id     INT NOT NULL REFERENCES empresas(id),
  nombre         VARCHAR(120) NOT NULL,
  email          VARCHAR(160) NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,
  rol            VARCHAR(20)  NOT NULL CHECK (rol IN ('admin','reclutador','entrevistador')),
  activo         BOOLEAN NOT NULL DEFAULT true,
  creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Habilidades normalizadas + sinónimos ("JS" = "JavaScript")
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS habilidades (
  id         SERIAL PRIMARY KEY,
  nombre     VARCHAR(80) NOT NULL UNIQUE,      -- forma canónica
  categoria  VARCHAR(40) NOT NULL DEFAULT 'tecnica'
);

CREATE TABLE IF NOT EXISTS habilidad_sinonimos (
  id            SERIAL PRIMARY KEY,
  habilidad_id  INT NOT NULL REFERENCES habilidades(id) ON DELETE CASCADE,
  sinonimo      VARCHAR(80) NOT NULL,           -- normalizado: minúsculas, sin tildes
  CONSTRAINT uq_sinonimo UNIQUE (sinonimo)
);
CREATE INDEX IF NOT EXISTS ix_sinonimos_habilidad ON habilidad_sinonimos(habilidad_id);

-- ---------------------------------------------------------------------
-- Vacantes
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vacantes (
  id                    SERIAL PRIMARY KEY,
  empresa_id            INT NOT NULL REFERENCES empresas(id),
  reclutador_id         INT REFERENCES usuarios(id) ON DELETE SET NULL,
  titulo                VARCHAR(150) NOT NULL,
  slug                  VARCHAR(170) NOT NULL,
  departamento          VARCHAR(80),
  ubicacion             VARCHAR(120),
  modalidad             VARCHAR(12) NOT NULL CHECK (modalidad IN ('remoto','hibrido','presencial')),
  tipo_contrato         VARCHAR(30) NOT NULL DEFAULT 'tiempo_completo',
  descripcion           TEXT NOT NULL,
  requisitos            TEXT,
  experiencia_min_anios NUMERIC(4,1) NOT NULL DEFAULT 0,
  salario_min           NUMERIC(12,2),
  salario_max           NUMERIC(12,2),
  moneda                VARCHAR(3) NOT NULL DEFAULT 'USD',
  mostrar_salario       BOOLEAN NOT NULL DEFAULT true,
  estado                VARCHAR(12) NOT NULL DEFAULT 'borrador'
                          CHECK (estado IN ('borrador','publicada','cerrada')),
  publicada_en          TIMESTAMPTZ,
  cerrada_en            TIMESTAMPTZ,
  creada_en             TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_vacante_slug UNIQUE (empresa_id, slug),
  CONSTRAINT ck_salario CHECK (salario_min IS NULL OR salario_max IS NULL OR salario_min <= salario_max)
);
CREATE INDEX IF NOT EXISTS ix_vacantes_estado ON vacantes(empresa_id, estado);

CREATE TABLE IF NOT EXISTS vacante_habilidades (
  vacante_id    INT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
  habilidad_id  INT NOT NULL REFERENCES habilidades(id),
  tipo          VARCHAR(12) NOT NULL CHECK (tipo IN ('obligatoria','deseable')),
  PRIMARY KEY (vacante_id, habilidad_id)
);

-- ---------------------------------------------------------------------
-- Candidatos (datos personales: sujetos a consentimiento y retención)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidatos (
  id                      SERIAL PRIMARY KEY,
  nombre                  VARCHAR(150) NOT NULL,
  email                   VARCHAR(160) NOT NULL UNIQUE,
  telefono                VARCHAR(40),
  ubicacion               VARCHAR(120),
  linkedin                VARCHAR(255),
  experiencia_anios       NUMERIC(4,1) NOT NULL DEFAULT 0,
  token_portal            VARCHAR(64) NOT NULL UNIQUE,     -- acceso sin contraseña al portal
  consentimiento_en       TIMESTAMPTZ NOT NULL,
  consentimiento_version  VARCHAR(10) NOT NULL,
  consentimiento_ip       VARCHAR(45),
  retener_hasta           DATE NOT NULL,                   -- retención limitada
  anonimizado_en          TIMESTAMPTZ,
  creado_en               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_candidatos_retencion ON candidatos(retener_hasta) WHERE anonimizado_en IS NULL;

CREATE TABLE IF NOT EXISTS candidato_habilidades (
  candidato_id  INT NOT NULL REFERENCES candidatos(id) ON DELETE CASCADE,
  habilidad_id  INT NOT NULL REFERENCES habilidades(id),
  origen        VARCHAR(10) NOT NULL DEFAULT 'cv' CHECK (origen IN ('cv','manual')),
  PRIMARY KEY (candidato_id, habilidad_id)
);

-- Documentos (CV). El texto extraído se indexa con un tsvector generado + GIN.
CREATE TABLE IF NOT EXISTS documentos (
  id               SERIAL PRIMARY KEY,
  candidato_id     INT NOT NULL REFERENCES candidatos(id) ON DELETE CASCADE,
  tipo             VARCHAR(12) NOT NULL DEFAULT 'cv' CHECK (tipo IN ('cv','otro')),
  nombre_original  VARCHAR(255) NOT NULL,
  ruta             VARCHAR(255) NOT NULL,
  mime             VARCHAR(120) NOT NULL,
  tamano_bytes     INT NOT NULL,
  texto_extraido   TEXT,
  datos_extraidos  JSONB NOT NULL DEFAULT '{}'::jsonb,
  tsv              TSVECTOR GENERATED ALWAYS AS (to_tsvector('tf_es'::regconfig, coalesce(texto_extraido, ''))) STORED,
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documentos_tsv  ON documentos USING GIN (tsv);
CREATE INDEX IF NOT EXISTS ix_documentos_json ON documentos USING GIN (datos_extraidos jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_documentos_candidato ON documentos(candidato_id);

-- ---------------------------------------------------------------------
-- Pipeline
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etapas (
  id        SERIAL PRIMARY KEY,
  codigo    VARCHAR(30) NOT NULL UNIQUE,
  nombre    VARCHAR(60) NOT NULL,
  orden     SMALLINT NOT NULL UNIQUE,
  es_final  BOOLEAN NOT NULL DEFAULT false,
  color     VARCHAR(7) NOT NULL DEFAULT '#64748b'
);

INSERT INTO etapas (codigo, nombre, orden, es_final, color) VALUES
  ('postulado',           'Postulado',           1, false, '#64748b'),
  ('revision',            'Revisión',            2, false, '#0ea5e9'),
  ('entrevista_tecnica',  'Entrevista técnica',  3, false, '#8b5cf6'),
  ('entrevista_rh',       'Entrevista RH',       4, false, '#d946ef'),
  ('oferta',              'Oferta',              5, false, '#f59e0b'),
  ('contratado',          'Contratado',          6, true,  '#10b981'),
  ('descartado',          'Descartado',          7, true,  '#ef4444')
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS postulaciones (
  id               SERIAL PRIMARY KEY,
  vacante_id       INT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
  candidato_id     INT NOT NULL REFERENCES candidatos(id) ON DELETE CASCADE,
  documento_id     INT REFERENCES documentos(id) ON DELETE SET NULL,
  etapa_id         INT NOT NULL REFERENCES etapas(id),
  fuente           VARCHAR(20) NOT NULL DEFAULT 'portal_empleo'
                     CHECK (fuente IN ('portal_empleo','linkedin','indeed','referido','evento','otro')),
  carta            TEXT,
  match_score      NUMERIC(5,2) NOT NULL DEFAULT 0,
  match_detalle    JSONB NOT NULL DEFAULT '{}'::jsonb,
  posicion_kanban  INT NOT NULL DEFAULT 0,
  motivo_descarte  VARCHAR(255),
  creada_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizada_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
  contratado_en    TIMESTAMPTZ,
  CONSTRAINT uq_postulacion UNIQUE (vacante_id, candidato_id)
);
CREATE INDEX IF NOT EXISTS ix_postulaciones_etapa ON postulaciones(vacante_id, etapa_id);

-- Bitácora de movimientos: alimenta el embudo y el tiempo de contratación.
CREATE TABLE IF NOT EXISTS historial_etapas (
  id              SERIAL PRIMARY KEY,
  postulacion_id  INT NOT NULL REFERENCES postulaciones(id) ON DELETE CASCADE,
  etapa_desde_id  INT REFERENCES etapas(id),
  etapa_hasta_id  INT NOT NULL REFERENCES etapas(id),
  usuario_id      INT REFERENCES usuarios(id) ON DELETE SET NULL,
  comentario      VARCHAR(500),
  creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_historial_postulacion ON historial_etapas(postulacion_id);

-- ---------------------------------------------------------------------
-- Entrevistas y evaluaciones por competencias
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entrevistas (
  id              SERIAL PRIMARY KEY,
  postulacion_id  INT NOT NULL REFERENCES postulaciones(id) ON DELETE CASCADE,
  tipo            VARCHAR(12) NOT NULL CHECK (tipo IN ('tecnica','rh','cultural','final')),
  inicio          TIMESTAMPTZ NOT NULL,
  duracion_min    SMALLINT NOT NULL DEFAULT 60 CHECK (duracion_min BETWEEN 15 AND 480),
  lugar           VARCHAR(255),          -- sala física o enlace de videollamada
  notas           TEXT,
  estado          VARCHAR(12) NOT NULL DEFAULT 'programada'
                    CHECK (estado IN ('programada','realizada','cancelada')),
  uid_ics         VARCHAR(80) NOT NULL UNIQUE,
  secuencia_ics   INT NOT NULL DEFAULT 0,
  creado_por      INT REFERENCES usuarios(id) ON DELETE SET NULL,
  creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_entrevistas_inicio ON entrevistas(inicio);

CREATE TABLE IF NOT EXISTS entrevista_entrevistadores (
  entrevista_id  INT NOT NULL REFERENCES entrevistas(id) ON DELETE CASCADE,
  usuario_id     INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  PRIMARY KEY (entrevista_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS competencias (
  id           SERIAL PRIMARY KEY,
  nombre       VARCHAR(80) NOT NULL UNIQUE,
  descripcion  VARCHAR(255),
  activa       BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS evaluaciones (
  id              SERIAL PRIMARY KEY,
  entrevista_id   INT NOT NULL REFERENCES entrevistas(id) ON DELETE CASCADE,
  evaluador_id    INT NOT NULL REFERENCES usuarios(id),
  recomendacion   VARCHAR(12) NOT NULL CHECK (recomendacion IN ('fuerte_si','si','no','fuerte_no')),
  fortalezas      TEXT,
  areas_mejora    TEXT,
  creada_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluacion UNIQUE (entrevista_id, evaluador_id)
);

CREATE TABLE IF NOT EXISTS evaluacion_puntajes (
  evaluacion_id   INT NOT NULL REFERENCES evaluaciones(id) ON DELETE CASCADE,
  competencia_id  INT NOT NULL REFERENCES competencias(id),
  puntaje         SMALLINT NOT NULL CHECK (puntaje BETWEEN 1 AND 5),
  comentario      VARCHAR(500),
  PRIMARY KEY (evaluacion_id, competencia_id)
);

-- ---------------------------------------------------------------------
-- Pruebas técnicas con calificación automática
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pruebas (
  id                 SERIAL PRIMARY KEY,
  empresa_id         INT NOT NULL REFERENCES empresas(id),
  titulo             VARCHAR(150) NOT NULL,
  descripcion        TEXT,
  tiempo_limite_min  SMALLINT NOT NULL DEFAULT 45,
  puntaje_aprobacion NUMERIC(5,2) NOT NULL DEFAULT 60,
  creada_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prueba_preguntas (
  id                  SERIAL PRIMARY KEY,
  prueba_id           INT NOT NULL REFERENCES pruebas(id) ON DELETE CASCADE,
  orden               SMALLINT NOT NULL DEFAULT 1,
  tipo                VARCHAR(16) NOT NULL CHECK (tipo IN ('opcion_multiple','codigo')),
  enunciado           TEXT NOT NULL,
  opciones            JSONB,            -- ["opción A", "opción B", ...]
  respuesta_correcta  SMALLINT,         -- índice dentro de opciones
  funcion             VARCHAR(60),      -- nombre de la función que debe implementar
  plantilla_codigo    TEXT,
  casos_prueba        JSONB,            -- [{"entrada": [args], "esperado": valor}, ...]
  puntos              NUMERIC(5,2) NOT NULL DEFAULT 10,
  CONSTRAINT ck_pregunta CHECK (
    (tipo = 'opcion_multiple' AND opciones IS NOT NULL AND respuesta_correcta IS NOT NULL) OR
    (tipo = 'codigo' AND funcion IS NOT NULL AND casos_prueba IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS prueba_asignaciones (
  id              SERIAL PRIMARY KEY,
  prueba_id       INT NOT NULL REFERENCES pruebas(id) ON DELETE CASCADE,
  postulacion_id  INT NOT NULL REFERENCES postulaciones(id) ON DELETE CASCADE,
  token           VARCHAR(64) NOT NULL UNIQUE,
  enviada_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expira_en       TIMESTAMPTZ NOT NULL,
  iniciada_en     TIMESTAMPTZ,
  completada_en   TIMESTAMPTZ,
  puntaje         NUMERIC(6,2),
  puntaje_max     NUMERIC(6,2),
  CONSTRAINT uq_asignacion UNIQUE (prueba_id, postulacion_id)
);

CREATE TABLE IF NOT EXISTS prueba_respuestas (
  asignacion_id     INT NOT NULL REFERENCES prueba_asignaciones(id) ON DELETE CASCADE,
  pregunta_id       INT NOT NULL REFERENCES prueba_preguntas(id) ON DELETE CASCADE,
  respuesta         JSONB NOT NULL,
  puntos_obtenidos  NUMERIC(5,2) NOT NULL DEFAULT 0,
  detalle           JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (asignacion_id, pregunta_id)
);

-- ---------------------------------------------------------------------
-- Comunicación con el candidato
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plantillas_correo (
  id              SERIAL PRIMARY KEY,
  codigo          VARCHAR(30) NOT NULL UNIQUE,
  nombre          VARCHAR(80) NOT NULL,
  asunto          VARCHAR(200) NOT NULL,
  cuerpo          TEXT NOT NULL,                 -- admite {{variables}}
  actualizada_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS correos (
  id              SERIAL PRIMARY KEY,
  candidato_id    INT REFERENCES candidatos(id) ON DELETE CASCADE,
  postulacion_id  INT REFERENCES postulaciones(id) ON DELETE CASCADE,
  plantilla       VARCHAR(30),
  para            VARCHAR(160) NOT NULL,
  asunto          VARCHAR(200) NOT NULL,
  cuerpo          TEXT NOT NULL,
  adjunto         VARCHAR(120),
  estado          VARCHAR(10) NOT NULL CHECK (estado IN ('enviado','simulado','error')),
  error           VARCHAR(500),
  enviado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_correos_postulacion ON correos(postulacion_id);

-- ---------------------------------------------------------------------
-- Privacidad: solicitudes del titular y bitácora de cumplimiento
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_privacidad (
  id             SERIAL PRIMARY KEY,
  candidato_id   INT REFERENCES candidatos(id) ON DELETE SET NULL,
  email_hash     VARCHAR(64) NOT NULL,       -- sobrevive al borrado como evidencia
  tipo           VARCHAR(12) NOT NULL CHECK (tipo IN ('borrado','acceso')),
  estado         VARCHAR(12) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','completada','rechazada')),
  motivo         VARCHAR(500),
  solicitada_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
  resuelta_en    TIMESTAMPTZ,
  resuelta_por   INT REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bitacora_privacidad (
  id          SERIAL PRIMARY KEY,
  accion      VARCHAR(30) NOT NULL,          -- anonimizacion, purga_retencion, exportacion
  email_hash  VARCHAR(64),
  detalle     JSONB NOT NULL DEFAULT '{}'::jsonb,
  usuario_id  INT REFERENCES usuarios(id) ON DELETE SET NULL,
  creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Modo "uso personal": seguimiento de mi propia búsqueda de empleo
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mi_cv (
  usuario_id       INT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  nombre_original  VARCHAR(255),
  texto            TEXT NOT NULL,
  datos            JSONB NOT NULL DEFAULT '{}'::jsonb,
  actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mis_postulaciones (
  id                   SERIAL PRIMARY KEY,
  usuario_id           INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  empresa              VARCHAR(150) NOT NULL,
  puesto               VARCHAR(150) NOT NULL,
  url                  VARCHAR(500),
  descripcion          TEXT,
  modalidad            VARCHAR(12) CHECK (modalidad IN ('remoto','hibrido','presencial')),
  salario              VARCHAR(80),
  estado               VARCHAR(16) NOT NULL DEFAULT 'por_postular'
                         CHECK (estado IN ('por_postular','postulada','en_proceso','entrevista',
                                           'oferta','aceptada','rechazada','sin_respuesta')),
  fecha_postulacion    DATE,
  proximo_seguimiento  DATE,
  contacto             VARCHAR(150),
  notas                TEXT,
  match_score          NUMERIC(5,2),
  match_detalle        JSONB,
  creada_en            TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizada_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_mis_postulaciones_usuario ON mis_postulaciones(usuario_id, estado);

CREATE TABLE IF NOT EXISTS mis_recordatorios (
  id                  SERIAL PRIMARY KEY,
  mi_postulacion_id   INT NOT NULL REFERENCES mis_postulaciones(id) ON DELETE CASCADE,
  fecha               DATE NOT NULL,
  texto               VARCHAR(255) NOT NULL,
  completado          BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_recordatorios_fecha ON mis_recordatorios(fecha) WHERE NOT completado;
