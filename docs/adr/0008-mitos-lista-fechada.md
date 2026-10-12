# Mitos: lista fechada, regra de veredito antes e faixa do acaso

Depois dos achados de 2026 e do histórico, a pergunta passou a ser "o que os dados mostram que não é óbvio?". Garimpar recortes até achar algo curioso é p-hacking: com 50 recortes, 2 ou 3 parecem surpreendentes por acaso. O [ADR 0002](./0002-analise-descritiva-nao-inferencial.md) já abre uma exceção para **uma afirmação externa, definida antes de olhar o dado**, e o [ADR 0006](./0006-camada-de-publicacao.md) limita p-valor a esses testes únicos e proíbe intervalo de confiança por célula.

Decidimos tratar **mitos do futebol** (afirmações que vêm de fora, do senso comum do torcedor) como uma generalização desses testes únicos:

- **Lista fechada, por leva.** As afirmações, a medida de cada uma e o limiar do veredito são escritos antes de rodar. Toda afirmação da lista é rodada e reportada, inclusive as que não acham nada. Pergunta nova entra numa leva nova, com data; a lista de uma leva não muda depois de rodada.
- **Um efeito e um intervalo por mito.** O efeito é orientado para que positivo apoie a afirmação. O intervalo de 95% vem de bootstrap por partida (reamostra jogos, não gols). Quando a pergunta é "isso foge do acaso?", a referência é uma **faixa do acaso**: simulação ou permutação com o mesmo tamanho de amostra.
- **Regra de veredito** (`aggregate.verdict`):
  - **Verdade:** intervalo acima de zero **e** mesma direção nas duas metades da história (1986-2002 e 2006-2026). Se o intervalo de 99% chega a zero, **Verdade, no limite**.
  - **Mito:** o intervalo inteiro fica abaixo do menor efeito que a afirmação implica (5 p.p., salvo outro limiar escrito para o mito).
  - **Não dá para dizer:** o resto.
  - Mitos com forma própria (o funnel plot das seleções, a auditoria de 2026, "quem lidera recua") têm a regra descrita na função que os calcula.
- **Reprodutível.** Bootstrap e permutação usam semente fixa (`config.MYTH_SEED`) e um número fixo de sorteios, então o export é determinístico e o `export --check` continua valendo. Intervalos saem arredondados em 3 casas.
- **Onde vive.** Definições por partida ou gol em `metrics.py` (o primeiro 2 a 0 e o 2 a 1 seguinte, o gol do último quarto); efeitos, intervalos e vereditos em `aggregate.py`; o export ganha `myths` (um veredito por mito) e uma tabela de detalhe por mito. Os testes golden fixam `k/n` e o veredito.

Fora dos mitos, nada muda: os demais números continuam com `k/n` e faixa entre Copas, sem intervalo por célula.

## Leva 1 (2026-10-12)

Doze afirmações, só com os dados já processados. Recorte: grupos e mata-mata, sem a disputa de 3º lugar, lente dos 90 minutos.

| # | Afirmação | Veredito | No site |
|---|---|---|---|
| 1 | O primeiro gol vale mais no mata-mata | Mito | não: diferença pequena e leitura confusa (vencer aos 90' vs avançar) |
| 2 | 2 a 0 é o placar mais perigoso | Mito | **sim** (`two_nil`) |
| 3 | O pior momento para sofrer gol é no fim do 1º tempo | Não dá para dizer | não: inconclusivo |
| 4 | Quem empata no fim ganha a prorrogação | Não dá para dizer | não: inconclusivo, 37 casos |
| 5 | Depois de marcar, o time fica vulnerável | Mito | não: fraco, metades discordam |
| 6 | Quem está ganhando por 1 recua | Mito | **sim** (`leader_sits_back`), com a ressalva de força das seleções |
| 7 | Gol chama gol | Mito | não: depende de explicar a pausa da nova saída de bola |
| 8 | No mata-mata os times jogam pelo empate | Mito, no limite | não: mensagem ambígua |
| 9 | 2026 foi uma Copa fora da curva | Verdade em parte | **sim**, como auditoria das manchetes da Home (`season_outlier`) |
| 10 | O futebol ficou mais travado | Mito | em espera: só entra junto com a "montanha-russa", se a leva 2 confirmar |
| 11 | Tem seleção especialista em decidir no fim | Mito | **sim** (`late_specialists`) |
| 12 | Perdeu a estreia, está fora (e o formato de 48 aliviou) | Verdade, no limite | **sim** (`opener_loss`) |

As que não vão para o site aparecem na página de método com o veredito e o motivo. Os números das cinco publicadas vêm do export; as demais foram rodadas num notebook de trabalho e ficam registradas aqui pelo veredito.

## Considered Options

- **P-valor por mito:** responde "é diferente de zero?", mas não sustenta **Mito**: um p-valor alto não diz que o efeito é pequeno. O limiar de efeito mínimo diz. Rejeitada.
- **Publicar só o que deu Verdade:** é exatamente o garimpo que a lista fechada evita. Rejeitada.
- **Modelo bayesiano com priors:** mais expressivo, mas difícil de explicar ao público executivo do site e de auditar. Rejeitada no v1.
- **Intervalo para todo número publicado:** convidaria a comparar tudo com tudo, como o ADR 0006 já registra. Rejeitada.

## Consequences

- Os mitos são a única parte do site com intervalo e faixa do acaso. Ampliar isso para outros números exige outro ADR.
- Mudança de versão do NumPy pode mexer na 3ª casa de um intervalo; o `export --check` acusa e basta regenerar.
- A leva 2 (força das seleções por Elo, "montanha-russa", pênaltis cobrança a cobrança) abre uma lista nova, com data, antes de rodar.
- Os mitos 6 e 12 e as goleadas de 2026 misturam efeito de jogo ou formato com força das seleções; a leva 2 com Elo é o que separa as duas coisas.
