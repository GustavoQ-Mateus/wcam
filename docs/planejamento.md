# WCam, planejamento

Status: Aprovado (2026-10-31)

## 1. Problema e objetivo

Quem não tem webcam precisa de câmera para entrevista, Meet, Teams e Zoom. O celular tem uma câmera melhor que a maioria das webcams. O WCam liga as duas pontas sem cabo e sem instalar app no celular: o PC roda o agente, mostra um QR code, o celular escaneia, abre uma página e passa a ser a webcam do PC.

Objetivos de portfólio e estudo: arquitetura limpa de ponta a ponta, WebRTC de verdade, integração com o SO, testes em todas as camadas, CI, front sem cara de template.

### Escopo do produto (v1.0.0)
- Vídeo do celular aparecendo como câmera no Windows, utilizável em qualquer app.
- Pareamento por QR code com token de uso único.
- Console no PC: QR, estado, prévia, métricas (fps, resolução, latência, bitrate) e controles (pausar, câmera frontal ou traseira, resolução, espelhar, prévia ligada ou desligada).
- Quadro "sem sinal" na câmera virtual quando o celular cai, para a reunião não travar numa imagem congelada.
- Reconexão automática dentro da sessão em andamento; toda sessão nova exige ler o QR.
- No PC, app Windows com instalador e ícone na bandeja. No celular nada é baixado nem instalado: só o navegador.

### Critérios de aceitação do produto

Valem para a v1.0.0 e são dominantes sobre qualquer spec intermediária. Cada spec que toca um deles repete o CA correspondente e registra a medição no changelog.

**CA-1. A câmera é reconhecida pelos principais aplicativos.**
A câmera "WCam" aparece na lista de câmeras e exibe a imagem do celular em todos os apps abaixo, no Windows 11:

| App | Variante |
|---|---|
| Google Meet | Chrome e Edge |
| Microsoft Teams | app desktop (novo Teams) e web |
| Zoom | app desktop |
| Discord | app desktop |
| OBS Studio | fonte "Dispositivo de captura de vídeo" |
| Navegador | qualquer site com `getUserMedia` (ex.: webcamtests.com) |

Limitação conhecida: o driver do OBS Virtual Camera é DirectShow, e apps que só leem Media Foundation (o app Câmera do Windows e alguns apps da Store) não o enxergam. Se algum app da tabela falhar por isso, a câmera virtual nativa (Media Foundation, `MFCreateVirtualCamera`) sobe do roteiro 1.x para antes da v1.0.0. A v0.4.0 confirma a tabela inteira logo no MVP, para essa decisão sair cedo.

**CA-2. Sem perda de qualidade entre o celular e a câmera virtual.**
"Sem perda" literal (vídeo sem compressão) é fisicamente impossível por Wi-Fi: 1080p30 bruto são cerca de 1,5 Gbit/s. O critério é ausência de perda perceptível e de qualquer degradação evitável no caminho, medido na saída da câmera virtual:
- Resolução e taxa de quadros da câmera virtual iguais às da captura: alvo 1920x1080 a 30 fps. Sem redimensionar em nenhum ponto do pipeline.
- Sem conversão de cor: o quadro decodificado (YUV 4:2:0) vai direto para a câmera virtual em I420/NV12, sem passar por RGB.
- Bitrate alto para LAN (alvo 10 Mbit/s em 1080p30) e `degradationPreference: "maintain-resolution"`: sob congestionamento cai o fps, nunca a resolução.
- Teste automatizado: track sintética de alto detalhe passando por codificação, rede local, decodificação e sink falso, com SSIM médio de pelo menos 0,98 contra o original.
- Teste real: 10 minutos em 1080p na LAN com média de pelo menos 29 fps e nenhuma queda de resolução registrada nas métricas.
- Captura em paisagem. Celular em pé gera quadro em retrato, e encaixar retrato em 16:9 obriga a reduzir ou recortar e ampliar, o que é perda. A `/cam` pede para girar o celular e só libera "Ao vivo" em paisagem.

Fora do nosso controle: Meet, Teams e Zoom recomprimem o vídeo antes de enviar para a chamada. O CA-2 vale até a saída da câmera virtual.

**CA-3. Pareamento por QR com duas interfaces totalmente diferentes.**
- O QR aparece só no console do PC e é lido pela câmera nativa do celular. Ler o QR abre direto a `/cam` com o token.
- No celular nada é baixado nem instalado: é uma página web no navegador padrão, sem app e sem PWA obrigatório.
- PC e celular são duas interfaces distintas, com propósito, layout e componentes próprios. Nenhuma é versão responsiva da outra e não compartilham telas:

