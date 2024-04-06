"""
Simulateur du montant que pourra coûter notre futur logement à Lisa et moi

$ source /Users/pierredesmet/miniconda3/envs/pierrou_env/bin/activate
$ streamlit run app.py

Réflexion sur le PEL, pour un souscription en janvier 2024 :
    Taux **d'intérêt** du compte = 2.25 %
    Taux du **prêt** : 3.45 %
    Pour être intéressant, le PEL doit avoir un taux plus intéressant que
    le taux BNP au moment de l'achat. On a :
      taux_emprunt_BNP ~ 0.7 * taux_nominal_public, et
      taux_emprunt_PEL = 0.0345
    Donc pour que le PEL soit intéressant, il faut qu'au moment de l'achat :
    taux_nominal_public > 0.0345 / 0.7, càd que le taux nominal public dépasse le 4.93 %...
    ce qui est très rarement arrivé :
    https://www.lesfurets.com/pret-immobilier/barometre-taux/votre-taux)

Sources :
- https://www.service-public.fr/particuliers/vosdroits/F2456
- https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html
- https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf
- https://fr.luko.eu/conseils/guide/taux-endettement-maximum/
- https://app.dvf.etalab.gouv.fr
- PEL : https://www.service-public.fr/particuliers/vosdroits/F16140
"""
import datetime
import numpy as np
import streamlit as st
from PIL import Image

from fonctions import (
    lieu_to_inflation_appart,
    lieu_to_inflation_maison,
    lieu_to_url_meilleurs_agents,
    get_mt_emprunt_max,
    sep_milliers,
    nb_mois_depuis_que_lisa_économise,
    montant_qui_sera_remboursé_à_date,
    img_to_bytes,
    get_mt_prêt_et_mensualité_du_PEL,
    TAUX_BNP, TAUX_NOMINAL_PUBLIC, TAUX_PEL
)

# Hypothèses
SECURITE_LISA = 10_000

# Appartement actuel à Cachan
TX_LBP = 0.9
DATE_DÉBUT_DU_PRÊT_EXISTANT = datetime.date(2020, 10, 1)
MONTANT_REMBOURSÉ_PAR_MOIS = 878
CHARGES_MENSUELLES = 215
PRIX_APPARTEMENT_CACHAN = 259_000
MONTANT_EMPRUNTE = 192_000
ASSURANCE_PRÊT = 16

# "Le taux maximum d'endettement ne peux excéder 35 % des revenus des emprunteurs,
# assurance comprise"
TAUX_MAX_ENDETTEMENT = 0.35  # assurance comprise
# "Depuis le 1er janvier 2022, les banques doivent limiter à 25 ans la durée
# des crédits immobiliers"
DURÉE_MAX_CRÉDIT_EN_MOIS = 25 * 12

PARTICIPATION = 3122.84  # montant pour 2023
INTERESSEMENT = 3000  # montant pour 2023
PARTICIPATION_INTERESSEMENT = PARTICIPATION + INTERESSEMENT
W_VARIABLE = (2000 + 1000) * (12 / 4)  # prorata de présence 2022, montant annuel


st.set_page_config(
    page_title='Estimation logement',
    page_icon=Image.open("logo.png")
)

st.header("🏠  Estimation logement 2029")


@st.cache_data()
def md_from_title_and_img(title: str, img_path: str):
    img64 = img_to_bytes(img_path)
    size = 28 if img_path != 'tirelire.png' else 35
    width = f'width={size} height={size}'
    return f"""## <img src='data:image/png;base64,{img64}' class='img-fluid' {width}>  {title}"""


st.sidebar.markdown(
    md_from_title_and_img("Type d'appartement", 'logo.png'),
    unsafe_allow_html=True
)

select_ville = st.sidebar.selectbox(
    'Ville', sorted(lieu_to_inflation_maison.keys()),
    index=sorted(lieu_to_inflation_appart).index('RUEIL-MALMAISON')
)
select_appart_ou_maison = st.sidebar.selectbox(
    'Appartement ou maison', ['Appartement', 'Maison']
)
select_neuf_ancien = st.sidebar.selectbox('Neuf ou ancien', ['Ancien', 'Neuf'])
select_date_achat = st.sidebar.date_input('Date achat futur logement', datetime.date(2029, 1, 1))


