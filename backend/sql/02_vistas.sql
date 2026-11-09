-- Vistas analíticas que consume el dashboard.

-- Etapa más avanzada alcanzada por cada postulación (sin contar "descartado").
-- Base del embudo: quien llegó a "oferta" también cuenta como que pasó "revisión",
-- aunque un reclutador haya saltado etapas al mover la tarjeta.
CREATE OR REPLACE VIEW v_postulacion_alcance AS
SELECT p.id AS postulacion_id,
       p.vacante_id,
       p.fuente,
       COALESCE(MAX(e.orden) FILTER (WHERE e.codigo <> 'descartado'), 1) AS orden_max
FROM postulaciones p
LEFT JOIN historial_etapas h ON h.postulacion_id = p.id
LEFT JOIN etapas e ON e.id = h.etapa_hasta_id
GROUP BY p.id, p.vacante_id, p.fuente;

-- Días desde la postulación hasta la contratación.
CREATE OR REPLACE VIEW v_tiempo_contratacion AS
SELECT p.id AS postulacion_id,
       p.vacante_id,
       p.fuente,
       p.contratado_en,
       EXTRACT(EPOCH FROM (p.contratado_en - p.creada_en)) / 86400.0 AS dias
FROM postulaciones p
WHERE p.contratado_en IS NOT NULL;
