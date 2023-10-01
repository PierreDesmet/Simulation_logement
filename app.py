"""Simulateur du montant que pourra coûter notre futur logis à Lisa et moi"""
import datetime
import streamlit as st
from PIL import Image

from fonctions import (
    lieu_to_inflation_appart,
    lieu_to_inflation_maison,
    get_mt_mensualités,
    sep_milliers,
    nb_mois_depuis_que_lisa_économise,
    montant_qui_sera_remboursé_à_date
)

# Hypothèses
SECURITE_LISA = 15_000
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
select_date_achat = st.sidebar.date_input('Date achat futur logement', datetime.date(2028, 1, 1))

st.sidebar.markdown("## Hypothèses")
select_avec_vente_appartement = st.sidebar.checkbox(
    "Avec vente appartement de Cachan", True
)
select_avec_crédit_BNP = st.sidebar.checkbox("Avec taux avantageux BNP", True)
select_tx_nominal = st.sidebar.slider("Taux nominal public", 0.01, 0.05, TAUX_CRÉDITS_PUBLIC)
select_tx_frais_agence = st.sidebar.slider("[Frais d'agence](https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf)", 0.02, 0.06, TAUX_FRAIS_AGENCE)
select_nb_années_pr_rembourser = st.sidebar.slider(
    "Nombre d'années pour rembourser",
    min_value=15, max_value=25, value=25, step=5
)
select_gain_mensuel_pde = st.sidebar.slider(
    'Gain mensuel Pierre',
    min_value=1000, max_value=2500, value=1500, step=100
)

select_gain_mensuel_lvo = st.sidebar.slider(
    'Gain mensuel Lisa',
    min_value=1000, max_value=2500, value=2000, step=100
)
select_apport_pde = st.sidebar.slider(
    'Apport actuel Pierre',
    min_value=20_000, max_value=150_000, value=50_000, step=5000
)
apport_lvo_actuel_default = int(
    select_gain_mensuel_lvo * nb_mois_depuis_que_lisa_économise() - SECURITE_LISA
)
select_apport_lvo = st.sidebar.slider(
    'Apport actuel Lisa',
    min_value=20_000, max_value=150_000, value=apport_lvo_actuel_default, step=5000
)
select_w_mensuel_pde_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Pierre à date d'achat",
    min_value=3000, max_value=5000, value=4200, step=100
)  # En sept. 2023, 3624 * 13 / 12 = 3930 de mensuel net avant impôt
select_w_mensuel_lvo_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Lisa à date d'achat",
    min_value=3000, max_value=5000, value=3300
)  # En 2023, 36 174 € / 12 = 3015€ de mensuel net avant impôt


# Les dépendances
nb_mois_restants_avant_achat = round(
    (select_date_achat - datetime.date.today()).days / 30.5
)
montant_qui_sera_remboursé = montant_qui_sera_remboursé_à_date(
    date_début_du_prêt_existant=DATE_DÉBUT_DU_PRÊT_EXISTANT,
    mt_remboursé_par_mois=MONTANT_REMBOURSÉ_PAR_MOIS,
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

mensualité_max_pde = TAUX_MAX_ENDETTEMENT * (
    select_w_mensuel_pde_date_achat - (
        (not select_avec_vente_appartement) * (MONTANT_REMBOURSÉ_PAR_MOIS + CHARGES_MENSUELLES)
    )
)
capacité_max_emprunt_pde = mensualité_max_pde * DURÉE_MAX_CRÉDIT_EN_MOIS
mensualité_max_lvo = TAUX_MAX_ENDETTEMENT * select_w_mensuel_lvo_date_achat
capacité_max_emprunt_lvo = mensualité_max_lvo * DURÉE_MAX_CRÉDIT_EN_MOIS

capacité_emprunt_totale = capacité_max_emprunt_pde + capacité_max_emprunt_lvo
montant_total_qui_sera_apporté = apport_qui_sera_apporté_pde + apport_qui_sera_apporté_lvo

mensualité = get_mt_mensualités(
    mt_emprunt=capacité_emprunt_totale,
    tx_nominal=select_tx_nominal / (1 + select_avec_crédit_BNP),
    nb_mois=select_nb_années_pr_rembourser * 12
)
prix_maximal_appartement = montant_total_qui_sera_apporté + capacité_emprunt_totale
coût_crédit = mensualité * 12 * select_nb_années_pr_rembourser - capacité_emprunt_totale

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


prix_maximal_appartement -= coût_crédit
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

st.markdown(f'Les mensualités : {sep_milliers(mensualité)} €')


st.markdown(f'Le coût du crédit : {sep_milliers(coût_crédit, 0)} €')


st.markdown("TODO: prendre en compte l'assurance du prêt, et les autres composantes du TAEG...")
# https://www.service-public.fr/particuliers/vosdroits/F2456
# Intérêts bancaires calculés sur la base du taux actuariel : Taux qui permet de calculer le montant effectif des intérêts que l'emprunteur doit verser au prêteur
# Frais de dossier (payés à la banque)
# Frais payés ou dus à des intermédiaires intervenus dans l'octroi du prêt (courtier par exemple)
# Coût de l'assurance emprunteur
# Frais de garanties (hypothèque ou cautionnement)
# Frais d'évaluation du bien immobilier (payés à un agent immobilier)
# Tous les autres frais qui vous sont imposés pour l'obtention du crédit (frais de tenue de compte, en cas d'obligation d'ouverture de compte dans la banque qui octroie le prêt)