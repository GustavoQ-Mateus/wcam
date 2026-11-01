export function requiredUrl(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Environment variable ${name} is not set. See "Variáveis dos testes e2e" in docs/contrato.md.`);
  }
  return value;
}
