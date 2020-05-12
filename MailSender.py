#!/usr/local/bin/python3

import sys
import argparse
import base64
import os
import csv
import time

# mail
import smtplib
import email.utils
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase

script_path = os.path.dirname(os.path.abspath(__file__))

def add_embedded_image_to_related(message_related):
    """ add embedded image
    not typically used because modern email clients don't display by default
    Returns: image cid to use as href, <img src="cid:${image_cid}"/>
    """
    # image_cid looks like <long.random.number@xyz.com>, strip first and last
    # char
    image_cid = email.utils.make_msgid(domain='foo.com')[1:-1]
    with open('attachments/pixabay-stock-art-free-presentation.png', 'rb') as img:
        maintype, subtype = mimetypes.guess_type(img.name)
        message_related.attach(MIMEImage(img.read(), subtype, cid=image_cid))
    return image_cid


def create_message_with_attachment(sender, to, subject, msg_html, msg_plain, attachment_file_list):
    # outer mime wrapper
    message = MIMEMultipart('mixed')

    # supports multiple recipients if separated by ","
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    print("CREATING HTML EMAIL MESSAGE")
    print("From: {}".format(sender))
    print("To: {}".format(to))
    print("Subject: {}".format(subject))

    # text and html versions of message
    message_alt = MIMEMultipart('alternative')
    message_alt.attach(MIMEText(msg_plain, 'plain'))
    message_rel = MIMEMultipart('related')
    message_rel.attach(MIMEText(msg_html, 'html'))
    # we are not adding an embedded 'cid:' image
    #add_embedded_image_to_related(message_rel)

    # on alternative wrapper, add related
    message_alt.attach(message_rel)

    # on outer wrapper, add alternative
    message.attach(message_alt)

    # each attachment
    for attachment_file in (attachment_file_list if attachment_file_list is not None else []):
        print("create_message_with_attachment: file: {}".format(attachment_file))
        content_type, encoding = mimetypes.guess_type(attachment_file)

        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)
        # print("main/sub={}/{}".format(main_type,sub_type))

        msg_att = None
        if main_type == 'text':
            fp = open(attachment_file, 'r')
            msg_att = MIMEText(fp.read(), _subtype=sub_type)
            fp.close()
            # DO NOT encode as base64, sent as text
        elif main_type == 'image':
            fp = open(attachment_file, 'rb')
            msg_att = MIMEImage(fp.read(), _subtype=sub_type)
            fp.close()
            # DO NOT encode as base64, already added as such
        else:
            fp = open(attachment_file, 'rb')
            msg_att = MIMEBase(main_type, sub_type)
            msg_att.set_payload(fp.read())
            fp.close()
            # encode as base64
            email.encoders.encode_base64(msg_att)

        # attach to main message
        filename = os.path.basename(attachment_file)
        msg_att.add_header(
            'Content-Disposition', 'attachment', filename=filename)
        message.attach(msg_att)

    return message


def send_message_via_relay(message, smtp, port, use_tls, smtp_user, smtp_pass, sender, to_csv, debug):
    server = smtplib.SMTP(smtp, port)
    if debug:
        server.set_debuglevel(9)
    server.ehlo()
    if use_tls:
        print("Using TLS for SMTP to {}".format(port))
        server.starttls()
    server.ehlo()
    if smtp_user and smtp_pass:
        print("Supplying credentials for relay: {}".format(smtp_user))
        server.login(smtp_user, smtp_pass)
    text = message.as_string()
    server.sendmail(sender, to_csv.split(','), text)


def send_message_to_google(message, sender):
    """
    Requires local 'credentials.json' for Gmail API
    https://developers.google.com/gmail/api/quickstart/python
    """

    # googleapi oauth
    # put here in the function so that users doing relay don't require install
    import pickle
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = 'https://www.googleapis.com/auth/gmail.send'

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    msg_raw = {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}
    try:
        message = (service.users().messages().send(userId=sender, body=msg_raw).execute())
        print("Message Id: {}".format(message['id']))
        return message
    except Exception as e:
        print("An error occurred: {}".format(e))
        raise e

def main():

    # parse args
    nb_of_line = 0
    with open("settings.txt", "r") as configfile:
        for lines in configfile:
            if nb_of_line == 1 : sender = lines.rstrip('\n')
            if nb_of_line == 4 : to_csv = lines.rstrip('\n')
            if nb_of_line == 7 : dest_file = lines.rstrip('\n')
            if nb_of_line == 10 : subject = lines.rstrip('\n')
            if nb_of_line == 13 : name = lines.rstrip('\n')
            if nb_of_line == 16 : smtp_server = lines.rstrip('\n')
            if nb_of_line == 19 : html_file = lines.rstrip('\n')
            if nb_of_line == 22 : msg_plain = lines.rstrip('\n')
            nb_of_line += 1;
    ap = argparse.ArgumentParser()
    ap.add_argument("--attach", nargs='*',help="variable list of files to attach")

    args = ap.parse_args()
    attachment_file_list = args.attach

    # HTML message, would use mako templating in real scenario
    file_html = open(html_file.rstrip('\n'), "r")
    msg_html = file_html.read()

    # open CSV file and turn it in dictionnary
    currentline = []
    with open(dest_file, "r") as filestream:
        for line in filestream:
            currentline.append(line)
    
    # send message
    if smtp_server == "google.com":
        # looping on each adress & send mail
        no_of_mail = 1
        for addr in currentline:
            if no_of_mail >= 450:
                print("Limit of 450 mail by 24h reached")
                break
            print("*****************\n")
            print("Contact n°" + str(no_of_mail))
            message = create_message_with_attachment(sender, addr, subject, msg_html, msg_plain, attachment_file_list)
            send_message_to_google(message, sender)
            print("*****************\n")
            time.sleep(0.4)
            no_of_mail += 1
    else:
        send_message_via_relay(message, smtp_server, smtp_port, 
                               use_tls, smtp_user, smtp_password, sender, to_csv, debug)


    print("\nSUCCESS: email sent to {}".format(to_csv))


if __name__ == '__main__':
    main()
