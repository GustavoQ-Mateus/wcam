# Spec v1.1.0, Zoom e enquadramento

Status: Draft (rascunho futuro; o usuário passou o zoom para depois da 1.0.0 em 2026-11-23)
Branch de integração: `feature/framing`
Sessões: `web`, `agent`
Referências: `docs/planejamento.md` §1 (CA-2, CA-3), §5.3, §5.4, §6 (linha 0.11.0); spec v0.8.0 §0 (definição do spike `zoom`, que saiu daquela versão); ADR 0019 e 0021 (custo de CPU ao vivo); `docs/backlog.md` (princípios: segurança, local, Android).

## Objetivo

Deixar o usuário escolher o que a câmera mostra: aproximar ou abrir a imagem no próprio celular (zoom real e troca de lente) e, se quiser, recortar um enquadramento no PC. O zoom no celular não perde qualidade, porque é o sensor ou a lente que muda; o recorte no PC amplia parte da imagem e por isso fica desligado por padrão, com exceção ao CA-2 registrada em ADR.

Vale para iPhone e Android. Onde o navegador não oferecer zoom ou lentes, o controle não aparece; nada é simulado no celular.

## 0. Spike de zoom e lentes (primeiro)

Antes do código, a sessão web mede no iPhone do usuário (Safari) e, se houver um aparelho Android disponível, no Chrome do Android:
- para cada câmera de `enumerateDevices()`: rótulo, `getCapabilities()` e `getSettings()` completos (`zoom`, `focusMode`, `torch`, largura, altura, fps);
- para cada câmera com `zoom`: `applyConstraints` no mínimo, 1, 2 e no máximo, com o `getSettings()` e o tamanho do quadro depois de cada um, e o tempo até o quadro novo;
- se a ultra-angular (0,5x) e a teleobjetiva aparecem como dispositivos separados ou como faixa de `zoom` de um dispositivo só;
- se trocar de dispositivo com a conexão aberta funciona por `replaceTrack`, sem renegociar, e quanto tempo a imagem some;
- se a frontal expõe o enquadramento aberto (zoom abaixo de 1 ou outro dispositivo).

Página temporária só na branch do spike; nada dela entra na branch da sessão. Resultado em tabela por aparelho no relatório web, e eu fecho com o usuário os controles da §1 antes do código.

## 1. Zoom no celular (web, `/cam`)

- Controle de zoom no visor, para uma mão: botões das lentes que o aparelho expõe (por exemplo 0,5x, 1x, 2x, 3x) e ajuste contínuo entre o mínimo e o máximo, por pinça no visor e por um controle deslizante. O valor atual aparece no visor.
- Aplicado por `applyConstraints({zoom})` quando o navegador expõe `zoom`; por troca de dispositivo com `replaceTrack` quando a lente é outro dispositivo. Nunca renegocia nem derruba a conexão.
- Sem zoom exposto pelo navegador, o controle não aparece. Nada de zoom digital no celular.
- Ao trocar de câmera (frontal e traseira), o zoom volta a 1x ou ao valor da lente padrão daquela câmera.
- API do navegador encapsulada em `media/`; valores e lentes num módulo puro em `data/` com Vitest.

## 2. Zoom pelo console (web e agent)

- O console mostra o mesmo controle de lentes e de zoom contínuo nos controles do celular, só com o celular `live` e só com o que o aparelho expõe.
- Mudança no celular aparece no console e vice-versa em menos de 300 ms (planejamento §5.4).
- Com o vídeo como câmera ativo, o zoom fica oculto (o celular está com a câmera desligada).
- A bandeja não ganha controle de zoom.

## 3. Enquadramento no PC (agent e web)

