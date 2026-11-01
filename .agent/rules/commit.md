---
trigger: always_on
---

# Regras para Geração de Commits

Sempre que gerar ou formatar uma mensagem de commit, siga rigorosamente estas regras:

1. Use o formato `<tipo>[escopo opcional]: <descrição>`.
2. Permita somente os tipos `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test` e `chore`.
3. Escreva toda a descrição e o corpo em Português do Brasil; mantenha os prefixos em inglês.
4. Use o modo imperativo, capitalize adequadamente e não inclua ponto final no título.
5. Baseie a mensagem apenas nos arquivos preparados, consultando `git diff --cached`.
6. Limite o título a 50–72 caracteres e a mensagem completa a no máximo 200 caracteres.
7. Use emoji para representar o tipo do commit sempre que possível.
8. Para mensagens longas, use título na primeira linha, uma linha em branco e corpo resumido.

O Husky executa as validações automaticamente:

- O hook `pre-commit` executa `npx lint-staged` e aplica o Prettier aos arquivos preparados.
- O hook `commit-msg` executa `npx --no -- commitlint --edit "$1"` e rejeita mensagens inválidas.
