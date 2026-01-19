from django.test import TestCase
from django.template import Context, Template
from blog.templatetags.blog_extras import markdown

class SecurityTests(TestCase):
    def test_markdown_xss_protection(self):
        """
        Test that the markdown filter strips dangerous tags (scripts)
        but allows safe tags (b, i, headings).
        """
        # 1. Test Script Injection
        dangerous_input = "Hello <script>alert('XSS')</script> World"
        output = markdown(dangerous_input)
        self.assertNotIn("<script>", output)
        self.assertIn("Hello", output)
        self.assertIn("World", output)
        # Bleach usually escapes it to &lt;script&gt; or removes it depending on config.
        # Our config uses strip=True, so it should remove the tag content or the tag itself.
        # Let's check that it is definitely NOT executing.
        
        # 2. Test Safe HTML
        safe_input = "**Bold** and *Italic*"
        output = markdown(safe_input)
        self.assertIn("<strong>Bold</strong>", output)
        self.assertIn("<em>Italic</em>", output)
        
        # 3. Test Links
        link_input = "[Google](https://google.com)"
        output = markdown(link_input)
        self.assertIn('<a href="https://google.com"', output)

    def test_markdown_attributes(self):
        """Test allowed attributes on tags"""
        # onclick should be stripped
        input_text = '<a href="http://example.com" onclick="steal()">Link</a>'
        output = markdown(input_text)
        self.assertIn('href="http://example.com"', output)
        self.assertNotIn('onclick', output)
