from google.appengine.ext import vendor
import os

# Add any libraries installed in the "lib" folder.
ABS = True
if ABS:
	vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))
else:
	vendor.add('lib')

def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)
    return app