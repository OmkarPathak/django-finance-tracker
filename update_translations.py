import os
import re

def update_po_file(filepath, translations, complex_replacements=None):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a msgid we want to translate
        match = re.match(r'^msgid "(.*)"$', line)
        if match:
            msgid = match.group(1)
            if msgid in translations:
                # We found a target msgid. 
                # Backtrack to remove #, fuzzy if it exists
                # We also remove #| lines which are previous msgid hints
                while new_lines and (new_lines[-1].strip().startswith("#, fuzzy") or new_lines[-1].strip().startswith("#|")):
                    new_lines.pop()
                
                # Add the msgid
                new_lines.append(line)
                
                # Find the msgstr (it should be the next line)
                i += 1
                if i < len(lines) and lines[i].startswith('msgstr "'):
                    new_lines.append(f'msgstr "{translations[msgid]}"\n')
                else:
                    # Handle case where msgstr is weirdly placed
                    new_lines.append(f'msgstr "{translations[msgid]}"\n')
                
                i += 1
                continue
        
        new_lines.append(line)
        i += 1

    content = "".join(new_lines)
    
    # Complex replacements (exact match for multi-line msgid)
    if complex_replacements:
        for msgid_block, msgstr in complex_replacements.items():
             # Remove fuzzy flag for complex blocks too
             # This is a bit harder with simple replace, but complex blocks are usually not fuzzy in this project
             if msgid_block in content:
                 # Check if the line before msgid_block is fuzzy
                 # (This is a bit crude but should work for this specific use case)
                 pattern = r'#,\s*fuzzy\n' + re.escape(msgid_block)
                 content = re.sub(pattern, msgid_block, content)
                 
                 pattern_with_hint = r'#,\s*fuzzy\n#\|.*?\n' + re.escape(msgid_block)
                 content = re.sub(pattern_with_hint, msgid_block, content, flags=re.DOTALL)

                 pattern_simple = msgid_block + r'\nmsgstr ""'
                 replacement = msgid_block + f'\nmsgstr "{msgstr}"'
                 content = content.replace(pattern_simple, replacement)
                 
                 # Also handle non-empty msgstr for complex blocks
                 pattern_overwrite = msgid_block + r'\nmsgstr ".*?"'
                 content = re.sub(pattern_overwrite, msgid_block + f'\nmsgstr "{msgstr}"', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Common translations
COMMON_HI = {
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
    "From": "से",
    "To": "तक",
    "Keep saving to see this!": "यह देखने के लिए बचत करते रहें!",
    "Based on your YTD average": "आपके YTD औसत पर आधारित",
    "Expenses": "खर्च",
    "Year End": "वर्ष का अंत",
    "No Budgets Set": "कोई बजट सेट नहीं",
    "Set limits for your categories to track spending.": "खर्च पर नज़र रखने के लिए अपनी श्रेणियों के लिए सीमाएँ निर्धारित करें।",
    "Set Budget": "बजेट सेट करें",
    "(Stacked by Category)": "(श्रेणी के अनुसार ढेरा)",
    "Payment Method Distribution": "भुगतान विधि वितरण",
    "Recent Transactions": "हाल के लेनदेन",
    "This Month's Insights": "इस महीने की अंतर्दृष्टि",
    "Save Income": "आय सहेजें",
    "New Category": "नई श्रेणी",
    "Save Category": "श्रेणी सहेजें",
    "Edit Expense": "खर्च संपादित करें",
    "New Expense": "नया खर्च",
    "Date": "दिनांक",
    "Payment": "भुगतान",
    "Add New Category": "नई श्रेणी जोड़ें",
    "Add Another Expense": "एक और खर्च जोड़ें",
    "Save All Expenses": "सभी खर्च सहेजें",
    "Category Name": "श्रेणी का नाम",
    "Add Row": "पंक्ति जोड़ें",
    "Category name cannot be empty.": "श्रेणी का नाम खाली नहीं हो सकता।",
    "Saving...": "सहेज रहा है...",
    "An error occurred.": "एक त्रुटि हुई।",
    "A network error occurred.": "नेटवर्क त्रुटि हुई।",
    "Update Subscription": "सदस्यता अपडेट करें",
    "Save Subscription": "सदस्यता सहेजें",
    "Type": "प्रकार",
    "Start Date": "प्रारंभ तिथि",
    "Category (For Expense)": "श्रेणी (खर्च के लिए)",
    "Source (For Income)": "स्रोत (आय के लिए)",
    "Payment Source Method": "भुगतान स्रोत विधि",
    "Active": "सक्रिय",
    "Save Task": "कार्य सहेजें",
    "Subscription updated successfully.": "सदस्यता सफलतापूर्वक अपडेट की गई।",
    "Recurring transaction updated successfully.": "आवर्ती लेनदेन सफलतापूर्वक अपडेट किया गया।",
    "This income entry already exists.": "यह आय प्रविष्टि पहले से मौजूद है।",
    "Duplicate record found!": "डुप्लिकेट रिकॉर्ड मिला!",
    "Category is required for expenses.": "खर्च के लिए श्रेणी आवश्यक है।",
    "Source is required for income.": "आय के लिए स्रोत आवश्यक है।",
    "e.g. Salary, Freelance": "जैसे वेतन, फ्रीलांस",
    "Monthly": "मासिक",
    "Quarterly": "त्रैमासिक",
    "Half-Yearly": "अर्धवार्षिक",
    "Yearly": "वार्षिक",
    "Cash": "नकद",
    "Credit Card": "क्रेडिट कार्ड",
    "Debit Card": "देबिट कार्ड",
    "UPI": "यूपीआई",
    "NetBanking": "नेटबैंकिंग",
    "Cancel": "रद्द करें",
    "Edit Income": "आय संपादित करें",
    "Save Changes": "परिवर्तन सहेजें",
    "Amount": "मूल्य",
    "Category": "श्रेणी",
    "Description": "विवरण",
    "Settings": "सेटिंग्स",
    "Theme": "थीम",
    "Login": "लॉगिन",
    "Join Now": "अभी शामिल हों",
    "Currency": "मुद्रा",
    "Profile": "प्रोफाइल",
    "Tutorial": "ट्यूटोरियल",
    "Current Plan": "वर्तमान योजना",
    "Upgrade": "अपग्रेड",
}

COMMON_MR = {
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
    "If TrackMyRupee helped you understand your money better, consider supporting its development.": "जवळजवळ सर्वच आर्थिक व्यवहार TrackMyRupee मुळे सुलभ झाले आहेत. त्याच्या विकासाला पाठिंबा देण्याचा विचार करा.",
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
    "Save Income": "आय जतन करा",
    "New Category": "नवीन श्रेणी",
    "Save Category": "श्रेणी जतन करा",
    "Edit Expense": "खर्च संपादित करा",
    "New Expense": "नवीन खर्च",
    "Date": "दिनांक",
    "Payment": "देयक",
    "Add New Category": "नवीन श्रेणी जोडा",
    "Add Another Expense": "आणखी एक खर्च जोडा",
    "Save All Expenses": "सर्व खर्च जतन करा",
    "Category Name": "श्रेणीचे नाव",
    "Add Row": "ओळ जोडा",
    "Category name cannot be empty.": "श्रेणीचे नाव रिकामे असू शकत नाही.",
    "Saving...": "जतन करत आहे...",
    "An error occurred.": "एक त्रुटी आली.",
    "A network error occurred.": "नेटवर्क त्रुटी आली.",
    "Update Subscription": "सदस्यता अद्ययावत करा",
    "Save Subscription": "सदस्यता जतन करा",
    "Type": "प्रकार",
    "Start Date": "प्रारंभ तारीख",
    "Category (For Expense)": "श्रेणी (खर्चासाठी)",
    "Source (For Income)": "स्रोत (उत्पन्नासाठी)",
    "Payment Source Method": "पेमेंट सोर्स पद्धत",
    "Active": "सक्रिय",
    "Save Task": "कार्य जतन करा",
    "Subscription updated successfully.": "सदस्यता यशस्वीरित्या अद्ययावत केली.",
    "Recurring transaction updated successfully.": "आवर्ती व्यवहार यशस्वीरित्या अद्ययावत केला.",
    "This income entry already exists.": "ही उत्पन्न नोंद आधीच अस्तित्वात आहे.",
    "Duplicate record found!": "दुप्पट रेकॉर्ड सापडले!",
    "Category is required for expenses.": "खर्चासाठी श्रेणी आवश्यक आहे.",
    "Source is required for income.": "उत्पन्नासाठी स्रोत आवश्यक आहे.",
    "e.g. Salary, Freelance": "उदा. पगार, फ्रीलान्स",
    "Monthly": "मासिक",
    "Quarterly": "त्रैमासिक",
    "Half-Yearly": "अर्धवार्षिक",
    "Yearly": "वार्षिक",
    "Cash": "रोख",
    "Credit Card": "क्रेडिट कार्ड",
    "Debit Card": "डेबिट कार्ड",
    "UPI": "यूपीआई",
    "NetBanking": "नेटबँकिंग",
    "Cancel": "रद्द करा",
    "Edit Income": "उत्पन्न संपादित करा",
    "Save Changes": "बदल जतन करा",
    "Amount": "रक्कम",
    "Category": "श्रेणी",
    "Description": "वर्णन",
    "Settings": "सेटिंग्ज",
    "Theme": "थीम",
    "Login": "लॉगिन",
    "Join Now": "आत्ताच सामील व्हा",
    "Currency": "चलन",
    "Profile": "प्रोफाइल",
    "Tutorial": "ट्यूटोरियल",
    "Current Plan": "सध्याचा प्लॅन",
    "Upgrade": "अपग्रेड",
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
