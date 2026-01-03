from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .forms import CustomUserRegistrationForm, CustomUserLoginForm, UserProfileForm
from .models import CustomUser
from notifications.models import Notification

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.save()
            
            # Send welcome email
            send_welcome_email(user)
            
            # Create welcome notification
            Notification.objects.create(
                user=user,
                notification_type='welcome',
                title='Welcome to CheersMe!',
                message=f'Hi {user.first_name}, welcome to CheersMe! Discover amazing events around you.',
            )
            
            messages.success(request, 'Registration successful! Please check your email to verify your account.')
            return redirect('accounts:login')
    else:
        form = CustomUserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def send_welcome_email(user):
    subject = 'Welcome to CheersMe!'
    html_message = render_to_string('emails/welcome_email.html', {
        'user': user,
        'site_name': 'CheersMe',
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email
    
    try:
        send_mail(subject, plain_message, from_email, [to], html_message=html_message)
    except Exception as e:
        print(f"Error sending welcome email: {e}")

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
    else:
        form = CustomUserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('accounts:register')
    
    return render(request, 'accounts/delete_account.html')