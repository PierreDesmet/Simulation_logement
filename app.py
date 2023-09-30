import datetime
import numpy as np
import streamlit as st
from PIL import Image


def sep_milliers(nb, nb_dec=2):
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


LIEU = 'SAINT-GERMAIN EN LAYE'
APPART_OU_MAISON = 'appartement'
NEUF_OU_ANCIEN = 'ancien'
DATE_ACHAT_FUTUR_LOGEMENT = datetime.date(2028, 1, 1)

# Hypothèses
GAIN_MOYEN_PAR_MOIS_PDE = 1500
GAIN_MOYEN_PAR_MOIS_LVO = 2000
APPORT_PDE_ACTUEL = 50_000
SECURITE_LISA = 15_000

AVEC_VENTE_APPARTEMENT_CACHAN = True
SALAIRE_NET_MENSUEL_LVO_À_DATE_ACHAT = 3200
SALAIRE_NET_MENSUEL_PDE_À_DATE_ACHAT = 3600
CREDIT_A_LA_BNP = True
TAUX_CRÉDITS_PUBLIC = 0.0392
# https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf
TAUX_FRAIS_AGENCE = 0.045

# Appartement actuel à Cachan
DATE_DÉBUT_DU_PRÊT_EXISTANT = datetime.date(2020, 10, 1)
MONTANT_REMBOURSÉ_PAR_MOIS = 878
CHARGES_MENSUELLES = 215
PRIX_APPARTEMENT_CACHAN = 259_000
MONTANT_EMPRUNTE = 192_000

# "Le taux maximum d'endettement ne peux excéder 35 % des revenus des emprunteurs,
# assurance comprise"
TAUX_MAX_ENDETTEMENT = 0.35  # assurance comprise
# "Depuis le 1er janvier 2022, les banques doivent limiter à 25 ans la durée
# des crédits immobiliers"
DURÉE_MAX_CRÉDIT_EN_MOIS = 25 * 12


# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_appart = {
    'RUEIL-MALMAISON': 0.112,
    'HOUILLES': 0.158,
    'VÉSINET': 0.121,
    'MAISONS-LAFFITTE': 0.121,
    'CACHAN': 0.15,
    'SAINT-GERMAIN EN LAYE': 0.206
}

# en 5 ans (https://www.meilleursagents.com/prix-immobilier/cachan-94230/rue-de-reims-2017464/1/)
lieu_to_inflation_maison = {
    'RUEIL-MALMAISON': 0.096,
    'HOUILLES': 0.150,
    'VÉSINET': 0.188,
    'MAISONS-LAFFITTE': 0.145,
    'CACHAN': 0.223,
    'SAINT-GERMAIN EN LAYE': 0.114
}


def nb_mois_depuis_que_lisa_économise():
    dt_début_INSPART = datetime.date(2022, 11, 1)
    return (datetime.date.today() - dt_début_INSPART).days // 30.5


def montant_qui_sera_remboursé_à_date(date=datetime.date.today()):
    """Le montant qui aura été remboursé à la `date`"""
    nb_mois_depuis_début_du_prêt = round((date - DATE_DÉBUT_DU_PRÊT_EXISTANT).days / 30.5)
    montant_qui_sera_remboursé = nb_mois_depuis_début_du_prêt * MONTANT_REMBOURSÉ_PAR_MOIS
    return montant_qui_sera_remboursé


APPORT_LVO_ACTUEL = int(
    GAIN_MOYEN_PAR_MOIS_LVO * nb_mois_depuis_que_lisa_économise() - SECURITE_LISA
)
st.set_page_config(
    page_title='Estimation logement',
    page_icon=Image.open("logo.png")
)

st.title('Estimation logement 2028')


st.sidebar.markdown("## Modalités")
select_ville = st.sidebar.selectbox('Ville', sorted(lieu_to_inflation_maison.keys()))
select_appart_ou_maison = st.sidebar.selectbox(
    'Appartement ou maison', ['Appartement', 'Maison']
)
select_neuf_ancien = st.sidebar.selectbox('Neuf ou ancien', ['Ancien', 'Neuf'])
select_date_achat = st.sidebar.date_input("Date achat futur logement", DATE_ACHAT_FUTUR_LOGEMENT)

