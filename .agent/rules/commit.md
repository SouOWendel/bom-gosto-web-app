---
trigger: always_on
---

# Regras para Geração de Commits

Sempre que gerar ou formatar uma mensagem de commit (git commit), você DEVE seguir as regras abaixo:

1. **Idioma:** Toda a descrição e o corpo do commit devem ser escritos em Português do Brasil (pt-BR). Os prefixos do Conventional Commits devem ser mantidos em inglês (ex: feat, fix).
2. **Padrão:** Siga rigorosamente a especificação *Conventional Commits*.
3. **Estrutura:** 
   - Use o formato: `<tipo>[escopo opcional]: <descrição>`
   - Tipos permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
4. **Mensagens Longas:** Se a mensagem for longa, utilize a primeira linha como título e as demais linhas como corpo da mensagem (separadas por uma linha em branco). Deixe o corpo da mensagem resumido.
5. **Tom:** Escreva a descrição no modo imperativo (ex: "adiciona funcionalidade" em vez de "adicionei funcionalidade").
6. **Contexto:** Baseie a mensagem APENAS nos arquivos que estão em "stage" (staged changes), ignorando arquivos não preparados.