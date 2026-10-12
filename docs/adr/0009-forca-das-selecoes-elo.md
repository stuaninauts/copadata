# Força das seleções: Elo calculado de uma base CC0 de resultados internacionais

Vários achados esbarram na mesma ressalva: sem uma medida de força, não dá para separar "efeito do jogo ou do formato" de "o time era melhor". Exemplos: as goleadas de 2026 (H3), "quem lidera por 1 não recua" e "perder a estreia já não elimina" (leva 1 do [ADR 0008](./0008-mitos-lista-fechada.md)). A leva 2 dos mitos depende disso.

Decidimos medir a força pelo **Elo pré-jogo**, calculado por nós:

- **Fonte:** [`martj42/international_results`](https://github.com/martj42/international_results), licença **CC0**. São todos os jogos entre seleções desde 1872 (inclusive os 104 de 2026), com campo neutro e torneio; mais as disputas de pênaltis (com quem bateu primeiro) e os gols com minuto. O download aponta para um commit fixo (`config.INTERNATIONAL_COMMIT`), como o OpenFootball e o Fjelstul.
- **Método:** a fórmula pública do World Football Elo (eloratings.net):
  - `R' = R + K × G × (W − We)`, com `We = 1 / (10^(−dr/400) + 1)`, e +100 para o mandante quando o jogo não é em campo neutro;
  - K pelo peso do jogo: 60 Copa, 50 finais continentais e Copa das Confederações, 40 eliminatórias e Ligas das Nações, 30 outros torneios, 20 amistosos;
  - G pelo saldo: 1 até 1 gol, 1,5 com 2, (11 + saldo)/8 com 3 ou mais;
  - jogo decidido nos pênaltis conta como empate; toda seleção começa com 1500.
- **Onde vive:** `copadata/elo.py` é o único lugar que define força, como o `metrics.py` para as métricas de jogo ([ADR 0003](./0003-pipeline-modulos-notebooks-so-analisam.md)). O adaptador `copadata/international.py` lê a base, calcula o Elo e o leva para as tabelas processadas: `elo1`/`elo2` em `matches`, `elo_for`/`elo_against` em `team_matches`, e as tabelas `international` e `international_goals`.
- **Nomes:** uma seleção tem um nome só entre as fontes (`config.TEAM_NAMES`: "USA" no OpenFootball vira "United States", como no Fjelstul). Para buscar o Elo, os nomes históricos apontam para a federação sucessora na base nova (`config.ELO_NAMES`: Alemanha Ocidental → Alemanha, União Soviética → Rússia, Sérvia e Montenegro → Sérvia). Todo jogo de Copa precisa achar seu par na base nova; se algum não achar, o pipeline para com erro, como no adaptador do Fjelstul.
- **Pênaltis cobrança a cobrança:** a tabela `penalty_kicks` do Fjelstul (mesma licença e atribuição do [ADR 0005](./0005-fonte-historica-fjelstul.md)) entra no download e vira a tabela processada `penalty_kicks`, com o `match_id` do CopaData. Não existe para 2026.

## Considered Options

- **Baixar os ratings do eloratings.net:** é a referência, mas não tem licença declarada nem download estável. Rejeitada; ele serve só para conferir alguns valores.
- **Ranking FIFA:** muda de método em 2018, não existe antes de 1992 e não tem licença aberta. Rejeitado.
- **Força a partir dos próprios jogos de Copa:** de 3 a 7 jogos por seleção por edição é pouco para estimar força. Rejeitada.
- **Mercado de apostas:** seria a melhor medida pré-jogo, mas não há fonte aberta para 1986-2026. Rejeitada.

## Consequences

- A base nova é CC0: não acrescenta exigência de licença ao export, que segue CC-BY-SA por causa do Fjelstul.
- O Elo depende da ordem e da completude da base. Jogos que faltarem nela (amistosos obscuros) mexem pouco no rating de quem chega a uma Copa.
- Mudar o commit da base nova, ou um parâmetro do Elo, muda os números que dependem de força. O teste golden e o `export --check` acusam.
- Seleções que deixaram de existir (Iugoslávia, Tchecoslováquia) mantêm o nome que têm na base nova; só as três da lista acima precisam de tradução.
