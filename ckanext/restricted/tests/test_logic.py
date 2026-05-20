"""Tests for logic.py functions."""
# encoding: utf-8
import ckan.model as model
from ckanext.restricted.logic import restricted_get_username_from_context


class TestRestrictedGetUsernameFromContext:
    """Tests for restricted_get_username_from_context function."""

    def test_with_authenticated_user_via_auth_user_obj(self):
        """Test getting username when auth_user_obj is an authenticated User."""
        # Create a mock authenticated user
        user = model.User(name='test_user', email='test@example.com')
        user.id = 'test-user-id'

        context = {
            'auth_user_obj': user,
            'user': 'test_user'
        }

        result = restricted_get_username_from_context(context)
        assert result == 'test_user'

    def test_with_anonymous_user_via_auth_user_obj(self):
        """Test getting username when auth_user_obj is AnonymousUser.

        This simulates what happens when an unauthenticated user visits
        the site (e.g., homepage). In CKAN 2.11, auth_user_obj is set to
        an AnonymousUser instance rather than None.
        """
        # Create an AnonymousUser instance
        anonymous_user = model.AnonymousUser()

        context = {
            'auth_user_obj': anonymous_user,
            'user': ''
        }

        # Should return empty string for anonymous users
        result = restricted_get_username_from_context(context)
        assert result == ''

    def test_with_no_auth_user_obj_and_valid_user(self):
        """Test getting username when auth_user_obj is None but user exists."""
        context = {
            'user': 'test_user'
        }

        # This will fail because the user doesn't actually exist in the DB
        # But we're testing that it tries to look up the user
        result = restricted_get_username_from_context(context)
        # When user doesn't exist in DB, it should return empty string
        assert result == ''

    def test_with_no_auth_user_obj_and_no_user(self):
        """Test getting username when both auth_user_obj and user are missing."""
        context = {}

        result = restricted_get_username_from_context(context)
        assert result == ''

    def test_with_none_auth_user_obj(self):
        """Test getting username when auth_user_obj is explicitly None."""
        context = {
            'auth_user_obj': None,
            'user': ''
        }

        result = restricted_get_username_from_context(context)
        assert result == ''
