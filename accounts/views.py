from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from .forms import UserSignupForm, UserLoginForm


@never_cache
def signup_view(request):
    """
    User registration view.
    """
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to YouTube Downloader.')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Always create a fresh form instance for GET requests
        form = UserSignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


@never_cache
def login_view(request):
    """
    User login view.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.email}!')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Please enter a correct email and password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def dashboard_view(request):
    """
    User dashboard view - shows "You are signed in" page.
    """
    return render(request, 'accounts/dashboard.html', {'user': request.user})


@require_http_methods(["POST"])
def logout_view(request):
    """
    User logout view.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:logged_out')


def logged_out_view(request):
    """
    Logged out confirmation page.
    """
    return render(request, 'accounts/logged_out.html')
