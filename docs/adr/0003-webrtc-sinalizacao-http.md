# 0003. WebRTC com sinalização HTTP de oferta única

Status: Aceita
Data: 2026-10-31

## Contexto
O celular envia vídeo ao PC na mesma rede local. Enviar JPEG por WebSocket gasta banda e aumenta latência. WebRTC entrega vídeo comprimido com controle de congestionamento. O aiortc não faz trickle ICE: junta os candidatos antes de responder.

## Decisão
WebRTC com sinalização por uma única requisição HTTP (`POST /api/sessions` com a oferta SDP completa, resposta com a SDP do agente), no espírito do WHIP. Sem trickle ICE, sem STUN e sem TURN: só candidatos `host` da sub-rede local. Controles trafegam num DataChannel `control`.

## Consequências
- Nenhum WebSocket é necessário; o contrato é HTTP simples e testável.
- O celular espera o ICE gathering terminar antes de enviar a oferta (milissegundos em LAN).
- Não funciona fora da rede local, o que é desejado (ADR 0009).
