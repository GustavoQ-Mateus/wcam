# 0010. Código de confirmação derivado do DTLS

Status: Aceita
Data: 2026-10-31

## Contexto
Quem fotografar o QR antes do usuário consegue abrir uma sessão e enviar o próprio vídeo para a câmera virtual. Um código mostrado no PC e digitado no celular não protege contra isso, porque sai da mesma tela que o QR, e digitar no celular gera atrito e erros.

## Decisão
Depois do QR, a conexão WebRTC é criada, mas nenhum quadro chega à câmera virtual. PC e celular calculam, cada um, um código de 6 caracteres a partir das impressões digitais DTLS das duas pontas e de um nonce da sessão, em Crockford base32 (sem `0/O/1/I/L`, cerca de 30 bits). O código aparece nas duas telas. O usuário confere e clica Confirmar no PC; só então os quadros passam. Uma confirmação por sessão; reconexão em até 60 segundos não pede de novo. Nada é digitado no celular.

## Consequências
- QR lido por outra pessoa: o código aparece no aparelho dela, o usuário não confirma, nada chega à reunião.
- Intermediário na conexão: os códigos divergem.
- Um clique a mais por sessão.
- O pipeline de mídia tem um portão (`frame_gate`) fechado até a confirmação.
