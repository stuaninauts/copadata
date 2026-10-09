# Fonte histórica: Fjelstul World Cup Database (supera parte do ADR 0004)

> Supera o [ADR 0004](./0004-fonte-openfootball.md) **só na parte histórica**. O OpenFootball continua sendo a fonte da Copa 2026.

O ADR 0004 assumia que o OpenFootball tinha as Copas de 2010-2022 "no mesmo schema" de 2026. A verificação (2026-10-08) mostrou que não: no `worldcup.json`, 2010, 2002, 1998 e 1994 não têm **nenhum** minuto de gol, 2006 quase não tem, 2014 tem gols faltando em vários jogos e o `score` vem como lista (sem `ft/et/p`). Só 2018 e 2022 seriam utilizáveis.

Decidimos usar o **[Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup)** (`data-csv/matches.csv` e `goals.csv`) para as edições **1986-2022**, fixado num commit (`config.FJELSTUL_COMMIT`). Em todas essas edições os minutos de gol batem com o placar, e a base distingue tempo normal, prorrogação e disputa de pênaltis.

Um **adaptador** (`copadata/fjelstul.py`) converte cada edição para o mesmo formato de dicionário do JSON do OpenFootball. Assim `transform` e `metrics` processam todas as edições com o mesmo código: nenhuma métrica é redefinida ([ADR 0003](./0003-pipeline-modulos-notebooks-so-analisam.md)). Os parquets ganham a coluna `year`.

**Corte em 1986:** é a primeira Copa com o formato moderno, fase de grupos seguida de mata-mata a partir das oitavas. Antes disso houve segunda fase de grupos e quadrangular final, que não cabem nos baldes grupos/mata-mata.

## Considered Options

- **OpenFootball `worldcup.json`:** sem minutos de gol antes de 2018. Rejeitada.
- **OpenFootball `wikipedia/YYYY.txt`:** tem os minutos, mas em texto livre; exigiria escrever e manter um parser. Rejeitada enquanto houver fonte estruturada.
- **API-Football:** o plano free não acessa as edições antigas (ADR 0004). Rejeitada.

## Consequences

- **Licença CC-BY-SA 4.0.** Exige atribuição (autor, aviso de copyright, link da licença e do repositório, indicação de modificações) e que obras derivadas dos dados saiam sob a mesma licença.
  - O pipeline **baixa os CSVs em tempo de execução** para `data/raw/fjelstul/` (gitignored): o repositório distribui só código, que segue MIT.
  - A atribuição fica no README e em todo gráfico ou post que use dados históricos.
  - Se um dia versionarmos dados derivados do Fjelstul (parquets, CSVs), esses arquivos precisam sair como CC-BY-SA, com atribuição.
  - Usar só os CSVs do GitHub: a distribuição do site WorldCups.ai tem outra licença (CC-BY-NC-SA).
- **Duas fontes, nomes diferentes:** as seleções não têm o mesmo nome nas duas bases (ex.: "United States" no Fjelstul, "USA" no OpenFootball). Qualquer análise que cruze seleções entre 2026 e o histórico precisa de um mapeamento explícito.
- **Validação:** o adaptador recusa jogo cujos gols não batam com o placar. 2018 e 2022 existem nas duas fontes e servem de checagem cruzada.
- **`match_id` passa a ser único entre edições** (`ano * 1000 + índice`), para que nenhum join misture Copas.