st.sidebar.markdown(
    md_from_title_and_img("Emprunt", 'bnp-paribas.jpg'),
    unsafe_allow_html=True
)
select_avec_vente_appartement = st.sidebar.checkbox(
    "Avec vente appartement de Cachan", True
)
select_avec_crédit_BNP = st.sidebar.checkbox("Avec taux avantageux BNP", True)
select_prise_en_compte_du_variable = st.sidebar.checkbox("Avec prise en compte du variable", True)
select_prise_en_compte_participation_interessement = st.sidebar.checkbox(
    "Avec prise en compte de la participation et de l'intéressement", False
)
select_remb_anticipé_gratuit = st.sidebar.checkbox(
    "Avec clause de remboursement anticipée gratuite", False
)

select_nb_années_pr_rembourser = st.sidebar.slider(
    "Nombre d'années pour rembourser le crédit",
    min_value=15, max_value=25, value=25, step=5
)

if select_avec_crédit_BNP:
    légende = 'Taux nominal BNP en %'
    default = TAUX_BNP[select_nb_années_pr_rembourser] * 100
else:
    légende = (
        "[Taux nominal public en %]"
        "(https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html)"
    )
    default = TAUX_NOMINAL_PUBLIC[select_nb_années_pr_rembourser] * 100
select_tx_nominal = st.sidebar.slider(
    légende, 1., 5., default, step=0.05  # "Bon taux"
    # source : https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html
)
tx_nominal = select_tx_nominal / 100
est_PEL_intéressant = TAUX_PEL < tx_nominal

if est_PEL_intéressant:
    select_nb_années_pr_rembourser_prêt_PEL = st.sidebar.slider(
        "Nombre d'années pour rembourser le prêt du PEL",
        min_value=2, max_value=15, value=3, step=1
    )
    select_mt_intérêts_acquis_pel = st.sidebar.number_input(
        'Montant des intérêt acquis PEL', value=675,
        step=100
    )

select_tx_frais_agence = st.sidebar.slider(
    "[Frais d'agence en %]"
    "(https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf)",
    3.0, 6.0, 4.5, step=0.5
)
select_tx_frais_agence /= 100

st.sidebar.markdown(
    md_from_title_and_img("Apports", 'tirelire.png'),
    unsafe_allow_html=True
)
select_gain_mensuel_pde = st.sidebar.slider(
    'Gain mensuel Pierre',
    min_value=1000, max_value=2500, value=1600, step=100
)

select_gain_mensuel_lvo = st.sidebar.slider(
    'Gain mensuel Lisa',
    min_value=1000, max_value=2500, value=2000, step=100
)
select_apport_actuel_pde = st.sidebar.slider(
    'Apport actuel Pierre',
    min_value=20_000, max_value=150_000, value=60_000, step=5000
)
apport_lvo_actuel_default = int(
    select_gain_mensuel_lvo * nb_mois_depuis_que_lisa_économise() - SECURITE_LISA
)
select_apport_actuel_lvo = st.sidebar.slider(
    'Apport actuel Lisa',
    min_value=20_000, max_value=150_000, value=apport_lvo_actuel_default, step=5000
)
select_w_mensuel_pde_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Pierre à date d'achat",
    min_value=3000, max_value=5000, value=4200, step=100
)
# En sept. 2023, 3624 * 13 / 12 = 3930 de mensuel net avant impôt
# En avril 2024, augmentation du fixe de 700€ (ou 800 ?)

select_w_mensuel_lvo_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Lisa à date d'achat",
    min_value=3000, max_value=5000, value=3500
)
# En 2023, 36 174 € / 12 = 3015€ de mensuel net avant impôt
# En 2024, (salaire brut = 46 000 * 1,07) * (PS -> 0.8) * (1 / 12) = 3280

# Les dépendances
nb_mois_restants_avant_achat = round(
    (select_date_achat - datetime.date.today()).days / 30.5
)
nb_années_restantes_avant_achat = nb_mois_restants_avant_achat / 12
montant_qui_sera_remboursé = montant_qui_sera_remboursé_à_date(
    date_début_du_prêt_existant=DATE_DÉBUT_DU_PRÊT_EXISTANT,
    mt_remboursé_par_mois=MONTANT_REMBOURSÉ_PAR_MOIS,
    date=select_date_achat
)

sign = np.sign(lieu_to_inflation_appart['CACHAN'])
inflation_annuelle_cachan = abs(lieu_to_inflation_appart['CACHAN']) ** (1 / 5)
inflation_cachan_avant_achat = sign * (
    inflation_annuelle_cachan ** nb_années_restantes_avant_achat
)
prix_estimé_revente = PRIX_APPARTEMENT_CACHAN * (1 + inflation_cachan_avant_achat)

