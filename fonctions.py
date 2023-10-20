"""Ce script contient les fonctions utilisées par l'application"""
import datetime
import numpy as np
import base64
from pathlib import Path

# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_appart = {
    'CACHAN': 0.15,
    'HOUILLES': 0.158,
    'MAISONS-LAFFITTE': 0.121,
    'RUEIL-MALMAISON': 0.112,
    'VÉSINET': 0.121,
    'SAINT-GERMAIN EN LAYE': 0.206
}

# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_maison = {
    'CACHAN': 0.223,
    'HOUILLES': 0.150,
    'MAISONS-LAFFITTE': 0.145,
    'RUEIL-MALMAISON': 0.096,
    'VÉSINET': 0.188,
    'SAINT-GERMAIN EN LAYE': 0.114
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
