import logging
from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class LoggedEmailBackend:
    """
    Wraps the real email backend and logs every sent email to the database.
    """
    def __init__(self, *args, **kwargs):
        self._init_args = args
        self._init_kwargs = kwargs
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            # Use the same logic as in settings.py to choose the real backend
            if settings.DEBUG:
                self._backend = ConsoleBackend(*self._init_args, **self._init_kwargs)
            else:
                from anymail.backends.brevo import EmailBackend as BrevoBackend
                self._backend = BrevoBackend(*self._init_args, **self._init_kwargs)
        return self._backend

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        # Initialize backend and send
        b = self.backend
        try:
            sent_count = b.send_messages(email_messages)
        except Exception as e:
            logger.error(f"Error sending email messages: {e}")
            sent_count = 0
            # Even if it fails, we want to log the attempt below if possible
        
        for message in email_messages:
            try:
                # We import here to avoid circular imports if models.py depends on mail
                from .models import EmailLog
                
                # Try to find a user with this email
                # message.to is a list of emails
                recipient = message.to[0] if message.to else ""
                user = User.objects.filter(email=recipient).first() if recipient else None
                
                # Collect HTML body if present
                html_body = ""
                if hasattr(message, 'alternatives'):
                    for alt in message.alternatives:
                        if alt[1] == 'text/html':
                            html_body = alt[0]
                            break

                EmailLog.objects.create(
                    user=user,
                    to_email=", ".join(message.to) if message.to else "No Recipient",
                    subject=message.subject,
                    body=message.body,
                    html_body=html_body,
                    status='SENT' if sent_count > 0 else 'FAILED',
                    error_message=None if sent_count > 0 else "Backend reported 0 sent messages"
                )
            except Exception as e:
                # Logging to DB failed, at least log it to console/file
                logger.error(f"Failed to log email to database: {e}")
                
        return sent_count