| | Console no PC (`/`) | Celular (`/cam`) |
|---|---|---|
| Papel | central de controle e monitoramento | visor da câmera que transmite |
| Uso | mouse e teclado, sentado, olhando de vez em quando | uma mão, em pé ou apoiado, configurado e esquecido |
| Conteúdo | QR, prévia do que sai na câmera virtual, estado, métricas, controles, histórico, dispositivos | visor em tela cheia (prévia que pode ser desligada), luz de tally, pausar, troca de câmera |
| Layout | painel largo, prévia como protagonista | tela cheia em paisagem, controles na zona do polegar |
| Acesso | só `127.0.0.1` no próprio PC | só pelo link do QR, na LAN |
- Abrir `/cam` sem token mostra uma tela que explica como parear pelo PC; abrir `/` pela LAN não é possível.
- Compartilham apenas tokens de design (cor, tipografia) e os tipos do contrato.

### Fora do escopo da v1
- Áudio (microfone virtual é outro driver, outro projeto).
- Acesso pela internet, fora da LAN (exigiria STUN/TURN e autenticação séria).
- Vários celulares ao mesmo tempo.
- Filtros (desfoque de fundo, etc.).
- App nativo no celular.

## 2. As três restrições que definem a arquitetura

1. **Apps de reunião só leem câmeras do sistema.** Uma página web não cria câmera. Precisamos de um processo nativo no PC que escreva quadros num dispositivo de câmera virtual. Isso elimina "só web" e pesa na escolha da linguagem.
2. **`getUserMedia` só funciona em contexto seguro.** No celular, `http://192.168.0.10` não libera a câmera. O agente precisa servir HTTPS na LAN. Sem domínio público não há certificado confiável, então o agente gera um certificado autoassinado e o usuário aceita o aviso uma vez no celular. O console do PC escapa disso porque `http://127.0.0.1` já é contexto seguro.
3. **Latência baixa em rede local.** Enviar JPEG por WebSocket funciona, mas gasta banda e trava. WebRTC entrega vídeo comprimido (VP8/H.264), com controle de congestionamento, e na mesma LAN conecta por candidato `host`, sem STUN nem TURN.

## 3. Decisão de stack

Status das decisões: aprovadas pelo usuário em 2026-10-31 (Python, SQLite, OBS na v1, nome WCam, app Windows com Docker só em desenvolvimento e CI, web no celular com autorização só por QR na mesma rede).

### Forma do produto: app Windows no PC, web no celular, Docker no desenvolvimento

O produto não roda em Docker para o usuário final. No Windows o Docker executa containers Linux numa VM (WSL2): o container não cria câmera virtual visível para Meet ou Zoom, fica atrás de NAT para as portas UDP dinâmicas do WebRTC e não enxerga o IP do PC na rede Wi-Fi, que é o que o QR precisa conter. E exigir Docker Desktop para usar uma webcam é atrito demais.

- PC: app Windows. Executável PyInstaller com ícone na bandeja (pystray) e o console React numa janela nativa WebView2 (pywebview). Instalador Inno Setup cria a regra de firewall e o atalho.
- Celular: só a página web `/cam` no navegador padrão.
- Docker: `docker compose` para desenvolvimento e CI. Sobe o agente em modo headless com câmera falsa, o web e o Playwright; roda o fluxo inteiro exceto a câmera virtual real. Contribuidores no Linux sobem tudo com um comando.

### Linguagem do agente: Python

| Critério | Python | Go | .NET |
|---|---|---|---|
| WebRTC servidor | aiortc, maduro, decodifica via PyAV | pion, excelente | SIPSorcery, menos usado |
| Decodificar VP8/H.264 em quadro | PyAV já entrega `ndarray` | precisa de cgo + ffmpeg/libvpx | precisa de wrapper ffmpeg |
| Câmera virtual no Windows | pyvirtualcam pronto (Windows, Linux, macOS) | não existe; cgo + DirectShow/Media Foundation | não existe pronto; COM na mão |
| Ganho de estudo | asyncio, tipagem estrita, pipeline de mídia | concorrência, mas o trabalho vira cgo | pouco novo, já é sua stack |

Go e .NET resolvem sinalização com folga, mas a parte difícil do projeto (quadro decodificado chegando na câmera virtual) já está resolvida em Python e teria que ser escrita do zero em C++/cgo/COM nas outras. Python também cumpre o objetivo educacional: asyncio, `Protocol`, pyright strict, uv.

### Banco: SQLite

O agente é um programa desktop de um usuário só, e o usuário final não tem Docker para rodar um Postgres. O que precisa ser guardado (preferências, histórico de sessões e amostras de métricas) cabe com folga em SQLite, que vem na biblioteca padrão do Python e vira um arquivo em `%LOCALAPPDATA%\wcam`. As mesmas boas práticas valem: migrations numeradas, repositórios, SQL no padrão do CLAUDE.md.

