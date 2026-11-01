# Agent Directives & Code Conventions

## Regras de Commits

Toda mensagem de commit deve seguir rigorosamente o Conventional Commits:

1. Use o formato `<tipo>[escopo opcional]: <descrição>`.
2. Use apenas estes tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test` e `chore`.
3. Escreva título e corpo em Português do Brasil; mantenha os prefixos em inglês.
4. Escreva a descrição no modo imperativo, sem ponto final no título.
5. Baseie a mensagem exclusivamente nas alterações preparadas em `git diff --cached`.
6. Mantenha o título entre 50 e 72 caracteres e a mensagem completa com no máximo 200 caracteres.
7. Quando possível, use emoji para representar o tipo do commit.
8. Em mensagens longas, use a primeira linha como título, uma linha em branco e um corpo resumido.

O Husky valida automaticamente os commits:

- `pre-commit`: executa `npx lint-staged`, aplicando o Prettier aos arquivos preparados.
- `commit-msg`: executa `npx --no -- commitlint --edit "$1"` e bloqueia mensagens fora do padrão.
