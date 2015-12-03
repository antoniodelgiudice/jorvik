from django.core.paginator import Paginator
from django.shortcuts import redirect

from anagrafica.models import Appartenenza, Persona
from anagrafica.permessi.costanti import GESTIONE_SOCI
from autenticazione.funzioni import pagina_privata
from base.errori import errore_generico
from base.files import Excel, FoglioExcel
from ufficio_soci.elenchi import ElencoSoci
from ufficio_soci.forms import ModuloCreazioneEstensione


@pagina_privata(permessi=(GESTIONE_SOCI,))
def us(request, me):
    """
    Ritorna la home page per la gestione dei soci.
    """

    sedi = me.oggetti_permesso(GESTIONE_SOCI).espandi()

    contesto = {
        "sedi": sedi,
    }

    return 'us.html', contesto


@pagina_privata(permessi=(GESTIONE_SOCI,))
def us_estensione(request, me):
    """
    Vista per la creazione di una nuova estensione da ufficio soci.
    """

    sedi = me.oggetti_permesso(GESTIONE_SOCI).espandi()  # es. per controllare che il volontario sia appartente attualmente
                                                         #     ad una delle sedi che gestisco io

    modulo = ModuloCreazioneEstensione(request.POST or None)

    # qui dovrebbe salvare...

    contesto = {
        "sedi": sedi,
        "modulo": modulo,
    }

    return 'us_estensione.html', contesto


@pagina_privata
def us_elenco(request, me, elenco_id=None, pagina=1):

    pagina = int(pagina)
    if pagina < 0:
        pagina = 1

    try:  # Prova a ottenere l'elenco dalla sessione.
        elenco = request.session["elenco_%s" % (elenco_id,)]

    except IndexError:  # Se l'elenco non e' piu' in sessione, potrebbe essere scaduto.
        return errore_generico(request, me, titolo="Sessione scaduta",
                               messaggio="Ricarica la pagina.",
                               torna_url=request.path, torna_titolo="Riprova")

    modulo = None

    if elenco.modulo():  # Se l'elenco richiede un modulo

        try:  # Prova a recuperare il modulo riempito
            modulo = request.session["elenco_modulo_%s" % (elenco_id,)]

        except IndexError:  # Se fallisce, il modulo non e' stato ancora compilato
            return redirect("/us/elenco/%s/modulo/" % (elenco_id,))

        if not modulo.is_valid():  # Se il modulo non e' valido, qualcosa e' andato storto
            return redirect("/us/elenco/%s/modulo/" % (elenco_id,))  # Prova nuovamente?

    pagina_precedente = "/us/elenco/%s/%d/" % (elenco_id, pagina-1)
    pagina_successiva = "/us/elenco/%s/%d/" % (elenco_id, pagina+1)
    download_url = "/us/elenco/%s/download/" % (elenco_id,)
    messaggio_url = "/us/elenco/%s/messaggio/" % (elenco_id,)

    p = Paginator(
        elenco.ordina(
            elenco.risultati(modulo=modulo)
        ), 15)  # Pagina (num risultati per pagina)
    pg = p.page(pagina)

    contesto = {
        'pagina': pagina,
        'pagine': p.num_pages,
        'totale': p.count,
        'risultati': pg.object_list,
        'ha_precedente': pg.has_previous(),
        'ha_successivo': pg.has_next(),
        'pagina_precedente': pagina_precedente,
        'pagina_successiva': pagina_successiva,
        'elenco_id': elenco_id,
        'download_url': download_url,
        'messaggio_url': messaggio_url,
    }

    return elenco.template(), contesto

# TODO elenco_modulo

@pagina_privata
def us_elenco_download(request, me, elenco_id):

    try:  # Prova a ottenere l'elenco dalla sessione.
        elenco = request.session["elenco_%s" % (elenco_id,)]

    except IndexError:  # Se l'elenco non e' piu' in sessione, potrebbe essere scaduto.
        raise ValueError("Elenco non presente in sessione.")

    modulo = None

    if elenco.modulo():  # Se l'elenco richiede un modulo

        try:  # Prova a recuperare il modulo riempito
            modulo = request.session["elenco_modulo_%s" % (elenco_id,)]

        except IndexError:  # Se fallisce, il modulo non e' stato ancora compilato
            return redirect("/us/elenco/%s/modulo/" % (elenco_id,))

        if not modulo.is_valid():  # Se il modulo non e' valido, qualcosa e' andato storto
            return redirect("/us/elenco/%s/modulo/" % (elenco_id,))  # Prova nuovamente?

    # Ottiene elenco
    persone = elenco.ordina(elenco.risultati(modulo=modulo))

    # Crea nuovo excel
    excel = Excel(oggetto=me)

    # Ottiene intestazione e funzioni colonne
    intestazione = [x[0] for x in elenco.excel_colonne()]
    colonne = [x[1] for x in elenco.excel_colonne()]
    fogli = {}

    for persona in persone:
        foglio = elenco.excel_foglio(persona)
        foglio_key = foglio.lower().strip()
        if foglio_key not in [x.lower() for x in fogli.keys()]:
            fogli.update({
                foglio_key: FoglioExcel(foglio, intestazione)
            })

        persona_colonne = [y if y is not None else "" for y in [x(persona) for x in colonne]]
        fogli[foglio_key].aggiungi_riga(
            *persona_colonne
        )

    excel.fogli = fogli.values()
    excel.genera_e_salva("Elenco.xlsx")
    return redirect(excel.download_url)


@pagina_privata(permessi=(GESTIONE_SOCI,))
def us_elenco_soci(request, me):

    elenco = ElencoSoci(me.oggetti_permesso(GESTIONE_SOCI))

    contesto = {
        "elenco": elenco
    }

    return 'us_elenco_soci.html', contesto