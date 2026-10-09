# Pipeline em módulos reproduzíveis; notebooks só analisam

O re-run acumulativo idempotente ([ADR 0001](./0001-ingestao-snapshot-acumulativo.md)) e o contrato de honestidade ([ADR 0002](./0002-analise-descritiva-nao-inferencial.md)) exigem código que rode igual toda vez e métricas com definição única.

Decidimos: **`ingest`, `transform` e `derive` são módulos Python re-executáveis**; as métricas ficam num **único módulo (`metrics.py`) com definição única de cada termo do glossário do projeto**; e **notebooks só consomem `data/processed/` pra analisar/comparar/plotar**, sem definir métrica. Contraria a cultura comum de "viver no notebook", mas notebook tem estado escondido e execução fora de ordem, e não re-roda de forma confiável.

## Consequences

- `metrics.py` é a fonte de verdade das definições: mudou a definição de um termo, muda lá (e no glossário).
- `data/raw/` é cache do delta (gitignored); `data/processed/` são os parquets que a análise consome.
- Notebooks viram descartáveis/reprodutíveis: qualquer um re-gera os parquets rodando o pipeline.
