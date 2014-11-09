#!/usr/bin/env python

import httplib2
import argparse
import base64
import email

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


gmail_service = setup()

# Retrieve a page of threads
#threads = gmail_service.users().threads().list(userId='me').execute()

# Print ID for each thread
#if threads['threads']:
#  for thread in threads['threads']:
#    print 'Thread ID: %s' % (thread['id'])

messages = ListMessagesMatchingQuery(gmail_service, 'me', 'Weekly Status: ')

print 'Got %d messages' % (len(messages))

for msgref in messages:
#  print '%s' % (message['id'])
  id = msgref['id']
  message = gmail_service.users().messages().get(userId='me', id=id, format='raw').execute()
  print 'Id %s: %s' % (id, message['snippet'])
  body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
  print body

