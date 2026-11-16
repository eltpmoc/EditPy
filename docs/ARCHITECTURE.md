# Arquitetura

## Decisões iniciais

Python 3.11+ e Qt/PySide6 fornecem uma base desktop compartilhada entre macOS, Windows e Linux. Foi utilizado PySide6-Essentials, que contém os módulos Qt necessários, evitando incluir WebEngine sem necessidade. A interface usa widgets desktop, com menus e ações adaptados à plataforma, sem servidor web local.

O editor é QPlainTextEdit com margem própria, realce incremental por bloco e popup de conclusão. O modelo QFileSystemModel carrega diretórios sob demanda. Documentos mantêm caminho, estado modificado, assinatura de disco e breakpoints.

Jedi fornece conclusão, definição e documentação. Ruff é chamado como ferramenta externa para formatação e análise. A navegação e o realce de código não importam os módulos do projeto. A seleção de interpretador é usada para execução e para o ambiente do Jedi.

## Concorrência

A interface permanece na thread Qt principal. Busca, inteligência, formatação e Git executam em QThreadPool com resultado por signals. Execução e shell utilizam QProcess, sem bloquear a interface. Operações de formatação descartam resultados se o conteúdo mudou. A busca descarta resultados de uma solicitação superada ou de outro projeto.

Processos em POSIX iniciam nova sessão; Parar encerra o grupo do processo. No Windows, o encerramento usa taskkill /T para alcançar a árvore de processos. O terminal usa um backend ConPTY separado, mantendo a mesma tela Qt.

## Arquivos e limites

Leitura de texto limitada a 2 MB por arquivo, rejeição de binários, busca limitada a 1.000 resultados e abertura rápida limitada a 20.000 arquivos. Busca ignora ambientes, dependências, diretórios de build e links simbólicos. Encoding Python é detectado com tokenize. Salvamento escreve em arquivo temporário na mesma pasta e substitui o destino, preservando permissões.

Arquivos limpos são recarregados se houver alteração externa. Arquivos modificados exigem resolução de conflito antes de sobrescrever. Não há recuperação de documentos não salvos após falha. A assinatura usa mtime_ns e tamanho; um sistema externo que preserve ambos pode escapar da detecção. Escrita atômica não fornece trava contra escritores simultâneos.

## Próximas separações

O controlador da janela concentra a composição inicial. Antes de adicionar DAP, LSP, bancos de dados e plugins, extrair serviços de DocumentManager, ProjectSession, InterpreterManager, RunConfiguration, LanguageClient e DebugSession. Cada serviço deverá expor eventos e modelos independentes dos widgets.

A camada de plataforma concentrará PTY/ConPTY, keychain, integração Finder/Explorer e processos. O domínio de documentos e protocolos permanecerá compartilhado. Não incluir operações destrutivas de Git ou instalação automática de pacotes em fluxos de consulta.

## Referência instalada

Inspeção local de metadados em 16/11/2026: `/Applications/PyCharm.app/Contents/Resources/product-info.json` informa PyCharm 2026.3, build 263.7307.206, código PY. A árvore instalada inclui plugins de banco de dados, JavaScript e outras integrações; isso é evidência de presença de arquivos, não de comportamento em execução.

REA não estava conectado à sessão. O diagnóstico CLI informou ausência de registro Codex; nenhuma configuração foi alterada. Não houve decompilação, cópia de código, recursos ou identidade visual do PyCharm. As escolhas do EditPy são implementação própria, com dependências públicas.

## Terminal e interface — 0.2.0

`terminal.py` mantém uma sessão PTY independente por aba. O dispositivo é criado com `posix_openpt` e `O_NOCTTY`; o escravo é aberto somente com `O_NOCTTY` no processo GUI. Um Python externo executa um bootstrap isolado, cria sua sessão com `setsid`, abre o escravo, atribui `TIOCSCTTY`, redireciona os descritores e executa o shell ou o REPL. O QProcess não abre o escravo no processo GUI. Isso evita herança indevida de terminal controlador e elimina callbacks Python depois de fork na aplicação Qt com múltiplas threads.

QSocketNotifier gerencia entrada/saída não bloqueante, com buffer para escritas parciais e leitura limitada por evento. O pyte interpreta os bytes UTF-8 e sequências VT/ANSI; um viewport Qt desenha células, seleção e cursor, mantendo até 5.000 linhas anteriores. Redimensionamento usa `tcsetwinsize`. A tela alternativa salva/restaura a tela principal. Fontes do terminal e métricas são independentes do stylesheet global.

