# 0004. HTTPS autoassinado na LAN e console só em localhost

Status: Aceita
Data: 2026-10-31

## Contexto
`getUserMedia` só funciona em contexto seguro. No celular, uma página em `http://<ip-da-lan>` não acessa a câmera. Sem domínio público não há certificado de autoridade confiável para um IP privado. Já `http://127.0.0.1` é contexto seguro para o navegador do PC.

## Decisão
Dois servidores no mesmo processo:
- Celular: HTTPS em `<ip-da-lan>:8443`, com certificado ECDSA P-256 autoassinado gerado por instalação, com o IP da LAN no SAN, guardado no diretório de dados do usuário e regenerado quando o IP muda.
- Console: HTTP em `127.0.0.1:8080`, nunca exposto à rede.

Os dois servidores verificam o cabeçalho `Host` contra a lista esperada, como defesa contra DNS rebinding.

## Consequências
- O celular mostra um aviso de certificado na primeira vez e quando o IP do PC muda. O console explica isso antes, e a impressão digital fica visível para conferência.
- Nenhuma configuração do agente é alcançável pela rede.
