const ALFABETO_SALA = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
const LONGITUD_CODIGO = 6

export function normalizarCodigoSala(valor: string): string {
  return valor.toUpperCase().replace(/[^A-Z0-9]/g, '')
}

export function esCaracterValido(caracter: string): boolean {
  return ALFABETO_SALA.includes(caracter)
}

export function esCodigoSalaCompleto(codigo: string): boolean {
  return codigo.length === LONGITUD_CODIGO && [...codigo].every(esCaracterValido)
}
