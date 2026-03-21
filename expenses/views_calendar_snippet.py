import calendar
from datetime import date, datetime

from django.db.models import Sum
from django.views.generic import TemplateView


class CalendarView(TemplateView):
    template_name = 'expenses/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.now()
        
        # Get year/month from URL or default to current
        year = self.kwargs.get('year', today.year)
        month = self.kwargs.get('month', today.month)
        
        # Validate year/month
        try:
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            year = today.year
            month = today.month

        # Calculate prev/next month for navigation
        if month == 1:
            prev_month_date = date(year - 1, 12, 1)
        else:
            prev_month_date = date(year, month - 1, 1)
            
        if month == 12:
            next_month_date = date(year + 1, 1, 1)
        else:
            next_month_date = date(year, month + 1, 1)

        # Get Expense and Income Data for the month
        expenses = Expense.objects.filter(
            user=self.request.user,
            date__year=year,
            date__month=month
        ).values('date').annotate(total=Sum('base_amount'))
        
        incomes = Income.objects.filter(
            user=self.request.user,
            date__year=year,
            date__month=month
        ).values('date').annotate(total=Sum('base_amount'))
        
        # Map data for easy lookup by day
        # Keys are integers (day of month)
        expense_map = {e['date'].day: e['total'] for e in expenses}
        income_map = {i['date'].day: i['total'] for i in incomes}
        
        # Build Calendar Grid
        cal = calendar.Calendar(firstweekday=6) # Start on Sunday
        month_days = cal.monthdayscalendar(year, month)
        
        # Transform into a list of weeks, where each day is an object
        calendar_data = []
        for week in month_days:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append(None) # Empty slot
                else:
                    week_data.append({
                        'day': day,
                        'income': income_map.get(day, 0),
                        'expense': expense_map.get(day, 0),
                    })
            calendar_data.append(week_data)
        
        context['calendar_data'] = calendar_data
        context['current_year'] = year
        context['current_month'] = month
        context['month_name'] = calendar.month_name[month]
        context['prev_year'] = prev_month_date.year
        context['prev_month'] = prev_month_date.month
        context['next_year'] = next_month_date.year
        context['next_month'] = next_month_date.month
        
        return context
