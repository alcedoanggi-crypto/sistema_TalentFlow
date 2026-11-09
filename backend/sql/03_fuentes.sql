-- Amplía las fuentes de reclutamiento con portales de empleo externos (idempotente).
ALTER TABLE postulaciones DROP CONSTRAINT IF EXISTS postulaciones_fuente_check;
ALTER TABLE postulaciones ADD CONSTRAINT postulaciones_fuente_check CHECK (fuente IN (
  'portal_empleo','computrabajo','linkedin','indeed','bumeran','occ','elempleo','glassdoor','referido','evento','otro'));
