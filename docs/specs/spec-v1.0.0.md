# Spec v1.0.0, App Windows

Status: Aprovada (2026-11-23, com o atalho na tela da §1.1 pedido pelo usuário na aprovação)
Branch de integração: `feature/windows-app`
Sessões: `app` (nova, C#, pasta `app`), `agent`, `web` (pouco), `installer` (pode ser a mesma sessão `app`)
Referências: `docs/planejamento.md` §1 (CA-1 a CA-4), §3, §5.4, §6 (linha 1.0.0); ADR 0008 (app Windows e Docker no desenvolvimento), ADR 0011 (câmera nativa, registro pelo instalador), ADR 0015 (prévia por WebRTC local), ADR 0018 a 0021; spec v0.10.0, "Não verificado"; `docs/backlog.md` (princípios).

## Objetivo

Transformar o WCam num app Windows que qualquer pessoa instala e usa sem repositório, sem terminal e sem PowerShell. Um instalador único nas Releases do GitHub; um app na bandeja que liga e desliga o WCam; o console numa janela própria. A parte do Windows passa a ser C# (escolha do usuário em 2026-11-23); o agente Python continua fazendo celular, vídeo e câmera.

Primeira versão estável: daqui em diante, mudança incompatível de contrato ou arquitetura é MAJOR.

## Emenda de 2026-11-23: interface em Avalonia (ADR 0025)

Prevalece sobre o texto abaixo onde houver conflito.
- A interface do app é Avalonia UI em C#, sem WebView2 e sem páginas web dentro do app (substitui o WinUI e a ADR 0024).
- A janela principal é um aplicativo de verdade, com estrutura própria (barra de título, navegação, áreas fixas), e cobre o que o console faz para o usuário: QR e confirmação, estado da conexão, prévia em qualidade total, controles, detalhes, formato, e a biblioteca e a linha do tempo de vídeo. O `/dev` continua só no navegador.
- Identidade visual do WCam definida primeiro (marca, ícone do app, tipografia, grade, componentes, movimento), a partir dos tokens de §5.6, com `impeccable` (`shape`), `taste-skill` (telas de app), `emil-design-eng`, `animate` e `review-animations`, registrada em `docs/design-v1.0.0.md`. O usuário valida um protótipo executável antes das telas finais.
- Ícone na tela, painel e prévia flutuante em Avalonia, com a identidade nova. Esclarecimento do usuário em 2026-11-23, que prevalece sobre a §1.1:
  - O ícone é de fato uma câmera: um quadradinho de cantos arredondados com a lente, no espírito do ícone de câmera dos celulares (sem copiar o de nenhuma marca), bonito e moderno. Fica por padrão no topo da tela, no meio; o usuário pode mudar o lugar.
  - O ícone fica escondido. Só aparece quando o usuário segura Ctrl e leva o mouse perto do lugar dele; soltando o Ctrl ou afastando o mouse, ele some. Na primeira abertura do app, aparece uma vez com a dica de como chamá-lo.
  - O painel não é uma lista como o menu da bandeja: é um painel moderno de botões com ícone para cada ação (e rótulo curto), que abre com animação a partir do ícone, com estado visível em cada botão (por exemplo, congelado aceso). Visual profissional, na identidade do app.
- Prévias do app desenhadas pelo Avalonia a partir da seção `Local\WCamFrames`.
- Web (§3): nada nesta versão além da `version` 1.0.0; o polimento do front web fica para a v1.4.0.
- Spike novo: Avalonia 12 com Native AOT (publish sem avisos), bandeja, janela sem moldura do sistema, janela sempre por cima sem foco com exclusão de captura, e a prévia NV12 em 1080p30 e 2160p30 (CPU).

## 0. Spikes (primeiro)

- **Host C#** (sessão `app`): WinUI com Native AOT, ícone na bandeja e janela com WebView2 apontando para `http://127.0.0.1:8080/`. Medir tamanho do executável, tempo de abertura e memória, e confirmar que publica sem avisos de AOT e trimming. Se o WinUI não fechar com AOT, a alternativa vai com números para a ADR.
- **Prévia em qualidade total na janela** (planejamento, linha 1.0.0): comparar a prévia de hoje (WebRTC local da ADR 0015, reduzida) com caminhos de qualidade total, por exemplo o host lendo a própria câmera "WCam" pelo Media Foundation e desenhando na janela, ou quadros do agente por memória compartilhada. CPU em 1080p30 e 2160p30, com o Meet aberto. A ADR escolhe.
- **Agente empacotado** (sessão `agent`): PyInstaller em pasta (não arquivo único), com o processo filho de decodificação da ADR 0018 funcionando dentro do executável (não verificado na v0.10.0).

## 1. App (C#, pasta `app`)

- Um executável .NET 10 com Native AOT, uma instância só. Abre o agente Python como processo filho, acompanha a saúde dele pelo `GET /api/health` e encerra junto. Se o agente cair, mostra na bandeja e tenta subir de novo, com limite de tentativas.
- Bandeja com os mesmos controles e estados de hoje (spec v0.8.0, planejamento §5.4): estado da conexão, pausar, desconectar, trocar câmera, usar vídeo e voltar à câmera, abrir o console, iniciar com o Windows (desligado por padrão) e sair. Mudanças aparecem no console e no celular em menos de 300 ms, pelo SSE do console.
- Janela do console: WebView2 com o console do agente, tamanho e posição lembrados, fechar a janela não fecha o app.
- Textos de `locales/en.json` e `locales/pt-BR.json`, os mesmos do web; idioma do Windows.
- Conversa com o agente só pela API do console em `127.0.0.1:8080` (HTTP e SSE). Sem porta nova, sem canal novo.
- Prioridade do agente contra a disputa de CPU que sobrou em 4K (ADR 0021): o app abre o agente e os processos de decodificação com prioridade acima do normal e sem a economia de energia do Windows para processos em segundo plano (EcoQoS), e as threads de decodificação e entrega pedem o perfil de captura do MMCSS. Medido numa reunião de 15 min em 2160p30 contra a v0.10.0; se não ajudar, sai.
- CsWin32 para Win32, sem reflection; testes em xUnit no padrão do `vcam`.

### 1.1 Atalho na tela (pedido do usuário na aprovação)

- Um ícone pequeno de câmera, simples, sempre por cima das janelas, preso numa borda da tela que o usuário escolhe (em cima, embaixo, nas laterais ou num canto, em qualquer monitor). Arrastado com Ctrl para mudar de lugar, ele gruda na borda mais próxima. O lugar fica lembrado.
- Com Ctrl pressionado e o mouse levado até o ícone, abre um painel rápido com os controles mais usados: pausar, congelar a imagem, trocar câmera, usar vídeo e voltar à câmera, desligar a câmera, abrir o console. O mesmo painel abre por um atalho de teclado global, configurável. Estado sincronizado com bandeja, console e celular em menos de 300 ms.
- Prévia flutuante opcional, ligada pelo painel: uma janela pequena só com a imagem que a câmera "WCam" está entregando, como um espelho da webcam, que o usuário arrasta para onde quiser e redimensiona. Lugar e tamanho lembrados.
- O ícone, o painel e a prévia flutuante não aparecem quando a pessoa compartilha a tela numa reunião (exclusão de captura do Windows). Não roubam o foco nem atrapalham cliques fora deles.
- O ícone mostra o estado sem depender só de cor (ao vivo, pausado, congelado, sem celular). Pode ser escondido pela bandeja.
- A prévia flutuante usa o caminho de prévia da ADR do spike; tamanho pequeno pede pouca CPU, e o custo é medido.
- Movimento só onde tem função (abrir e fechar o painel, grudar na borda), curto e respeitando "reduzir movimento" do Windows. Skills: `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng`, `animate` e `review-animations`, registradas em `docs/design-v1.0.0.md`, com tokens de §5.6 e as regras anti slop.

- Emenda de 2026-11-23 (ADR 0024, pedido do usuário depois de ver a primeira versão nativa): o ícone, o painel e a prévia flutuante são páginas React do `web`, cada uma numa janela pequena do app com WebView2; o app continua dono do comportamento de janela (sempre por cima, foco, exclusão de captura, arrastar e grudar, atalho global). O menu da bandeja segue nativo. O polimento pesado do front fica para a v1.4.0.

## 2. Agent

- Modo filho: o agente aceita ser iniciado pelo app, sem a bandeja Python e sem abrir navegador, e encerra limpo quando o app pede ou quando o processo pai morre.
- A bandeja Python (`pystray`) sai do produto; o desenvolvimento usa o console no navegador. Dependência removida se nada mais usar. O Pillow, que hoje entra só como dependência do `pystray`, passa a ser dependência direta, porque a tira de miniaturas da biblioteca de vídeo (`video/filmstrip.py`, v0.9.0) usa ele; já está no pacote, sem dependência nova no produto.
- Empacotamento com PyInstaller em pasta, com `web/dist`, `locales` e o FFmpeg do PyAV; caminhos por variável quando instalado.
- Nada muda no contrato do celular.

## 3. Web

- O console detecta que está dentro do app (por exemplo, um parâmetro na URL que o app passa) só para esconder o que não faz sentido na janela, como "abrir em nova aba". Nada muda no `/cam`.
- Prévia em qualidade total conforme a ADR do spike, se ela pedir mudança no web.

## 4. Instalador (Inno Setup, pasta `installer`)

- Um arquivo `.exe` nas Releases do GitHub. Um único pedido de administrador para: copiar o app, o agente e a DLL da câmera para `%ProgramFiles%\WCam`; registrar a câmera "WCam" (ADR 0011); criar a regra de firewall só para a porta 8443, só no perfil de rede privada e só para a sub-rede local (CA-4); atalho no menu Iniciar.
- Nada de script ou PowerShell para o usuário final.
- Desinstalar remove o app, a câmera, a regra de firewall e o início com o Windows, e pergunta se apaga também os dados do usuário (`%LOCALAPPDATA%\wcam`: certificado, banco, vídeos da biblioteca).
- Sem assinatura de código (decisão do usuário em 2026-11-23; fica no backlog D3); o guia explica o aviso do SmartScreen.

## 5. Documentação

- Guia de solução de problemas em `docs/solucao-de-problemas.md`: câmera não aparece, celular não abre a página, aviso de certificado, firewall, SmartScreen, rede de visitantes.
- `README.md` com instalação e um GIF de demonstração. Pedido explícito do usuário ao aprovar esta spec.

## 6. ADRs

- ADR nova: app Windows em C# com o agente Python como processo filho, substituindo em parte a ADR 0008 e o planejamento §3 (bandeja `pystray` e janela `pywebview`).
- ADR nova: caminho da prévia em qualidade total na janela, com a CPU medida no spike.

## 7. Contrato

- Sem mudança prevista. Se o modo filho ou a prévia pedirem rota ou variável nova, eu emendo o contrato antes do código.

## Textos

Chaves novas antes do código: itens novos da bandeja (iniciar com o Windows, agente reiniciando, agente parado, mostrar atalho na tela), título da janela, atalho na tela (rótulos do painel, prévia flutuante, ajuda do arrastar com Ctrl, atalho de teclado), textos do instalador e da desinstalação.

## Testes

- App: xUnit no atalho na tela (borda mais próxima ao soltar, lugar lembrado por monitor, monitor removido volta para o principal), no painel refletindo o status e na prévia flutuante abrindo e fechando; xUnit no ciclo de vida do agente (sobe, cai, sobe de novo, limite de tentativas, encerra junto) com um processo falso; estado da bandeja a partir do status; uma instância só.
- Agent: modo filho (encerra quando o pai morre); executável do PyInstaller sobe e decodifica com a placa de vídeo no processo filho.
- Instalador: instalação e desinstalação limpas numa máquina virtual Windows sem o repositório.
- e2e de sempre no CI.

## Fora do escopo

- Assinatura de código e WinGet (backlog D3 e D4).
- Microsserviços e mensageria com broker: o WCam é um app local de um usuário, e os processos que existem (app, agente, decodificação, câmera) já conversam por HTTP local, fila e memória compartilhada; broker ou serviços separados não resolveriam problema real (decisão registrada a pedido do usuário em 2026-11-23).
- Zoom e enquadramento (v1.1.0), persistência de preferências (v1.2.0), robustez de reconexão (v1.3.0), polimento do front (v1.4.0), engenharia e observabilidade (v1.5.0).
- Linux e macOS.

## Critérios de aceitação

1. Instalação limpa num Windows 11 sem o repositório, com um único pedido de administrador: a câmera "WCam" aparece nos apps, a regra de firewall existe só para a 8443 na rede privada e na sub-rede local, e o app abre na bandeja.
2. Desinstalação remove app, câmera, regra de firewall e início com o Windows, e pergunta pelos dados do usuário.
3. O app sobe e encerra o agente; com o app fechado, nenhuma porta aberta; com o agente caindo, o app mostra e sobe de novo; uma instância só.
4. Controles da bandeja, do console e do celular em sincronia em menos de 300 ms.
5. Janela do console com a prévia em qualidade total pelo caminho da ADR, com a CPU medida em 1080p30 e 2160p30.
5a. Atalho na tela: ícone preso na borda escolhida, painel pelo Ctrl com o mouse e pelo atalho de teclado, controles em sincronia em menos de 300 ms, prévia flutuante arrastável e redimensionável; nada disso aparece num compartilhamento de tela do Meet; CPU da prévia flutuante medida.
6. Fluxo real com a versão instalada: QR, celular, imagem em Meet, Teams, Zoom, Discord, OBS e um site com `getUserMedia` (CA-1); SSIM do CA-2 no e2e; Android se houver aparelho, senão registrado como não verificado.
7. CA-4: varredura `nmap` de outro aparelho da rede mostra só a 8443 com o WCam ativo e nada com o app fechado; o console não responde fora do PC.
8. Decodificação na placa de vídeo do vídeo da biblioteca funcionando no executável instalado; prioridade do agente medida em 2160p30 e mantida só se reduzir as travadas do PC.
9. Verificação completa do CLAUDE.md (agent, web, vcam e o novo `app`, com `dotnet publish` sem avisos de AOT); `npm run test:e2e`; `version` 1.0.0 no agent, no web, no app e no instalador.
10. Guia de solução de problemas e `README.md` com instalação e GIF.
