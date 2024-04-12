"""Ce script contient les fonctions utilisées par l'application"""
import datetime
import numpy as np
import pandas as pd
import base64
from pathlib import Path


TAUX_BNP = {
    15: 0.0278,
    20: 0.0283,
    25: 0.0284
}

# On considère 'Bon taux'
TAUX_NOMINAL_PUBLIC = {
    15: 0.0377,
    20: 0.0385,
    25: 0.04
}

TAUX_PEL = 0.0345  # Taux d'emprunt du PEL, fixé au moment de l'ouverture du contrat en 02/2024

# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_appart = {
    'CACHAN': -0.004,
    'CHATOU': 0.021,
    'MAISONS-LAFFITTE': -0.017,
    'RUEIL-MALMAISON': 0.032,
    'VÉSINET': -0.017,
    'SAINT-GERMAIN EN LAYE': 0.232
}

# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_maison = {
    'CACHAN': 0.073,
    'CHATOU': 0.129,
    'MAISONS-LAFFITTE': 0.191,
    'RUEIL-MALMAISON': 0.051,
    'VÉSINET': 0.149,
    'SAINT-GERMAIN EN LAYE': 0.129
}

lieu_to_url_meilleurs_agents = {
    'CACHAN': 'cachan-94230',
    'CHATOU': 'chatou-78400',
    'HOUILLES': 'houilles-78800',
    'MAISONS-LAFFITTE': 'maisons-laffitte-78600',
    'RUEIL-MALMAISON': 'rueil-malmaison-92500',
    'VÉSINET': 'le-vesinet-78110',
    'SAINT-GERMAIN EN LAYE': 'saint-germain-en-laye-78100'
}


def get_mt_mensualités(mt_emprunt: float, tx_nominal: float, nb_mois: int):
    """
    À partir du montant à emprunter, du taux nominal du crédit immobilier et
    du nombre d'échéances, retourne le montant de chaque mensualité dans le cas
    d'un prêt ammortissable à taux fixe.
    Source :
    https://immobilier.lefigaro.fr/financer/guide-financement-immobilier/
    1288-pret-amortissable-definition-et-calcul-de-la-mensualite/
    """
    return ((mt_emprunt * tx_nominal) / 12) / (1 - (1 + (tx_nominal / 12))**(-nb_mois))


# Un test, conformément à cette page :
# https://www.meilleurtaux.com/credit-immobilier/simulation-de-pret-immobilier/
# calcul-des-mensualites.html
assert round(get_mt_mensualités(230_000, 0.02, 20 * 12)) == 1164


def get_mt_emprunt_max(mensualité_max, tx_nominal, nb_mois):
    """
    À partir d'une mensualité maximale supportable, d'un taux nominal et d'un nombre
    d'échéances, retourne le montant maximal empruntable.
    Source :
    https://immobilier.lefigaro.fr/financer/guide-financement-immobilier/
    """
    return 12 * mensualité_max / tx_nominal * (1 - (1 + tx_nominal / 12)**(-nb_mois))


assert round(get_mt_emprunt_max(1164, 0.02, 20 * 12)) == 230_093  # ~230K


def sep_milliers(nb, nb_dec=0):
    """
    Usage :
    >>> sep_milliers(1254839.1245) --> '1 254 839.12'
    nb peut etre une string ou un nombre.
    """
    if nb != nb:
        return nb
    if not isinstance(nb, str):
        nb = str(nb)
    if (nb_dec == 0) and ('.' in nb):
        nb = nb[: nb.index('.')]
    decimales = '' if '.' not in nb else nb[nb.index('.'):]
    nb = nb if '.' not in nb else nb[: nb.index('.')]
    d, r = divmod(len(nb), 3)
    res = ' '.join(([nb[:r]] + [nb[i:i + 3] for i in np.arange(r, len(nb), 3)]))
    return res.strip() + decimales[:nb_dec + 1]


def nb_mois_depuis_que_lisa_économise():
    dt_début_INSPART = datetime.date(2022, 11, 1)
    return (datetime.date.today() - dt_début_INSPART).days // 30.5


def montant_qui_sera_remboursé_à_date(
    date_début_du_prêt_existant,
    mt_remboursé_par_mois,
    date=datetime.date.today()
):
    """Le montant qui aura été remboursé à la `date`"""
    nb_mois_depuis_début_du_prêt = round((date - date_début_du_prêt_existant).days / 30.5)
    montant_qui_sera_remboursé = nb_mois_depuis_début_du_prêt * mt_remboursé_par_mois
    return montant_qui_sera_remboursé


def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


