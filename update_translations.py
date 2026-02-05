import os
import re

def update_po_file(filepath, translations, complex_replacements=None):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple strings
    for msgid, msgstr in translations.items():
        pattern = f'msgid "{re.escape(msgid)}"\nmsgstr ""'
        replacement = f'msgid "{msgid}"\nmsgstr "{msgstr}"'
        content = re.sub(pattern, replacement, content)
        
    # Complex replacements (exact match for multi-line msgid)
    if complex_replacements:
        for msgid_block, msgstr in complex_replacements.items():
             # pattern matches the msgid block followed by empty msgstr
             # We rely on exact string match of the msgid block from the file
             pattern = msgid_block + '\nmsgstr ""'
             replacement = msgid_block + f'\nmsgstr "{msgstr}"'
             if msgid_block in content:
                 content = content.replace(pattern, replacement)
             else:
                 print(f"Complex pattern not found: {msgid_block[:50]}...")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Common translations
COMMON_HI = {
    # Existing
    "Subscriptions": "सदस्यताएँ",
    "Manage": "प्रबंधित करें",
    "Add": "जोड़ें",
    "Subscription": "सदस्यता",
    "Manage your recurring payments and never miss a due date again.": "अपने आवर्ती भुगतानों को प्रबंधित करें और कभी भी नियत तारीख न चूकें।",
    "Total Monthly Cost": "कुल मासिक लागत",
    "mo": "माह",
    "Yearly Projection": "वार्षिक प्रक्षेपण",
    "yr": "वर्ष",
    "renewals due soon": "नवीनीकरण जल्द ही होने वाले हैं",
    "All": "सभी",
    "Renewing Soon": "जल्द ही नवीनीकरण",
    "Cancelled": "रद्द की गई",
    "Edit": "संपादित करें",
    "Delete": "मिटाएँ",
    "Are you sure you want to delete subscription": "क्या आप वाकई सदस्यता हटाना चाहते हैं",
    "This will stop all future tracking for this item.": "यह इस मद के लिए भविष्य की सभी ट्रैकिंग रोक देगा।",
    "No active subscriptions": "कोई सक्रिय सदस्यता नहीं",
    "Most people forget at least one renewal every year. Add yours now so we can remind you before you pay.": "ज्यादातर लोग हर साल कम से कम एक नवीनीकरण भूल जाते हैं। अपना अभी जोड़ें ताकि हम आपको भुगतान करने से पहले याद दिला सकें।",
    "Add your first subscription": "अपनी पहली सदस्यता जोड़ें",
    "Renewing This Month": "इस महीने नवीनीकरण",
    "No renewals coming up this month!": "इस महीने कोई नवीनीकरण नहीं आ रहा है!",
    "Reactivate": "फिर से सक्रिय करें",
    "No cancelled subscriptions.": "कोई रद्द की गई सदस्यता नहीं।",
    "In {{ sub.annotated_days_until }} day": "{{ sub.annotated_days_until }} दिन में",
    "In {{ sub.annotated_days_until }} days": "{{ sub.annotated_days_until }} दिनों में",
    "Search entries...": "प्रविष्टियाँ खोजें...",
    "Search": "खोजें",
    "Clear search": "खोज साफ़ करें",
    "Back to Dashboard": "डैशबोर्ड पर वापस",
    "{{ month_name }} net savings:": "{{ month_name }} शुद्ध बचत:",
    "Income": "आय",
    "Expense": "खर्च",
    "Sun": "रवि", "Mon": "सोम", "Tue": "मंगल", "Wed": "बुध", "Thu": "गुरु", "Fri": "शुक्र", "Sat": "शनि",
    "No activity": "कोई गतिविधि नहीं",
    "View Details": "विवरण देखें",
    "View expenses for this day": "इस दिन के खर्च देखें",
    "Analytics": "विश्लेषण",
    "Analytics & Trends": "विश्लेषण और रुझान",
    "Visualizing your financial journey over the last 12 months.": "पिछले 12 महीनों में अपनी वित्तीय यात्रा को देख रहे हैं।",
    "Last 12 Months": "पिछले 12 महीने",
    "Total Income (YTD)": "कुल आय (YTD)",
    "Total Expenses (YTD)": "कुल खर्च (YTD)",
    "Avg. Balance Rate (YTD)": "औसत शेष दर (YTD)",
    "Percentage of income kept as balance/savings": "शेष/बचत के रूप में रखी गई आय का प्रतिशत",
    "Income vs Expenses Analysis": "आय बनाम खर्च विश्लेषण",
    "Comparing what comes in (Green) vs. what goes out (Red). The gap is your potential savings.": "जो आता है (हरा) बनाम जो जाता है (लाल) की तुलना करना। अंतर आपकी संभावित बचत है।",
    "Spending by Category": "श्रेणी के अनुसार खर्च",
    "See which categories are consuming the most of your budget this year.": "देखें कि इस वर्ष आपके बजट का अधिकांश भाग किन श्रेणियों में खर्च हो रहा है।",
    "Balance Rate Trend (%)": "शेष दर रुझान (%)",
    "Shows what % of your income is left after expenses. A higher positive percentage means you're growing your wealth.": "दिखाता है कि खर्चों के बाद आपकी आय का कितना प्रतिशत बचा है। एक उच्च सकारात्मक प्रतिशत का मतलब है कि आप अपनी संपत्ति बढ़ा रहे हैं।",
    "Net Balance": "शुद्ध शेष",
    "Balance Rate (%)": "शेष दर (%)",
    "Product": "उत्पाद",
    "About": "के बारे में",
    "Contact": "संपर्क",
    "Legal": "कानूनी",
    "Privacy Policy": "गोपनीयता नीति",
    "Terms of Service": "सेवा की शर्तें",
    "Refund & Cancellation": "धनवापसी और रद्दीकरण",
    "All rights reserved.": "सर्वाधिकार सुरक्षित।",
    "Add Expense": "खर्च जोड़ें",
    "Add Income": "आय जोड़ें",
    "Select...": "चुनें...",
    "- Selected": "- चयनित",
    "All Selected": "सभी चयनित",
    "Support TrackMyRupee": "TrackMyRupee का समर्थन करें",
    "If TrackMyRupee helped you understand your money better, consider supporting its development.": "यदि TrackMyRupee ने आपको अपने पैसे को बेहतर ढंग से समझने में मदद की है, तो इसके विकास का समर्थन करने पर विचार करें।",
    "Donate Now": "अभी दान करें",
    "We use cookies to improve your experience and analyze site traffic.": "हम आपके अनुभव को बेहतर बनाने और साइट ट्रैफ़िक का विश्लेषण करने के लिए कुकीज़ का उपयोग करते हैं।",
    "By clicking \"Accept\", you verify that you are comfortable with us using tracking cookies.": "\"स्वीकार करें\" पर क्लिक करके, आप पुष्टि करते हैं कि आप हमारे द्वारा ट्रैकिंग कुकीज़ का उपयोग करने में सहज हैं।",
    "Decline": "अस्वीकार करें",
    "Accept": "स्वीकार करें",
    "Support Us": "हमारा समर्थन करें",
    "Features": "सुविधाएँ",
    "Pricing": "मूल्य निर्धारण",
    "Blog": "ब्लॉग",
    "Live Demo": "लाइव डेमो",
    "Company": "कंपनी",
    "Category Distribution": "श्रेणी वितरण",
    "Top Categories": "शीर्ष श्रेणियाँ",
    "View All": "सभी देखें",
    "No data available": "कोई डेटा उपलब्ध नहीं",
    "No expense data available": "कोई व्यय डेटा उपलब्ध नहीं",
    
    # NEWEST DASHBOARD ITEMS
    "From": "से",
    "To": "तक",
    "Keep saving to see this!": "यह देखने के लिए बचत करते रहें!",
    "Based on your YTD average": "आपके YTD औसत पर आधारित",
    "Expenses": "खर्च",
    "Year End": "वर्ष का अंत",
    "No Budgets Set": "कोई बजट सेट नहीं",
    "Set limits for your categories to track spending.": "खर्च पर नज़र रखने के लिए अपनी श्रेणियों के लिए सीमाएँ निर्धारित करें।",
    "Set Budget": "बजट सेट करें",
    "(Stacked by Category)": "(श्रेणी के अनुसार ढेरा)",
    "Payment Method Distribution": "भुगतान विधि वितरण",
    "Recent Transactions": "हाल के लेनदेन",
    "This Month's Insights": "इस महीने की अंतर्दृष्टि",
    
    # Income Page
    "Filters": "फिल्टर",
    "Date From": "दिनांक से",
    "Date To": "दिनांक तक",
    "Source": "स्रोत",
    "Total Records": "कुल रिकॉर्ड",
    "Total Amount": "कुल राशि",
    "Description": "विवरण",
    "Actions": "क्रियाएं",
    "No Income Records": "कोई आय रिकॉर्ड नहीं",
    "We couldn't find any income records matching your filters.": "हमें आपके फिल्टर से मेल खाने वाला कोई आय रिकॉर्ड नहीं मिला।",
    "You haven't recorded any income yet. Start tracking your earnings!": "आपने अभी तक कोई आय दर्ज नहीं की है। अपनी कमाई को ट्रैक करना शुरू करें!",
    "Clear Filters": "फिल्टर साफ करें",
    "Edit Income": "आय संपादित करें",
    "Save Changes": "परिवर्तन सहेजें",
    
    # Budget Page
    "Budget": "बजट",
    "A budget is telling your money where to go, instead of wondering where it went.": "बजट आपके पैसे को यह बताना है कि कहाँ जाना है, बजाय इसके कि यह सोचना कि वह कहाँ गया।",
    "Total Budget Goal": "कुल बजट लक्ष्य",
    "vs last month": "बनाम पिछले महीने",
    "% Used": "% उपयोग किया गया",
    "Over budget by": "बजट से अधिक",
    "remaining": "शेष",
    "View Expenses": "खर्च देखें",
    "Edit Limit": "सीमा संपादित करें",
    "Spent:": "खर्च किया:",
    "Limit:": "सीमा:",
    "left": "बचा",
    "Limit reached — consider adjusting": "सीमा समाप्त — समायोजन पर विचार करें",
    "You’re close to your limit": "आप अपनी सीमा के करीब हैं",
    "No limit set": "कोई सीमा निर्धारित नहीं",
    "Set limit": "सीमा निर्धारित करें",
    "No categories found. Start by adding some categories to your settings.": "कोई श्रेणियाँ नहीं मिलीं। अपनी सेटिंग्स में कुछ श्रेणियाँ जोड़कर शुरुआत करें।",
    "Add Category": "श्रेणी जोड़ें",

    # Categories Page
    "Categories": "श्रेणियाँ",
    "Categories help you understand your spending habits": "श्रेणियाँ आपको अपनी खर्च करने की आदतों को समझने में मदद करती हैं",
    "Search categories...": "श्रेणियाँ खोजें...",
    "Name": "नाम",
    "Monthly Limit": "मासिक सीमा",
    "Monthly Limit (Optional)": "मासिक सीमा (वैकल्पिक)",
    "No Categories Yet": "अभी तक कोई श्रेणी नहीं",
    "Organize your transactions by creating custom categories.": "कस्टम श्रेणियाँ बनाकर अपने लेनदेन को व्यवस्थित करें।",
    "Edit Category": "श्रेणी संपादित करें",

    # Dashboard - Dynamic Dates
    "No Budgets Set": "कोई बजट निर्धारित नहीं",
    "For %(month)s %(year)s": "%(month)s %(year)s के लिए",
    "For %(year)s": "%(year)s के लिए",
    "All Time": "पूरा समय",
    
    # Months
    "January": "जनवरी", "February": "फरवरी", "March": "मार्च", "April": "अप्रैल",
    "May": "मई", "June": "जून", "July": "जुलाई", "August": "अगस्त",
    "September": "सितंबर", "October": "अक्टूबर", "November": "नवंबर", "December": "दिसंबर",

    # Expense List Page
    "Expenses": "खर्च",
    "Tracking every penny is the first step to financial freedom.": "हर पैसे की ट्रैकिंग वित्तीय स्वतंत्रता का पहला कदम है।",
    "Delete Selected": "चयनित हटाएं",
    "Total Records": "कुल रिकॉर्ड",
    "Total Amount": "कुल राशि",


}