- O usuário liga "Enquadrar" no console e escolhe, sobre a prévia, um retângulo na proporção do formato anunciado (arrastar para mover, alças para o tamanho). A câmera passa a entregar só esse trecho, ampliado para o formato anunciado.
- Desligado por padrão. Desligado, a imagem segue o CA-2 sem nenhuma mudança.
- Ligado, é a única ampliação permitida, com exceção ao CA-2 registrada em ADR nova (§5). O console mostra, só na área de detalhes, quanto a imagem está sendo ampliada.
- Recorte e ampliação feitos no agente, em NV12, num grafo do FFmpeg fora do event loop e sem prender o GIL (como a tradução de cor da v0.10.0), com escala de boa qualidade escolhida por medição.
- Vale também para o vídeo como câmera.
- O enquadramento dura enquanto o WCam estiver aberto; guardar entre execuções fica para a v1.2.0 (persistência).
- Retrato com faixas (v0.7.0): o recorte é escolhido sobre a imagem já com as faixas.

## 4. Contrato (`docs/contrato.md` vai para 1.1.0, escrito por mim antes do código)

- DataChannel, celular para o agente: `zoom_capabilities` (lentes e faixa de zoom da câmera em uso, a cada troca de câmera) e `zoom` (valor atual, a cada mudança).
- DataChannel, agente para o celular: `set_zoom` (valor ou lente pedidos pelo console).
- `GET /api/status`: zoom atual e capacidades em `session`; `framing` no primeiro nível (`enabled`, retângulo normalizado, ampliação). Mudanças contam para o SSE.
- `PUT /api/controls` com `zoom`; `PUT /api/framing` com `enabled` e o retângulo. Erros pelo formato de sempre (`409` sem sessão `live` para o zoom, `422` para retângulo inválido).
- `/api/dev/events`: etapa `framing` nos tempos por etapa (0 desligado) e eventos `zoom` e `framing`.

O formato exato das mensagens eu escrevo depois do spike.

## 5. ADR

- ADR nova: exceção ao CA-2 para o enquadramento no PC, só quando o usuário liga, com a escala escolhida e o custo medido.

## Textos

Chaves novas antes do código: lentes e zoom no `/cam` e no console, "Enquadrar", ajuda do recorte, ampliação nos detalhes, etapa e eventos novos do `/dev`, erros novos. Português e inglês.

## Testes

- Web: Vitest nas regras de zoom e lentes, no retângulo do recorte (proporção, limites, arrastar e redimensionar) e na sincronia de estado; e2e com o celular falso trocando o zoom pelo console e pelo celular, e com o enquadramento ligado e desligado (SSIM do CA-2 só com ele desligado).
- Agent: mensagens novas do DataChannel; `PUT /api/framing` e `PUT /api/controls` com `zoom`; recorte e ampliação em NV12 com o resultado esperado em quadros sintéticos; enquadramento desligado igual byte a byte ao caminho da v0.10.0; custo por quadro em 1080p30 e 2160p30.

## Fora do escopo

- Zoom digital no celular, foco, lanterna e exposição (ficam para outra versão, se o spike mostrar suporte).
- Enquadramento automático que segue o rosto (backlog F3).
- Guardar o enquadramento entre execuções (v1.2.0).

## Critérios de aceitação

1. Spike registrado com a tabela por aparelho: iPhone do usuário, e Android se houver aparelho; sem Android, registrado como não verificado.
2. Zoom e troca de lente pelo celular e pelo console mudam a imagem no Meet, sem renegociar e sem queda da sessão, nas lentes que o navegador expõe; a mudança aparece no outro lado em menos de 300 ms.
3. Sem zoom exposto pelo navegador, o controle não aparece e nada quebra.
4. Enquadramento: escolhido sobre a prévia, aplicado em menos de 300 ms, a câmera mantém o formato anunciado; desligado por padrão.
5. Com o enquadramento desligado, a imagem é igual byte a byte à da v0.10.0 e o SSIM do CA-2 continua acima de 0,98.
6. Com o enquadramento ligado em 1080p30, o p95 por quadro continua abaixo do tempo de um quadro (CA 1 da v0.10.0); em 2160p30, custo medido e registrado.
7. ADR da exceção ao CA-2 aceita.
8. Verificação completa do CLAUDE.md e `npm run test:e2e`; `version` 1.1.0 em `agent/pyproject.toml` e `web/package.json`.
