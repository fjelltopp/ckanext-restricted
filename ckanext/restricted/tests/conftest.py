import pytest
import mock


@pytest.fixture(autouse=True)
def restricted_action_mail():
    with mock.patch('ckanext.restricted.action.mail_recipient'):
        yield


@pytest.fixture(scope='function')
def debug_app_creation(make_app):
    """Debug fixture to understand app creation issues"""
    print("\n=== DEBUG: Starting app creation ===")
    import ckan.plugins as p
    print(f"DEBUG: Loaded plugins before app: {p.core._PLUGINS}")
    try:
        app = make_app()
        print(f"DEBUG: App created successfully")
        return app
    except Exception as e:
        print(f"DEBUG: App creation failed with: {type(e).__name__}: {e}")
        raise
