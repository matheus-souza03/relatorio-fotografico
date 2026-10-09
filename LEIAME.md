# Relatório Fotográfico — gerador automático

Monta o relatório fotográfico mensal da Prefeitura de Quissamã a partir da planilha do formulário:
Equipes de campo que trabalham em Quissamã preenche um forms toda vez que um serviço é concluido, o que causa
baixa as fotos de antes e depois do Google Drive, preenche datas, equipes e endereços e entrega um
`.docx` pronto, no mesmo formato do relatório feito à mão. As horas continuam sendo preenchidas à mão.

---

## Uso mensal

1. **Baixe a planilha** no Google Planilhas: _Arquivo > Fazer download > Microsoft Excel (.xlsx)_.
2. **Deixe só as linhas do período:** apague as linhas que já entraram nos relatórios anteriores,
   mantendo a linha 1 (cabeçalho). O relatório começa pela primeira linha que sobrar.
3. **Coloque a planilha na pasta `entrada`.** Se houver mais de uma, o programa usa a mais recente.
4. **Abra o `configuracao.ini`** e ajuste:
   - `data_inicial` e `data_final` (ex.: `27/09/2026` e `26/10/2026`);
   - `nome_arquivo` (ex.: `RFM57`), opcional.
5. **Dê dois cliques** em `Gerar Relatorio - Windows.bat` ou em `Gerar Relatorio - Mac.command`.
6. **Abra o relatório na pasta `saida`.** Procure por `ERRO` (Ctrl+F / Cmd+F) para achar as fotos que não
   puderam ser inseridas e complete à mão. Depois preencha as horas.

Ao terminar, o programa mostra na tela, e salva em `saida/<nome> - ocorrencias.txt`:

- as fotos que deram problema;
- os registros que não couberam no período (as linhas que devem abrir o próximo relatório);
- os dias que ficaram sem registros.

---

## Como o relatório é montado

- **6 atividades por dia com expediente, na ordem da planilha:** as 3 primeiras linhas vão para a
  **Equipe 1** (Bruno e Anderson) e as 3 seguintes para a **Equipe 2** (Cláudio e Oracy); o dia seguinte
  continua da próxima linha.
- **Cada dia tem 3 páginas:** Equipe 1, Equipe 2 e a página de carga horária (mão de obra e veículos),
  com a data preenchida e as horas em branco.
- **Dias sem expediente** têm as páginas com a data e o texto `SEM EXPEDIENTE`, sem fotos; as atividades
  passam para o próximo dia útil. São eles:
  - sábados e domingos;
  - feriados nacionais e estaduais (RJ);
  - os pontos facultativos de Carnaval (segunda e terça), Quarta-feira de Cinzas, Corpus Christi e as
    vésperas de Natal e de Ano-Novo;
  - os feriados municipais do `configuracao.ini` (12/01).

  O Dia do Servidor (28/10) é dia normal. Para exceções, use `outros_dias` e `dias_com_expediente` no
  `configuracao.ini`.

- **Se os registros acabarem** antes da data final, os dias restantes ficam com as páginas em branco.
  **Se sobrarem registros**, o relatório para na data final e avisa quais linhas ficaram de fora.
- **Fotos:** o 1º link da coluna "Fotos (antes e depois)" é a foto de ANTES e o 2º é a de DEPOIS.
  - As fotos são ajustadas ao espaço da tabela sem distorcer.
  - A rotação do celular é corrigida automaticamente.
  - Fotos de iPhone (HEIC) são convertidas.
- **Endereço:** logradouro, bairro e nº. O programa:
  - tira espaços sobrando e observações como `obs: ...` ou `( casa rosa )`;
  - escreve `14` em vez de `14.0` e `3` em vez de `03`.
- **Quando uma foto falha** (link ausente, quebrado ou sem permissão), aparece no lugar dela, em vermelho:
  `ERRO – FOTO ANTES`, a linha da planilha, o motivo e "Inserir manualmente".
- **O programa nunca apaga nem substitui um relatório existente:** se gerar de novo, o novo arquivo
  recebe um número no final, por exemplo `RFM57 (2).docx`.

---

## Configuração inicial (uma vez por computador)

### 1. Instalar o Python

Baixe em <https://www.python.org/downloads/> e instale.

- **Windows:** marque a opção **"Add python.exe to PATH"** na primeira tela do instalador.
- **Mac:** na primeira vez, clique com o botão direito em `Gerar Relatorio - Mac.command` > **Abrir**
  (o macOS bloqueia o duplo clique em arquivos baixados).

Na primeira execução, o atalho instala sozinho os componentes do programa. Isso precisa de internet e
leva alguns minutos.

### 2. Dar acesso às fotos do Google Drive

As fotos enviadas pelo formulário ficam **privadas** no Google Drive da conta dona do formulário. Por isso
o programa precisa de uma credencial: um **arquivo `.json`** que deve ser colocado na pasta `credenciais`.
Uma "chave de API" simples (um texto que começa com `AIza...`) **não funciona** para fotos privadas.

**Nunca envie esse arquivo por e-mail nem cole o conteúdo dele em mensagens.**

#### Opção A — Conta de serviço (recomendada: configura uma vez e não pede login)

1. Acesse <https://console.cloud.google.com/> com uma conta Google da empresa.
2. No seletor de projetos (barra superior), clique em **Novo projeto**, dê o nome `relatorio-fotografico`
   e crie.
3. Menu ☰ > **APIs e serviços** > **Biblioteca**. Procure **Google Drive API** e clique em **Ativar**.
4. Menu ☰ > **IAM e administrador** > **Contas de serviço** > **Criar conta de serviço**. Use o nome
   `relatorio-fotos`, clique em **Criar e continuar** e depois em **Concluir** (não precisa escolher
   papel).
