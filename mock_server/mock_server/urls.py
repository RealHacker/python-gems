from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    # The web page for the SPA                       
    url(r'^mock/$', 'mock_server.views.index', name='home'),
    # Global settings for state / proxy
    url(r'^mock/states/$', 'mock_server.views.states', name='states'),
    url(r'^mock/proxy/$', 'mock_server.views.proxy', name='proxy'),
    # URL settings   
    url(r'^mock/urls/$', 'mock_server.views.urls'),
    url(r'^mock/conditions/$', 'mock_server.views.conditions'),
    url(r'^mock/responses/$', 'mock_server.views.responses'),
    url(r'^.*$', 'mock_server.views.urlhandler'),
)

