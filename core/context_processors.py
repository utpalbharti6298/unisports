# What this file does:
# Supplies global template context variables (current year, logged-in session user, and admin status) to all templates.

import datetime

# Inject session user and platform metadata into every rendered template
def global_context(request):
    """
    Supplies global brutalist UI context variables across all templates.
    """
    session = getattr(request, 'session', {})
    session_user = session.get('user', None) if isinstance(session, dict) or hasattr(session, 'get') else None
    return {
        'current_year': datetime.datetime.now().year,
        'session_user': session_user,
        'is_admin': session_user.get('role') == 'admin' if session_user else False,
    }
