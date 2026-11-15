# Design v0.9.0, web (revisão 2)

Registro das decisões de interface da sessão web na v0.9.0, com a skill que guiou cada uma (CLAUDE.md, seção Front). Mundo visual herdado da v0.8.0 (`docs/design-v0.8.0.md`), tokens de `docs/planejamento.md` §5.6. Esta revisão substitui o registro da revisão 1; o que mudou e por quê está na seção 1.

## 1. O que mudou da revisão 1 e por quê

| Revisão 1 | Revisão 2 | Por quê |
| --- | --- | --- |
| Painel Vídeo abaixo do QR, sem celular | Nada de vídeo sem celular `live` e sem vídeo ativo; "Usar vídeo" na fileira de controles do Ao vivo abre o editor | O usuário achou a área solta abaixo do QR feia, e a spec passou a exigir o celular (ADR 0017) |
| Descongelar sobre a prévia e na fileira | Cada controle uma vez só: a prévia mostra só o estado (congelado desde, câmera desligada), o botão fica na fileira. Vale também para o Ao vivo da v0.8.0, que tinha o mesmo par repetido com Ligar câmera | Bug apontado na bateria; a spec §2.1 pede um controle por lugar |
| Um arquivo, barra de posição simples | Editor: biblioteca, linha do tempo de trechos com miniaturas, régua, cursor, cortar, dividir, arrastar, zoom | Pedido do usuário (estilo Clipchamp) |
| Voltar ao celular desconectava | Voltar à câmera religa a câmera do mesmo celular | ADR 0017 |

## 2. Editor: brief do `impeccable shape`

A rodada de perguntas da skill foi substituída pela spec v0.9.0 revisão 2 aprovada (§2), pelas falas do usuário registradas nela e pelo console da v0.8.0, que já define o mundo visual. O usuário não opera esta sessão; ele confere o visual no fechamento. Suposições marcadas com (S).

1. **Tarefa e público.** Quem usa o WCam no próprio PC, com o celular conectado, e quer que a câmera mostre uma sequência de vídeos em vez do celular, antes ou durante uma reunião. Modo Operate (`impeccable`, `taste-skill` app screen): montar a sequência, ligar, saber num olhar o que a câmera está mostrando, voltar à câmera.
2. **A pergunta da tela** (`taste-skill` §2.2): "O que a câmera está mostrando agora, e o que vem depois?". O maior bloco é a prévia (o quadro entregue, ADR 0015); o segundo é a linha do tempo, na largura toda, com o cursor mostrando onde a prévia está. O achado da tela é o estado: "Vídeo em repetição" na pílula e, abaixo da prévia, "A câmera está mostrando o vídeo, não o celular".
3. **Direção.** Mesmo esqueleto do Ao vivo, para quem já conhece o console:
   - Linha de cima: prévia 16:9 à esquerda; à direita, a biblioteca "Vídeos" e, abaixo dela, o celular (painel Celular, ou o QR quando o celular saiu com o vídeo rodando).
   - Fileira de reprodução na largura toda: Pausar ou Continuar, "0:12 de 0:34" em figuras tabulares, Dividir, Excluir trecho, Afastar e Aproximar; à direita, Espelhar, Prévia e o botão principal (Usar vídeo com o vídeo inativo, Voltar à câmera com ele ativo). Com o vídeo inativo, Voltar à câmera também aparece, como secundário, e fecha o editor.
   - Linha do tempo na largura toda: régua em cima, faixa de trechos embaixo, cursor atravessando as duas.
   - Formato e Detalhes abaixo, lado a lado.
   Planos em `--surface` sem borda nem sombra, elevação só por luminosidade (`true-black-flat`), cor só em dado e estado.
4. **Escopo.** O da spec §2.1 a §2.5. Sem desfazer, sem várias faixas, sem cancelar envio (S: a spec não pede).
5. **Estados e faixas.** Biblioteca de 0 a 20 vídeos (lista com rolagem própria depois de uns 5); linha do tempo de 0 a 50 trechos, de 0,5 s a horas; nomes longos com reticências; envio na fila (na fila, enviando com porcentagem, erro com o texto do `code`); linha do tempo vazia (caixa tracejada "Arraste um vídeo para cá", o único tracejado da tela, permitido pelo `taste-skill` §13 para espaço vazio); sem celular com o vídeo ativo (adicionar desabilitado com "Conecte o celular para enviar um vídeo", QR no lugar do painel Celular); remover vídeo em uso (confirmação na própria linha: "Este vídeo está na linha do tempo. Remover também os trechos?", Remover e Manter).
6. **Interação.**
   - Trecho: largura proporcional à duração, a tira de miniaturas lado a lado na proporção do vídeo, nome embaixo à esquerda num rótulo em `--scrim`. Entre trechos, 2 px de chão (`--ground`) separam sem linha. Selecionado: contorno interno de 2 px em `--ink` e as bordas de corte aparecem como barras de 12 px em `--ink`; sem seleção, as bordas aparecem no hover.
   - Cursor: linha de 2 px em `--ink` com uma cabeça retangular na régua. Pausado ou inativo, o cursor é o ponto de Dividir; com o vídeo ativo, clicar ou arrastar na régua pula (pedido ao soltar).
   - Biblioteca: miniatura (primeiro quadro da tira), nome, duração, botão Adicionar à linha do tempo (ícone `Plus` do lucide, com rótulo acessível) e Remover (ícone `Trash2`). Cada linha pode ser arrastada para a faixa; arquivos do sistema soltos na biblioteca ou na faixa entram na fila de envio.
   - Pílula: "Vídeo em repetição" com o triângulo em `--data-2` (sexto estado da bandeja); com o vídeo inativo, o editor continua "Ao vivo" em verde, porque a câmera ainda é o celular.
