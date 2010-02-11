#!/usr/bin/env python

# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cgi
import xmlrpclib

import gdata.service
import gdata.urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import traceback
import lj2b
import wsgiref.handlers

__author__ = 'JJ Lueck (jlueck@gmail.com)'

# Use urlfetch instead of httplib
gdata.service.http_request_handler = gdata.urlfetch


class FetchAndTransformPage(webapp.RequestHandler):
  def post(self):
    # All input/output will be in UTF-8
    self.response.charset = 'utf8'

    # Run the blogger import processor
    translator = lj2b.LiveJournal2Blogger(self.request.get('username'),
                                          self.request.get('password'))
    try:
      translator.Translate(self.response.out)
      self.response.content_type = 'application/atom+xml'
      self.response.headers['Content-Disposition'] = \
          'attachment;filename=blogger-export.xml'
    except xmlrpclib.Fault, f:
      # Provide just the fault message, ususally "password incorrect"
      self.response.content_type = 'text/html'
      self.response.out.write(cgi.escape(str(f)))
    except:
      # Just provide an error message to the user.
      self.response.content_type = 'text/html'
      self.response.out.write("Error encountered during conversion.<br/><br/>")
      exc = traceback.format_exc()
      self.response.out.write(cgi.escape(exc).replace('\n', '<br/>'))

application = webapp.WSGIApplication([('/lj2b/', FetchAndTransformPage)],
                                     debug=True)

def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
