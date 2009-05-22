Welcome to Blog Converters.

This project contains a number of converters to and from different Blog
services.  The code is written in Python with scripts to execute the
conversionseither on the command-line scripts or hosted on Google App Engine.
This projectis open source and distributed under the Apache license.  Please
feel free to add to or modify this source and propose changes or new converters.

This project makes extensive use of the Google GData API.  For notes on
installing python that is suitable for this API, see:

  http://gdata-python-client.googlecode.com/svn/trunk/INSTALL.txt


The directory structure for this project:

  bin/               - Runnable scripts
  lib/               - Project dependencies
    googleappengine/ - External reference to the Google App Engine
                       source.  Useful for running hosted converters.
    gdata/           - Google's Data API for communication to various Google
                       services.
    atom/            - Library for native Atom parsing/creation in Python 
  src/               - Source for the converters
  samples/           - Sample export files for various formats.  
  

There are a number of scripts in the bin/ directory that demonstrate the 
various conversions available.  For instance:

  bin/wordpress2blogger.sh samples/wordpress-sample.wxr

will emit a Blogger export file that can be used to upload the Wordpress blog
contents to Blogger.  Similarly:

  bin/blogger2wordpress.sh samples/blogger-sample.xml

will convert from a Blogger export file to a Wordpress export file.  There also
exist batch files in the bin/ directory for those working in a Windows
environment.

To run a demonstration of a Google App Engine hosted conversion, run the
command:

  bin/run-appengine.sh [-p <port>] blogger2wordpress

or
  
  bin/run-appengine.sh [-p <port>] wordpress2blogger

will execute the hosted version of the converters.  Just direct a browser to
http://localhost:port and you will see a page that takes an export file,
converts the uploaded file and provides a converted file for download.  The
default port with the -p flag is not used is 8080.

Note that these converters are also hosted directly on Google App Engine with
the latest code checked into this projects SVN directory.  The hostname for
these converters uses the same name as the directories found in the src/
directory.  

See:

  http://blogger2wordpress.appspot.com/
  http://wordpress2blogger.appspot.com/
  http://livejournal2blogger.appspot.com/

for examples of these converters hosted on Google App Engine.  Note that there
is a huge caveat to using these hosted services at the moment in that there is 
a limit to the size of a downloaded file on appspot.com of 1 MB of data.  Thus,
these hosted applications should only be used for reference or for the
conversion of small blog export files.

Enjoy!

-JJ. 
jlueck @ gmail.com
 of the
Data Liberation Front 
