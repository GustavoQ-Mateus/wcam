# Design v1.0.0, app

Registro das decisões de interface da sessão app na v1.0.0, com a skill que guiou cada uma (CLAUDE.md, seção Front). Tokens de `docs/planejamento.md` §5.6.

## Atalho na tela: brief do `impeccable shape`

A rodada de perguntas da skill foi substituída pela spec v1.0.0 §1.1 e pelo planejamento §5, como no design v0.8.0; o brief foi aprovado pelo orquestrador em 2026-11-23. Suposições marcadas com (S). Pela ADR 0024, o desenho passou para páginas React do `web`; o comportamento de janela abaixo continua com o app.

1. **Tarefa.** A pessoa está numa reunião, com outra janela em foco, e quer ver de relance se a câmera está saindo e agir em dois gestos (Ctrl e mouse, depois um clique) sem sair do app da reunião. Modo Operate. Nada rouba o foco no uso pelo mouse nem aparece no compartilhamento de tela.
2. **Ícone.** Círculo de 36 px a 100% de escala (S) em `--surface`, glifo de câmera em `--ink` e marca de estado no canto com as formas da bandeja e do console: círculo cheio `--data` ao vivo, quadrado congelada, duas barras `--warning` câmera desligada, círculo vazado `--muted` sem celular, triângulo `--negative` problema, triângulo de reprodução vídeo. Fica 6 px para dentro da borda escolhida. Ctrl e arrastar move; ao soltar, gruda na borda mais próxima, e os cantos atraem a 5% deles.
3. **Painel.** Fundo `--surface`, sem sombra nem borda, ao lado do ícone, abrindo para dentro da tela, ~248 px de largura (S). Topo: estado em texto ("Ao vivo · Câmera traseira"). Ações: Congelar ou Descongelar ("travar"), Desligar ou Ligar câmera ("pausar"), Trocar câmera, Usar vídeo ou Voltar à câmera; depois Mostrar ou Esconder prévia flutuante, Abrir console, Esconder atalho na tela. Rodapé em `--faint`: a ajuda do Ctrl e o atalho de teclado. Ação indisponível em `--faint`, desabilitada.
4. **Foco.** Pelo Ctrl e mouse, o painel abre sem foco e fecha quando o mouse sai de painel e ícone por 400 ms. Pelo atalho global (padrão Win+Alt+W, configurável no arquivo de ajustes), o painel recebe o foco: Tab e setas navegam, Esc fecha e devolve o foco à janela anterior, clique fora ou uma ação fecham.
5. **Prévia flutuante.** Janela 16:9 sem moldura, 320x180 ao nascer, ao lado do ícone (S); arrasta por qualquer ponto e redimensiona pelas bordas entre 160x90 e 960x540 (S). Com o mouse em cima, um × em `--scrim` no canto. Sem quadro novo, o estado de espera.
6. **Movimento.** Painel abre em 120 ms (opacidade e 4 px vindo do lado do ícone) e fecha em 90 ms; o ícone desliza até a borda em 160 ms com ease-out. Com "Efeitos de animação" desligado no Windows, tudo é instantâneo. Troca de estado do ícone sem animação.

## Decisões do orquestrador (2026-11-23)

- "Pausar" é desligar a câmera (`cameraOff`) e "travar" é congelar (`frozen`); sem contrato novo.
- Atalho padrão Win+Alt+W: Ctrl+Alt+W colide com AltGr+W ("?") em parte dos teclados ABNT2. A Xbox Game Bar usa Win+Alt+R, G, B, K e PrtScn.
- O ícone e a prévia nativos (Win32 e D3D11) deram lugar a páginas React (ADR 0024) depois que o usuário viu a primeira versão.
