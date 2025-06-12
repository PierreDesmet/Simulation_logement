"""Ce script contient les fonctions utilisées par l'application"""
import datetime
import numpy as np
import pandas as pd
import base64
from pathlib import Path


TAUX_BNP = {
    15: 0.0238,
    20: 0.0245,
    25: 0.0249
}

# On considère 'Bon taux'
TAUX_NOMINAL_PUBLIC = {
    15: 0.033,
    20: 0.0338,
    25: 0.0342
}

TAUX_PEL = 0.0345  # Taux d'emprunt du PEL, fixé au moment de l'ouverture du contrat en 02/2024
INFLATION_SUR_NB_YEARS = 5
# https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/
lieu_to_inflation_appart = {
    'CACHAN': -0.105,
    'CHATOU': -0.082,
    'RUEIL-MALMAISON': -0.029,
    'VÉSINET': -0.047
}

# https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/
lieu_to_inflation_maison = {
    'CACHAN': 0.069,
    'CHATOU': -0.081,
    'RUEIL-MALMAISON': -0.086,
    'VÉSINET': 0.023
}

lieu_to_url_meilleurs_agents = {
    'CACHAN': 'cachan-94230',
    'CHATOU': 'chatou-78400',
    'HOUILLES': 'houilles-78800',
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


def get_tableau_amortissement_prêt_pierre(montant_emprunté: float):
    """
    Le tableau est récupéré depuis de site :
    https://www.anil.org/outils/outils-de-calcul/echeancier-dun-pret/
    """
    columns = (
        "Echéance;Intérêts;Amortissement;"
        "CRD en fin de période;Assurance;Mensualité"
    ).split(';')
    df = pd.read_csv('data/tableau_amortissement.csv', sep='\t', header=None, names=columns)
    df = df.applymap(
        lambda x: str(x).replace(',', '.').replace(' ', '').replace('€', '')
    ).astype(float)
    df['mt_emprunt_initial'] = montant_emprunté
    df['CRD_précis'] = (df['mt_emprunt_initial'] - df['Amortissement'].cumsum())
    return df


def nb_mois_depuis_que_pierre_rembourse_son_prêt(
    date_début_du_prêt_existant, à_date=datetime.date.today()
):
    dt_début = date_début_du_prêt_existant
    return (à_date - dt_début).days // 30.5


def get_CRD_à_date(à_date, date_début_du_prêt_existant, montant_emprunté: float):
    nb_mois = nb_mois_depuis_que_pierre_rembourse_son_prêt(
        date_début_du_prêt_existant, à_date=à_date
    )
    amortissement = get_tableau_amortissement_prêt_pierre(montant_emprunté)
    cond = amortissement.Echéance == nb_mois
    return amortissement.loc[cond, 'CRD en fin de période'].squeeze()


# Ce test vérifie que, le 31 mai 2024, le CRD était bien de 156_980€,
# conformément au site de LBP
assert get_CRD_à_date(
    à_date=datetime.date(2024, 5, 31),
    date_début_du_prêt_existant=datetime.date(2020, 5, 5),
    montant_emprunté=192_820
) == 156_980


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


def get_mt_max_prêt_PEL(barême, mt_intérêts_acquis_PEL: int, mensualité_plafond: int,
                        durée_du_prêt_PEL: int = 2, verbose=False):
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
    if verbose:
        debug_msg = f'{durée_du_prêt_PEL=}  {mt_intérêts_acquis_PEL=}  ->  {mt_du_prêt_du_PEL=}  '
        debug_msg += f'{mensualité=}  '
        print(debug_msg)
    # Si on optimise en premier la durée du prêt :
    if mensualité > mensualité_plafond:
        if durée_du_prêt_PEL < 15:
            return get_mt_max_prêt_PEL(
                barême,
                mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL,
                mensualité_plafond=mensualité_plafond,
                durée_du_prêt_PEL=durée_du_prêt_PEL + 1,
                verbose=verbose
            )
        else:
            lr = 100
            return get_mt_max_prêt_PEL(
                barême,
                mt_intérêts_acquis_PEL=mt_intérêts_acquis_PEL - lr,
                mensualité_plafond=mensualité_plafond,
                durée_du_prêt_PEL=durée_du_prêt_PEL,
                verbose=verbose
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
    barême, mt_intérêts_acquis_PEL=3712, mensualité_plafond=1, verbose=False
)
assert durée_du_prêt_PEL == 15
assert mt_du_prêt_du_PEL == 169
assert mensualité == 1
