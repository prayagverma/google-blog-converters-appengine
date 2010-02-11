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
import gdata.service
import gdata.urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import traceback
import wp2b
import wsgiref.handlers

__author__ = 'JJ Lueck (jlueck@gmail.com)'

# Use urlfetch instead of httplib
gdata.service.http_request_handler = gdata.urlfetch


class TransformPage(webapp.RequestHandler):
  def post(self):
    # All input/output will be in UTF-8
    self.response.charset = 'utf8'

    # Parse the mulit-part form-data part out of the POST
    input = self.request.get('input-file', allow_multiple=False)

    # Run the blogger import processor
    translator = wp2b.Wordpress2Blogger()
    try:
      translator.Translate(input, self.response.out)
      self.response.content_type = 'application/atom+xml'
      self.response.headers['Content-Disposition'] = \
         'attachment;filename=blogger-export.xml'
    except RuntimeWarning, e:
      # Just provide an error message to the user.
      self.response.content_type = 'text/plain'
      self.response.out.write("Error encountered during conversion.<br/><br/>")
      self.response.out.write(str(e))
    except:
      self.response.content_type = 'text/plain'
      self.response.out.write("Error encountered during conversion.<br/><br/>")
      self.response.out.write(traceback.format_exc().replace('\n', '<br/>'))

application = webapp.WSGIApplication([('/wp2b/', TransformPage)],
                                     debug=True)

def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
