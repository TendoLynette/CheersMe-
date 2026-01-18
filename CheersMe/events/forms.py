from django import forms
from django.utils.text import slugify
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, Div
from .models import Event, EventCategory, EventReview


class EventForm(forms.ModelForm):
    """
    Form for creating and editing events
    """
    
    class Meta:
        model = Event
        fields = [
            'title', 'category', 'description', 'featured_image',
            'venue_name', 'address', 'city', 'latitude', 'longitude',
            'start_date', 'start_time', 'end_date', 'end_time',
            'is_free', 'base_price', 'total_capacity',
            'has_food', 'food_deals', 'has_drinks', 'drink_deals',
            'status', 'is_featured', 'meta_description'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event Title'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your event...'
            }),
            'featured_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'venue_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Venue Name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Latitude (e.g., 0.3476)'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Longitude (e.g., 32.5825)'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'total_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum attendees'
            }),
            'has_food': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'food_deals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe food offerings...'
            }),
            'has_drinks': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'drink_deals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe drink specials...'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO description (160 characters max)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make some fields not required
        self.fields['food_deals'].required = False
        self.fields['drink_deals'].required = False
        self.fields['meta_description'].required = False
        
        # Add help text
        self.fields['latitude'].help_text = 'You can get coordinates from Google Maps'
        self.fields['longitude'].help_text = 'Right-click on Google Maps and select coordinates'
        self.fields['is_free'].help_text = 'Check if this is a free event'
        self.fields['is_featured'].help_text = 'Featured events appear on homepage'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate dates
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('End date must be after start date.')
            
            if start_date == end_date and start_time and end_time:
                if end_time <= start_time:
                    raise forms.ValidationError('End time must be after start time.')
        
        # Validate price
        is_free = cleaned_data.get('is_free')
        base_price = cleaned_data.get('base_price')
        
        if not is_free and (not base_price or base_price <= 0):
            raise forms.ValidationError('Please set a price or mark event as free.')
        
        if is_free:
            cleaned_data['base_price'] = 0
        
        # Validate capacity
        total_capacity = cleaned_data.get('total_capacity')
        if total_capacity and total_capacity < 1:
            raise forms.ValidationError('Total capacity must be at least 1.')
        
        return cleaned_data
    
    def save(self, commit=True):
        event = super().save(commit=False)
        
        # Auto-generate slug if not set
        if not event.slug:
            event.slug = slugify(event.title)
        
        # Set remaining capacity for new events
        if not event.pk:
            event.remaining_capacity = event.total_capacity
        
        if commit:
            event.save()
        
        return event


class EventReviewForm(forms.ModelForm):
    """
    Form for submitting event reviews
    """
    
    class Meta:
        model = EventReview
        fields = ['rating', 'comment']
        
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (5, '⭐⭐⭐⭐⭐ Excellent'),
                (4, '⭐⭐⭐⭐ Good'),
                (3, '⭐⭐⭐ Average'),
                (2, '⭐⭐ Below Average'),
                (1, '⭐ Poor'),
            ]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].required = False
        self.fields['comment'].help_text = 'Optional: Tell others about your experience'


class EventSearchForm(forms.Form):
    """
    Form for searching and filtering events
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search events, venues, organizers...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=EventCategory.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    price_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Price',
            'step': '0.01'
        })
    )
    
    price_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Price',
            'step': '0.01'
        })
    )
    
    is_free = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Free Events Only'
    )
    
    has_food = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Has Food'
    )
    
    has_drinks = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Has Drinks'
    )


class EventFilterForm(forms.Form):
    """
    Simple filter form for event lists
    """
    SORT_CHOICES = [
        ('date_asc', 'Date (Earliest First)'),
        ('date_desc', 'Date (Latest First)'),
        ('price_asc', 'Price (Low to High)'),
        ('price_desc', 'Price (High to Low)'),
        ('popular', 'Most Popular'),
        ('rating', 'Highest Rated'),
    ]
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=EventCategory.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )


class QuickReviewForm(forms.Form):
    """
    Quick review form with just rating
    """
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput()
    )
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating not in [1, 2, 3, 4, 5]:
            raise forms.ValidationError('Rating must be between 1 and 5.')
        return rating