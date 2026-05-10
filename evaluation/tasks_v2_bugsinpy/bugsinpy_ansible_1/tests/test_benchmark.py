import os
import sys
import pytest
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')
sys.path.insert(0, buggy_dir)
import source


def test_source_importable():
    assert source is not None


class RealAnsibleError(Exception):
    def __init__(self, *args, message=None, **kwargs):
        self.message = message or (args[0] if args else '')
        super().__init__(self.message)


def real_to_bytes(s, **kwargs):
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode('utf-8')
    return str(s).encode('utf-8')


def real_to_text(s, **kwargs):
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return str(s)


def real_to_native(s, **kwargs):
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return str(s)


@contextmanager
def noop_display_progress():
    yield


@contextmanager
def fake_tempdir():
    with tempfile.TemporaryDirectory() as d:
        yield d.encode()


def test_verify_collections_no_manifest_raises_error():
    """
    Bug: verify_collections skips the MANIFEST.json check before calling from_path.
    The fixed version raises AnsibleError when the collection directory lacks MANIFEST.json.
    On the buggy code this check is absent so a different error propagates — the assertion fails.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Collection directory exists but contains NO MANIFEST.json
        collection_dir = os.path.join(tmpdir, 'mynamespace', 'mycollection')
        os.makedirs(collection_dir)

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text):

            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('mynamespace.mycollection', '*')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )
            # Fixed code raises with MANIFEST.json message; buggy code raises a
            # "Failed to find remote collection" message instead — assertion fails.
            assert 'MANIFEST.json' in exc_info.value.message


def test_verify_collections_from_path_not_called_when_manifest_missing():
    """
    Bug: buggy verify_collections calls CollectionRequirement.from_path even when MANIFEST.json
    is absent, because the guard check is missing. Fixed code raises before reaching from_path.
    This test tracks whether from_path is invoked to distinguish the two code paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = os.path.join(tmpdir, 'testns', 'testcol')
        os.makedirs(collection_dir)
        # No MANIFEST.json — directory exists but is not a built/installed collection

        from_path_calls = []
        original_from_path = source.CollectionRequirement.from_path

        def tracking_from_path(b_path, force, parent=None):
            from_path_calls.append(True)
            return original_from_path(b_path, force, parent=parent)

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text), \
             patch.object(source.CollectionRequirement, 'from_path', tracking_from_path):

            with pytest.raises(RealAnsibleError):
                source.verify_collections(
                    collections=[('testns.testcol', '*')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )

        # Fixed code raises AnsibleError about MANIFEST.json BEFORE calling from_path.
        # Buggy code calls from_path first (no MANIFEST.json guard), so list has one entry.
        assert from_path_calls == [], (
            "from_path should NOT be called when MANIFEST.json is missing, "
            "but it was called %d time(s)" % len(from_path_calls)
        )


def test_verify_collections_manifest_guard_prevents_api_calls():
    """
    Fixed verify_collections raises AnsibleError about missing MANIFEST.json before
    contacting any remote Galaxy API. Buggy code lacks this guard, so it calls the
    remote API and fails with a different error (no MANIFEST.json mention).
    Two assertions distinguish the two versions:
      1. The error message must mention 'MANIFEST.json' (fails on buggy code).
      2. No API calls were made (fails on buggy code which calls get_collection_versions).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = os.path.join(tmpdir, 'myns', 'mycol')
        os.makedirs(collection_dir)
        # Directory exists but NO MANIFEST.json — looks like a non-installed collection

        api_calls = []

        class MockGalaxyApi:
            name = 'mock'
            api_server = 'http://mock'

            def get_collection_versions(self, namespace, name):
                api_calls.append('get_collection_versions')
                return []

            def get_collection_version_metadata(self, namespace, name, version):
                api_calls.append('get_collection_version_metadata')
                raise RealAnsibleError("not found")

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text), \
             patch.object(source, 'to_native', real_to_native):

            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('myns.mycol', '*')],
                    search_paths=[tmpdir],
                    apis=[MockGalaxyApi()],
                    validate_certs=False,
                    ignore_errors=False,
                )

            # Fixed: error raised before API is ever contacted, message names MANIFEST.json
            # Buggy: API is called (returns no versions), error message is about missing
            #        versions or remote collection — never mentions MANIFEST.json
            assert 'MANIFEST.json' in exc_info.value.message, (
                "Expected error about missing MANIFEST.json, got: %r" % exc_info.value.message
            )
            assert api_calls == [], (
                "Fixed code must not contact the Galaxy API when MANIFEST.json is missing, "
                "but these API methods were called: %r" % api_calls
            )


def test_verify_collections_missing_manifest_error_is_specific():
    """
    Fixed verify_collections raises immediately when a collection directory exists but
    lacks MANIFEST.json, with a message containing 'does not appear to have a MANIFEST.json'.
    Buggy code skips this guard and falls through to the Galaxy API, raising about
    'Failed to find remote collection' instead — the assertion fails on buggy code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'myns', 'mycol'))
        # No MANIFEST.json written — directory exists but collection is not built/installed

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text):

            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('myns.mycol', '1.0.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )

            # Fixed: "Collection myns.mycol does not appear to have a MANIFEST.json. ..."
            # Buggy: "Failed to find remote collection myns.mycol:1.0.0 on any of the galaxy servers"
            assert 'does not appear to have a MANIFEST.json' in exc_info.value.message, (
                "Expected MANIFEST.json-specific error, got: %r" % exc_info.value.message
            )


def test_verify_collections_manifest_guard_prevents_from_path():
    """
    The fixed code adds a MANIFEST.json guard inside verify_collections that fires BEFORE
    CollectionRequirement.from_path is ever called. The buggy code has no such guard and
    calls from_path directly.

    Strategy: patch from_path to raise a sentinel exception (_FromPathCalled) that is NOT
    a subclass of AnsibleError/RealAnsibleError. Then:
      - Fixed code: guard raises RealAnsibleError before from_path → pytest.raises catches
        it → test passes.
      - Buggy code: from_path is called → _FromPathCalled is raised → not caught by
        `except AnsibleError` → propagates past pytest.raises(RealAnsibleError) → test fails.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'myns', 'mycol'))
        # Deliberately no MANIFEST.json in the collection directory

        class _FromPathCalled(Exception):
            pass

        def _sentinel_from_path(b_path, force, parent=None):
            raise _FromPathCalled("from_path was invoked — the MANIFEST.json guard is missing (bug)")

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text), \
             patch.object(source.CollectionRequirement, 'from_path', _sentinel_from_path):

            # Fixed: MANIFEST.json guard fires first → RealAnsibleError → caught here
            # Buggy: from_path called → _FromPathCalled (not AnsibleError) propagates out
            #        → not caught by pytest.raises(RealAnsibleError) → test fails
            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('myns.mycol', '1.0.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )
            assert 'does not appear to have a MANIFEST.json' in exc_info.value.message


def test_verify_collections_error_is_local_manifest_not_remote_lookup():
    """
    Bug: buggy verify_collections skips the MANIFEST.json guard, falls through to
    CollectionRequirement.from_name (with no APIs → 'Failed to find collection'),
    then re-raises as 'Failed to find remote collection...'.

    Fixed code raises immediately inside the search-path loop with a message about the
    missing MANIFEST.json — never reaching any remote API call.

    Distinguishing assertions:
      1. The raised message must NOT contain 'remote collection'  ← fails on buggy code
      2. The raised message must contain 'MANIFEST.json'          ← passes on fixed code
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'acme', 'utils'))
        # Deliberately no MANIFEST.json — directory exists but collection is not installed

        raised_message = None
        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text):
            try:
                source.verify_collections(
                    collections=[('acme.utils', '3.1.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )
            except RealAnsibleError as e:
                raised_message = e.message

        assert raised_message is not None, "Expected AnsibleError to be raised"
        # Buggy:  "Failed to find remote collection acme.utils:3.1.0 on any of the galaxy servers"
        # Fixed:  "Collection acme.utils does not appear to have a MANIFEST.json. ..."
        assert 'remote collection' not in raised_message, (
            "verify_collections should fail locally on missing MANIFEST.json, "
            "not on a remote collection lookup. Got: %r" % raised_message
        )
        assert 'MANIFEST.json' in raised_message, (
            "Expected error to mention MANIFEST.json, got: %r" % raised_message
        )


def test_verify_collections_ignore_errors_warns_about_local_manifest_not_remote():
    """
    With ignore_errors=True and a collection directory missing MANIFEST.json:
    - Fixed code: MANIFEST.json guard fires first → AnsibleError about local check →
      warning contains 'does not appear to have a MANIFEST.json'.
    - Buggy code: no guard → from_path called → remote Galaxy lookup fails →
      warning contains 'Failed to find remote collection' (no MANIFEST.json phrase).
    Assertion FAILS on buggy code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'myns', 'mycol'))
        # No MANIFEST.json — directory exists but collection is not built/installed

        warning_messages = []

        class CapturingDisplay:
            def warning(self, msg):
                warning_messages.append(msg)
            def display(self, *args, **kwargs):
                pass
            def vvv(self, *args, **kwargs):
                pass
            def vvvv(self, *args, **kwargs):
                pass
            def debug(self, *args, **kwargs):
                pass

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text), \
             patch.object(source, 'display', CapturingDisplay()):

            source.verify_collections(
                collections=[('myns.mycol', '1.0.0')],
                search_paths=[tmpdir],
                apis=[],
                validate_certs=False,
                ignore_errors=True,
            )

        combined = ' | '.join(warning_messages)
        # Fixed: caught error is "Collection myns.mycol does not appear to have a MANIFEST.json."
        # Buggy: caught error is "Failed to find remote collection myns.mycol:1.0.0 on any of
        #        the galaxy servers" — the local MANIFEST.json guard was never reached.
        assert 'does not appear to have a MANIFEST.json' in combined, (
            "Expected warning about local missing MANIFEST.json, got: %r" % combined
        )


def test_verify_collections_manifest_missing_message_mentions_ansible_galaxy():
    """
    The fixed code raises with the message:
      'Collection <name> does not appear to have a MANIFEST.json. A MANIFEST.json is expected
       if the collection has been built and installed via ansible-galaxy.'
    Both clauses of that message are verified. Buggy code skips the guard, falls through to
    CollectionRequirement.from_name (empty apis list), and raises:
      'Failed to find remote collection <name>:<ver> on any of the galaxy servers'
    Neither 'does not appear to have a MANIFEST.json' nor 'ansible-galaxy' appears in the
    buggy error — both assertions fail on buggy code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Collection directory exists but contains no MANIFEST.json (e.g. not yet built/installed)
        os.makedirs(os.path.join(tmpdir, 'devco', 'auth'))

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text):

            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('devco.auth', '3.0.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )

        msg = exc_info.value.message
        # Fixed:  "Collection devco.auth does not appear to have a MANIFEST.json.
        #          A MANIFEST.json is expected if the collection has been built and installed via ansible-galaxy."
        # Buggy:  "Failed to find remote collection devco.auth:3.0.0 on any of the galaxy servers"
        assert 'does not appear to have a MANIFEST.json' in msg, (
            "Expected MANIFEST.json guard error, got: %r" % msg
        )
        assert 'ansible-galaxy' in msg, (
            "Expected full fixed-code error mentioning ansible-galaxy, got: %r" % msg
        )


def test_verify_collections_directory_with_other_files_but_no_manifest():
    """
    Bug: buggy verify_collections has no MANIFEST.json guard, so even a directory
    that contains other files (e.g. galaxy.yml) but NOT MANIFEST.json passes straight
    through to CollectionRequirement.from_path, which silently creates a stub
    CollectionRequirement. It then fails at the Galaxy API stage with
    'Failed to find remote collection...' — never mentioning MANIFEST.json.

    Fixed code raises AnsibleError about the missing MANIFEST.json before
    from_path is ever reached.

    Assertion: the error message must contain 'MANIFEST.json' — fails on buggy code
    (which raises about 'remote collection' instead).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = os.path.join(tmpdir, 'vendor', 'toolkit')
        os.makedirs(collection_dir)
        # Directory has a file, just not MANIFEST.json
        with open(os.path.join(collection_dir, 'galaxy.yml'), 'w') as f:
            f.write('namespace: vendor\nname: toolkit\nversion: 2.0.0\n')

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text):

            with pytest.raises(RealAnsibleError) as exc_info:
                source.verify_collections(
                    collections=[('vendor.toolkit', '2.0.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )

            msg = exc_info.value.message
            # Fixed:  "Collection vendor.toolkit does not appear to have a MANIFEST.json. ..."
            # Buggy:  "Failed to find remote collection vendor.toolkit:2.0.0 on any of the galaxy servers"
            assert 'MANIFEST.json' in msg, (
                "Expected error about missing MANIFEST.json, got: %r" % msg
            )
            assert 'vendor.toolkit' in msg, (
                "Expected collection name in error, got: %r" % msg
            )


def test_verify_collections_api_not_called_when_manifest_missing():
    """
    Bug: buggy verify_collections skips the MANIFEST.json guard and calls from_path
    regardless of whether MANIFEST.json is present. from_path succeeds silently (version='*'),
    then the code proceeds to CollectionRequirement.from_name (the Galaxy API lookup path).

    Fixed code raises AnsibleError about missing MANIFEST.json BEFORE ever reaching from_name.

    Strategy: patch from_name with a tracker and verify it is never invoked on fixed code.
    - Fixed code:  MANIFEST.json guard fires first → RealAnsibleError → from_name never called
                   → from_name_called == [] → assertion PASSES
    - Buggy code:  from_path called, succeeds, then from_name is called → from_name_called == [True]
                   → assertion from_name_called == [] FAILS → bug revealed
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'corp', 'utils'))
        # Deliberately NO MANIFEST.json — collection dir exists but is not a built/installed collection

        from_name_called = []

        def tracking_from_name(*args, **kwargs):
            from_name_called.append(True)
            raise RealAnsibleError("sentinel: from_name was invoked")

        with patch.object(source, 'AnsibleError', RealAnsibleError), \
             patch.object(source, '_display_progress', noop_display_progress), \
             patch.object(source, '_tempdir', fake_tempdir), \
             patch.object(source, 'to_bytes', real_to_bytes), \
             patch.object(source, 'to_text', real_to_text), \
             patch.object(source.CollectionRequirement, 'from_name', tracking_from_name):

            try:
                source.verify_collections(
                    collections=[('corp.utils', '1.0.0')],
                    search_paths=[tmpdir],
                    apis=[],
                    validate_certs=False,
                    ignore_errors=False,
                )
            except RealAnsibleError:
                pass  # Both versions raise; we only care WHICH path they took

        # Fixed code never reaches from_name (MANIFEST.json guard fires first)
        # Buggy code calls from_path (no guard), succeeds, then calls from_name
        assert from_name_called == [], (
            "Bug detected: CollectionRequirement.from_name (Galaxy API lookup) was called "
            "%d time(s) despite MANIFEST.json being absent. "
            "Fixed code should raise locally before any API lookup." % len(from_name_called)
        )
