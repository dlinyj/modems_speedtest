import smtplib                                              # Importiruem biblioteku po rabote s SMTP
import os                                                   # Funkcii dlja raboty s operacionnoj sistemoj, ne zavisjashhie ot ispol'zuemoj operacionnoj sistemy
import ssl

# Dobavljaem neobhodimye podklassy - MIME-tipy
import mimetypes                                            # Import klassa dlja obrabotki neizvestnyh MIME-tipov, bazirujushhihsja na rasshirenii fajla
from email import encoders                                  # Importiruem jenkoder
from email.mime.base import MIMEBase                        # Obshhij tip
from email.mime.text import MIMEText                        # Tekst/HTML
from email.mime.image import MIMEImage                      # Izobrazhenija
from email.mime.audio import MIMEAudio                      # Audio
from email.mime.multipart import MIMEMultipart              # Mnogokomponentnyj ob#ekt


def send_email(addr_to, msg_subj, msg_text, files):
    addr_from = "login@yandex.ru"                # Otpravitel'
    password  = "password"                                # Parol'

    msg = MIMEMultipart()                                   # Sozdaem soobshhenie
    msg['From']    = addr_from                              # Adresat
    msg['To']      = addr_to                                # Poluchatel'
    msg['Subject'] = msg_subj                               # Tema soobshhenija

    body = msg_text                                         # Tekst soobshhenija
    msg.attach(MIMEText(body, 'plain'))                     # Dobavljaem v soobshhenie tekst

    process_attachement(msg, files)

    #======== Jetot blok nastraivaetsja dlja kazhdogo pochtovogo provajdera otdel'no ===============================================
    server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)        # Sozdaem ob#ekt SMTP
    #server.starttls()                                      # Nachinaem shifrovannyj obmen po TLS
    #server.set_debuglevel(True)                            # Vkljuchaem rezhim otladki, esli ne nuzhen - mozhno zakommentirovat'
    server.login(addr_from, password)                       # Poluchaem dostup
    server.send_message(msg)                            # Otpravljaem soobshhenie
    server.quit()                                           # Vyhodim
    #==========================================================================================================================

def process_attachement(msg, files):                        # Funkcija po obrabotke spiska, dobavljaemyh k soobshheniju fajlov
    for f in files:
        if os.path.isfile(f):                               # Esli fajl sushhestvuet
            attach_file(msg,f)                              # Dobavljaem fajl k soobshheniju
        elif os.path.exists(f):                             # Esli put' ne fajl i sushhestvuet, znachit - papka
            dir = os.listdir(f)                             # Poluchaem spisok fajlov v papke
            for file in dir:                                # Perebiraem vse fajly i...
                attach_file(msg,f+"/"+file)                 # ...dobavljaem kazhdyj fajl k soobshheniju

def attach_file(msg, filepath):                             # Funkcija po dobavleniju konkretnogo fajla k soobshheniju
    filename = os.path.basename(filepath)                   # Poluchaem tol'ko imja fajla
    ctype, encoding = mimetypes.guess_type(filepath)        # Opredeljaem tip fajla na osnove ego rasshirenija
    if ctype is None or encoding is not None:               # Esli tip fajla ne opredeljaetsja
        ctype = 'application/octet-stream'                  # Budem ispol'zovat' obshhij tip
    maintype, subtype = ctype.split('/', 1)                 # Poluchaem tip i podtip
    if maintype == 'text':                                  # Esli tekstovyj fajl
        with open(filepath) as fp:                          # Otkryvaem fajl dlja chtenija
            file = MIMEText(fp.read(), _subtype=subtype)    # Ispol'zuem tip MIMEText
            fp.close()                                      # Posle ispol'zovanija fajl objazatel'no nuzhno zakryt'
    elif maintype == 'image':                               # Esli izobrazhenie
        with open(filepath, 'rb') as fp:
            file = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
    elif maintype == 'audio':                               # Esli audio
        with open(filepath, 'rb') as fp:
            file = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
    else:                                                   # Neizvestnyj tip fajla
        with open(filepath, 'rb') as fp:
            file = MIMEBase(maintype, subtype)              # Ispol'zuem obshhij MIME-tip
            file.set_payload(fp.read())                     # Dobavljaem soderzhimoe obshhego tipa (poleznuju nagruzku)
            fp.close()
            encoders.encode_base64(file)                    # Soderzhimoe dolzhno kodirovat'sja kak Base64
    file.add_header('Content-Disposition', 'attachment', filename=filename) # Dobavljaem zagolovki
    msg.attach(file)                                        # Prisoedinjaem fajl k soobshheniju
