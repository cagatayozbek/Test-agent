import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')


def test_source_exists():
    assert os.path.exists(os.path.join(buggy_dir, 'source.py'))


def test_urlparse_imported_from_stdlib():
    """
    Bug: source.py does not import urlparse from urllib.parse.
    urlparse stays as a _Stub, so fetch_role_related cannot parse api_server
    to extract the base URL (scheme://netloc/) when building pagination URLs.
    Fixed: adds 'from urllib.parse import urlparse' (with Python 2 fallback),
    overwriting the stub with the real URL parser.

    FAILS on buggy code (stdlib urlparse import absent from source text).
    PASSES on fixed code (stdlib urlparse import present).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    assert 'from urllib.parse import urlparse' in source_text, (
        "Bug detected: source.py does not import urlparse from urllib.parse. "
        "The buggy code leaves urlparse as a _Stub, so fetch_role_related cannot "
        "correctly strip the API path from api_server when building pagination URLs."
    )


def test_fetch_role_related_uses_urlparse_for_base_url():
    """
    Bug: fetch_role_related paginates using _urljoin(self.api_server, next_link).
    When api_server already contains an API path (e.g. /api/), joining it with
    next_link (which also starts with /api/) duplicates that path segment.
    Fixed: calls urlparse(self.api_server) to extract just scheme://netloc/,
    then joins only that stripped base_url with next_link.

    FAILS on buggy code (urlparse(self.api_server) absent from source text).
    PASSES on fixed code (urlparse call present in fetch_role_related body).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    assert 'urlparse(self.api_server)' in source_text, (
        "Bug detected: fetch_role_related does not call urlparse(self.api_server). "
        "The buggy code uses _urljoin(self.api_server, next_link) directly, which "
        "doubles the /api/ path segment when api_server includes an API path prefix."
    )


def test_fetch_role_related_builds_base_url_from_scheme_and_netloc():
    """
    Bug: the buggy fetch_role_related has no logic to extract scheme/netloc from
    api_server before joining pagination next_link URLs. As a result the full
    api_server path (including any /api/ prefix) is prepended to next_link.
    Fixed: extracts url_info.scheme and url_info.netloc to form a clean base_url.

    FAILS on buggy code (url_info.scheme / url_info.netloc absent from source).
    PASSES on fixed code (both attributes present in fetch_role_related).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    assert 'url_info.scheme' in source_text and 'url_info.netloc' in source_text, (
        "Bug detected: source.py does not build base_url from url_info.scheme/netloc. "
        "The fix for fetch_role_related pagination requires extracting the base URL "
        "as '%s://%s/' % (url_info.scheme, url_info.netloc) to avoid doubling the "
        "API path when joining with next_link."
    )


def test_urlparse_in_module_is_real_not_stub():
    """
    Runtime check: after exec-ing the source with the GalaxyError base-class stub
    patched to Exception, source.urlparse must be the real urlparse from urllib.parse,
    not the _Stub instance the ansible stubs create.

    FAILS on buggy code (source.urlparse is a _Stub — .scheme is a _Stub instance).
    PASSES on fixed code (source.urlparse is the real function — .scheme is a str).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    # Make GalaxyError(AnsibleError) exec-able: AnsibleError stub can't be a base class.
    patched = source_text.replace(
        'class GalaxyError(AnsibleError):',
        'class GalaxyError(Exception):'
    )

    namespace = {}
    exec(patched, namespace)  # noqa: S102

    urlparse_fn = namespace.get('urlparse')
    assert urlparse_fn is not None, "urlparse not found in module namespace after exec"

    result = urlparse_fn('https://galaxy.ansible.com/api/')

    assert isinstance(result.scheme, str), (
        "Bug detected: source.urlparse is not the real urlparse from urllib.parse. "
        "Calling urlparse('https://galaxy.ansible.com/api/').scheme returned "
        "%r (type %s) instead of a plain string. "
        "The buggy code leaves urlparse as a _Stub that returns _Stub instances for "
        "all attribute access, preventing correct base URL extraction in "
        "fetch_role_related." % (result.scheme, type(result.scheme).__name__)
    )
    assert result.scheme == 'https', (
        "Bug detected: urlparse did not parse scheme correctly. "
        "Expected 'https', got %r." % result.scheme
    )
    assert result.netloc == 'galaxy.ansible.com', (
        "Bug detected: urlparse did not parse netloc correctly. "
        "Expected 'galaxy.ansible.com', got %r." % result.netloc
    )


