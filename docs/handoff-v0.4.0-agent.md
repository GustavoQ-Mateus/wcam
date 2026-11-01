# Handoff v0.4.0, sessão agent

De: orquestrador
Para: sessão `agent`
Spec: `docs/specs/spec-v0.4.0.md` (Aprovada)
Contrato: `docs/contrato.md` (versão 0.4.0)

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\agent-camera-virtual`. Faça `cd` para ela e trabalhe só dentro dela.
- Branch: `feature/camera-virtual-agent`, a partir de `feature/camera-virtual`. PR futuro para `feature/camera-virtual`.
- Não edite `web/`, `locales/` nem `docs/` (exceto o relatório). O contrato é o ponto de encontro com a sessão web; pergunte antes de qualquer desvio.

## Escopo

A seção "Escopo da sessão agent" da spec inteira, com os testes listados. Destaques:

1. **Caminho sem perda.** Quando o tamanho do quadro é igual ao da saída, o I420 decodificado vai para o sink sem redimensionar e sem passar por RGB. O teste `test_phone_frame_reaches_sink_unchanged_when_size_matches` compara os bytes de entrada e de saída. Confira na documentação do pyvirtualcam o formato exato que ele espera para I420 (forma do array) e registre no relatório.
2. **Quadro preto de espera a 30 fps** sempre que não houver quadro do celular. O pyvirtualcam com o backend OBS precisa de quadros contínuos; nunca deixe a câmera sem receber nada.
3. **Conversão e envio fora do event loop,** num único worker, para manter a ordem. O loop de envio tem dono e cancelamento explícito.
4. **Driver ausente ou ocupado não derruba o agente.** Teste os dois motivos com um sink que falha ao abrir.
5. **SSIM com numpy** no plano Y, janela de 8x8, e o gerador determinístico do `.y4m` de referência em `wcam.tools.make_reference`.
6. **Compose:** `WCAM_VIRTUAL_CAMERA=fake` no `agent`, `WCAM_QUALITY_REFERENCE` apontando para a referência, e um jeito de o serviço `e2e` receber o mesmo arquivo. Escolha entre volume compartilhado e passo de geração, e registre a escolha. O `e2e` é da sessão web; avise a ela o caminho dentro do container. Se precisar mudar o `docker-compose.yml`, ele é seu.
7. **Status:** `codec`, `framesScaled`, `virtualCamera`, `process.cpuPercent` e `quality`, como no contrato. Os textos do terminal já estão em `locales/` (`terminal.virtual_camera_*`).
8. **Dependências:** `pyvirtualcam` e `numpy`. Versão 0.4.0.

## Teste no Windows real (antes do relatório)

Rode `uv run wcam` com o backend `obs` e confira:
- o status mostra `virtualCamera.state` `active`;
- um consumidor da câmera vê o quadro preto, por exemplo um script local com OpenCV, se você já tiver um, ou só um app que abra a câmera.

Não instale software novo na máquina sem me perguntar. Se não houver como ver a câmera daqui, registre como não verificado: o usuário testa com os apps do CA 1.

## Verificação

A partir de `.worktrees/agent-camera-virtual/agent`: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest`.

## Commits e relatório

Conventional Commits, sem referência a Claude ou Anthropic. Push liberado; PR não. No fim, `docs/relatorio-v0.4.0-agent.md` no formato de sempre, e me avise (`wcam-c8`).
