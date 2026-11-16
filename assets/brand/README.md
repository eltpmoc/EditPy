# Identidade EditPy

Símbolo original: monograma E acompanhado de um chevron de código, sobre uma base grafite arredondada. A paleta combina violeta e verde menta.

- `editpy-icon.svg`: matriz vetorial do ícone.
- `editpy-icon.png`: ícone de 1024 × 1024 com transparência externa.
- `editpy-logo-dark.svg` / `.png`: logotipo para superfícies escuras.
- `editpy-logo-light.svg` / `.png`: logotipo para superfícies claras.
- `../EditPy.icns`: pacote de tamanhos para Finder e Dock do macOS.

A tipografia dos SVGs foi convertida em contornos: os arquivos finais não exigem uma fonte instalada. Os PNGs dos logotipos têm fundo transparente. Preserve a proporção e use a variante correspondente ao fundo.

O gerador reproduzível é `scripts/create_icon.py`. As versões usadas pelo aplicativo ficam em `editpy/assets/` e são incluídas no pacote macOS.