Ao encerrar uma sessão, o app envia SIGHUP ao shell e ao grupo em primeiro plano, fecha o PTY antes de esperar pelo processo e recorre a SIGKILL quando necessário. A ordem evita bloqueio de drenagem de terminal no macOS. Processos que se daemonizam e saem da sessão não têm garantia de encerramento automático.

Documentos e terminais são tipos distintos na área de abas. Salvar e restaurar documentos ignora sessões. Trocar de projeto resolve primeiro documentos modificados, preservando terminais se a operação for cancelada. Atalhos de edição são desativados ou redirecionados ao selecionar um terminal, e Tab é entregue ao shell.

A árvore usa um proxy com filtro de diretórios gerados e um provedor de ícones vetoriais do EditPy, sem associações visuais de outros aplicativos. A barra lateral oferece acesso a projeto, busca, Git, terminal e console Python.

## Ícones e realce — 0.3.0

`file_icons.py` centraliza prioridades por nome e extensão para o explorador e as abas. `ProjectIcons` fornece QIcons com cache; pastas incluem estados fechado/aberto. As fontes SVG são produzidas por `scripts/create_file_icons.py`, com rótulos convertidos em contornos para não depender de fontes na máquina de destino. A árvore inclui dotfiles de projeto e mantém os filtros de diretórios gerados.

`syntax.py` aplica Pygments ao documento completo e usa AST somente para acrescentar papéis sintáticos em código Python válido. O arquivo nunca é importado. Código incompleto conserva a análise lexical. Uma tarefa por documento executa no QThreadPool global, após breve debounce; geração, texto e caminho são conferidos antes da aplicação. As cores lexicais locais continuam disponíveis durante a digitação. A renderização traduz índices Python/UTF-8 do AST para as unidades UTF-16 do QTextDocument, incluindo caracteres fora do BMP.

As cores separam declaração, chamada, classe/tipo, parâmetro, atributo, decorator, constante, string, docstring, escape, comentário, número, operador e pontuação, com paletas próprias para cada tema. Essa camada não substitui um servidor de linguagem nem resolve integralmente símbolos entre arquivos; é um complemento sintático ao lexer. Formatos não Python usam o lexer identificado pelo nome do arquivo. Salvar como atualiza caminho, ícone e lexer.

## Windows — 0.4.0

`windows_terminal.py` adapta o contrato de sessão ao ConPTY/pywinpty. Um QTimer lê a saída Unicode sem bloquear e a converte para o stream UTF-8 compartilhado. O backend oferece escrita, redimensionamento e encerramento da árvore de processos. O shell padrão é cmd.exe; o REPL usa o Python selecionado. Não é necessário um interpretador externo para iniciar o shell Windows.

`platforms.py` concentra shell, CommandLineToArgvW para argumentos de execução e aparência da barra de título via DWM. A versão portátil inclui ICO com sete resoluções, recursos PE de versão e avisos de terceiros. `packaging/windows.spec` e `scripts/build_windows.py` executam no Windows; GitHub Actions testa o código e o executável gerado. O frontend e os serviços de documentos permanecem compartilhados com macOS.


## Explorador — 0.5.0

`ProjectTree` implementa seleção múltipla e arrastar/soltar com URLs locais. `ExplorerMixin` conecta menu, clipboard, barra de ações e abas. `file_operations.py` prepara o lote antes da transferência, rejeita colisões e recursão em pastas, preserva links simbólicos e usa criação exclusiva para cópias de arquivos. Colar na pasta original gera nomes de cópia livres. Movimentos atualizam caminhos, highlighter, ícones e assinatura de disco dos documentos abertos sem descartar buffers modificados.

A exclusão solicita confirmação, trata documentos modificados e chama QFile.moveToTrash, sem fallback de exclusão permanente. Arquivos do clipboard usam URLs nativas do Qt; itens externos soltos na árvore são copiados, enquanto itens internos são movidos por padrão. Na área do editor, o drop abre arquivos/pasta em vez de inserir URLs no documento. As operações de disco são síncronas nesta versão; transferências grandes podem ocupar a interface. Não há desfazer de operações do explorador.