### Câmera virtual: pyvirtualcam sobre OBS Virtual Camera (v1)

pyvirtualcam no Windows escreve no driver do OBS Virtual Camera (ou Unity Capture). O usuário precisa ter o OBS instalado, só pelo driver; não precisa abrir o OBS. É a dependência mais pesada do projeto e fica explícita na instalação.

Evolução planejada (pós v1, ADR própria): câmera virtual nativa do Windows 11 via `MFCreateVirtualCamera`, com uma media source em C++ empacotada como DLL. Elimina o OBS e é um ótimo capítulo de portfólio, mas é C++/COM e não deve travar o MVP.

### Front: React + Vite + TypeScript + SCSS

Um app, duas rotas com code splitting (`/cam` não carrega nada do console). Build estático servido pelo próprio agente; em produção não existe servidor Node.

### Resumo

| Camada | Escolha |
|---|---|
| Agente | Python 3.13, uv, FastAPI + uvicorn, aiortc, PyAV, numpy, pyvirtualcam, cryptography (certificado), segno (QR) |
| Banco | SQLite, migrations SQL próprias |
| Front | React, Vite, TypeScript estrito, SCSS com tokens, qrcode no console |
| Testes | pytest + pytest-asyncio, Vitest, Playwright com câmera falsa do Chromium |
| Qualidade | ruff, pyright strict, ESLint, GitHub Actions |
| App Windows | PyInstaller, pystray (bandeja), pywebview (janela WebView2), Inno Setup (instalador e regra de firewall) |
| Docker | `docker compose` de desenvolvimento e CI: agente headless com câmera falsa, web, Playwright |

## 4. Arquitetura

### Visão geral

```
 Celular (navegador)                         PC
 ┌──────────────────────┐   HTTPS :8443   ┌──────────────────────────────────────────┐
 │ /cam                  │ ─────────────▶ │ agente wcam (Python)                      │
 │ getUserMedia          │  POST offer    │                                           │
 │ RTCPeerConnection ════╪═══ WebRTC ════▶│ media: track ▶ decodifica ▶ ajusta quadro │
 │ DataChannel "control" │◀═══ controle ══│        │                    │             │
 │ Wake Lock             │                │        ▼                    ▼             │
 └──────────────────────┘                │   MediaRelay           VirtualCameraSink  │
                                          │        │                    │             │
 Console no PC (navegador)  HTTP :8080    │        ▼                    ▼             │
 ┌──────────────────────┐ ◀── SSE ─────── │   prévia WebRTC      OBS Virtual Camera   │
 │ / QR, estado, prévia, │ ◀═ WebRTC ════ │                            │             │
 │ métricas, controles   │ ── REST ─────▶ │ pairing, settings, sessions, persistence  │
 └──────────────────────┘                └────────────────────────────┼─────────────┘
                                                                       ▼
                                                        Meet, Teams, Zoom, Câmera do Windows
```

### Fluxo principal

1. `wcam` inicia: descobre o IP da LAN, gera ou carrega o certificado, abre o console em `http://127.0.0.1:8080` e o servidor do celular em `https://<ip-lan>:8443`, liga a câmera virtual já mostrando o quadro "aguardando celular".
2. O console pede um token de pareamento (uso único, 2 minutos) e mostra o QR com `https://<ip-lan>:8443/cam#t=<token>`. O token vai no fragmento (`#`) para não aparecer em log de servidor.
3. O celular abre o link, aceita o certificado na primeira vez, concede a câmera. A página mostra o visor e mantém a tela acesa (Wake Lock).
4. O celular cria a oferta WebRTC, espera juntar os candidatos ICE e faz `POST /api/sessions` com SDP e token, no espírito do padrão WHIP. O agente confere se o IP do celular está na mesma sub-rede do PC, valida e consome o token e responde com a SDP de resposta e um token de sessão. O token de sessão só serve para reconectar esta mesma sessão após uma queda curta; nunca abre uma sessão nova.
5. A mídia flui. O celular captura em paisagem a 1920x1080 e envia com bitrate alto. O agente abre a câmera virtual na mesma resolução, lê cada quadro já decodificado em YUV e o entrega ao sink sem redimensionar nem converter cor (CA-2), sempre fora do event loop. Espelhar é a única transformação, e só por escolha do usuário.
6. O console recebe estado e métricas por SSE e, com a prévia ligada, assina uma segunda conexão WebRTC alimentada pelo `MediaRelay`. A prévia é reduzida (640x360 a 15 fps) porque precisa ser recodificada; ela é só um monitor e não toca a saída da câmera virtual, que segue em 1080p sem perda (CA-2). Prévia desligada encerra essa conexão e o custo de CPU dela.
7. Controles do console (trocar câmera, resolução, espelhar) vão para o agente por REST e do agente para o celular pelo DataChannel. Celular cai: a câmera virtual volta ao quadro "sem sinal" e o celular tenta reconectar com o token de sessão.

