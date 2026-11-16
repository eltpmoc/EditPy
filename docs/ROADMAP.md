# Produto e cobertura de recursos

EditPy tem como objetivo tornar-se uma IDE Python completa, com identidade visual própria e prioridade inicial no macOS. A versão 0.2.0 estabelece o editor e os fluxos locais. A tabela distingue implementação existente de planejamento; não declara paridade com o PyCharm.

## Etapa 1 — base local entregue em código

| Área | Situação em 0.2.0 | Evolução necessária |
| --- | --- | --- |
| Interface | Temas claro/escuro, abas, painéis, preferências | Acessibilidade completa, atalhos editáveis, zoom, localização |
| Projetos | Abrir/fechar pasta, recentes, árvore, menu de contexto, criar/copiar/colar/mover, Lixeira e arrastar/soltar | Assistentes de projetos, renomear, desfazer operações, múltiplas raízes |
| Edição | Python, numeração, autoindentação, comentários | Folding, múltiplos cursores, pares de delimitadores, minimapa, split editor |
| Persistência | Escrita atômica, encoding Python, conflito externo, abas salvas | Recuperação de documentos não salvos e histórico local |
| Busca | Texto no arquivo/projeto, substituição no arquivo | Regex, filtros, substituição no projeto com prévia |
| Navegação | Abrir rápido, linha, definição, estrutura | Referências, hierarquia, símbolos globais, voltar/avançar |
| Inteligência | Jedi sob demanda com interpretador selecionado | LSP, assinaturas, autoimport, cache e cancelamento |
| Diagnósticos | AST e Ruff explícito | Diagnósticos contínuos, correções rápidas e tipos via Pyright |
| Formatação | Ruff com desfazer em uma operação | Configuração por projeto, import sorting e EditorConfig |
| Execução | Arquivo atual, argumentos, interpretador e stdin | Configurações nomeadas, env vars, módulos, perfis e cwd configurável |
| Depuração | pdb com breakpoints e inspeção textual | DAP/debugpy, variáveis/pilha visuais, watches, condições, threads e attach |
| Testes | unittest e comandos manuais | Árvore pytest/unittest, seleção, falhas navegáveis, cobertura e debug |
| Ambientes | Seleção de Python, criação .venv, pip list | Detecção automática, Poetry, uv, Conda e gestão de pacotes |
| Console | Terminal PTY no macOS, ConPTY no Windows e REPL Python persistentes em abas; múltiplas sessões, ANSI, scrollback e encerramento | Validar Linux, compatibilidade TUI adicional e persistência de perfis |
| Git | Status e diff HEAD, somente leitura | Stage/unstage, commits, histórico, branches, conflitos e merge visual |

## Etapa 2 — inteligência e refatoração

- Implementar protocolo de serviços de linguagem com versões de documentos, cancelamento e timeouts.
- Adicionar find usages e rename de símbolos com análise de referências e prévia de mudanças.
- Extrair função/variável, alterar assinatura, mover símbolos e organizar imports.
- Validar refatorações com casos entre arquivos, escopos, ambientes e sintaxe incompleta.
- Integrar inferência de tipos, quick fixes e inspeções configuráveis.
- Suportar edição de HTML, CSS, JavaScript/TypeScript, JSON, YAML, TOML, Markdown e SQL com parsers próprios.

## Etapa 3 — execução profissional

- DAP/debugpy: breakpoints condicionais, exceções, console de avaliação, pilha e inspeção de objetos.
- Perfis de execução persistentes por projeto, pytest, cobertura e profiler CPU/memória.
- Ampliar compatibilidade do terminal e gestão de perfis; validar processos desacoplados, protocolos de mouse e TUI.
- Jupyter: kernels, notebooks, células, outputs e visualização de tabelas e gráficos.
- Frameworks Django, Flask e FastAPI: projetos, templates, rotas, configuração e execução.
- Cliente HTTP com arquivos de requisição e ambientes.

## Etapa 4 — integrações avançadas

- Banco de dados: conexões, credenciais no keychain, schema, editor SQL e resultados paginados.
- Docker/Compose e interpretadores em contêineres.
- SSH/SFTP, execução e depuração remotas; sincronização explícita.
- Integração WSL na versão Windows.
- Ferramentas frontend, npm e depuração JavaScript.
- Controle de versão completo, visualização de diff, resolução de conflitos e histórico local.
- API de extensões isolada, descoberta, permissões, compatibilidade e atualização.
- Recursos assistidos por IA com provedor configurável e consentimento para envio de código.

## Etapa 5 — distribuição

1. Consolidar macOS Intel: integração Cocoa, testes reais de teclado, retina, suspensão, arquivos externos e projetos grandes.
2. Criar build macOS Apple Silicon e testar em hardware arm64. Não declarar universal sem validar ambas as arquiteturas.
3. Ampliar a validação Windows em hardware físico; instalador e assinatura Authenticode. O pacote portátil, ConPTY, caminhos/quoting e testes no runner já estão disponíveis.
4. Empacotar e validar Linux: Wayland/X11, shell, permissões, ícones e AppImage/deb.
5. Adicionar CI por plataforma, assinatura/notarização, instaladores, atualizações, SBOM e auditoria de licenças.

## Critérios de conclusão

Uma funcionalidade somente será considerada entregue quando tiver comportamento implementado, tratamento de erros, validação proporcional, interface utilizável e limitações documentadas. Paridade integral depende da versão/edição e das integrações do PyCharm usadas como referência, além de uma auditoria funcional por cenário. O inventário local de plugins não demonstra que todos estejam ativos, licenciados ou tenham sido testados.
