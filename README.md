# MailSender
Auto mail sender for marketing/communication

### Usage

MailSender requires a Python compatible environment

Clone the repository from GitHub

```sh
$ git clone "https://github.com/EnzoDelahaye/MailSender/"
$ cd CNA_groundhog_2019
```

Then, setup your GMAIL API by following instructions on: https://developers.google.com/gmail/api/quickstart/python

Download client configuration file, copy 'credentials.json' at the root of MailSender

Install Google client Library

```sh
$ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
If you are using Python3 make instead :
```sh
$ pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Edit the file 'settings.txt' with your own values

THEN, Launch the script by

```sh
$ ./MailSender
```
or
```sh
$ Python3 MailSender
```

More help for usage

```sh
$ ./MailSender -h
```
