# Continuar o EditPy em C++/Qt no Windows

Abra o repositório EditPy no Codex no Windows e envie o prompt abaixo. Este arquivo é uma passagem de contexto: a implementação C++ ainda não foi iniciada. A versão Python/Qt existente continua funcional.

---

Quero desenvolver e compilar a versão Windows do EditPy em C++ com Qt, preservando o comportamento e o visual da versão atual. Execute o trabalho no repositório, valide no Windows e entregue um aplicativo utilizável. Não encerre apenas com um plano ou um esqueleto de janela.

## Contexto e estado confirmado

- Repositório: https://github.com/eltpmoc/EditPy — branch principal `main`.
- Localize o checkout no Windows; não use literalmente o caminho macOS `/Volumes/ARQUIVOS/PROJETOS/DESKTOP/macOS/EditPy`.
- O projeto atual é Python/PySide6, com Qt Widgets. Não existe implementação C++ neste ponto da história; confirme o estado do checkout antes de criar arquivos.
- Última versão distribuída: **0.5.0**, com macOS Intel e Windows x64 portátil.
- Release funcional de referência: https://github.com/eltpmoc/EditPy/releases/tag/v0.5.0.
- Commit validado para essa release: `b6e96f703376fab9d585c44fa4af267e478099ca`; commits posteriores de documentação podem estar em main.
- Validação: 49 testes macOS passaram e 5 exclusivos Windows foram ignorados; 46 testes Windows passaram e 8 casos POSIX foram ignorados. Smoke tests dos dois aplicativos empacotados passaram.
- Run Windows aprovado: https://github.com/eltpmoc/EditPy/actions/runs/43918548925.
- SHA-256 do ZIP Windows 0.5.0: `e19dc211450ddbca88e26e6619f97ab6372104e8d263e408064007aa4ec4ad71`.
- A 0.5.0 Windows foi construída em runner Windows; não há bloqueio conhecido impedindo sua compilação. A migração C++ é uma nova implementação, não uma correção obrigatória do empacotamento atual.
- O app macOS 0.5.0 foi instalado em `/Applications/EditPy.app`. Preserve a versão macOS e o código Python funcional durante o desenvolvimento C++.
- O usuário pediu que o projeto permaneça **sem licença própria**. Não adicione automaticamente LICENSE MIT/GPL/etc. Preserve os avisos e as licenças das dependências e avalie compatibilidade antes de incluí-las.
- O EditPy não tem paridade completa com o PyCharm. Não anuncie cobertura de funcionalidades não implementadas; consulte `docs/ROADMAP.md`.

## Primeiros passos

