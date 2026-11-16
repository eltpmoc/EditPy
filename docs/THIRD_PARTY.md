# Componentes de terceiros

O EditPy é uma implementação independente. Não inclui código, ícones, marca ou runtime do PyCharm. O nome PyCharm identifica apenas o produto de referência informado pelo usuário.

Dependências diretas e ferramentas usadas:

| Componente | Uso | Licença declarada pelo projeto |
| --- | --- | --- |
| Python | Runtime | PSF |
| Qt / PySide6 / Shiboken | Interface desktop | LGPLv3/GPLv3/comercial, conforme componente |
| Jedi / Parso | Inteligência Python | MIT |
| Pygments | Análise lexical e realce de código | BSD-2-Clause |
| Ruff | Formatação e lint | MIT |
| PyInstaller | Empacotamento | GPL com exceção para aplicações empacotadas |
| pyte / wcwidth | Emulação VT e largura de caracteres | LGPLv3+ (pyte) / MIT (wcwidth) |
| pytest | Testes de desenvolvimento | MIT |

As licenças originais estão nos pacotes instalados no ambiente `.venv`. A distribuição pública exigirá inventário/SBOM, inclusão de avisos e textos correspondentes, verificação dos módulos Qt distribuídos e atendimento das condições aplicáveis. O empacotamento atual destina-se a validação local.

Fontes oficiais: https://doc.qt.io/qtforpython-6/ ; https://github.com/davidhalter/jedi ; https://github.com/astral-sh/ruff ; https://pyinstaller.org/ .
