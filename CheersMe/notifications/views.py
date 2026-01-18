from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def notifications_list_view(request):
    return render(request, 'notifications/list.html')


from django.shortcuts import redirect, get_object_or_404
from .models import Notification

def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save()
    return redirect('notifications:list')


from django.shortcuts import redirect
from .models import Notification

def mark_all_as_read(request):
    Notification.objects.update(is_read=True)
    return redirect('notifications:list')