COMMON_MR = {
    # Existing
    "Calendar": "कॅलेंडर",
    "Subscriptions": "सदस्यता",
    "Manage": "व्यवस्थापित करा",
    "Add": "जोडा",
    "Subscription": "सदस्यता",
    "Manage your recurring payments and never miss a due date again.": "तुमची आवर्ती देयके व्यवस्थापित करा आणि देय तारीख कधीही चुकवू नका.",
    "Total Monthly Cost": "एकूण मासिक खर्च",
    "mo": "महिना",
    "Yearly Projection": "वार्षिक अंदाज",
    "yr": "वर्ष",
    "renewals due soon": "नूतनीकरण लवकरच येत आहे",
    "All": "सर्व",
    "Renewing Soon": "लवकरच नूतनीकरण",
    "Cancelled": "रद्द केलेले",
    "Edit": "संपादित करा",
    "Delete": "हटवा",
    "Are you sure you want to delete subscription": "तुम्हाला खात्री आहे की तुम्ही सदस्यता हटवू इच्छिता",
    "This will stop all future tracking for this item.": "यामुळे या आयटमसाठी भविष्यातील सर्व ट्रॅकिंग थांबेल.",
    "No active subscriptions": "कोणतीही सक्रिय सदस्यता नाही",
    "Most people forget at least one renewal every year. Add yours now so we can remind you before you pay.": "बहुतेक लोक दरवर्षी किमान एक नूतनीकरण विसरतात. तुमचे आता जोडा जेणेकरून तुम्ही पैसे देण्यापूर्वी आम्ही तुम्हाला आठवण करून देऊ शकू.",
    "Add your first subscription": "तुमची पहिली सदस्यता जोडा",
    "Renewing This Month": "या महिन्यात नूतनीकरण",
    "No renewals coming up this month!": "या महिन्यात कोणतेही नूतनीकरण नाही!",
    "Reactivate": "पुन्हा सक्रिय करा",
    "No cancelled subscriptions.": "कोणतीही रद्द केलेली सदस्यता नाही.",
    "In {{ sub.annotated_days_until }} day": "{{ sub.annotated_days_until }} दिवसात",
    "In {{ sub.annotated_days_until }} days": "{{ sub.annotated_days_until }} दिवसात",
    "Search entries...": "नोंदी शोधा...",
    "Search": "शोधा",
    "Clear search": "शोध साफ करा",
    "Back to Dashboard": "डॅशबोर्डवर परत",
    "{{ month_name }} net savings:": "{{ month_name }} निव्वळ बचत:",
    "Income": "उत्पन्न",
    "Expense": "खर्च",
    "Sun": "रवि", "Mon": "सोम", "Tue": "मंगळ", "Wed": "बुध", "Thu": "गुरु", "Fri": "शुक्र", "Sat": "शनि",
    "No activity": "कोणतीही हालचाल नाही",
    "View Details": "तपशील पहा",
    "View expenses for this day": "या दिवसाचे खर्च पहा",
    "Analytics": "विश्लेषण",
    "Analytics & Trends": "विश्लेषण आणि ट्रेंड",
    "Visualizing your financial journey over the last 12 months.": "गेल्या १२ महिन्यांतील तुमच्या आर्थिक प्रवासाचे दृश्यमान स्वरूप.",
    "Last 12 Months": "गेले १२ महिने",
    "Total Income (YTD)": "एकूण उत्पन्न (YTD)",
    "Total Expenses (YTD)": "एकूण खर्च (YTD)",
    "Avg. Balance Rate (YTD)": "सरासरी शिल्लक दर (YTD)",
    "Percentage of income kept as balance/savings": "शिल्लक/बचत म्हणून ठेवलेल्या उत्पन्नाची टक्केवारी",
    "Income vs Expenses Analysis": "उत्पन्न बनाम खर्च विश्लेषण",
    "Comparing what comes in (Green) vs. what goes out (Red). The gap is your potential savings.": "येणारे उत्पन्न (हिरवे) आणि जाणारा खर्च (लाल) यांची तुलना. अंतर तुमची संभाव्य बचत आहे.",
    "Spending by Category": "श्रेणीनुसार खर्च",
    "See which categories are consuming the most of your budget this year.": "या वर्षी तुमच्या बजेटचा सर्वाधिक भाग कोणत्या श्रेणींमध्ये खर्च होत आहे ते पहा.",
    "Balance Rate Trend (%)": "शिल्लक दर ट्रेंड (%)",
    "Shows what % of your income is left after expenses. A higher positive percentage means you're growing your wealth.": "खर्चानंतर तुमच्या उत्पन्नाचा किती टक्के भाग शिल्लक आहे हे दर्शवते. उच्च सकारात्मक टक्केवारी म्हणजे तुमची संपत्ती वाढत आहे.",
    "Net Balance": "निव्वळ शिल्लक",
    "Balance Rate (%)": "शिल्लक दर (%)",
    "Product": "उत्पादन",
    "About": "बद्दल",
    "Contact": "संपर्क",
    "Legal": "कायदेशीर",
    "Privacy Policy": "गोपनीयता धोरण",
    "Terms of Service": "सेवा अटी",
    "Refund & Cancellation": "परतावा आणि रद्दीकरण",
    "All rights reserved.": "सर्व हक्क राखीव.",
    "Add Expense": "खर्च जोडा",
    "Add Income": "उत्पन्न जोडा",
    "Select...": "निवडा...",
    "- Selected": "- निवडलेले",
    "All Selected": "सर्व निवडलेले",
    "Support TrackMyRupee": "TrackMyRupee ला पाठिंबा द्या",
    "If TrackMyRupee helped you understand your money better, consider supporting its development.": "जर TrackMyRupee ने तुम्हाला तुमचे पैसे अधिक चांगल्या प्रकारे समजून घेण्यास मदत केली असेल, तर त्याच्या विकासाला पाठिंबा देण्याचा विचार करा.",
    "Donate Now": "आता दान करा",
    "We use cookies to improve your experience and analyze site traffic.": "आम्ही तुमचा अनुभव सुधारण्यासाठी आणि साइट ट्रॅफिकचे विश्लेषण करण्यासाठी कुकीज वापरतो.",
    "By clicking \"Accept\", you verify that you are comfortable with us using tracking cookies.": "\"स्वीकार करा\" वर क्लिक करून, तुम्ही पुष्टी करता की तुम्ही आमच्या ट्रॅकिंग कुकीज वापरण्याबाबत समाधानी आहात.",
    "Decline": "नाकारणे",
    "Accept": "स्वीकारणे",
    "Support Us": "आम्हाला समर्थन द्या",
    "Features": "वैशिष्ट्ये",
    "Pricing": "किंमत",
    "Blog": "ब्लॉग",
    "Live Demo": "थेट डेमो",
    "Company": "कंपनी",
    "Category Distribution": "श्रेणी वितरण",
    "Top Categories": "शीर्ष श्रेणी",
    "View All": "सर्व पहा",
    "No data available": "कोणताही डेटा उपलब्ध नाही",
    "No expense data available": "कोणताही खर्च डेटा उपलब्ध नाही",
    
    # NEWEST DASHBOARD ITEMS
    "From": "करून",
    "To": "पर्यंत",
    "Keep saving to see this!": "हे पाहण्यासाठी बचत करत राहा!",
    "Based on your YTD average": "तुमच्या YTD सरासरीवर आधारित",
    "Expenses": "खर्च",
    "Year End": "वर्ष अखेर",
    "No Budgets Set": "कोणतेही बजेट सेट नाही",
    "Set limits for your categories to track spending.": "खर्च ट्रॅक करण्यासाठी तुमच्या श्रेणींसाठी मर्यादा सेट करा.",
    "Set Budget": "बजेट सेट करा",
    "(Stacked by Category)": "(श्रेणीनुसार स्टॅक केलेले)",
    "Payment Method Distribution": "पेमेंट पद्धत वितरण",
    "Recent Transactions": "अलीकडील व्यवहार",
    "This Month's Insights": "या महिन्याची अंतर्दृष्टी",

    # Income Page
    "Filters": "फिल्टर",
    "Date From": "या तारखेपासून",
    "Date To": "या तारखेपर्यंत",
    "Source": "स्रोत",
    "Total Records": "एकूण रेकॉर्ड",
    "Total Amount": "एकूण रक्कम",
    "Description": "वर्णन",
    "Actions": "क्रिया",
    "No Income Records": "कोणतेही उत्पन्न रेकॉर्ड नाही",
    "We couldn't find any income records matching your filters.": "आम्हाला तुमच्या फिल्टरशी जुळणारे कोणतेही उत्पन्न रेकॉर्ड सापडले नाही.",
    "You haven't recorded any income yet. Start tracking your earnings!": "तुम्ही अद्याप कोणतेही उत्पन्न रेकॉर्ड केलेले नाही. तुमच्या कमाईचा मागोवा घेणे सुरू करा!",
    "Clear Filters": "फिल्टर साफ करा",
    "Edit Income": "उत्पन्न संपादित करा",
    "Save Changes": "बदल जतन करा",

    # Budget Page
    "Budget": "बजेट",
    "A budget is telling your money where to go, instead of wondering where it went.": "बजेट म्हणजे तुमच्या पैशाला कुठे जायचे हे सांगणे, ते कुठे गेले याचा विचार करण्याऐवजी.",
    "Total Budget Goal": "एकूण बजेट ध्येय",
    "vs last month": "वि मागील महिना",
    "% Used": "% वापरले",
    "Over budget by": "बजेटपेक्षा जास्त",
    "remaining": "शिल्लक",
    "View Expenses": "खर्च पहा",
    "Edit Limit": "मर्यादा संपादित करा",
    "Spent:": "खर्च:",
    "Limit:": "मर्यादा:",
    "left": "बाकी",
    "Limit reached — consider adjusting": "मर्यादा गाठली — समायोजित करण्याचा विचार करा",
    "You’re close to your limit": "तुम्ही तुमच्या मर्यादेच्या जवळ आहात",
    "No limit set": "कोणतीही मर्यादा सेट केलेली नाही",
    "Set limit": "मर्यादा सेट करा",
    "No categories found. Start by adding some categories to your settings.": "कोणत्याही श्रेणी सापडल्या नाहीत. तुमच्या सेटिंग्जमध्ये काही श्रेणी जोडून सुरुवात करा.",
    "Add Category": "श्रेणी जोडा",

    # Categories Page
    "Categories": "श्रेण्या",
    "Categories help you understand your spending habits": "श्रेण्या तुम्हाला तुमच्या खर्चाच्या सवयी समजून घेण्यास मदत करतात",
    "Search categories...": "श्रेण्या शोधा...",
    "Name": "नाव",
    "Monthly Limit": "मासिक मर्यादा",
    "Monthly Limit (Optional)": "मासिक मर्यादा (पर्यायी)",
    "No Categories Yet": "अद्याप कोणतीही श्रेणी नाही",
    "Organize your transactions by creating custom categories.": "सानुकूल श्रेण्या तयार करून तुमचे व्यवहार व्यवस्थित करा.",
    "Edit Category": "श्रेणी संपादित करा",

    # Dashboard - Dynamic Dates
    "No Budgets Set": "कोणतेही बजेट सेट नाही",
    "For %(month)s %(year)s": "%(month)s %(year)s साठी",
    "For %(year)s": "%(year)s साठी",
    "All Time": "सर्व वेळ",

    # Months
    "January": "जानेवारी", "February": "फेब्रुवारी", "March": "मार्च", "April": "एप्रिल",
    "May": "मे", "June": "जून", "July": "जुलै", "August": "ऑगस्ट",
    "September": "सप्टेंबर", "October": "ऑक्टोबर", "November": "नोव्हेंबर", "December": "डिसेंबर",

    # Expense List Page
    "Expenses": "खर्च",
    "Tracking every penny is the first step to financial freedom.": "प्रत्येक पैसा ट्रॅक करणे हे आर्थिक स्वातंत्र्याचे पहिले पाऊल आहे.",
    "Delete Selected": "निवडलेले हटवा",
    "Total Records": "एकूण रेकॉर्ड",
    "Total Amount": "एकूण रक्कम",


}

