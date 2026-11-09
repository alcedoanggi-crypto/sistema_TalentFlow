const CLAVE = 'tf_token'

export const sesion = {
  get token() { try { return localStorage.getItem(CLAVE) } catch { return null } },
  guardar(t) { try { localStorage.setItem(CLAVE, t) } catch { /* modo privado */ } },
  cerrar() { try { localStorage.removeItem(CLAVE) } catch { /* modo privado */ } },
}

export class ApiError extends Error {
  constructor(status, mensaje) { super(mensaje); this.status = status }
}

async function solicitar(metodo, ruta, cuerpo, { publico = false, formData = false } = {}) {
  const headers = {}
  if (!publico && sesion.token) headers.Authorization = `Bearer ${sesion.token}`
  let body
  if (cuerpo !== undefined) {
    if (formData) body = cuerpo
    else { headers['Content-Type'] = 'application/json'; body = JSON.stringify(cuerpo) }
  }
  const r = await fetch(`/api${ruta}`, { method: metodo, headers, body })
  if (r.status === 401 && !publico && sesion.token) {
    sesion.cerrar()
    window.location.href = '/login'
  }
  if (r.status === 204) return null
  const tipo = r.headers.get('content-type') || ''
  const datos = tipo.includes('json') ? await r.json() : await r.text()
  if (!r.ok) {
    let msg = typeof datos === 'string' ? datos : datos.detail
    if (Array.isArray(msg)) msg = msg.map((e) => e.msg.replace('Value error, ', '')).join(' · ')
    throw new ApiError(r.status, msg || 'Error inesperado')
  }
  return datos
}

export const api = {
  get: (r, o) => solicitar('GET', r, undefined, o),
  post: (r, c, o) => solicitar('POST', r, c, o),
  put: (r, c, o) => solicitar('PUT', r, c, o),
  patch: (r, c, o) => solicitar('PATCH', r, c, o),
  del: (r, o) => solicitar('DELETE', r, undefined, o),
}

/** Descarga un archivo protegido con el token (los <a href> no envían el header Authorization). */
export async function descargar(ruta, nombre) {
  const r = await fetch(`/api${ruta}`, { headers: { Authorization: `Bearer ${sesion.token}` } })
  if (!r.ok) throw new ApiError(r.status, 'No se pudo descargar')
  const url = URL.createObjectURL(await r.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: nombre })
  a.click()
  URL.revokeObjectURL(url)
}
