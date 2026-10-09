# Fonte de dados: OpenFootball (supera o ADR 0001)

> Supera o [ADR 0001](./0001-ingestao-snapshot-acumulativo.md).

A verificação da key mostrou que o **plano Free do API-Football bloqueia a season 2026** (erro literal: "try from 2022 to 2024"), e o **football-data.org free não entrega o minuto do gol**. A pesquisa de mercado achou o **[OpenFootball/worldcup.json](https://github.com/openfootball/worldcup.json)**: domínio público, **sem API key**, com 2026 atual (104 jogos, 95 concluídos até 2026-07-07), **minuto do gol** (ex.: `"90+2"`) e `score` fatiado em `ht/ft/et/p`: prorrogação e disputa de pênaltis distinguidas, com a disputa **fora** dos arrays de gol (nossa Regra 1 de graça, por construção).

Decidimos usar o **OpenFootball como fonte única do MVP e do v2 histórico**: as Copas de 2010–2022 estão no mesmo schema, também grátis (o API-Football free nem acessa 2018/2014/2010).

## Consequences

- **Ingestão simplifica:** sem key, sem cota, sem delta-fetch. Baixa-se **um JSON (~40KB)** e reprocessa. O `raw/` passa a ser o snapshot do arquivo baixado; a re-execução acumulativa continua (re-rodo → pega jogos novos), mas trivial.
- **Nunca terá xG.** O "além dos gols" (volume, xG) do v3 exigirá **outra fonte, paga** (BALLDONTLIE ~US$9.99/mo ou API-Football US$19/mo) e uma **alteração no fluxo de ingestão** pra plugá-la. A separação raw/processado ([ADR 0003](./0003-pipeline-modulos-notebooks-so-analisam.md)) é o que torna essa troca barata.
- **Riscos do wiki:** erro pontual ou atraso se o mantenedor parar. Mitigação: dado versionado + validação cruzada com o API-Football free (2022, que a key atual acessa de graça).
- **Parsing extra:** minuto como string (`"90+2"`), e a `rodada` de grupo derivada por data (o OpenFootball usa "Matchday N", não o "Group Stage - 1/2/3" mastigado do API-Football).