# Complex strings
COMPLEX_MSGID = '''msgid ""
"Turn financial chaos into clarity. TrackMyRupee gives you a precision "
"dashboard to visualize\\n"
"                        your spending, spot trends, and master your monthly "
"budget."'''

COMPLEX_REPLACEMENTS_HI = {
    COMPLEX_MSGID: "वित्तीय अराजकता को स्पष्टता में बदलें। TrackMyRupee आपको अपने खर्च की कल्पना करने, रुझानों को पहचानने और अपने मासिक बजट में महारत हासिल करने के लिए एक सटीक डैशबोर्ड देता है।"
}

COMPLEX_REPLACEMENTS_MR = {
    COMPLEX_MSGID: "आर्थिक गोंधळाचे स्पष्टतेमध्ये रूपांतर करा. तुमचा खर्च पाहण्यासाठी, ट्रेंड ओळखण्यासाठी आणि तुमच्या मासिक बजेटवर प्रभुत्व मिळवण्यासाठी TrackMyRupee तुम्हाला एक अचूक डॅशबोर्ड देते."
}

if __name__ == "__main__":
    update_po_file('locale/hi/LC_MESSAGES/django.po', COMMON_HI, COMPLEX_REPLACEMENTS_HI)
    update_po_file('locale/mr/LC_MESSAGES/django.po', COMMON_MR, COMPLEX_REPLACEMENTS_MR)
    print("Translations updated successfully.")
