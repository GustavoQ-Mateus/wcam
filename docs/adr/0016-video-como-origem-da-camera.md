# 0016. Vídeo enviado pelo usuário como origem própria da câmera

Status: Aceita, substituída em parte pela ADR 0017 (a sessão do celular não termina mais ao ativar)
Data: 2026-11-15

## Contexto
O usuário quer que a câmera WCam mostre um vídeo em repetição, enviado pelo console, até desativar (spec v0.9.0). Os apps têm que continuar vendo a mesma câmera nativa "WCam" (ADR 0011), aberta no formato anunciado (ADR 0013). O vídeo pode ter qualquer resolução, fps, rotação, codec e faixa de cor que o PC consiga abrir. O CA-2 proíbe redimensionar e converter cor entre o celular e a câmera.

Opções consideradas:
- **Trocar o formato da câmera para o do vídeo**: preserva o vídeo sem ajuste, mas obriga o app a reabrir a câmera no meio da reunião (ADR 0013) e falha com formatos que a câmera não anuncia.
- **Aceitar só vídeos no formato atual**: sem conversão, mas recusa quase todo vídeo real (em pé, 4K HEVC, 60 fps).
- **Ajustar o vídeo ao formato anunciado**, como uma origem separada do celular.

## Decisão
- O vídeo é uma origem própria da câmera, ao lado do celular, do quadro de espera, do congelamento e do quadro de câmera desligada. `virtualCamera.source` `video`.
- O agente decodifica com PyAV no executor, aplica a rotação gravada, converte para I420 no formato anunciado mantendo a proporção, com faixas pretas, e entrega no fps anunciado seguindo o `pts` do vídeo (repete ou pula quadros, nunca fica em câmera lenta). No fim, volta ao começo sem quadro preto.
- Com o vídeo ativo, o celular não é usado: a sessão termina com `video_source` e o pareamento fica fechado até desativar.
- O CA-2 continua valendo só para a imagem do celular, que não passa por esse caminho. O vídeo pode ser redimensionado e ter a cor convertida pelo caminho padrão do PyAV; HDR sai sem mapeamento de tom.
- A câmera virtual nativa (`vcam`) e o contrato com ela não mudam.

## Consequências
- Qualquer vídeo que o PyAV abra funciona sem o app reabrir a câmera.
- Vídeo com proporção diferente aparece com faixas; vídeo HDR pode ficar com a cor lavada. Mapeamento de tom e escolha de formato pelo vídeo ficam para depois.
- Decodificar 4K HEVC em Python custa CPU; o relatório da v0.9.0 registra o custo (spec v0.9.0, CA 6). Se for alto demais, a decodificação no hardware (já apontada na ADR 0014) passa a ser o próximo passo.
