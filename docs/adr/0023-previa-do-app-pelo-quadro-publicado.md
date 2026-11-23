# 0023. Prévia do app lida do quadro que a câmera publica

Status: Aceita, substituída em parte pela ADR 0025 (prévias desenhadas pelo Avalonia, sem canal para a página)
Data: 2026-11-23
Complementa: ADR 0015 (prévia por WebRTC local, que continua para o console no navegador) e ADR 0022 (app em C#)

## Contexto
A spec v1.0.0 pede a prévia em qualidade total na janela do console e uma prévia flutuante pequena no atalho na tela. O spike da sessão app mediu no PC do usuário (i5-8500, UHD 630), com quadros sintéticos na mesma estrutura dos reais, em % da máquina:

| Caminho | 1080p | 2160p |
|---|---|---|
| A, prévia de hoje (WebRTC local, reduzida a 960x540), só no agente | +3,1 | +6,8 |
| C nativo: o app lê o quadro publicado e desenha com o processador de vídeo do D3D11 | 0,4 a 0,5 | 0,8 a 1,3 |
| C na página: o app passa o quadro por `CoreWebView2SharedBuffer` e a página desenha NV12 com WebGL2 (árvore inteira, 960x540) | 3,0 | 4,1 |
| B, o app abrindo a câmera "WCam" pelo Media Foundation | não medido | não medido |

- O caminho C lê a seção `Local\WCamFrames` que o agente já preenche para a câmera nativa (NV12, três posições, seqlock, leitura só para o usuário dono). É exatamente o que a câmera entrega, com espelho, congelamento e câmera desligada aplicados, sem codificar nem decodificar.
- O caminho B acende o indicador de câmera em uso do Windows para o próprio WCam, faz uma cópia a mais no Frame Server e conflita com a opção que limita a câmera a um app.

## Decisão
- Prévia flutuante: janela nativa do app, lendo a seção e desenhando pelo D3D11.
- Prévia na janela do console: o app lê a seção e passa os quadros à página por `CoreWebView2SharedBuffer`; a página desenha NV12 com WebGL2. Esse canal entre o app e a página só existe dentro do app e é documentado em `docs/contrato.md` antes do código; o formato das mensagens é proposto juntos pelas sessões app e web.
- No navegador comum, o console continua com o WebRTC local da ADR 0015.
- A seção continua sendo escrita só pelo agente; o app só lê. Leitura feita só enquanto a prévia está visível.
- O caminho B fica descartado.

## Consequências
- Prévia em qualidade total com custo abaixo do da prévia reduzida de hoje.
- O formato da seção `Local\WCamFrames` passa a ter dois leitores (a câmera nativa e o app); mudá-lo exige atualizar os dois.
- Números finais medidos com o WCam real e o Meet aberto na sessão de validação da versão.