### Módulos do agente

```
agent/
  pyproject.toml
  src/wcam/
    cli.py                 entrada `wcam`, argumentos, ciclo de vida
    app.py                 composição: monta dependências e os dois servidores
    config.py              configuração tipada (portas, resolução, diretório de dados)
    network/
      lan.py               descoberta do IP da LAN
      certificates.py      geração e carga do certificado autoassinado
    pairing/
      tokens.py            tokens de pareamento e de sessão (domínio puro)
    media/
      peer.py              RTCPeerConnection, oferta/resposta, DataChannel
      pipeline.py          quadro recebido ▶ quadro da câmera virtual
      frame_format.py      validação de formato e espelho (funções puras, testadas)
      quality.py           SSIM e checagens do CA-2 usadas nos testes
      placeholder.py       quadros "aguardando" e "sem sinal"
      metrics.py           fps, bitrate, latência, perdas
    virtualcam/
      sink.py              Protocol VirtualCameraSink
      pyvirtualcam_sink.py implementação real
      fake_sink.py         implementação de teste
    persistence/
      database.py          conexão, aplicação de migrations
      migrations/0001_initial.sql
      settings.py, sessions.py   repositórios
    api/
      phone_routes.py      rotas do servidor HTTPS da LAN
      console_routes.py    rotas do console local
      events.py            SSE
      errors.py            formato `{"error":{"code","message"}}`
  tests/
    unit/                  domínio e funções puras
    integration/           aiortc dos dois lados com track sintética, SQLite em arquivo temporário
```

Regra de dependência: `pairing`, `media/frame_format`, `persistence` não importam FastAPI; `api` depende do domínio, nunca o contrário. A câmera virtual e o hardware ficam atrás de `Protocol`, por isso o pipeline inteiro roda em teste e no CI sem driver.

### Front

```
web/
  src/
    main.tsx, router.tsx
    cam/                   superfície do celular
      cam-page.tsx, viewfinder.tsx, connection-badge.tsx, permission-gate.tsx
    console/               superfície do PC
      console-page.tsx, pairing-qr.tsx, live-preview.tsx, metrics-strip.tsx, controls-panel.tsx
    media/                 use-camera-stream.ts, use-publisher.ts, use-wake-lock.ts, use-preview.ts
    data/                  api-client.ts, events.ts, contract.ts (tipos espelhando docs/contrato.md)
    styles/                tokens.scss, base.scss
  e2e/                     Playwright com --use-fake-device-for-media-stream
```

### Contrato (vira `docs/contrato.md` na spec v0.3.0)

Servidor do celular (HTTPS :8443)
- `POST /api/sessions` `{token, sdp}` ▶ `{sessionId, sessionToken, sdp}`; erros `pairing_token_invalid`, `pairing_token_expired`, `pairing_window_closed`, `not_same_network`, `too_many_attempts`, `session_already_active`.
- `POST /api/sessions/{id}/reconnect` `{sessionToken, sdp}` ▶ `{sdp}`.

DataChannel `control` (agente para celular)
- `{"type":"switch_camera","facing":"user"|"environment"}`
- `{"type":"set_constraints","width":1280,"height":720,"fps":30}`
- `{"type":"set_paused","paused":true}` (nos dois sentidos: quem pausa avisa o outro lado)

Console (HTTP 127.0.0.1:8080)
- `POST /api/pairing` ▶ `{url, expiresAt}`
- `GET /api/status`, `GET/PUT /api/settings`, `GET /api/sessions`, `DELETE /api/sessions/current` (desconectar o celular)
- `POST /api/preview` `{sdp}` ▶ `{sdp}`
- `GET /api/events` (SSE): `session_started`, `session_ended`, `metrics`, `settings_changed`

### Dados (SQLite)

- `settings`: chave e valor (resolução de saída, fps, espelhar, câmera padrão).
- `sessions`: início, fim, nome do aparelho (a partir do user agent), IP, motivo do fim, resolução média. Só histórico: nada guardado autoriza uma conexão futura.
- `session_metrics`: amostras agregadas por 10 s (fps, bitrate, latência). Dá um histórico simples no console sem virar ferramenta de observabilidade.

### Segurança (CA-4: segurança mínima das portas abertas)

Ameaça considerada: qualquer pessoa na mesma rede (Wi-Fi de casa com visitas, café, hotel, empresa) tentando abrir a câmera, ver o vídeo ou mexer no agente. Fora do escopo: atacante com acesso ao próprio PC.