7. **Restrições.** Textos só em `locales/`; glossário §5.7 (nada de "upload", "clipe", "servidor"); foco visível de 2 px; cor nunca é o único sinal (selecionado tem contorno e `aria-pressed`, envio tem porcentagem em texto); teclado da spec §2.3; métricas técnicas do vídeo só em Detalhes.

## 3. Movimento (`emil-design-eng`, `animate`, `review-animations`, `animation-performance`)

- Arrastar trecho: o trecho segue o ponteiro sem transição (resposta direta), sobe para `--raised`; os vizinhos abrem espaço com `transform` em 200 ms `--ease-out`. Ao soltar, assenta em 160 ms. Só `transform`: nada de `left` ou `width` durante o arraste.
- Cortar: a borda segue o ponteiro sem animação; o tempo do ponto de corte aparece sobre a borda enquanto segura.
- Cursor: anda pelo relógio local a cada quadro (`requestAnimationFrame`, só `transform`), corrigido pelo valor do agente a cada evento (regra da revisão 1).
- Zoom: sem animação; mantém o cursor à vista.
- Pressionar: `scale(var(--scale-press))` em 120 ms, como no resto do console.
- `prefers-reduced-motion`: os vizinhos trocam de lugar sem deslizar.
- Mover pelo teclado (Alt com setas), dividir (S) e excluir (Delete) não animam: ação de teclado repetida (`animate`, passo 1).
- Revisão `emil-design-eng` aplicada no código:

| Antes | Depois | Por quê |
| --- | --- | --- |
| Ao soltar, os vizinhos voltavam do deslocamento com a transição enquanto o `left` já mudava, e davam um salto para trás | Um quadro com `data-instant` sem transição na troca de ordem | A nova ordem aparece no lugar, sem o trecho voltar e deslizar de novo |
| Um segundo dedo ou ponteiro podia começar outro gesto no meio do arraste | Gesto novo ignorado enquanto há um em curso | Proteção de vários toques |
| Bordas de corte sempre à mostra | Bordas aparecem no trecho selecionado, no foco e no hover (com `hover: hover`) | Menos ruído na faixa; o toque não gera hover falso |
| Arraste por `left` | Arraste por `transform`, captura do ponteiro | Fora do layout e sem perder o gesto se o ponteiro sair do trecho |

- `review-animations` não pôde ser chamado por esta sessão (a skill só roda por pedido do usuário, `/review-animations`); fica como pendência no relatório.

## 4. Celular (`mobile-native`)

- Com `video_source` `true`, a faixa da câmera para (luz apagada) e o visor dá lugar a uma mensagem em tela cheia, no mesmo sistema das mensagens do `/cam`: "O computador está mostrando um vídeo", "A câmera deste celular está desligada." e o botão principal "Voltar à câmera", na zona do polegar. A luz de "ao vivo" some, porque o celular não está mandando imagem.
- Com `false`, a câmera é pedida de novo e o visor volta, sem novo QR.
- `mobile-native`: a tela usa as margens com `env(safe-area-inset-*)` do `/cam`, o botão principal da v0.8.0 (resposta no `:active`, sem destaque de toque) e transição só de opacidade, desligada com `prefers-reduced-motion`. Falta conferir num celular real.

## 5. Gráficos do `/dev` e ícones (sem mudança desde a revisão 1)

- uPlot medido e não adotado: não reduziu a CPU (renderizador 9,97% com SVG contra 15,14% com uPlot, prévia ligada) e somou 22,5 KB ao `/dev`. Números em `docs/relatorio-v0.9.0-web.md`.
- Ícones em `lucide-react`: Congelar `MonitorPause`, Desligar câmera `VideoOff`, Prévia desligada `MonitorOff`, Trocar câmera `SwitchCamera`, Formato `Proportions`, Celular `Smartphone`; nesta revisão, `Plus` e `Trash2` na biblioteca. Mesmo traço e tamanho dos outros.
