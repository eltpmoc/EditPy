# Validação local — 16/11/2026

## Ambiente

- macOS 26.7.3 em Intel x86_64, conforme o ambiente disponibilizado.
- Python 3.14.7; PySide6-Essentials 6.12.0; Jedi 0.19.2; Ruff 0.17.5.
- Versões exatas do ambiente em `requirements-macos.lock` (gerado no macOS; não é um lock universal entre plataformas).

## Testes automatizados

A suíte usa arquivos temporários e uma instância Qt com plataforma offscreen e preferências isoladas. Cobre:

1. Leitura e escrita de código Python com encoding latin-1.
2. Salvamento completo e preservação de permissão executável.
3. Rejeição de binários e arquivos maiores que o limite.
4. Busca ignorando dependências e links simbólicos.
5. Símbolos e erros de sintaxe sem executar o projeto.
6. Edição, salvamento, mudança de tema, recarga externa e abas únicas.
7. Substituição com desfazer e comentários em bloco.
8. Execução real de Python com entrada/saída e término do processo.
9. Breakpoint real com pdb e inspeção de variável.
10. Conclusão real com Jedi e formatação com Ruff.
11. Preservação de alteração local ao detectar conflito com disco.
12. Autoindentação por eventos reais de teclado Qt.
13. Interrupção de processo Python em execução.
14. Isolamento das chaves de sessão entre projetos.

Comandos:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check editpy tests scripts examples
.venv/bin/python -m compileall -q editpy
.venv/bin/python -m pip check
```

## Verificação do pacote

O modo explícito `--smoke-test REPORT` cria um projeto temporário, abre um arquivo, consulta Jedi, formata via Ruff, salva, executa o Python selecionado e alterna os dois temas. Produz um relatório JSON e uma captura da janela; termina com código diferente de zero se alguma verificação falhar. As preferências desse modo são isoladas.

```sh
dist/EditPy.app/Contents/MacOS/EditPy --smoke-test build/package-smoke.json
```

Os resultados de execução ficam na pasta local `build/`, ignorada no Git. Capturas de revisão de ambos os temas estão em `docs/screenshots/`.

O empacotador verifica a assinatura local antes e depois desse teste. A inicialização do pacote desabilita escrita de bytecode nos processos Python herdados, evitando que os subprocessos de inspeção do Jedi adicionem arquivos `__pycache__` ao bundle assinado.

## Limites da validação

Ainda faltam validação em Windows, Linux, Apple Silicon, outros computadores, leitores de tela, layouts internacionais de teclado e projetos grandes. As capturas geradas por Qt offscreen verificam layout, mas não substituem testes de interação no sistema operacional. O pacote local não representa uma distribuição pública assinada e notarizada.

## Tema nativo e identidade visual

A revisão da barra de título usa `QApplication.styleHints().setColorScheme`, além do stylesheet. A verificação `scripts/check_native_theme.py` consulta o `effectiveAppearance` da NSWindow real via runtime Objective-C, em plataforma Cocoa: escuro = `NSAppearanceNameDarkAqua`, claro = `NSAppearanceNameAqua`. Ela executa escuro → claro → escuro sem reiniciar a janela.

A suíte passou a incluir o carregamento do ícone e de ambos os logotipos em cada tema (15 testes). O smoke test do pacote também valida a marca e o esquema de cores nativo no macOS.

Documentação: https://doc.qt.io/qt-6/qstylehints.html#setColorScheme

## Revisão 0.2.0 — abas de terminal

Resultado da suíte local: **23 testes passaram**. Os oito novos cenários de integração cobrem PTY real e diretório persistente; entrada pelo teclado e Ctrl+C; dimensões transmitidas ao processo; REPL Python multilinha e Unicode; cores, scrollback e tela alternativa; documentos e terminais mistos, copiar/colar e fechamento imediato; Tab para conclusão do shell; cancelamento de troca de projeto preservando documentos e sessões.

O smoke test do pacote passou a abrir um shell em PTY, verificar `test -t 0`, executar um comando, abrir um REPL Python e executar uma expressão. Também verifica que salvar ignora sessões e que ambos os tipos de abas acompanham o tema. Os relatórios locais ficam em `build/source-smoke.json` e `build/package-smoke.json`.

Capturas do editor, terminal e console Python estão em `docs/screenshots/`, em versões claras e escuras. As sessões usadas nas capturas são processos reais com preferências isoladas.

Limites: testes de PTY realizados no macOS Intel desta máquina. Não foi realizada validação em Linux nem implementado ConPTY no Windows. O terminal não implementa todos os protocolos xterm ou todas as combinações de grafemas Unicode.

## Ícone e reconhecimento do pacote no Finder

O pacote foi reconstruído com `packaging/macos.spec`, incluindo versão 0.2.0, categoria de ferramentas de desenvolvimento e macOS mínimo 14.0 antes da assinatura. O build compara o ICNS distribuído com a matriz do projeto, verifica o executável e valida a assinatura antes e depois do smoke test.

A geração agora ocorre em `build/macos-dist`; somente o pacote completo e validado é publicado em `dist/EditPy.app`. O pacote anterior fica preservado em `build/previous`. O registro do aplicativo é atualizado individualmente via LaunchServices, sem limpar caches globais nem modificar proteções do sistema.

Verificação visual no Finder: o novo ícone aparece sem o símbolo de proibição. O smoke test do pacote e a verificação da assinatura passaram após a reconstrução. A causa exata do estado anterior do cache não foi demonstrada; o ICNS anterior, o executável Intel e a assinatura já eram válidos.

## Revisão 0.3.0 — ícones e cores

A suíte local cobre 31 cenários, incluindo papéis de declaração/parâmetro/chamada/tipo; isolamento entre funções; comentários com aspas; strings com `#`; strings multilinha e código após o delimitador; interpolação de f-strings; identificadores Unicode e posições UTF-16; Python incompleto; lexer JSON e texto simples; descarte de análises antigas; troca de paleta; nomes e extensões especiais; renderização dos SVGs e atualização do ícone/lexer ao salvar como.