Superfície exposta
- Console só em `127.0.0.1`; nenhuma configuração é alcançável pela rede.
- Servidor da LAN escuta só no IP da interface Wi-Fi escolhida, não em `0.0.0.0`, e expõe apenas a página `/cam` e as rotas de sessão.
- As portas só existem enquanto o agente está "Ativo". "Parar" na bandeja fecha os servidores na hora.

Rede e firewall
- O instalador cria uma regra no Firewall do Windows por programa (`wcam.exe`), restrita ao perfil **Privado** e a **LocalSubnet**. A regra é por programa porque as portas UDP do WebRTC são dinâmicas. A desinstalação remove a regra.
- Em rede marcada como **Pública** o agente não abre a porta da LAN e explica como marcar a rede como privada ou usar o hotspot do celular.
- WebRTC só com candidatos ICE `host` da sub-rede local; sem STUN e sem TURN, nada sai para a internet.

Autorização: só pelo QR, só na mesma rede
- A única forma de autorizar um celular é ler o QR mostrado no PC. Não existe login, senha, aparelho lembrado nem link reutilizável.
- O token vai no fragmento da URL (`/cam#t=<token>`): o navegador nunca envia o fragmento em requisições, então ele não aparece em log, cabeçalho `Referer` nem histórico do servidor. A página lê o fragmento, apaga-o da barra de endereço e envia o token só no corpo do `POST /api/sessions`.
- No agente o token é guardado apenas como hash SHA-256 e comparado em tempo constante. Vazar o banco ou a memória de logs não entrega token utilizável.
- Token de 128 bits (`secrets`), uso único, válido por 2 minutos e só enquanto o QR está visível no console. Fora dessa janela o servidor da LAN responde `pairing_window_closed`.
- Mesma rede: o IP de origem da requisição precisa estar na sub-rede da interface Wi-Fi do PC (`not_same_network` caso contrário). Os candidatos ICE da oferta fora dessa sub-rede são descartados antes de aceitar a SDP. A regra do firewall restrita a LocalSubnet é a segunda camada da mesma garantia.
- Limite de tentativas por IP (5 por minuto, bloqueio de 10 minutos depois disso).
- Reconexão: o token de sessão (também guardado como hash) só religa a sessão em andamento, em até 60 segundos após a queda. Passou disso, sessão encerrada ou agente parado, só um novo QR.
- Uma sessão ativa por vez; segunda tentativa recebe `session_already_active`. O console mostra o aparelho e o IP conectados e tem "Desconectar".
- Código de confirmação: depois do QR, PC e celular mostram o mesmo código de 6 caracteres (Crockford base32, sem `0/O/1/I/L`, cerca de 30 bits), derivado das impressões digitais DTLS das duas pontas. Cada lado calcula o seu. O usuário confere e clica "Confirmar" no PC; até lá nenhum quadro chega à câmera virtual. Protege contra QR lido por outra pessoa (o código aparece no aparelho dela, não no do usuário) e contra intermediário na conexão (os códigos divergem). Uma confirmação por sessão; reconexão em até 60 segundos não pede de novo. Nada é digitado no celular.

Transporte
- HTTPS com certificado ECDSA gerado por instalação; chave privada no diretório de dados do usuário, com permissão só para ele. Impressão digital visível no console.
- Mídia criptografada por DTLS-SRTP (padrão do WebRTC).

Aplicação
- Checagem do cabeçalho `Host`, sem CORS, CSP estrita, limite de tamanho de corpo, timeout de sessão ociosa.
- Vídeo nunca é gravado em disco; logs nunca contêm tokens.
- CI com `pip-audit`, `npm audit` e CodeQL; a skill `security` roda antes de cada release.

Verificação do CA-4
- Teste automatizado para cada regra de pareamento e sessão (token expirado, reutilizado, fora da janela, IP de outra sub-rede, candidato ICE externo, limite de tentativas, reconexão depois de 60 segundos, token ausente dos logs).
- Varredura com `nmap` de outro aparelho na LAN: com o agente parado nenhuma porta aberta; ativo, só a porta da LAN; o console inacessível.

## 5. Interface

Processo: `taste-skill` (estilo `true-black-flat`, regras de app screen), `impeccable shape` para os estados, `emil-design-eng` e `mobile-native` no polimento, `impeccable audit` no fechamento. A spec de front registra qual skill guiou cada decisão.

### 5.1 Ideia

Linguagem de estúdio de transmissão. A luz de tally (aceso = a imagem está saindo nos apps) é o único estado compartilhado pelas duas telas e pelo ícone da bandeja. O elemento próprio do produto é a **cadeia de sinal** `Celular → Rede → WCam → Apps`, com o estado de cada trecho; quando algo falha, ela mostra onde e o que fazer.

