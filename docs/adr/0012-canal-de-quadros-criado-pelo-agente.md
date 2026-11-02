# 0012. Canal de quadros criado pelo processo do agente

Status: Aceita
Data: 2026-11-02
Refina: ADR 0011 (só o item "transporte de quadros"; o resto da 0011 continua valendo)

## Contexto
A ADR 0011 definiu a seção de memória em `Global\` criada pela media source, com escrita só para o SID do dono, e deixou para a fase 2 o caminho confiável desse SID até a media source. Na prova, chamadas por um usuário comum sobre uma câmera de acesso `CurrentUser`, `IMFVirtualCamera.AddProperty` e `AddRegistryEntry` (com e sem subchave) retornaram `0x80070005`. O Windows também não guarda o dono da câmera nas propriedades do dispositivo. Não há caminho confiável para o SID chegar à media source.

## Decisão
Inverter quem cria o canal:
- A DLL, carregada no processo do agente, cria a seção `Local\WCamFrames` dentro do `WcamCameraStart`, na sessão do usuário, com DACL `D:(A;;GA;;;SY)(A;;GA;;;<SID do usuário do processo>)(A;;GR;;;LS)`: tudo para `SYSTEM` e para o próprio usuário, só leitura para `LOCAL SERVICE`.
- A media source, no Frame Server (sessão 0, `LOCAL SERVICE`), abre `Session\<sessão do console>\WCamFrames` só para leitura, com `WTSGetActiveConsoleSessionId`, tentando de novo a cada 1 s enquanto o canal não existir. Sem canal, entrega preto.
- O formato do canal não muda (cabeçalho e três posições NV12 com seqlock), nem a API C.

## Evidência (2026-11-02)
- DLL no processo de um usuário comum criou `Local\WCamOwnerSpike` na sessão 1 para o SID do usuário.
- Media source no Frame Server (pid 13392, `LocalService`, sessão 0) abriu `Session\1\WCamOwnerSpike`, leu o marcador intacto e teve a abertura para escrita negada (`0x80070005`).
- Na mesma rodada, o Chrome leu a câmera em 1920x1080 a 30,2 fps.

## Consequências
- Nenhum SID atravessa processos, e nenhum grupo amplo (`INTERACTIVE`) recebe escrita. Nem a media source consegue escrever no canal.
- O canal existe antes de qualquer app abrir a câmera e some quando o agente encerra.
- Só o usuário da sessão do console é atendido. Troca rápida de usuário atende quem estiver no console; sessões de área de trabalho remota ficam de fora. Aceitável para uma webcam local.
- Saem do código a seção `Global\`, o caminho do arquivo mapeado e a busca pelo dono.