5. Clique na conta criada > aba **Chaves** > **Adicionar chave** > **Criar nova chave** > **JSON** >
   **Criar**. Um arquivo `.json` será baixado.
6. Copie o **e-mail da conta de serviço**, que termina em `@relatorio-fotografico.iam.gserviceaccount.com`.
7. Entre no **Google Forms com a conta dona do formulário** e vá na aba **Respostas**. Na pergunta das
   fotos, clique em **Ver pasta**. No Drive, compartilhe essa pasta com o e-mail do passo 6 como **Leitor**
   (pode desmarcar "Notificar"). As fotos que chegarem depois herdam o acesso.
8. Mova o arquivo `.json` para a pasta `credenciais` do projeto. Qualquer nome serve.

#### Opção B — Login com a conta Google (use se a empresa bloquear a Opção A)

1. Faça os passos 1 a 3 da Opção A.
2. Menu ☰ > **APIs e serviços** > **Tela de permissão OAuth** (ou **Google Auth Platform**). Configure o app:
   - se a conta for Google Workspace da empresa, escolha o público **Interno**;
   - se for Gmail, escolha **Externo** e adicione o e-mail da conta dona do formulário em
     **Usuários de teste**.
3. Em **Clientes** (ou **Credenciais**), clique em **Criar cliente** > tipo **App para computador** >
   **Criar** e **baixe o JSON**.
4. Mova o arquivo `.json` para a pasta `credenciais`.
5. Na primeira vez que gerar o relatório, o navegador abre. Entre com a conta dona do formulário e
   permita o acesso. O login fica salvo em `credenciais/token.json`.

> Em conta Gmail com o app em modo "Teste", o Google pede o login de novo a cada 7 dias. Para evitar, use
> **Publicar app** na tela de permissão. Vai aparecer o aviso "O Google não verificou este app": clique em
> _Avançado > Acessar_ para continuar.

---

## Alterar o modelo do relatório

O layout de um dia está em `modelo/modelo_dia.docx`. Ele pode ser editado no Word: número do contrato,
nomes, veículos, logos etc.

Os campos entre chaves duplas precisam ser **mantidos**, porque é neles que o programa coloca os dados:

| Campo                                       | O que entra                                      |
| ------------------------------------------- | ------------------------------------------------ |
| `{{DATA}}`                                  | data do dia, ex.: `29/06/2026 (segunda-feira)`   |
| `{{SEM_EXPEDIENTE}}`                        | o texto `SEM EXPEDIENTE` nos dias sem expediente |
| `{{E1_P1_ANTES}}` … `{{E2_P3_DEPOIS}}`      | fotos (E = equipe 1 ou 2, P = ponto 1 a 3)       |
| `{{E1_P1_ENDERECO}}` … `{{E2_P3_ENDERECO}}` | endereço do ponto                                |

O tamanho das fotos acompanha o tamanho das células do modelo.

---

## Problemas comuns

| Mensagem ou situação                                                        | O que fazer                                                                                                                           |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `Nenhuma planilha (.xlsx) foi encontrada`                                   | Coloque a planilha na pasta `entrada`, no formato .xlsx.                                                                              |
| `Nenhum arquivo de credenciais`                                             | Faça o passo 2 da configuração inicial.                                                                                               |
| Todas as fotos com `Foto não encontrada no Google Drive`                    | A pasta das fotos não foi compartilhada com o e-mail da conta de serviço (Opção A, passo 7).                                          |
| `A criação de chaves de conta de serviço está desativada` (no Google Cloud) | A política da empresa bloqueia a Opção A: use a Opção B ou peça ao administrador.                                                     |
| Compartilhamento com a conta de serviço bloqueado                           | A empresa bloqueia compartilhar com contas externas: use a Opção B.                                                                   |
| Login do Google pedido toda semana                                          | Publique o app (veja o aviso da Opção B).                                                                                             |
| `O Python 3 não está instalado`                                             | Instale o Python (passo 1).                                                                                                           |
| No Mac, "não é possível abrir" o atalho                                     | Clique com o botão direito > **Abrir**. Se aparecer "permissão negada", rode no Terminal: `chmod +x "Gerar Relatorio - Mac.command"`. |

---

## Para quem mantém o programa

- **Código:** pasta `relatorio/`, com um módulo para cada etapa:
  - `config`: leitura do `configuracao.ini`;
  - `planilha`: leitura da planilha;
  - `calendario`: dias com e sem expediente;
  - `distribuicao`: 6 registros por dia;
  - `google_drive`: credenciais e downloads;
  - `imagens`: preparação das fotos;
  - `documento`: montagem do .docx;
  - `principal`: orquestra tudo.
- **Testes:** `pip install -r requirements-dev.txt` e depois `python -m pytest`.
- **Testar sem acesso ao Google:** `python gerar_relatorio.py --sem-fotos`. Gera o documento com avisos no
  lugar das fotos.
- **Recriar o modelo** a partir de um relatório feito à mão:
  `python ferramentas/criar_modelo.py documentos_exemplo/RFM54.docx`.
- **Pastas fora do projeto:**
  - Python dos atalhos: `~/.relatorio_fotografico/venv` (Mac) ou
    `%LOCALAPPDATA%\relatorio_fotografico\venv` (Windows);
  - cache das fotos baixadas (apagado após 90 dias): `~/Library/Caches/relatorio_fotografico` (Mac) ou
    `%LOCALAPPDATA%\relatorio_fotografico` (Windows).