As duas telas são máquinas de estado: em cada momento há uma coisa a fazer, e ela domina a tela. Sem sidebar, sem grade de cards, sem saudação.

### 5.2 Console no PC (janela WebView2, consultada de relance)

| Estado | O que domina |
|---|---|
| Aguardando celular | QR grande, contagem da janela de 2 min, uma linha sobre o aviso de certificado |
| Confirmar | código de confirmação grande, nome e IP do aparelho, Confirmar e Recusar |
| Ao vivo | prévia 16:9 do que os apps recebem (espelho aplicado), tally, cadeia de sinal, métricas (resolução, fps, bitrate, latência), controles; com a prévia desligada, a cadeia de sinal e as métricas ocupam o lugar dela |
| Pausado | prévia escura com "Pausado", Retomar como ação principal |
| Sinal perdido | prévia congelada e esmaecida, contagem de reconexão |
| Problema | cadeia de sinal destaca o trecho com falha e a correção |

Ajustes (resolução, fps, câmera padrão, espelhar, idioma, iniciar com o Windows) e Histórico ficam numa área secundária.

### 5.3 Celular (`/cam`, uma mão, configurado e esquecido)

| Estado | Tela |
|---|---|
| Sem token | como parear pelo PC, e nada mais |
| Antes da permissão | por que a câmera será pedida, depois o pedido do navegador |
| Em retrato | pede para girar; "Ao vivo" só em paisagem (CA-2) |
| Confirmar | o mesmo código, enorme, "Confira se é igual no PC" |
| Ao vivo | visor em tela cheia, tally, controles na zona do polegar |
| Pausado, reconectando, encerrado | estado claro e o que fazer |

Prévia desligada: um toque cobre o visor de preto, deixando só a tally e os controles esmaecidos (economia em OLED, menos calor, sem luz no rosto); a transmissão continua igual. Um toque religa. Com a câmera frontal, o visor do celular é espelhado como selfie, independente do ajuste Espelhar, que vale só para a saída do PC.

### 5.4 Controles nos dois lados

Toda ação existe nos dois lados quando faz sentido, e qualquer mudança aparece nos três lugares (console, bandeja, celular) em menos de 300 ms, pelo DataChannel e pelo SSE.

| Ação | Bandeja | Console | Celular | Efeito |
|---|---|---|---|---|
| Pausar / Retomar câmera | sim | sim | sim | a câmera do celular é desligada de fato (o indicador de privacidade do sistema apaga); a câmera virtual mostra o quadro "Pausado"; a sessão continua |
| Desconectar | sim | sim | sim | encerra a sessão; voltar exige novo QR |
| Trocar câmera (frontal, traseira) | sim | sim | sim | |
| Espelhar | sim | sim | não | só na saída do PC |
| Prévia ligada / desligada | não | sim | sim | cada lado controla a própria prévia; no PC desligar economiza CPU, no celular apaga a tela; a câmera virtual não é afetada |
| Parear celular (mostrar QR) | sim | sim | | abre o console no estado Aguardando |
| Abrir console | sim | | | |
| Iniciar com o Windows, Idioma | sim | Ajustes | | |
| Parar WCam | sim | sim | | fecha as portas e a câmera virtual volta a "Desligada" |
| Sair | sim | | | |

O ícone da bandeja muda com o estado: cinza (parado ou aguardando), verde (ao vivo), âmbar (pausado ou reconectando), vermelho (problema). Cada estado também muda a forma do ícone, não só a cor.

### 5.5 Idiomas

Inglês e português do Brasil desde a v0.1.0. Os textos ficam em `locales/en.json` e `locales/pt-BR.json` na raiz, lidos pelo web e pela bandeja do agente. Idioma detectado do sistema, com troca nos Ajustes; o celular segue o idioma do navegador. Nenhum texto de interface fica escrito no código; erros da API são traduzidos pelo `code`.

### 5.6 Tokens de cor

Paleta do usuário, já usada nos outros projetos, com o estilo `true-black-flat`: elevação só por luminosidade, sem sombra nem borda em painéis.

Fundos

| Token | Cor | Uso |
|---|---|---|
| `--ground` | #000000 | fundo |
| `--surface` | #111111 | painéis |
| `--raised` | #2a2a2a | elemento aninhado, botão secundário |
| `--rule` | #1a1a1a | filetes em listas |
| `--divider` | #222222 | divisórias |
| `--grid` | #2b2b2b | grade dos gráficos |

Texto