CRD = MONTANT_EMPRUNTE - montant_qui_sera_remboursé
# Source : pdf des conditions générales LBP
indemnités_de_remb_par_anticipation = min(
    TX_LBP * CRD * 6,
    CRD * 0.03,
)
dû_à_la_banque = CRD + (
    (not select_remb_anticipé_gratuit) * indemnités_de_remb_par_anticipation
)
solde_revente = prix_estimé_revente - dû_à_la_banque

apport_qui_sera_apporté_pde = select_apport_actuel_pde
apport_qui_sera_apporté_pde += select_gain_mensuel_pde * nb_mois_restants_avant_achat
apport_qui_sera_apporté_pde += solde_revente * select_avec_vente_appartement

apport_qui_sera_apporté_lvo = select_apport_actuel_lvo
apport_qui_sera_apporté_lvo += select_gain_mensuel_lvo * nb_mois_restants_avant_achat

montant_total_qui_sera_apporté = apport_qui_sera_apporté_pde + apport_qui_sera_apporté_lvo

# Si je garde mon appartement, c'est pour le mettre en location (et donc, j'aurai
# des revenus fonciers). On lit ici que les revenus fonciers sont pris en compte dans le
# calcul du taux d'endettement à hauteur de 70% :
# https://fr.luko.eu/conseils/guide/taux-endettement-maximum/
# 1200 € : le montant que je peux mettre en location, charges comprises (source SeLoger)
# Hypothèse pessimiste : l'établissement bancaire retire les charges de copropriété de
# mes revenus fonciers dans le calcul du taux d'endettement. C'est plutôt rare, cf ChatGPT.
mensualité_max_pde = TAUX_MAX_ENDETTEMENT * (
    select_w_mensuel_pde_date_achat +
    select_prise_en_compte_du_variable * (W_VARIABLE / 12) +
    select_prise_en_compte_participation_interessement * (PARTICIPATION_INTERESSEMENT / 12) +
    (not select_avec_vente_appartement) * (0.7 * (1200 - 250)) -
    (not select_avec_vente_appartement) * (MONTANT_REMBOURSÉ_PAR_MOIS + ASSURANCE_PRÊT) -
    (not select_avec_vente_appartement) * 0.0295 * 1200  # assurance loyer impayé, source Macif
)
capacité_max_emprunt_pde = mensualité_max_pde * select_nb_années_pr_rembourser
mensualité_max_lvo = TAUX_MAX_ENDETTEMENT * select_w_mensuel_lvo_date_achat
capacité_max_emprunt_lvo = mensualité_max_lvo * select_nb_années_pr_rembourser



mensualité_maximale = mensualité_max_pde + mensualité_max_lvo
st.markdown(
    'Mensualité maximale supportable par Lisa et Pierre : '
    f'{sep_milliers(mensualité_maximale)} €, '
    f'dont {sep_milliers(mensualité_max_pde)} € Pierre et '
    f'{sep_milliers(mensualité_max_lvo)} € Lisa.'
)
mt_emprunt_max = get_mt_emprunt_max(
    mensualité_max=mensualité_maximale,
    tx_nominal=tx_nominal,
    nb_mois=select_nb_années_pr_rembourser * 12
)
st.markdown(
    f'Cette mensualité, adossée à un taux nominal de {tx_nominal:.2%}, '
    f"permet d'emprunter au maximum {sep_milliers(mt_emprunt_max)} € "
    f'sur {select_nb_années_pr_rembourser} ans.'
)
budget = montant_total_qui_sera_apporté + mt_emprunt_max
phrase = f'Notre apport est de {sep_milliers(montant_total_qui_sera_apporté)} €'
if select_avec_vente_appartement:
    phrase += (
        f", dont {sep_milliers(solde_revente)} € liés à la revente de l'appartement de Cachan "
        f"(prix de revente estimé à {sep_milliers(prix_estimé_revente)} €)"
    )
st.markdown(phrase + '.')

st.markdown(f"Notre budget total d'achat est donc de {sep_milliers(budget)} €.")

