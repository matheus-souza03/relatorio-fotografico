## Como Funciona

Todo mês temos que enviar um relatório fotográfico para a prefeitura de uma cidade a qual prestamos serviços, que são documentos que expõe o que se foi feito durante todo o mês

As imagens são adicionadas no forms pelos colaboradores que trabalham nesta cidade.

Gledson (colaborador da administração) coleta as imagens uma a uma na planilha que é gerada pelo forms e as adiciona manualmente no word, preenchendo também em qual logradouro, bairro e número o serviço ilustrado pela imagem foi realizado. Isso o custa muito tempo desnecessário.

---

## Formato da página com as fotos

Data: Coluna (`Carimbo de data/hora)`

Equipe X: (sempre vai seguir a ordem: Página da Equipe 1 antes da Página da Equipe 2, equipe 1 sempre será Bruno e Anderson, equipe 2 Cláudio e Oracy) (IMPORTANTE!!! Os trabalhos não são divididos por equipe no Mundo Real, e por isso não possui nenhum campo indicando qual equipe foi responsável pelo serviço na planilha. As fotos devem ser adicionadas de 3 em 3, então logicamente, as 3 anteriores pertencerão à equipe 1 e as 3 seguintes à equipe 2)

| Antes                             | Depois                            |
| --------------------------------- | --------------------------------- |
| <Imagem antes>                    | <Imagem depois>                   |
| Colunas(`Logradouro: Bairro: Nº`) | Colunas(`Logradouro: Bairro: Nº`) |

---

Sempre são feitos 6 serviços por dia ( 3 por equipe), as datas que estão na planilha não são as exatas mesmas datas que vão para o Relatório Fotográfico.

As fotos do relatório são organizadas da seguinte maneira:

Pega o primeiro dia de trabalho que será registrado no relatório ( deve-se ter uma variável para que o usuário possa adicionar a data inicial e a data final do relatório ), nessa primeira data deve-se colocar as fotos relacionadas às primeiras 3 atividades (as primeiras 3 linhas da tabela) para a equipe 1, e as 3 seguintes para a equipe 2, para que assim sejam contabilizadas 6 atividades no dia, e isso deve ser feito até que se acabem as linhas da tabela.

Recaptulando, 6 atividades por dia cada atividade registrada em fotos em antes e depois.

**As páginas que possuem informações de carga horária de veículos e equipamentos deve apenas ser replicada logo após a página com as fotos da equipe 2, com todos os dados de carga horária em branco, pois estes dados serão preenchidos de forma manual.**

## Como Deve funcionar a automação, a priori

Subir a planilha com os dados do período desejado, isso em uma pasta específica dentro do projeto.

Ter como resultado um arquivo .docx com todas as imagens de antes e depois cadastradas, assim como os campos Data, Equipe e Endereço. (As imagens devem estar dentro do espaço delimitadas para elas, não devem ser modificadas de formato, se necessário apenas aumente ou diminua o tamanho, mas em proporção, para não distorcer nada.)

Com isso o script deve acessar a planilha e procurar a coluna “Fotos (antes e depois)”, em todas as linhas dessa coluna terão dois links, o primeiro link (à esquerda, antes da vírgula) para a foto de Antes, o segundo link (à direita, depois da vírgula) para a foto do depois.

Além disso, o endereço deve ser preenchido de acordo com os dados da tabela (das colunas logradoro:, bairro: e Nº, respectivamente). O campo do endereço está logo abaixo das imagens de antes e depois, como demostra o exemplo enviado em anexo.

**As páginas que possuem informações de carga horária de veículos e equipamentos deve apenas ser replicada logo após a página com as fotos da equipe 2, com todos os dados de carga horária em branco, pois estes dados serão preenchidos de forma manual**