| Token | Cor | Uso |
|---|---|---|
| `--ink` | #ffffff | texto principal, botão primário (pílula branca, texto preto) |
| `--muted` | #b4b4b4 | rótulos |
| `--faint` | #949494 | terciário, indisponível |

Dados e estado

| Token | Cor | Uso |
|---|---|---|
| `--data` | #3ecf8e | série principal; tally "ao vivo" |
| `--data-2` | #e6e6e6 | segunda série |
| `--data-3` | #6b6b6b | terceira série |
| `--reference` | rgba(255, 255, 255, 0.4) | linha de referência tracejada (meta de 30 fps) |
| `--positive` | #3ecf8e | sucesso, ao vivo |
| `--negative` | #e5484d | erro |
| `--warning` | #e5a93b | pausado, reconectando, atenção |

Acréscimos para o WCam

| Token | Cor | Uso |
|---|---|---|
| `--positive-tint` | #12291e | fundo de pílula de estado verde |
| `--negative-tint` | #261012 | fundo de pílula de erro |
| `--warning-tint` | #2e2310 | fundo de pílula de atenção |
| `--scrim` | rgba(0, 0, 0, 0.6) | texto e controles sobre o vídeo (única transparência permitida) |
| `--focus` | #ffffff | anel de foco de 2px com 2px de afastamento |

Decisão: a tally "ao vivo" é verde (`--data`), não vermelha como na TV. Vermelho já é erro nesta paleta, e verde é a convenção atual de "câmera em uso" (indicador de privacidade do Android e do macOS). Cor nunca é o único sinal: todo estado tem também texto e forma.

Contraste conferido (WCAG): sobre `--ground`, `--muted` 10,1:1, `--faint` 6,9:1, `--negative` 5,4:1 e `--data-3` 3,9:1 (este só em marcas gráficas, nunca em texto). `--faint` sobre `--raised` fica em 4,7:1, perto do mínimo de 4,5:1. Cada cor de estado sobre o seu tint: verde 7,7:1, âmbar 7,4:1, vermelho 4,6:1.

### 5.7 Linguagem da interface

O WCam será usado por quem nunca vai ler o código. A interface fala de coisas que a pessoa vê: o WCam no computador, o celular, o QR code, o código, a câmera nos apps de reunião. Os nomes da arquitetura ficam no código e na documentação técnica.

| Termo interno | Na interface |
|---|---|
| agente, servidor, processo | o WCam (no computador) |
| sessão | conexão; "conectado", "desconectado" |
| pareamento, janela de pareamento, token | o QR code; "QR code novo", "QR code vencido" |
| código de confirmação | o código |
| requisição inválida, erro interno | "algo deu errado" com a próxima ação |
| interface não gerada | mensagem de instalação incompleta, com a ação |
| câmera virtual | "a câmera do WCam" ou "OBS Virtual Camera", que é o nome que os apps mostram |
| fps, bitrate, codec, CPU, SHA-256 | só em "Detalhes" no console, nunca na mensagem principal |

Levantamento de 2026-11-01: `console.status_checking`, `console.status_running`, `console.cpu`, `errors.network_error`, `errors.internal_error`, `errors.invalid_request`, `errors.web_not_built` e `errors.pairing_window_closed` usam termos internos; `terminal.fingerprint` e `console.video_format` mostram detalhe técnico fora de uma área de detalhes. A revisão completa, com um teste que falha se um termo proibido aparecer em `locales/`, entra na v0.5.0, junto com o console definitivo.

## 6. Roteiro de specs

Cada linha vira uma spec `docs/specs/spec-vX.Y.Z.md` com CA verificáveis. Uma só começa depois da anterior entregue.