O smoke test empacotado também verifica o realce de funções, a análise JSON e o carregamento de ícones representativos. O atlas de ícones e as capturas do editor em ambos os temas ficam em `docs/screenshots/`.

## Revisão 0.3.1 — fechar projeto/pasta

A suíte passou a 36 cenários. Os novos testes acionam a opção do menu e verificam limpeza da área de trabalho, reabertura posterior e início sem restaurar o projeto fechado; cancelamento de documentos modificados; salvamento antes de encerrar shell/processo; cancelamento da confirmação de processos; descarte de resultados de background recebidos após o fechamento. O smoke test empacotado também fecha o projeto e confere abas, árvore e preferências.

## Windows — 0.4.0

Build Windows aprovado: https://github.com/eltpmoc/EditPy/actions/runs/43915587302 (commit 179613f). Runner Windows Server 2025 x64, Python 3.14.10. Resultado: 33 testes passaram; 8 cenários POSIX foram ignorados. O macOS passou nos 36 testes compartilhados/POSIX e ignorou os 5 específicos de Windows.

O executável portátil passou no smoke test empacotado com plataforma Qt Windows e fontes verificadas (editor, Jedi, Ruff, realce Python/JSON, ícones, temas, execução, ConPTY, REPL, abas mistas e Fechar projeto/pasta). O ZIP foi baixado para dist, seu SHA-256 foi conferido e o executável PE foi verificado como x86_64. A validação Windows foi automatizada; revisão visual em hardware Windows físico e Authenticode continuam pendentes.

A captura do runner com plataforma Qt nativa foi revisada: fontes legíveis e terminal em aba. Registro em `screenshots/windows-terminal.png`. SHA-256 do ZIP 0.4.0: `e47a901f86fd44b51d66f09fbed16f30731a4492642716bc1f690aff7fc7008a`.


## Explorador — 0.5.0

Suíte macOS: 49 testes passaram e 5 cenários Windows foram ignorados. Treze novos cenários exercitam criação na seleção, menu/barra, cópia de pastas e seleção deduplicada, prevenção de colisões/recursão/traversal, movimentação com buffer modificado e salvamento no destino, cancelamento de cópia/exclusão, envio à Lixeira e falha da Lixeira, drop externo na árvore, drop no editor, drop interno e duplicação com nomes livres. O carregamento assíncrono da árvore é respeitado pelos testes de seleção.

O smoke test passou a copiar e mover um arquivo real, verificando que a aba acompanha o destino e que a barra contém as quatro ações. O envio real de um arquivo temporário à Lixeira foi conferido no macOS.

Windows 0.5.0: 46 testes passaram e 8 casos POSIX foram ignorados no run https://github.com/eltpmoc/EditPy/actions/runs/43918548925 (commit b6e96f7). O teste de seleção usa Path para normalizar separadores Windows. O macOS foi empacotado, passou no smoke test com `explorer_operations: true` e foi instalado em `/Applications/EditPy.app` com assinatura verificada e backup da versão anterior. O botão Novo arquivo foi conferido no aplicativo instalado; o evento Qt de contexto também foi verificado com um popup real.

O ZIP Windows 0.5.0 foi baixado e conferido por CRC e SHA-256; o executável é PE x86_64. Hash: `e19dc211450ddbca88e26e6619f97ab6372104e8d263e408064007aa4ec4ad71`. As capturas com a barra do explorador estão em `screenshots/explorer-macos.png` e `screenshots/explorer-windows.png`.
