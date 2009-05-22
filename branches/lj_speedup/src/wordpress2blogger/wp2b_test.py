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

import glob
import os.path
import StringIO
import unittest
import wp2b
import xml.dom.minidom

class TestWordpress2Blogger(unittest.TestCase):

  def setUp(self):
    self.translator = wp2b.Wordpress2Blogger()

    # Read the test data
    testDir = os.path.join(os.path.dirname(os.path.abspath(wp2b.__file__)),
                           'testdata')
    self.input_files = glob.glob('%s/wordpress.*.xml' % testDir)
    self.golden_files = glob.glob('%s/blogger.goldenfile.*.xml' % testDir)

  def assertDocumentsEqual(self, expected, output):
    expected_lines = expected.split('\n')
    output_lines = output.split('\n')
    #self.assertEquals(len(expected_lines), len(output_lines),
    #                  'Documents have different number of lines: %d != %d' %
    #                  (len(expected_lines), len(output_lines)))

    for line_num in xrange(len(expected_lines)):
      expected = expected_lines[line_num].strip()
      output = output_lines[line_num].strip()
      self.assertEquals(expected, output,
                        'Documents differ at line %d: "%s" != "%s"' %
                        (line_num + 1, expected, output))

  def testFullInputOutput(self):
    for i in xrange(len(self.golden_files)):
      expected_file = open(self.golden_files[i])
      input_file = open(self.input_files[i])
      output_file = StringIO.StringIO()

      self.translator.Translate(input_file.read(), output_file)
      output_dom = xml.dom.minidom.parseString(output_file.getvalue())
      self.assertDocumentsEqual(expected_file.read(),
                                output_dom.toprettyxml(encoding="UTF-8"))



def generateGoldenfiles():
  testDir = os.path.join(os.path.dirname(os.path.abspath(wp2b.__file__)),
                           'testdata')
  input_files = glob.glob('%s/wordpress.*.xml' % testDir)
  golden_files = glob.glob('%s/blogger.goldenfile.*.xml' % testDir)
  for i in xrange(len(golden_files)):
    print input_files[1]
    input_file = open(input_files[i])
    output_file = open(golden_files[i], "w")

    translator = wp2b.Wordpress2Blogger()
    translator.Translate(input_file.read(), output_file)
    output_file.close()

if __name__ == '__main__':
  import sys
  
  if len(sys.argv) > 1 and sys.argv[1] == '--generate':
    generateGoldenfiles()
  else:
    unittest.main()