| Versão | Nome | Entrega | CA principais |
|---|---|---|---|
| 0.1.0 | Fundação | monorepo, uv, Vite, ruff, pyright, ESLint, Vitest, pytest, `docker compose` de desenvolvimento, CI no GitHub Actions; `wcam` sobe os dois servidores com certificado gerado e imprime URL e QR no terminal | celular abre `https://<ip>:8443/cam` e vê uma página; `docker compose up` sobe o ambiente; CI verde |
| 0.2.0 | Captura no celular | `/cam` com permissão, visor, troca de câmera, Wake Lock, exigência de paisagem, tratamento de negação | 1920x1080 local em Android Chrome e iOS Safari; retrato bloqueia "Ao vivo" (CA-2) |
| 0.3.0 | Pareamento e WebRTC | tokens com hash, janela de pareamento, checagem de sub-rede, limite de tentativas, `POST /api/sessions`, peer aiortc, bitrate e `maintain-resolution`, `docs/contrato.md` | agente recebe 1080p30; todos os testes de pareamento do CA-4 verdes; teste de integração aiortc com aiortc |
| 0.4.0 | Câmera virtual (MVP) | pipeline sem redimensionar nem converter cor, sink real e falso, quadros "aguardando" e "sem sinal" | tabela inteira do CA-1 verificada; SSIM de pelo menos 0,98 e teste de 10 min do CA-2 |
| 0.5.0 | Console | QR no console, SSE, prévia por MediaRelay com liga e desliga, métricas numa área de detalhes, controles via DataChannel, revisão de linguagem de todas as superfícies (§5.7) | CA-3 completo; trocar câmera pelo console muda a imagem no Meet |
| 0.6.0 | Persistência | SQLite, migrations, preferências, histórico de sessões e métricas | preferências sobrevivem a reinício; histórico visível no console |
| 0.7.0 | Robustez | reconexão com token de sessão, troca de rede, tela do celular bloqueada, encerramento limpo | Wi-Fi do celular fora por 10 s volta sozinho; fora por mais de 60 s exige novo QR |
| 0.8.0 | Polimento do front | passada completa de `impeccable audit`, `emil-design-eng`, Playwright e2e | auditoria sem pendência crítica; e2e verde no CI |
| 1.0.0 | App Windows | executável PyInstaller, bandeja, janela WebView2, instalador com regra de firewall, README com GIF de demonstração, guia de solução de problemas, varredura `nmap` do CA-4 | instalação limpa num Windows sem o repositório funciona do zero; celular não instala nada |
| 1.x | Futuro | câmera virtual nativa (Media Foundation, sem OBS), Linux, macOS | cada uma com ADR própria |

## 7. ADRs iniciais (escritas na spec 0.1.0, após aprovação deste plano)

1. 0001 Monorepo com `agent` e `web`.
2. 0002 Agente em Python com aiortc.
3. 0003 WebRTC com sinalização HTTP de oferta única, sem trickle ICE e sem STUN/TURN.
4. 0004 HTTPS autoassinado na LAN e console só em localhost.
5. 0005 Câmera virtual via pyvirtualcam sobre OBS Virtual Camera na v1.
6. 0006 SQLite como banco local.
7. 0007 Front único com duas superfícies servido pelo agente.
8. 0008 App Windows de bandeja para o usuário final; Docker só em desenvolvimento e CI.
9. 0009 Autorização só por QR com token de uso único no fragmento da URL, guardado como hash, restrita à mesma sub-rede.
10. 0010 Código de confirmação derivado das impressões digitais DTLS, comparado nas duas telas e confirmado no PC.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Aviso de certificado assusta o usuário | explicação prévia no console; impressão digital visível; documentação com prints |
| iOS Safari pausa a câmera com a tela bloqueada | Wake Lock, aviso na `/cam`, reconexão automática |
| Dependência do OBS para o driver | checagem na inicialização com mensagem clara; câmera nativa no roteiro 1.x |
| Wi-Fi com isolamento de clientes (redes de hotel, empresa) | detecção de falha de conexão com mensagem orientando hotspot do celular |
| Driver DirectShow do OBS invisível para apps só Media Foundation (CA-1) | tabela do CA-1 verificada já na v0.4.0; se falhar, câmera nativa Media Foundation antes da v1.0.0 |
| Wi-Fi fraco não sustenta 10 Mbit/s (CA-2) | métrica de bitrate e perdas visível no console com aviso; fps cai antes da resolução |
| Celular aquece ou limita fps em 1080p por muito tempo | teste de 10 min do CA-2 em aparelho real; aviso no console quando o fps cai |
| Custo de CPU por quadro | sem conversão de cor nem redimensionamento; decodificação fora do event loop; meta medida na v0.4.0 (1080p30 abaixo de 20% de CPU num notebook comum) |
| Navegador descarta o fragmento `#t=` ao aceitar o aviso de certificado, e o primeiro pareamento falha | testar em Android Chrome e iOS Safari na v0.3.0; se acontecer, a `/cam` sem token, logo após o aviso, pede para ler o QR de novo e o console explica antes |
| Firewall do Windows bloqueando a porta 8443 | a primeira execução explica o prompt do firewall |

## 9. Decisões tomadas

1. Agente em Python.
2. SQLite como banco; sem Postgres.
3. OBS Virtual Camera como dependência na v1; se o CA-1 falhar, câmera nativa antes da v1.0.0.
4. Nome do projeto e da câmera virtual: WCam.
5. App Windows no PC, web no celular, Docker só em desenvolvimento e CI.
6. Autorização só pelo QR, com token no fragmento da URL, guardado como hash, uso único e restrita à mesma rede. Sem aparelho lembrado.
7. Código de confirmação derivado do DTLS, mostrado nas duas telas e confirmado no PC (ADR 0010).
