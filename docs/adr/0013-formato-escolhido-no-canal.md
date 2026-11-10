# 0013. Formato escolhido pelo usuário no canal de quadros

Status: Proposta (aceita depois do spike `vcam-format` da spec v0.7.0)
Data: 2026-11-10
Refina: ADR 0012 (o formato fixo 1920x1080 do canal; o resto da 0012 continua valendo)

## Contexto
A câmera WCam anuncia um formato só, 1920x1080 a 30 fps, fixo no canal `WCamFrames`, na API C e na media source. A spec v0.7.0 deixa o usuário escolher resolução e fps (de 1280x720 a 3840x2160, 30 ou 60 fps), e o CA-2 proíbe redimensionar em paisagem. O usuário decidiu em 2026-11-10 que a escolha é dele, no seletor, e que a câmera anuncia só o formato escolhido, em vez de anunciar vários e deixar o app escolher.

## Decisão
- O cabeçalho do canal ganha largura, altura e fps do formato atual. As três posições NV12 têm tamanho para o maior formato (3840x2160).
- A API C ganha `WcamFormatSet(width, height, fps)`, chamada pelo agente quando o usuário escolhe um formato. `WcamFramePublish` aceita só quadros do formato atual.
- A media source anuncia um tipo de mídia só, o formato do canal no momento em que o app abre a câmera. Os quadros de espera e de preto saem nesse formato.
- Mudança de formato com um app usando a câmera: a definir pelo spike (troca imediata pelo evento de mudança de formato do Media Foundation, se os apps do CA-1 aceitarem; senão, o novo formato vale na próxima abertura da câmera). Esta ADR é aceita com o resultado escrito aqui.

## Consequências
- O canal passa de cerca de 9 MB para cerca de 37 MB de memória compartilhada.
- A media source continua só leitura no canal (ADR 0012); nenhum caminho de escrita do Frame Server para o agente é criado.
- Um app aberto num formato nunca recebe quadro de outro tamanho.