1. Leia instruções AGENTS.md aplicáveis, `README.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, `docs/WINDOWS.md` e `docs/ROADMAP.md`.
2. Inspecione o código real, especialmente:
   - `editpy/window.py`: composição da janela, ações, projetos e sessões.
   - `editpy/explorer.py`, `file_operations.py`, `project_tree.py`: operações de arquivos, clipboard, menus e drops.
   - `editpy/editor.py`, `syntax.py`, `file_icons.py`, `themes.py`, `editpy/assets/`: editor e identidade visual.
   - `editpy/terminal.py`, `windows_terminal.py`, `platforms.py`, `tasks.py`: terminal, argumentos e processos.
   - `tests/test_explorer.py`, `test_desktop.py`, `test_windows.py`, `test_terminal.py`, `test_syntax_icons.py`: comportamento de referência.
   - `packaging/windows.spec`, `scripts/build_windows.py`, `.github/workflows/windows.yml`: build Python existente; não o confunda com compilação C++.
3. Verifique alterações locais e preserve trabalho do usuário. Identifique Windows, arquitetura, compilador, Qt SDK, CMake e ferramentas disponíveis. O Qt incluído no PySide6 não equivale automaticamente a um kit C++ completo.
4. Use um kit Qt/compilador de mesma ABI e arquitetura. Prefira MSVC x64 se houver um kit correspondente; não misture DLLs de MinGW/MSVC ou Debug/Release. Consulte a documentação oficial da versão escolhida e registre versões reais.
5. Use `native/` para o projeto C++ e diretórios de build separados. Se já existir implementação C++, continue-a; não a substitua às cegas.

## Arquitetura e entrega

- C++ e Qt 6 Widgets para janela, editor, arquivos, projetos, temas, terminal e persistência. CMake como sistema de build; padrão C++ compatível com o kit escolhido.
- A interface deve iniciar sem runtime Python embutido. Python instalado externamente continua sendo necessário para executar projetos Python e o REPL. Ferramentas externas de inteligência/análise podem usar Python por um protocolo documentado, sem transformar o aplicativo C++ em um lançador da GUI Python.
- Separe documentos, sessões de projeto, explorer, execução, terminal, configurações e inteligência. Use Qt signals/slots e operações assíncronas para impedir bloqueios da interface.
- Preserve recursos visuais originais: logo, ICO em múltiplas resoluções, ícones por extensão/pasta, paletas claras/escuras e contraste do realce. Não copie código/recursos proprietários do PyCharm ou do VSCode.
- Faça o núcleo compartilhável com macOS/Linux. Isole ConPTY, DWM, Explorer e detalhes de processos em código específico Windows.
- Desenvolva em incrementos compiláveis. Priorize primeiro a paridade com o EditPy 0.5.0; depois trate recursos avançados do roadmap. Registre diferenças pendentes em uma matriz de paridade.

## Recursos obrigatórios da referência 0.5.0

### Janela, documentos e editor

- Menus, atalhos Windows, temas claro/escuro e barra de título acompanhando o tema.
- Abas com ícones, fechamento, indicação de alterações, múltiplos documentos, atalhos e editor com números de linha, indentação, comentar, localizar/substituir, desfazer/refazer e navegação.
- Realce Python consistente, strings/comentários multilinha, f-strings, Unicode e código incompleto; destaque por formato para outros arquivos suportados. Mantenha os casos de teste de referência.
- Salvar/Salvar como/Salvar todos com escrita segura, encoding, detecção de alterações externas, proteção contra sobrescrever documento aberto em outra aba e decisões Salvar/Descartar/Cancelar.
- Abrir/fechar projeto, recentes, restauração de sessão e descarte de resultados assíncronos de um projeto encerrado. Cancelar deve preservar abas e processos.

### Explorador solicitado pelo usuário

- Barra abaixo de **Projeto**, com novo arquivo, criar pasta, colar e recolher pastas.
- Menu de contexto: **Novo**, **Copiar**, **Colar**, **Criar pasta**, **Mover para**, **Mostrar no Explorer** e **Excluir**.
- Seleção múltipla; criar no diretório selecionado ou ao lado do arquivo selecionado; área vazia usa a raiz.
- Clipboard nativo com URLs de arquivos. Copiar/Colar/Delete atuam na árvore quando ela tem foco e não interferem na edição de texto.
- Colar na mesma pasta cria nomes livres de cópia. Colisões em outros destinos não podem sobrescrever arquivos silenciosamente. Impeça recursão de uma pasta dentro dela mesma e movimentação/exclusão da raiz pelo menu.
- Excluir pede confirmação, trata documentos modificados e usa a Lixeira. Se a Lixeira falhar, preserve os itens e informe o erro; não use exclusão permanente como fallback.
- Ao mover arquivo/pasta, atualize caminhos, abas, ícones, highlighter e salvamento dos documentos abertos, preservando buffers modificados.
- Arrastar itens na árvore move entre pastas; Ctrl copia. Drops externos na árvore copiam; drops na área do editor abrem arquivos ou uma pasta de projeto. Não insira URLs no texto do documento.
- A abertura de uma pasta por drop deve respeitar o cancelamento de fechamento do projeto atual.

### Execução, terminal e inteligência Python

- Terminal real via **ConPTY**, com shell persistente em aba, entrada interativa, Unicode, redimensionamento, interrupção, seleção/copiar/colar, cores ANSI/VT, scrollback e limpeza dos processos ao fechar.
- Implemente renderização/interpretação VT em C/C++ ou use uma dependência adequada e avaliada. `pyte`/`pywinpty` são referências do backend Python, não uma implementação C++ pronta. Um QPlainTextEdit que apenas mostra saída de QProcess não substitui um terminal.
- Console Python interativo em aba com o interpretador selecionado, inclusive entrada multilinha.
- Executar/Parar e depuração; caminhos/argumentos Windows com espaços, aspas, Unicode e argumentos vazios. Encerre também os descendentes dos processos gerenciados.
- Preserve ou substitua explicitamente as integrações de conclusão, definição, documentação, formatação/análise e Git. A referência usa Jedi, Ruff e pdb; não apresente botões sem comportamento real como recursos concluídos.

## Compilar e distribuir no Windows

- Crie CMakeLists.txt, testes Qt Test/CTest e um script PowerShell de build reproduzível. Os comandos abaixo são a forma esperada **depois que esses arquivos e alvos existirem**; ajuste aos nomes efetivamente implementados.
- Em um terminal com o ambiente do compilador correspondente ao kit Qt, use `Qt6_DIR`/`CMAKE_PREFIX_PATH` ou `qt-cmake` para localizar o SDK. Não grave caminhos particulares da máquina no repositório.

```powershell
# Exemplo com gerador multi-config disponível e o Qt SDK configurado:
cmake -S native -B build/native-windows -DCMAKE_PREFIX_PATH="$env:EDITPY_QT_ROOT"
cmake --build build/native-windows --config Release --parallel
ctest --test-dir build/native-windows -C Release --output-on-failure
cmake --install build/native-windows --config Release --prefix dist/EditPy-native-Windows-x64
# O nome e o destino devem corresponder ao alvo real instalado:
& "$env:EDITPY_QT_ROOT\bin\windeployqt.exe" --release dist/EditPy-native-Windows-x64/EditPy.exe
```

- Verifique que `EDITPY_QT_ROOT` corresponde a um SDK C++ real antes de usar esse exemplo. Para geradores single-config, configure explicitamente `CMAKE_BUILD_TYPE=Release`. Não suponha a pasta de saída do executável.
- Inclua plugin de plataforma Windows, suporte a SVG, recursos de marca, dependências reais e avisos de terceiros. Trate o runtime MSVC com o redistribuível oficial adequado, conforme a documentação; não presuma que copiar DLLs do computador de desenvolvimento é suficiente.
- Gere PE com ícone e metadados de versão e sem console extra para a GUI. Verifique separadamente shell/REPL e processos filhos.
- Teste a distribuição em ambiente sem Qt SDK, sem o PATH do desenvolvimento e sem Python para a abertura da IDE; depois valide execução de projetos com Python externo selecionado.
- Gere ZIP portátil e SHA-256. Um instalador pode ser adicionado após o pacote validado. Não anuncie assinatura Authenticode inexistente.
- Acrescente CI Windows específico para C++ sem remover a validação da versão Python/macOS.

## Critérios de conclusão

1. Aplicativo C++ compilado e iniciado no Windows; não apenas projeto configurado ou GUI Python renomeada.
2. Testes de documentos, arquivos, colisões, exclusão/cancelamento, clipboard e drops com arquivos temporários reais.
3. Testes do ConPTY/REPL com TTY, Unicode, entrada, resize, Ctrl+C, processos descendentes e caminhos com espaços.
4. Revisão visual da janela/menus nos dois temas e validação da barra de título, fontes e ícones. Teste o botão direito real, além de construir o QMenu em testes.
5. Pacote Release independente do SDK de desenvolvimento, ZIP/SHA-256 e documentação de execução.
6. Registre comandos e resultados reais, capturas sem dados pessoais do usuário, dependências, limitações e matriz de paridade com a 0.5.0. Não marque como completo um recurso só porque sua ação aparece no menu.
7. Se houver impedimento de ambiente, explique o erro exato e deixe código, scripts e instruções reproduzíveis para continuar. Não invente uma compilação Windows bem-sucedida a partir do macOS.

Prossiga com a implementação, compilação e correção dos problemas encontrados. Faça escolhas rotineiras de arquitetura e organização de arquivos sem interromper o trabalho para pedir confirmação de cada etapa.

## Documentação oficial de referência

- Qt + CMake: https://doc.qt.io/qt-6/cmake-get-started.html
- Distribuição Windows e windeployqt: https://doc.qt.io/qt-6/windows-deployment.html

Consulte a documentação correspondente ao SDK efetivamente instalado; os links acima acompanham a versão atual do Qt.
