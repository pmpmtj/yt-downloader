from django.urls import path
from . import views
from . import cookie_views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logged_out/', views.logged_out_view, name='logged_out'),
    
    # Cookie management
    path('cookies/', cookie_views.cookie_management_view, name='cookie_management'),
    path('cookies/upload/', cookie_views.upload_cookies_view, name='upload_cookies'),
    path('cookies/paste/', cookie_views.paste_cookies_view, name='paste_cookies'),
    path('cookies/delete/', cookie_views.delete_cookies_view, name='delete_cookies'),
    path('api/cookies/', cookie_views.CookieAPIView.as_view(), name='cookie_api'),
]
