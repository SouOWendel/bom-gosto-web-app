# template

Este template é uma adaptação baseada no uso do modelo abntex-ifpi(https://g0dkar.github.io/abntex-ifpi/) criado por Rafael Madureira Lins de Araújo. Essa versão foi atualizada tendo como referência o modelo para monografia disponibilizado no site do IFPI (https://www.ifpi.edu.br/area-do-estudante/bibliotecas/monografiatemplate.pdf) e o Manual de Normalização de Trabalhos Acadêmicos do IFPI - 2022 (https://www.ifpi.edu.br/area-do-estudante/bibliotecas/manual-de-trabalhos-academicos). Além disso foram incluídas adequações e correções para o devido funcionamento aqui no OverLeaf, referências, inserção da citação direta e outras estilizações também necessárias.

Para contato ou sugestões: tulio.vidal@ifpi.edu.br (Prof. Tulio Vidal - Campus Corrente)

# abntex IFPI
Modificações ao [abnTeX](https://github.com/abntex/abntex2) para TCCs do IFPI. Este projeto contém uma série de modificações e ajustes ao modelo abnTeX original as quais o adaptam para os padrões exigidos pelo IFPI, disponíveis através [deste link](http://www5.ifpi.edu.br/consup/attachments/article/18/Resolução%20nº%20116%20Manual%20Trabalhos%20Acadêmicos.pdf).

O abnTeX-ifpi está na pasta abntex-ifpi. Se você quer usar apenas o abntex-ifpi e fazer seu trabalho do seu jeito, você vai precisar apenas da pasta `abntex-ifpi`.


## Não conheço o TeX/LaTeX... onde começar?
Faremos em breve um guia ensinando do zero como começar a trabalhar com TeX/LaTeX e como fazer um trabalho acadêmico com ele :)

## Como Usar
Aqui veremos como utilizar o abntex-ifpi. Para essa parte é esperado que você tenha conhecimentos sobre TeX/LaTeX, mas nada muito avançado.

### Apenas o abntex-ifpi
**Você pode pular esta parte se for utilizar o projeto todo como base para o seu trabalho**.

Para utilizar o abntex-ifpi, basta copiar a pasta `abntex-ifpi` dentro de seu projeto LaTeX e incluir o pacote com `\usepackage{abntex-ifpi/abntex-ifpi}`.

### Usando este projeto como base

Se você for usar esse projeto como ponto de partida é importante saber o que há em cada pasta do projeto:

* `abntex-ifpi`: Modificações do abnTeX para o IFPI. **Não mexa aqui**;
* `estrutura`: Mantém as partes do documento que são o preâmbulo, pré-textual, textual e pós-textual - **Você adiciona e remove capítulos no arquivo textual.tex que fica aqui**;
* `configuracoes`: Tem arquivos com várias configurações relacionadas ao documento final. **É aqui onde você configura o título do trabalho, Autor, Orientador e várias outras coisas**;
* `pre-textual`: Aqui ficam os elementos pré-textuais como Resumo, Abstract, Agradecimento, etc.;
* `pos-textual`: Aqui ficam os elementos pós-textuais como Bibliografia, Anexos, etc.;
* `capitulos`: Aqui ficam os capítulos do trabalho.

O arquivo principal do projeto é o `documento.tex`, na pasta raiz. **Compile este arquivo e seu trabalho estará pronto**!

O banco de dados BibTeX da bibliografia do projeto fica no arquivo `bibliografia.bib`.

### Primeiros Passos

Apesar de ser bem _na cara_ a forma de trabalhar e botar a coisa toda para funcionar, recomendamos que você veja os seguintes arquivos na ordem que estão apresentados:

1. `configuracoes/metadados.tex`: É onde você configura autor, titulo e outras coisas;
2. `configuracoes/tipografia.tex`: Aqui você pode configurar que fonte seu documento vai usar;
3. Na pasta `pre-textual`: Veja os arquivos que lhe interessarem na parte pré-textual. Observe que não há arquivos para as partes obrigatórias (como capa e folha de aprovação);
4. `estrutura/textual.tex`: Aqui é onde você inclui e remove capítulos;
5. Na pasta `capitulos`: Veja como são escritos os capítulos;
6. `bibliografia.bib`: Este é o banco de dados das citações que você colocará no texto através do comando `\cite{nome-da-referencia-no-arquivo-bibliografia.bib}`;
7. `documento.tex`: Arquivo principal do documento, e este que deve ser compilado para gerar seu trabalho.

## O que falta?
Fazer um tutorial legal ensinando o básico do LaTeX de forma simples :)
