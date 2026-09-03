# Méthodologie — FTQ vs S&P 500

## Objectif

Comparer, depuis la création du Fonds de solidarité FTQ (octobre 1984), la valeur d'un
placement initial dans le Fonds FTQ (crédit d'impôt de la première année réinvesti dans le
S&P 500) par rapport à un placement équivalent investi directement dans le S&P 500.

## Sources de données

### Fonds de solidarité FTQ

Les rendements annuels officiels (1985 à 2026) proviennent du graphique « Historique de la
valeur de l'action » publié par le Fonds de solidarité FTQ sur fondsftq.com. Une copie de ce
document est conservée dans [Documentation/ftq-historique-valeur-action-20260531.png](ftq-historique-valeur-action-20260531.png)
et l'image source originale est liée directement dans l'application.

Ces rendements sont transcrits dans [../data/ftq_annual_returns.csv](../data/ftq_annual_returns.csv),
avec une date de fin d'exercice qui varie dans le temps :

- 1985 à 1995 : exercices se terminant le 31 octobre
- 1996 à 2003 : exercices se terminant le 30 juin (le changement de date en 1996 correspond à
  un exercice partiel de 8 mois)
- 2004 à aujourd'hui : exercices se terminant le 31 mai (le changement de date en 2004
  correspond à un exercice partiel de 11 mois)

La valeur de l'action est reconstituée par capitalisation composée à partir d'une valeur de
départ de 10 $ (prix de souscription de la campagne « Une action pour l'emploi », octobre
1984). Pour les exercices 2017 à 2026, l'application tente aussi de rafraîchir les rendements
en direct à partir de la page de rendement du Fonds FTQ (voir `ftq_data.py:fetch_live_returns`);
en cas d'échec (site inaccessible, page modifiée), les valeurs du fichier CSV sont utilisées
comme repli.

### S&P 500

Les données du S&P 500 proviennent de Yahoo Finance via la bibliothèque `yfinance`. Le
rendement total (`^SP500TR`, dividendes réinvestis) est utilisé en priorité; si cette série
est incomplète pour la période demandée, l'application se rabat sur l'indice de prix seul
(`^GSPC`) et raccorde les deux séries de façon continue (mise à l'échelle au point de
jonction) pour éviter toute discontinuité artificielle.

## Construction de la simulation

Pour un montant initial `X` investi à une date `D` :

1. **FTQ seul** : `X` est converti en « unités » de l'action FTQ à la valeur de l'action en
   date `D`, puis cette position est valorisée à chaque date de fin d'exercice subséquente.
2. **Remboursement d'impôt investi dans le S&P 500** : le crédit d'impôt de première année
   (par défaut 30 % de `X`, ajustable dans l'application) est supposé investi dans le S&P 500
   **à la même date `D`** que le placement FTQ (et non un an plus tard), puis capitalisé sur
   l'indice S&P 500.
3. **FTQ total** = valeur FTQ seul + valeur du remboursement d'impôt investi en S&P 500.
4. **S&P 500 direct (référence)** : le même montant `X` est investi directement dans le
   S&P 500 à la date `D`, sans aucun crédit d'impôt, pour représenter le scénario de
   comparaison sans avantage fiscal du Fonds FTQ.

Toutes les dates de la simulation (graphique et tableau) suivent le calendrier des exercices
financiers du Fonds FTQ; les valeurs du S&P 500 sont simplement interpolées à ces mêmes dates
(dernière valeur disponible à la date ou avant), puisque les données quotidiennes du S&P 500
sont, elles, disponibles pour n'importe quelle date.

Une ligne supplémentaire correspondant à la date de placement `D` elle-même (avant tout
rendement) est ajoutée en tête du tableau/graphique afin que la croissance parte visiblement
de la mise de fonds initiale.

## Colonnes du tableau de données brutes

- `ftq_value` : valeur du placement FTQ seul, à chaque date.
- `tax_refund_sp500_value` : valeur du remboursement d'impôt investi en S&P 500, à chaque date.
- `ftq_total_value` : somme des deux colonnes précédentes (stratégie FTQ complète).
- `sp500_direct_value` : valeur du scénario de référence (100 % S&P 500, sans crédit d'impôt).
- `delta` : écart entre `ftq_total_value` et `sp500_direct_value`, exprimé en % du montant
  initial investi.
- `ftq_total_yoy_growth_pct` : croissance cumulative de `ftq_total_value` depuis le montant
  initial investi (et non une variation d'une période à l'autre, malgré le nom hérité).
- `rendement_ftq_pct` : rendement de l'exercice (période contre période) de `ftq_value`.
- `rendement_sp500_pct` : rendement de l'exercice (période contre période) de
  `sp500_direct_value`.

## Limites et hypothèses

- Placement forfaitaire unique (« lump sum ») à une date donnée, et non des cotisations
  annuelles récurrentes.
- Crédit d'impôt appliqué à taux fixe (par défaut 30 %) sur l'ensemble du montant, sans tenir
  compte du plafond réel de cotisation admissible au crédit (5 000 $/an au Québec/fédéral).
- Le rendement du S&P 500 total (`^SP500TR`) ne couvre pas nécessairement toute la période
  1984-1988; un raccord avec l'indice de prix (`^GSPC`) est alors effectué (voir plus haut).
- Les rendements FTQ affichés par fondsftq.com sont des rendements totaux composés annuels
  historiques (fluctuation de la valeur de l'action + réinvestissement des dividendes) et ne
  tiennent pas compte de l'impôt sur le revenu payable par un porteur, ce qui aurait pour effet
  de réduire le rendement réel après impôt (autre que le crédit d'impôt initial modélisé ici).