converters = {str(i): (lambda x: float(x.replace(',', '.'))) for i in range(2, 15 + 1)}
barême = pd.read_csv('data/Barême PEL.csv', sep=";",
                     header=1, index_col=0, converters=converters)


def get_mt_prêt_et_mensualité_du_PEL(
    barême,
    mt_intérêts_acquis_PEL, durée_du_prêt_PEL=5
) -> tuple([float, float]):
    (
        prêt_pour_1_euro_dintérêts_acquis,
        mensualité_pour_1000_euros_prêtés
    ) = barême[str(durée_du_prêt_PEL)]
    mt_du_prêt_du_PEL = mt_intérêts_acquis_PEL * prêt_pour_1_euro_dintérêts_acquis
    mensualité = (mt_du_prêt_du_PEL * mensualité_pour_1000_euros_prêtés) / 1000
    # "Le montant maximum du prêt est de 92 000 €" :
    mt_du_prêt_du_PEL = min(mt_du_prêt_du_PEL, 92_000)
    return round(mt_du_prêt_du_PEL), round(mensualité)


# L'exemple donné sur mon contrat PEL
assert get_mt_prêt_et_mensualité_du_PEL(barême, 100, 7) == (3090, 41)


def get_mt_max_prêt_PEL(barême, mt_intérêts_acquis_PEL: int,
                        mensualité_plafond: int, durée_du_prêt_PEL: int = 2):
    """
    Trouve le plus grand montant empruntable tel que la mensualité qu'il permet soit
    inférieure au plafond
    """
    if mt_intérêts_acquis_PEL <= 0 and durée_du_prêt_PEL >= 15:
        # Game over, on ne peut pas utiliser le PEL
        return 0, 0, 0, 0
    mt_du_prêt_du_PEL, mensualité = get_mt_prêt_et_mensualité_du_PEL(
        barême=barême,
        mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL,
        durée_du_prêt_PEL=durée_du_prêt_PEL
    )
    print(f'{mt_du_prêt_du_PEL=}', f'{mensualité=}', f'{durée_du_prêt_PEL=}', f'{mt_intérêts_acquis_PEL=}')
    # Si on optimise en premier la durée du prêt :
    if mensualité > mensualité_plafond:
        if durée_du_prêt_PEL < 15:
            return get_mt_max_prêt_PEL(
                barême,
                mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL,
                mensualité_plafond=mensualité_plafond,
                durée_du_prêt_PEL=durée_du_prêt_PEL + 1
            )
        else:
            lr = 100
            return get_mt_max_prêt_PEL(
                barême,
                mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL - lr,
                mensualité_plafond=mensualité_plafond,
                durée_du_prêt_PEL=durée_du_prêt_PEL
            )
        # Si on optimise en premier les intérêt acquis :
        # if mt_intérêts_acquis_PEL > 0:
        #     lr = 100
        #     return get_mt_max_prêt_PEL(
        #         barême,
        #         mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL - lr,
        #         mensualité_plafond=mensualité_plafond,
        #         durée_du_prêt_PEL=durée_du_prêt_PEL
        #     )
        # else:
        #     return get_mt_max_prêt_PEL(
        #         barême,
        #         mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL,
        #         mensualité_plafond=mensualité_plafond,
        #         durée_du_prêt_PEL=durée_du_prêt_PEL - 1
        #     )
    return (
        durée_du_prêt_PEL, mt_du_prêt_du_PEL,
        mensualité, mt_intérêts_acquis_PEL
    )


(
    durée_du_prêt_PEL, mt_du_prêt_du_PEL,
    mensualité, intérêts_acquis_utilisés_PEL
) = get_mt_max_prêt_PEL(
    barême, mt_intérêts_acquis_PEL=3712, mensualité_plafond=421
)
assert durée_du_prêt_PEL == 14
assert mt_du_prêt_du_PEL == 56_274
assert mensualité == 421

(
    durée_du_prêt_PEL, mt_du_prêt_du_PEL,
    mensualité, intérêts_acquis_utilisés_PEL
) = get_mt_max_prêt_PEL(
    barême, mt_intérêts_acquis_PEL=3712, mensualité_plafond=420
)
assert durée_du_prêt_PEL == 15
assert mt_du_prêt_du_PEL == 52_358
assert mensualité == 372

(
    durée_du_prêt_PEL, mt_du_prêt_du_PEL,
    mensualité, intérêts_acquis_utilisés_PEL
) = get_mt_max_prêt_PEL(
    barême, mt_intérêts_acquis_PEL=3712, mensualité_plafond=1
)
assert durée_du_prêt_PEL == 15
print(mt_du_prêt_du_PEL)
assert mt_du_prêt_du_PEL == 169
assert mensualité == 1
