from django.shortcuts import render, get_object_or_404
from .models import Theater
from bookings.models import ShowSchedule

def theater_list_view(request):
    city = request.GET.get('city')
    theaters = Theater.objects.filter(status=Theater.Status.ACTIVE)
    if city:
        theaters = theaters.filter(city__iexact=city)

    cities = Theater.objects.filter(status=Theater.Status.ACTIVE).values_list('city', flat=True).distinct()

    return render(request, 'theaters/list.html', {
        'theaters': theaters,
        'cities': cities,
        'selected_city': city,
    })

def theater_detail_view(request, theater_id):
    theater = get_object_or_404(Theater, pk=theater_id)
    shows = ShowSchedule.objects.filter(
        theater=theater,
        status__in=[ShowSchedule.Status.OPEN, ShowSchedule.Status.UPCOMING]
    ).select_related('movie', 'screen').order_by('show_date', 'start_time')

    return render(request, 'theaters/detail.html', {
        'theater': theater,
        'shows': shows,
    })