def test_pagination_base_url_is_scheme_netloc_only():
    """
    The pagination bug fix requires urlparse to strip the /api/ path from
    api_server so that joining with next_link does not double the segment.
    This test execs the source and verifies that the complete base_url
    string '%s://%s/' % (scheme, netloc) equals 'https://galaxy.ansible.com/'.

    FAILS on buggy code: urlparse is _Stub, so .scheme and .netloc are
    _Stub instances; the %-format yields a repr string, not the real URL.
    PASSES on fixed code: real urllib.parse.urlparse returns proper
    ParseResult so base_url == 'https://galaxy.ansible.com/'.
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    patched = source_text.replace(
        'class GalaxyError(AnsibleError):',
        'class GalaxyError(Exception):'
    )

    namespace = {}
    exec(patched, namespace)  # noqa: S102

    urlparse_fn = namespace.get('urlparse')
    assert urlparse_fn is not None, "urlparse not defined in module namespace after exec"

    api_server = 'https://galaxy.ansible.com/api/'
    url_info = urlparse_fn(api_server)
    base_url = "%s://%s/" % (url_info.scheme, url_info.netloc)

    assert base_url == 'https://galaxy.ansible.com/', (
        "Bug detected: base_url produced %r; expected 'https://galaxy.ansible.com/'. "
        "The buggy urlparse is a _Stub so .scheme and .netloc are _Stub instances "
        "that stringify to their repr, not real URL components. The fix imports "
        "real urllib.parse.urlparse so that fetch_role_related can strip the /api/ "
        "path segment before building pagination URLs." % base_url
    )


def test_fetch_role_related_pagination_does_not_use_raw_api_server():
    """
    Directly targets the buggy pagination pattern inside fetch_role_related.

    Bug: the while-loop in fetch_role_related calls
      url = _urljoin(self.api_server, data['next_link'])
    When api_server already contains an API sub-path (e.g. /api/v1/), the
    _urljoin call prepends that sub-path again to next_link, doubling the
    segment — producing URLs like /api/v1/api/v1/roles/…

    Fix: derives base_url = "%s://%s/" % (url_info.scheme, url_info.netloc)
    via urlparse BEFORE the loop, then calls _urljoin(base_url, data['next_link'])
    so the scheme+netloc-only base is joined with next_link, not the full api_server.

    FAILS on buggy code: the string "_urljoin(self.api_server, data['next_link'])"
    appears inside fetch_role_related.
    PASSES on fixed code: that string is absent; _urljoin(base_url, …) is used instead.
    """
    import re

    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    # Extract only the fetch_role_related method body so we don't
    # accidentally match the same pattern in other methods.
    match = re.search(
        r'(def fetch_role_related\b.*?)(?=\n    @g_connect|\n    def |\nclass |\Z)',
        source_text,
        re.DOTALL,
    )
    assert match is not None, "fetch_role_related not found in source.py"
    method_body = match.group(1)

    assert "_urljoin(self.api_server, data['next_link'])" not in method_body, (
        "Bug detected: fetch_role_related paginates with "
        "_urljoin(self.api_server, data['next_link']). "
        "When api_server already contains an API sub-path the join doubles that "
        "segment (e.g. /api/v1/ becomes /api/v1/api/v1/ after joining). "
        "The fix uses urlparse(self.api_server) to extract scheme://netloc/ as "
        "base_url, then calls _urljoin(base_url, data['next_link'])."
    )


def test_fetch_role_related_uses_base_url_for_pagination():
    """
    Positive complement to test_fetch_role_related_pagination_does_not_use_raw_api_server.
    The fix must add _urljoin(base_url, data['next_link']) inside fetch_role_related
    so pagination joins against only scheme://netloc/ rather than the full api_server path.

    FAILS on buggy code: _urljoin(base_url, ...) is absent; the method uses
    _urljoin(self.api_server, ...) which doubles the /api/ path segment.
    PASSES on fixed code: _urljoin(base_url, data['next_link']) is present.
    """
    import re

    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    match = re.search(
        r'(def fetch_role_related\b.*?)(?=\n    @g_connect|\n    def |\nclass |\Z)',
        source_text,
        re.DOTALL,
    )
    assert match is not None, "fetch_role_related not found in source.py"
    method_body = match.group(1)

    assert "_urljoin(base_url, data['next_link'])" in method_body, (
        "Bug detected: fetch_role_related does not use _urljoin(base_url, data['next_link']). "
        "The buggy code paginates with _urljoin(self.api_server, data['next_link']), which "
        "doubles the API path segment when api_server already includes /api/ (e.g. "
        "/api/v1/roles/ becomes /api/v1/api/v1/roles/ after joining). "
        "The fix derives base_url = '%s://%s/' % (url_info.scheme, url_info.netloc) via "
        "urlparse(self.api_server), then calls _urljoin(base_url, data['next_link'])."
    )