st.sidebar.markdown("## Hypothèses")
select_avec_vente_appartement = st.sidebar.checkbox(
    "Avec vente appartement de Cachan", AVEC_VENTE_APPARTEMENT_CACHAN
)
select_avec_crédit_BNP = st.sidebar.checkbox("Avec taux du crédit BNP 2%", CREDIT_A_LA_BNP)
select_tx_frais_agence = st.sidebar.slider("Frais **d'agence**", 0.02, 0.06, TAUX_FRAIS_AGENCE)
select_gain_mensuel_pde = st.sidebar.slider(
    'Gain mensuel Pierre',
    min_value=1000, max_value=2500, value=GAIN_MOYEN_PAR_MOIS_PDE, step=100
)
select_gain_mensuel_lvo = st.sidebar.slider(
    'Gain mensuel Lisa',
    min_value=1000, max_value=2500, value=GAIN_MOYEN_PAR_MOIS_LVO, step=100
)
select_apport_pde = st.sidebar.slider(
    'Apport Pierre actuel',
    min_value=20_000, max_value=150_000, value=APPORT_PDE_ACTUEL, step=5000
)
select_apport_lvo = st.sidebar.slider(
    'Apport Lisa actuel',
    min_value=20_000, max_value=150_000, value=APPORT_LVO_ACTUEL, step=5000
)
select_w_mensuel_pde_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Pierre à date d'achat",
    min_value=3000, max_value=4500, value=SALAIRE_NET_MENSUEL_PDE_À_DATE_ACHAT, step=100
)
select_w_mensuel_lvo_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Lisa à date d'achat",
    min_value=3000, max_value=4500, value=SALAIRE_NET_MENSUEL_LVO_À_DATE_ACHAT
)


# Les dépendances
nb_mois_restants_avant_achat = round(
    (select_date_achat - datetime.date.today()).days / 30.5
)
montant_qui_sera_remboursé = montant_qui_sera_remboursé_à_date(
    date=select_date_achat
)
prix_estimé_revente = PRIX_APPARTEMENT_CACHAN * (1 + lieu_to_inflation_appart['CACHAN'])
gain_revente = prix_estimé_revente - PRIX_APPARTEMENT_CACHAN
dû_à_la_banque = MONTANT_EMPRUNTE - montant_qui_sera_remboursé

apport_qui_sera_apporté_pde = select_apport_pde
apport_qui_sera_apporté_pde += select_gain_mensuel_pde * nb_mois_restants_avant_achat
apport_qui_sera_apporté_pde += gain_revente * select_avec_vente_appartement
apport_qui_sera_apporté_pde -= dû_à_la_banque * select_avec_vente_appartement

apport_qui_sera_apporté_lvo = select_apport_lvo
apport_qui_sera_apporté_lvo += select_gain_mensuel_lvo * nb_mois_restants_avant_achat

capacité_max_emprunt_pde = TAUX_MAX_ENDETTEMENT * (
    select_w_mensuel_pde_date_achat - (
        (not select_avec_vente_appartement) * (MONTANT_REMBOURSÉ_PAR_MOIS + CHARGES_MENSUELLES)
    )
)
capacité_max_emprunt_pde *= DURÉE_MAX_CRÉDIT_EN_MOIS
capacité_max_emprunt_lvo = TAUX_MAX_ENDETTEMENT * select_w_mensuel_lvo_date_achat
capacité_max_emprunt_lvo *= DURÉE_MAX_CRÉDIT_EN_MOIS

capacité_emprunt_totale = capacité_max_emprunt_pde + capacité_max_emprunt_lvo
montant_total_qui_sera_apporté = apport_qui_sera_apporté_pde + apport_qui_sera_apporté_lvo

prix_maximal_appartement = montant_total_qui_sera_apporté + capacité_emprunt_totale

st.markdown('Prix maximal du logement : ' + sep_milliers(prix_maximal_appartement, 0) + ' €')
st.markdown("Attention, il faut prendre en compte :")

lieu_to_inflation = (
    lieu_to_inflation_appart if select_appart_ou_maison == 'Appartement'
    else lieu_to_inflation_maison
)
inflation_temps_restant_avant_achat = (
    (nb_mois_restants_avant_achat / 12) / 5
) * lieu_to_inflation[select_ville]
prix_maximal_appartement = round(
    prix_maximal_appartement / (1 + inflation_temps_restant_avant_achat)
)
st.markdown(f"* L'inflation : {sep_milliers(prix_maximal_appartement, 0)} €")


prix_maximal_appartement -= (
    (TAUX_CRÉDITS_PUBLIC / (1 + select_avec_crédit_BNP)) * capacité_emprunt_totale
)
st.markdown(f"* Le coût du crédit (hors assurance) : {sep_milliers(prix_maximal_appartement, 0)} €")

frais_de_notaire = 0.08 if select_neuf_ancien == 'Ancien' else 0.03
frais_de_notaire *= prix_maximal_appartement
prix_maximal_appartement -= frais_de_notaire
st.markdown(f"* Les frais de notaire : {sep_milliers(prix_maximal_appartement, 0)} €")

prix_maximal_appartement -= (select_tx_frais_agence * prix_maximal_appartement)
st.markdown(f"* Les frais d'agence : {sep_milliers(prix_maximal_appartement, 0)} €")

st.markdown(f'**➜ Soit un prix final maximum de : {sep_milliers(prix_maximal_appartement, 0)} €**')
st.markdown('-' * 3)

st.markdown("Pour obtenir cet appartement il nous faut :")
st.markdown(f'* avoir un apport de {sep_milliers(montant_total_qui_sera_apporté, 0)} € ')
st.markdown(f'* obtenir un emprunt de {sep_milliers(capacité_emprunt_totale, 0)} €')
