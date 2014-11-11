#!/usr/bin/env python

import httplib2
import argparse
import base64
import email
from parse import parse
import time
from collections import defaultdict
import sys

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser


def setup():

  parser = argparse.ArgumentParser(parents=[argparser])
  flags = parser.parse_args()

  # Path to the client_secret.json file downloaded from the Developer Console
  CLIENT_SECRET_FILE = 'client_secret.json'

  # Check https://developers.google.com/gmail/api/auth/scopes for all available scopes
  OAUTH_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'

  # Location of the credentials storage file
  STORAGE = Storage('../google/phonestats.storage')

  # Start the OAuth flow to retrieve credentials
  flow = flow_from_clientsecrets(CLIENT_SECRET_FILE, scope=OAUTH_SCOPE)
  http = httplib2.Http()

  # Try to retrieve credentials from storage or run the flow to generate them
  credentials = STORAGE.get()
  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, STORAGE, flags, http=http)

  # Authorize the httplib2.Http object with our credentials
  http = credentials.authorize(http)

  # Build the Gmail service from discovery
  gmail_service = build('gmail', 'v1', http=http)

  return gmail_service

def ListMessagesMatchingQuery(service, user_id, query=''):
  """List all Messages of the user's mailbox matching the query.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    query: String used to filter messages returned.
    Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

  Returns:
    List of Messages that match the criteria of the query. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate ID to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               q=query).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = service.users().messages().list(userId=user_id, q=query,
                                         pageToken=page_token).execute()
      messages.extend(response['messages'])

    return messages
  except errors.HttpError, error:
    print 'An error occurred: %s' % error

def HandleMessage(service, user_id, msgref):
  account = ''
  date = ''
  balance = 0
  minutes = 0
  texts = 0
  data = 0

  id = msgref['id']
  message = service.users().messages().get(userId=user_id, id=id, format='raw').execute()
  msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
  mime_msg = email.message_from_string(msg_str)
  date_struct = email.utils.parsedate(mime_msg['Date'])
  date = time.strftime("%x", date_struct)
  #print 'Id %s on %s: %s' % (id, date, message['snippet'])
  body = mime_msg.get_payload()
  for line in body.splitlines():
    #print line
    match = parse("Your Phone Number:{:^}", line)
    if match:
      #print ">>>> Number: %s" % match[0]
      account = match[0]
      continue
    match = parse("Your Current Balance:{:^f}", line)
    if match:
      #print ">>>> Balance: %s" % match[0]
      balance = match[0]
      continue
    match = parse("Remaining Minutes:{:^d} - LEFT{}", line)
    if match:
      #print ">>>> Minutes: %s" % match[0]
      minutes = match[0]
      continue
    match = parse("Remaining Text Messages:{:^d} - LEFT{}", line)
    if match:
      #print ">>>> Texts: %s" % match[0]
      texts = match[0]
      continue
    match = parse("Remaining Data in MB:{:^f}MB - LEFT{}", line)
    if match:
      #print ">>>> Data: %s" % match[0]
      data = match[0]
  return (account, date, balance, minutes, texts, data)

gmail_service = setup()

# Retrieve a page of threads
#threads = gmail_service.users().threads().list(userId='me').execute()

# Print ID for each thread
#if threads['threads']:
#  for thread in threads['threads']:
#    print 'Thread ID: %s' % (thread['id'])

accounts = defaultdict(list)

messages = ListMessagesMatchingQuery(gmail_service, 'me', 'subject:"Weekly Status: "')

print 'Got %d messages' % (len(messages))

for msgref in messages:
  (account, date, balance, minutes, texts, data) = HandleMessage(gmail_service, 'me', msgref)
  #print "(%s) on %s: bal=%f, min=%d, texts=%d, data=%f" % (account, date, balance, minutes, texts, data)
  accounts[account].append((date, balance, minutes, texts, data))
  print ".",
  sys.stdout.flush()

print ""

print accounts
