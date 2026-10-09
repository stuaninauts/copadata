# Ingestão: snapshot acumulativo idempotente via API-Football

> ⚠️ **Superado pelo [ADR 0004](./0004-fonte-openfootball.md).** O plano Free do API-Football bloqueia a season 2026; a fonte passou a ser o OpenFootball. O padrão "snapshot acumulativo idempotente" abaixo permanece válido: mudou a fonte, não a forma.

O MVP analisa a Copa 2026 **em andamento**, então o dado cresce ao longo do torneio. Decidimos ingerir via **API-Football (api-sports.io)** num modelo de **snapshot acumulativo, re-executável sob demanda**: cada execução faz _upsert_ pela ID da partida, o store local sempre reflete tudo que já foi concluído, e re-rodar depois de uma nova fase apenas adiciona as partidas novas. Só partidas concluídas (FT/prorrogação/pênaltis) entram na análise.

## Considered Options

- **football-data.org (grátis):** atende o "nível leve" (resultado + minuto do gol), mas fecha a porta pra métricas além do gol (finalizações, xG). Rejeitada pra manter a porta do xG aberta na v2.
- **Pipeline vivo (auto-atualização):** over-engineering pra um uso local e solo; a Copa acaba em ~12 dias e re-rodar manual basta. Rejeitada.
- **Snapshot único descartável:** não permite refazer a análise conforme o torneio avança. Rejeitada.

## Consequences

- **Cota apertada** (100 req/dia no free tier) → guarda-se o **raw cru** em cache local e re-execuções buscam só o **delta** (partidas novas/recém-concluídas), sem re-baixar tudo.
- **Raw separado do processado** → trocar de fonte depois, ou puxar xG, não quebra a camada de análise.
- **Robustez a fases faltando** → a análise nunca assume que semis/final existem; opera sobre o que já foi concluído.
- Depende de a API-Football realmente ter 2026 ao vivo com minuto do gol (**a verificar com o key antes de construir**).
