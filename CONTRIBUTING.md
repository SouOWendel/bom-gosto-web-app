# Guia de Contribuição — Confeitaria Bom Gosto

Obrigado por contribuir com o projeto! Para manter o código organizado, legível e padronizado entre todos os membros da equipe, seguimos as diretrizes abaixo.

---

## 🛠️ Padrão de Nomenclatura de Branches

Sempre crie uma nova branch a partir da `main` utilizando o padrão de prefixos:

`prefixo/escopo-ou-issue/descricao-curta`

| Prefixo     | Finalidade                                         | Exemplo                       |
| :---------- | :------------------------------------------------- | :---------------------------- |
| `feat/`     | Novas funcionalidades                              | `feat/12-cadastro-pedidos`    |
| `fix/`      | Correção de bugs                                   | `fix/calculo-sinal-pagamento` |
| `refactor/` | Refatoração de código sem alterar regra de negócio | `refactor/django-views-core`  |
| `chore/`    | Manutenção, dependências e configurações           | `chore/setup-husky-prettier`  |
| `docs/`     | Alterações de documentação                         | `docs/update-contributing`    |
| `test/`     | Adição ou modificação de testes unitários          | `test/order-service-jest`     |

---

## 📝 Conventional Commits

Todas as mensagens de commit são validadas automaticamente pelo **Commitlint** através do **Husky**. Commits fora do padrão serão bloqueados.

### Formato Obrigatório

```text
tipo(escopo opcional): descrição curta no imperativo
```