st.markdown("Attention, il faut prendre en compte :")
lieu_to_inflation = (
    lieu_to_inflation_appart if select_appart_ou_maison == 'Appartement'
    else lieu_to_inflation_maison
)
inflation_par_an_les_5_dernières_années = lieu_to_inflation[select_ville] ** (1 / 5)
inflation_temps_restant_avant_achat = (
    inflation_par_an_les_5_dernières_années ** nb_années_restantes_avant_achat
)
budget = round(budget / (1 + inflation_temps_restant_avant_achat))
url_meilleurs_agents = lieu_to_url_meilleurs_agents[select_ville]
st.markdown(
    f"* [L'inflation](https://www.meilleursagents.com/prix-immobilier/{url_meilleurs_agents}/)"
    f" ({lieu_to_inflation[select_ville]:.2%} en 5 ans à {select_ville}) : "
    f'{sep_milliers(budget)} €'
)


coût_crédit = mensualité_maximale * 12 * select_nb_années_pr_rembourser - mt_emprunt_max
budget -= coût_crédit
if select_avec_crédit_BNP:
    prefix = (
        "* [Le coût du crédit ]"
        "(https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html)"
    )
else:
    prefix = '* Le coût du crédit '
st.markdown(prefix + f"(hors assurance) : {sep_milliers(budget)} €")

# mensualité d'assurance / mensualité du crédit
tx_assurance_actuelle = 16.07 / MONTANT_REMBOURSÉ_PAR_MOIS
coût_assurance = tx_assurance_actuelle * mensualité_maximale * 12 * select_nb_années_pr_rembourser
budget -= coût_assurance
st.markdown(f"* Le coût de l'assurance emprunteur : {sep_milliers(budget)} €")

frais_de_notaire = 0.075 if select_neuf_ancien == 'Ancien' else 0.03
frais_de_notaire *= budget
budget -= frais_de_notaire
st.markdown(f"* Les frais de notaire : {sep_milliers(budget)} €")

if select_avec_vente_appartement:
    budget -= (select_tx_frais_agence * prix_estimé_revente)
    st.markdown(
        "* Les [frais d'agence]"
        "(https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf) "
        "sur la revente de l'appartement de Cachan : "
        f'{sep_milliers(budget)} €'
    )

if not select_remb_anticipé_gratuit:
    budget -= indemnités_de_remb_par_anticipation
    st.markdown(
        "* Les indemnités de remboursement par anticipation : "
        f'{sep_milliers(budget)} €'
    )

budget -= 1000
st.markdown(f'* Les frais de dossier bancaire : {sep_milliers(budget)} €')

st.markdown(f'**➜ Soit un prix final maximum de : {sep_milliers(budget)} €**')
st.markdown('-' * 3)

phrase = "Utiliser le prêt du PEL n'est pas intéressant."
if est_PEL_intéressant:
    phrase = "Utiliser le prêt du PEL est intéressant : \n"
    mt_du_prêt_du_PEL, mensualité_PEL = get_mt_prêt_et_mensualité_du_PEL(
        mt_intérêts_acquis_PEL=select_mt_intérêts_acquis_pel,
        durée_du_prêt_PEL=select_nb_années_pr_rembourser_prêt_PEL
    )
    phrase += f'Mt du prêt du PEL = {mt_du_prêt_du_PEL}, {mensualité_PEL=}'
st.markdown(phrase)


st.markdown(
    'Pour être exhaustive, cette simulation devrait aussi tenir compte '
    'des gros impacts sur nos finances :\n'
    '* un enfant, le ravalement, un mariage, des voyages, etc.\n'
    '* un héritage, les JO 2024, etc.'
)
st.markdown(
    f'Une marge de sécurité est conservée par Lisa à hauteur de {sep_milliers(SECURITE_LISA)} €.'
)

st.markdown(
    """
    Cette simulation ne tient pas compte :
    * des 30% de réduction sur l'assurance emprunteur,
    * des éventuels frais de courtage,
    * des éventuels frais de tenue de compte en cas d'ouverture de compte dans une banque,
    * des éventuels frais de garanties (hypothèque ou cautionnement)
    * du taux d'emprunt PEL potentiellement plus avantageux que le taux d'emprunt BNP

    Hypothèses prises :
    * Pour prédire l'inflation, on a estimé l'inflation moyenne dans la ville
    sur les 5 dernières années, et projeté ce taux d'inflation sur le temps restant avant achat.
    * En cas de revente de mon appartement, on suppose que la vente a lieu en même temps que
    l'achat du futur logement.
    """
)

# TODO :
# refactoring
# intégrer le PEL (?)
# vf que pour un euro d'emprunt supplémentaire, ça passe plus (mensualité > mensualité max)
# compte à terme : https://placement.meilleurtaux.com/assurance-vie/actualites/2024-avril/voici-le-meilleur-compte-a-terme-en-2024.html