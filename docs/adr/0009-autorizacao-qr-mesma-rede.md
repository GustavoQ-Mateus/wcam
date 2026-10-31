# 0009. Autorização só por QR, na mesma rede

Status: Aceita
Data: 2026-10-31

## Contexto
Enquanto o agente está ativo, uma porta fica aberta na rede local. Qualquer aparelho na mesma rede (casa com visitas, café, hotel, empresa) pode tentar usá-la. O celular não instala nada e não tem login.

## Decisão
- A única forma de autorizar um celular é ler o QR mostrado no PC. Sem login, senha, aparelho lembrado ou link reutilizável.
- O token vai no fragmento da URL (`/cam#t=<token>`), que o navegador nunca envia ao servidor. A página lê, apaga da barra de endereço e envia o token só no corpo do `POST /api/sessions`.
- Token de 128 bits (`secrets`), uso único, válido por 2 minutos e só enquanto o QR está visível. Guardado apenas como hash SHA-256, comparado em tempo constante.
- O IP de origem precisa estar na sub-rede da interface Wi-Fi do PC; candidatos ICE de fora dela são descartados.
- Limite de 5 tentativas por minuto por IP, com bloqueio de 10 minutos.
- O token de sessão (também em hash) só religa a sessão em andamento, em até 60 segundos após uma queda.
- Firewall do Windows: regra por programa, perfil Privado, LocalSubnet. Em rede Pública a porta da LAN não abre.

## Consequências
- Toda sessão nova exige o QR.
- Redes com isolamento de clientes não funcionam; o app orienta usar o hotspot do celular.
- O banco não guarda nada que autorize conexão futura.
