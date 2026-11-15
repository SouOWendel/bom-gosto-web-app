# Instruções de Commits

Ao gerar, sugerir ou executar um commit, siga rigorosamente o Conventional Commits:

- Formato: `<tipo>[escopo opcional]: <descrição>`.
- Tipos permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test` e `chore`.
- Escreva título e corpo em Português do Brasil; mantenha os prefixos em inglês.
- Use o modo imperativo, capitalize adequadamente e não adicione ponto final ao título.
- Baseie a mensagem exclusivamente em `git diff --cached`.
- Mantenha o título entre 50 e 72 caracteres e a mensagem completa com no máximo 200 caracteres.
- Sempre que possível, use emoji para representar o tipo do commit.
- Em mensagens longas, use a primeira linha como título, uma linha em branco e um corpo resumido.

O Husky valida os commits automaticamente:

- `pre-commit` executa `npx lint-staged` e aplica o Prettier aos arquivos preparados.
- `commit-msg` executa `npx --no -- commitlint --edit "$1"` e bloqueia mensagens fora do padrão.
