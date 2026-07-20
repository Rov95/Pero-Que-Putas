const CLAVES = {
  usuarioId: 'pqp_usuario_id',
  username: 'pqp_username',
  token: 'pqp_token',
  salaCodigo: 'pqp_sala_codigo',
} as const

function obtener(clave: string): string | null {
  try {
    return localStorage.getItem(clave)
  } catch {
    return null
  }
}

function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor)
  } catch {
    // almacenamiento no disponible (modo privado, cuota, etc.): se ignora
  }
}

function eliminar(clave: string): void {
  try {
    localStorage.removeItem(clave)
  } catch {
    // almacenamiento no disponible: se ignora
  }
}

export const almacenamiento = {
  obtenerUsuarioId: () => obtener(CLAVES.usuarioId),
  guardarUsuarioId: (id: string) => guardar(CLAVES.usuarioId, id),

  obtenerUsername: () => obtener(CLAVES.username),
  guardarUsername: (username: string) => guardar(CLAVES.username, username),

  obtenerToken: () => obtener(CLAVES.token),
  guardarToken: (token: string) => guardar(CLAVES.token, token),

  obtenerSalaCodigo: () => obtener(CLAVES.salaCodigo),
  guardarSalaCodigo: (codigo: string) => guardar(CLAVES.salaCodigo, codigo),
  eliminarSalaCodigo: () => eliminar(CLAVES.salaCodigo),

  limpiarSesion: () => {
    eliminar(CLAVES.usuarioId)
    eliminar(CLAVES.username)
    eliminar(CLAVES.token)
    eliminar(CLAVES.salaCodigo)
  },
}
