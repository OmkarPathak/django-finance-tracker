
import os
import re
from collections import defaultdict

# Simple Rule-Based Keyword Mapping
KEYWORD_MAPPING = {
    'Food': ['food', 'dinner', 'lunch', 'breakfast', 'snack', 'coffee', 'tea', 'cafe', 'restaurant', 'burger', 'pizza', 'zomato', 'swiggy', 'groceries', 'vegetables', 'fruits'],
    'Transport': ['taxi', 'uber', 'ola', 'auto', 'bus', 'train', 'metro', 'flight', 'ticket', 'fuel', 'petrol', 'diesel', 'parking', 'toll'],
    'Shopping': ['amazon', 'flipkart', 'myntra', 'clothes', 'shoes', 'mall', 'store', 'shop', 'electronics', 'gadget'],
    'Bills': ['electricity', 'water', 'gas', 'bill', 'recharge', 'wifi', 'internet', 'broadband', 'phone', 'mobile', 'subscription', 'netflix', 'spotify', 'prime'],
    'Health': ['doctor', 'hospital', 'medicine', 'pharmacy', 'clinic', 'gym', 'fitness', 'workout', 'yoga'],
    'Education': ['book', 'course', 'udemy', 'coursera', 'school', 'college', 'fee', 'tuition', 'stationary'],
    'Entertainment': ['movie', 'cinema', 'theatre', 'game', 'concert', 'show', 'event', 'party', 'pub', 'bar'],
    'Rent': ['rent', 'house', 'maintenance'],
    'Salary': ['salary', 'wage', 'paycheck', 'bonus', 'stipend'],
    'Investment': ['stock', 'mutual fund', 'sip', 'gold', 'fd', 'rd', 'crypto'],
    'Cab': ['cab', 'taxi', 'ola', 'uber', 'auto', 'rental', 'car', 'rapido'],
}

def predict_category_rule_based(description):
    """
    Predicts category based on keywords in the description.
    Returns the probable category or None.
    """
    description = description.lower()
    
    # Normalize description
    words = re.findall(r'\w+', description)
    
    # direct match
    for category, keywords in KEYWORD_MAPPING.items():
        for keyword in keywords:
            if keyword in words or keyword in description:
                # Check for exact word match or substring if useful
                return category
    return None

def predict_category_ai(description, user=None):
    """
    Predicts category using:
    1. Historical Data (User-specific Custom Categories)
    2. Rule-Based Keywords (General)
    3. Generative AI (Gemini) - Fallback
    """
    description = description.strip()
    
    # 0. Check Historical Data (Personalization)
    if user:
        try:
            # Avoid circular import
            from expenses.models import Expense
            from django.db.models import Count
            
            # Simple exact/contains match
            # Find expenses with similar description by this user
            # We look for exact match of description OR description containing the new term (if long enough)
            # For simplicity and speed, let's try fuzzy match or simple "icontains"
            
            # Strategy: Look for existing expenses where description matches fuzzy
            # Limitation: 'icontains' might be too broad. Let's try exact first, then words.
            
            # 1. Exact match (case insensitive)
            exact_match = Expense.objects.filter(user=user, description__iexact=description).values('category').annotate(count=Count('category')).order_by('-count').first()
            if exact_match:
                return exact_match['category']
                
            # 2. Token overlap? Or Starts With?
            # "Uber to work" vs "Uber"
            # If input is "Uber", we want to find "Uber to work" (maybe?) No, other way around.
            # If input is "Uber to work", we match "Uber" rule.
            
            # What if user has "Momos" -> "Street Food" (Custom)
            # Input: "Momos at corner"
            # We check if any previous description was "Momos".
            
            # Let's check for "starts with" matches from history (common for repeated manual entries)
            # actually better: query recent expenses and see if they have common words? Too slow.
            
            # Let's stick to "Similar" = exact match of first few words?
            # Or just rely on the fact that users likely type the same thing.
            
            # Let's try a regex search for the FIRST word if description > 1 word
            words = description.split()
            if len(words) >= 1:
                first_word = words[0]
                if len(first_word) > 3:
                     # Find entries starting with this word
                     similar = Expense.objects.filter(user=user, description__istartswith=first_word).values('category').annotate(count=Count('category')).order_by('-count').first()
                     if similar:
                         return similar['category']

        except Exception as e:
            print(f"Historical Prediction Error: {e}")
            pass

    # 1. Try Rule-Based First (Fastest, Free)
    category = predict_category_rule_based(description)
    if category:
        return category

    # 2. Try Gemini AI (if configured)
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        try:
            # Lazy import to avoid import errors if library not installed
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash') # Use Flash for speed/cost
            
            prompt = f"""
            Classify the following expense description into one of these categories: 
            Food, Transport, Shopping, Bills, Health, Education, Entertainment, Rent, Investment, Other.
            
            Description: "{description}"
            
            Return ONLY the category name.
            """
            
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip()
                
        except Exception as e:
            # Log error or print?
            print(f"Gemini API Error: {e}")
            pass
            
    return None
