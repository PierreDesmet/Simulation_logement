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
- https://www.salaire-brut-en-net.fr
- https://www.service-public.fr/particuliers/vosdroits/F2456
- https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html
- https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf
- https://fr.luko.eu/conseils/guide/taux-endettement-maximum/
- https://app.dvf.etalab.gouv.fr
- PEL : https://www.service-public.fr/particuliers/vosdroits/F16140
"""
import datetime

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from fonctions import (
    INFLATION_SUR_NB_YEARS, TAUX_BNP, TAUX_NOMINAL_PUBLIC, TAUX_PEL, barême, get_CRD_à_date,
    get_mt_emprunt_max, get_mt_max_prêt_PEL, img_to_bytes, LIEU_TO_INFLATION_APPART,
    LIEU_TO_INFLATION_MAISON, lieu_to_url_meilleurs_agents, nb_mois_depuis_que_lisa_économise,
    sep_milliers, get_inflation_annuelle, projette_prix_inflate
)

# Hypothèses
SECURITE_LISA = 10_000

# Appartement actuel à Cachan
TX_LBP = 0.9
DATE_DÉBUT_DU_PRÊT_EXISTANT = datetime.date(2020, 5, 5)
MONTANT_REMBOURSÉ_PAR_MOIS = 878.19
CHARGES_MENSUELLES = 200
PRIX_APPARTEMENT_CACHAN = 259_000
MONTANT_EMPRUNTE = 192_820
ASSURANCE_PRÊT = 16

# "Le taux maximum d'endettement ne peux excéder 35 % des revenus des emprunteurs,
# assurance comprise"
TAUX_MAX_ENDETTEMENT = 0.35  # assurance comprise
# "Depuis le 1er janvier 2022, les banques doivent limiter à 25 ans la durée
# des crédits immobiliers"
DURÉE_MAX_CRÉDIT_EN_MOIS = 25 * 12

PARTICIPATION = 3697  # montant pour 2024
INTERESSEMENT = 3460  # montant pour 2024
PARTICIPATION_INTERESSEMENT = PARTICIPATION + INTERESSEMENT
W_TOTAL_AVANT_IMPÔT = (67_000 + 5000 + 12_000) * (63_000 / 84_000)  # hors PI et abondemment
W_VARIABLE_AVANT_IMPÔT = 12_000 * (63_000 / 84_000)  # https://www.salaire-brut-en-net.fr


st.set_page_config(
    page_title='Estimation logement',
    page_icon=Image.open("logo.png")
)

titre = st.empty()


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
    'Ville', sorted(LIEU_TO_INFLATION_MAISON.keys()),
    index=sorted(LIEU_TO_INFLATION_MAISON).index('RUEIL-MALMAISON')
)
select_appart_ou_maison = st.sidebar.selectbox(
    'Appartement ou maison', ['Maison', 'Appartement']
)
select_neuf_ancien = st.sidebar.selectbox('Neuf ou ancien', ['Ancien', 'Neuf'])
select_date_achat = st.sidebar.date_input('Date achat futur logement', datetime.date(2029, 1, 1))
titre.header("🏠  Estimation logement " + str(select_date_achat.year))

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
# Une fois révolu le 7e anniversaire suivant la date de signature de la présente offre,
# l'Emprunteur peut effectuer des remboursements par anticipation, sans frais
remb_anticipé_gratuit = (DATE_DÉBUT_DU_PRÊT_EXISTANT + pd.DateOffset(years=7)).date()
remb_anticipé_gratuit = select_date_achat > remb_anticipé_gratuit
select_remb_anticipé_gratuit = st.sidebar.checkbox(
    "Avec clause de remboursement anticipée gratuite", value=remb_anticipé_gratuit
)

select_nb_années_pr_rembourser = st.sidebar.slider(
    "Nombre d'années pour rembourser le crédit",
    min_value=15, max_value=25, value=20, step=5
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
est_PEL_intéressant = TAUX_PEL <= tx_nominal

if est_PEL_intéressant:
    # % de mon endettement alloué au PEL par opposition au prêt principal :
    curseur_PEL = st.sidebar.slider('curseur_PEL', 0., 1., 0., step=0.01)
    select_mt_intérêts_acquis_pel = st.sidebar.number_input(
        'Montant des intérêt acquis PEL',
        value=int(0.0225 * 20000 + 0.0225 * 35000 + 0.0225 * 52000 + 0.0225 * 60000),
        step=100
    )
else:
    curseur_PEL = 0  # par défaut, on n'utilise pas le PEL
    mensualité_PEL = 0
    mt_prêt_PEL = 0
    durée_du_prêt_PEL = 0

select_tx_frais_agence = st.sidebar.slider(
    "[Frais d'agence en %]"
    "(https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf)",
    0.0, 7.0, 4.8, step=0.5
)
select_tx_frais_agence /= 100

st.sidebar.markdown(
    md_from_title_and_img("Apports", 'tirelire.png'),
    unsafe_allow_html=True
)
select_avec_projection_inflation = st.sidebar.checkbox(
    f"Avec projection d'inflation sur {INFLATION_SUR_NB_YEARS} ans", True
)
select_gain_mensuel_pde = st.sidebar.slider(
    'Gain mensuel Pierre',
    min_value=1000, max_value=2500, value=1800, step=100
)

select_gain_mensuel_lvo = st.sidebar.slider(
    'Gain mensuel Lisa',
    min_value=1000, max_value=2500, value=2200, step=100
)
select_apport_actuel_pde = st.sidebar.slider(
    'Apport actuel Pierre',
    min_value=20_000, max_value=150_000, value=100_000, step=5000
)
apport_lvo_actuel_default = int(
    select_gain_mensuel_lvo * nb_mois_depuis_que_lisa_économise() - SECURITE_LISA
)
select_apport_actuel_lvo = st.sidebar.slider(
    'Apport actuel Lisa',
    min_value=20_000, max_value=150_000, value=apport_lvo_actuel_default, step=5000
)
select_w_mensuel_pde_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Pierre à date d'achat",  # Hors variable !
    min_value=3000, max_value=6000,
    value=int((W_TOTAL_AVANT_IMPÔT - W_VARIABLE_AVANT_IMPÔT) / 12), step=100
)
# En sept. 2023, 3624 * 13 / 12 = 3930 de mensuel net avant impôt
# En avril 2024, 3652 * 13 / 12 = 3956 de mensuel net avant impôt

select_w_mensuel_lvo_date_achat = st.sidebar.slider(
    "Salaire mensuel net av. impôt Lisa à date d'achat",
    min_value=3000, max_value=6000, value=3500
)
# En 2023, 36 174 € / 12 = 3015€ de mensuel net avant impôt
# En 2024, (salaire brut = 46 000 * 1,07) * (PS -> 0.8) * (1 / 12) = 3280

# Les dépendances
lieu_to_inflation_appart, lieu_to_inflation_maison = {}, {}
for k in LIEU_TO_INFLATION_APPART.keys():
    lieu_to_inflation_appart[k] = (
        LIEU_TO_INFLATION_APPART[k] if select_avec_projection_inflation else 0
    )
    lieu_to_inflation_maison[k] = (
        LIEU_TO_INFLATION_MAISON[k] if select_avec_projection_inflation else 0
    )

années_depuis_achat = (
    (
        select_date_achat - DATE_DÉBUT_DU_PRÊT_EXISTANT
    ).days / 365
)

nb_mois_restants_avant_achat = round(
    (select_date_achat - datetime.date.today()).days / 30.5
)
nb_années_restantes_avant_achat = nb_mois_restants_avant_achat / 12

inflation_annuelle_cachan = get_inflation_annuelle(
    inflation_cum=lieu_to_inflation_appart['CACHAN'],
    nb_years_cum=INFLATION_SUR_NB_YEARS
)
prix_estimé_revente = projette_prix_inflate(
    prix_initial=PRIX_APPARTEMENT_CACHAN,
    inf_annuelle_en_pct=inflation_annuelle_cachan,
    nb_years_projetées=nb_années_restantes_avant_achat
)

CRD = get_CRD_à_date(
    à_date=select_date_achat,
    date_début_du_prêt_existant=DATE_DÉBUT_DU_PRÊT_EXISTANT,
    montant_emprunté=MONTANT_EMPRUNTE
)

# Source : pdf des conditions générales LBP
indemnités_de_remb_par_anticipation = min(
    # "En cas de remboursement anticipé, LBP percevra une indemnité égale à un semestre d'intérêts
    # calculés au taux indiqué dans les conditions particulières sur le montant du CRD."
    144.62 * 6,
    # "Cette indemnité est plafonnée à 3 % du capital restant dû avant le remboursement."
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


def calcule_mensualité_max_pde(
    w_mensuel_pde_date_achat=select_w_mensuel_pde_date_achat,
    prise_en_compte_du_variable=select_prise_en_compte_du_variable,
    w_variable=W_VARIABLE_AVANT_IMPÔT,
    taux_max_endettement=TAUX_MAX_ENDETTEMENT,
    prise_en_compte_participation_interessement=select_prise_en_compte_participation_interessement,
    participation_intéressement=PARTICIPATION_INTERESSEMENT,
    avec_vente_appartement=select_avec_vente_appartement,
    mt_remboursé_par_mois=MONTANT_REMBOURSÉ_PAR_MOIS,
    assurance_prêt=ASSURANCE_PRÊT
):
    """
    Si je garde mon appartement, c'est pour le mettre en location (et donc, j'aurai
    des revenus fonciers). On lit ici que les revenus fonciers sont pris en compte dans le
    calcul du taux d'endettement à hauteur de 70% :
    https://fr.luko.eu/conseils/guide/taux-endettement-maximum/
    1200 € : le montant que je peux mettre en location, charges comprises (source SeLoger)
    Hypothèse pessimiste : l'établissement bancaire retire les charges de copropriété de
    mes revenus fonciers dans le calcul du taux d'endettement. C'est plutôt rare, cf ChatGPT.
    """
    mensualité_max_pde = taux_max_endettement * (
        w_mensuel_pde_date_achat +
        prise_en_compte_du_variable * (w_variable / 12) +
        prise_en_compte_participation_interessement * (participation_intéressement / 12) +
        (not avec_vente_appartement) * (0.7 * (1200 - 250)) -
        (not avec_vente_appartement) * (mt_remboursé_par_mois + assurance_prêt) -
        (not avec_vente_appartement) * 0.0295 * 1200  # assurance loyer impayé, source Macif
    )
    return mensualité_max_pde


def calcule_mensualité_max_lvo(
        w_mensuel_lvo_date_achat=select_w_mensuel_lvo_date_achat,
        tx_max_endettement=TAUX_MAX_ENDETTEMENT
):
    mensualité_max_lvo = tx_max_endettement * w_mensuel_lvo_date_achat
    return mensualité_max_lvo


mensualité_max_lvo = calcule_mensualité_max_lvo()
mensualité_max_pde = calcule_mensualité_max_pde()
mensualité_maximale = mensualité_max_pde + mensualité_max_lvo

st.markdown('_Mis à jour le 05/04/2026_')

age_lisa, age_pierre = select_date_achat.year - 1998 - 1, select_date_achat.year - 1993 - 1
st.markdown(
    f"Lisa aura {age_lisa} ans, Pierre aura {age_pierre} ans."
)

mois_depuis_achat = (années_depuis_achat * 12)
pct_remboursé = mois_depuis_achat / 240
if select_avec_vente_appartement:
    phrase = (
        f"L'appartement de Cachan sera remboursé à {pct_remboursé:.0%} "
        f"depuis {années_depuis_achat:.2} années ({int(mois_depuis_achat)} / 240 mensualités) :\n"
        f"* En tenant compte d'une inflation annuelle de {inflation_annuelle_cachan:.2%} "
        f"les {INFLATION_SUR_NB_YEARS} dernières années à Cachan, le prix de revente est estimé "
        f"à {sep_milliers(prix_estimé_revente)} €.\n"
        f"* Le CRD au {select_date_achat.strftime('%d/%m/%Y')} sera de {sep_milliers(CRD)} €.\n"
        f"La revente de l'appartement apportera donc {sep_milliers(solde_revente)} €."
    )
    st.markdown(phrase)

st.markdown(
    f'Notre apport sera de {sep_milliers(montant_total_qui_sera_apporté)} €, '
    f'dont {sep_milliers(apport_qui_sera_apporté_lvo)} € pour Lisa '
    f'et {sep_milliers(apport_qui_sera_apporté_pde)} € pour Pierre.'
)

mensualité_plafond_pde_PEL = curseur_PEL * mensualité_max_pde
mensualité_max_pde_prêt_principal = (1 - curseur_PEL) * mensualité_max_pde

if est_PEL_intéressant:
    (
        durée_du_prêt_PEL, mt_prêt_PEL,
        mensualité_PEL, intérêts_acquis_utilisés_PEL
    ) = get_mt_max_prêt_PEL(
        barême,
        mt_intérêts_acquis_PEL=select_mt_intérêts_acquis_pel,
        mensualité_plafond=mensualité_plafond_pde_PEL
    )

mt_prêt_principal_pde = get_mt_emprunt_max(
    mensualité_max=mensualité_max_pde_prêt_principal,
    tx_nominal=tx_nominal,
    nb_mois=select_nb_années_pr_rembourser * 12
)
mt_prêt_principal_lvo = get_mt_emprunt_max(
    mensualité_max=mensualité_max_lvo,
    tx_nominal=tx_nominal,
    nb_mois=select_nb_années_pr_rembourser * 12
)
mt_prêt_principal = mt_prêt_principal_pde + mt_prêt_principal_lvo
mt_emprunt_max = mt_prêt_principal + mt_prêt_PEL
mensualités_prêt_principal = mensualité_max_pde_prêt_principal + mensualité_max_lvo

phrase = (
    'Mensualité maximale supportable par Lisa et Pierre : '
    f'{sep_milliers(mensualité_maximale)} €, '
    f'dont {sep_milliers(mensualité_max_pde)} € pour Pierre et '
    f'{sep_milliers(mensualité_max_lvo)} € pour Lisa.\n'
    f'Cette mensualité, adossée à un taux nominal de {tx_nominal:.2%}, '
    f"permet d'emprunter au maximum {sep_milliers(mt_emprunt_max)} € "
    f'sur {select_nb_années_pr_rembourser} ans.'
)
st.markdown(phrase)

if est_PEL_intéressant:
    st.markdown(
        phrase +
        f'\n* {sep_milliers(mt_prêt_PEL)} € '
        f'avec le PEL (sur {durée_du_prêt_PEL} ans, '
        f'avec des mensualités de {mensualité_PEL} € et en utilisant '
        f"{sep_milliers(intérêts_acquis_utilisés_PEL)} € d'intérêts acquis)"
        f'\n* {sep_milliers(mt_prêt_principal)} € '
        f'avec le prêt principal (sur {select_nb_années_pr_rembourser} ans '
        f'avec des mensualités de {sep_milliers(mensualités_prêt_principal)} €)'
    )

budget = montant_total_qui_sera_apporté + mt_emprunt_max

st.markdown(f"Notre budget total d'achat sera donc de {sep_milliers(budget)} €.")

st.markdown("Attention, il faut prendre en compte :")
lieu_to_inflation = (
    lieu_to_inflation_appart if select_appart_ou_maison == 'Appartement'
    else lieu_to_inflation_maison
)
inflation_par_an_les_x_dernières_années = get_inflation_annuelle(
    inflation_cum=lieu_to_inflation[select_ville],
    nb_years_cum=INFLATION_SUR_NB_YEARS
)
inflation_temps_restant_avant_achat = (
    (1 + inflation_par_an_les_x_dernières_années) ** nb_années_restantes_avant_achat
)
budget = round(budget / inflation_temps_restant_avant_achat)
url_meilleurs_agents = lieu_to_url_meilleurs_agents[select_ville]
st.markdown(
    f"* [L'inflation](https://www.meilleursagents.com/prix-immobilier/{url_meilleurs_agents}/)"
    f' ({lieu_to_inflation[select_ville]:.2%} en {INFLATION_SUR_NB_YEARS} ans à {select_ville}, '
    f'soit {inflation_par_an_les_x_dernières_années:.2%} par an, '
    f"soit {inflation_temps_restant_avant_achat - 1:.2%} d'ici les "
    f"{nb_années_restantes_avant_achat:.0f} ans avant l'achat) : reste {sep_milliers(budget)} €"
)

coût_crédit_principal = (
    mensualités_prêt_principal * 12 * select_nb_années_pr_rembourser - mt_prêt_principal
)
coût_crédit_PEL = mensualité_PEL * 12 * durée_du_prêt_PEL - mt_prêt_PEL
coût_crédit = coût_crédit_principal + coût_crédit_PEL
budget -= coût_crédit
if select_avec_crédit_BNP:
    prefix = (
        "* [Le coût du crédit ]"
        "(https://www.meilleurtaux.com/credit-immobilier/barometre-des-taux.html)"
    )
else:
    prefix = '* Le coût du crédit '
st.markdown(
    prefix + f"(hors assurance) : {sep_milliers(coût_crédit)} €, "
    f"reste {sep_milliers(budget)} €. Détail :\n"
    f"\t - {sep_milliers(coût_crédit_principal)} € "
    "d'intérêts à rembourser au titre du crédit principal\n"
    f"\t - {sep_milliers(coût_crédit_PEL)} € "
    "d'intérêts à rembourser au titre du crédit PEL"
)

# mensualité d'assurance / mensualité du crédit
tx_assurance_actuelle = 16.07 / MONTANT_REMBOURSÉ_PAR_MOIS
coût_assurance = tx_assurance_actuelle * mt_emprunt_max
budget -= coût_assurance
st.markdown(f"* Le coût de l'assurance emprunteur : reste {sep_milliers(budget)} €")

frais_de_notaire = 0.075 if select_neuf_ancien == 'Ancien' else 0.03
frais_de_notaire *= budget
budget -= frais_de_notaire
st.markdown(f"* Les frais de notaire : reste {sep_milliers(budget)} €")

if select_avec_vente_appartement:
    budget -= (select_tx_frais_agence * prix_estimé_revente)
    st.markdown(
        "* Les [frais d'agence]"
        "(https://www.human-immobilier.fr/content/pdf/bareme_honoraires_human_immobilier.pdf) "
        "sur la revente de l'appartement de Cachan : "
        f'reste {sep_milliers(budget)} €'
    )

if not select_remb_anticipé_gratuit:
    budget -= indemnités_de_remb_par_anticipation
    st.markdown(
        "* Les indemnités de remboursement par anticipation : "
        f'reste {sep_milliers(budget)} €'
    )

budget -= 1000
st.markdown(f'* Les frais de dossier bancaire : reste {sep_milliers(budget)} €')

st.markdown(f'**➜ Soit un prix final maximum de : {sep_milliers(budget)} €**')
st.markdown('-' * 3)


st.markdown(
    'Pour être exhaustive, cette simulation devrait aussi tenir compte '
    'des gros changements sur nos finances :\n'
    '* Impact négatif : un enfant, un mariage, des voyages, un licenciement, etc.\n'
    '* Impact positif : un héritage, une donation, ~les JO 2024~, etc.'
)
st.markdown(
    f'Une marge de sécurité est conservée par Lisa à hauteur de {sep_milliers(SECURITE_LISA)} €.'
)

st.markdown(
    f"""
    Cette simulation ne tient pas compte :
    * pour l'estimation du prix de revente de l'appartement cachanais : 
        * des travaux de rénovation qui ont été menés
        * de l'amélioration du DPE lié au remplacement de chaudière, [au changement de mode de calcul](https://www.economie.gouv.fr/actualites/un-nouveau-dpe-au-1er-janvier-2026-pour-favoriser-le-chauffage-electrique), à la pose de robinets thermostatiques 
        * du ravalement
    * des 30 % de réduction sur l'assurance emprunteur,
    * des éventuels frais de courtage,
    * des éventuels frais de tenue de compte en cas d'ouverture de compte dans une banque,
    * des éventuels frais de garanties (hypothèque ou cautionnement),
    * d'une éventuelle renégociation de taux ultérieure,
    * de l'[impôt sur la plus-value immobilière](https://www.service-public.fr/particuliers/vosdroits/F10864) en cas d'achat d'une résidence secondaire (TODO)

    Hypothèses prises :
    * Pour prédire l'inflation, on a estimé l'inflation moyenne dans la ville
    sur les {INFLATION_SUR_NB_YEARS} dernières années, et projeté ce taux d'inflation sur le temps restant avant achat.
    * En cas de revente de l'appartement cachanais, on suppose que la vente a lieu en même temps que
    l'achat du futur logement.
    """
)

# TODO :
# refactoring
# vf que pour un euro d'emprunt supplémentaire, ça passe plus (mensualité > mensualité max)
# compte à terme : https://placement.meilleurtaux.com/assurance-vie/actualites/2024-avril/voici-le-meilleur-compte-a-terme-en-2024.html
# Y a-t-il une assurance du PEL ?
