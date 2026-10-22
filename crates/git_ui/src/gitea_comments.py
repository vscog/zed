"""Read Gitea comments using user-owned configuration, never repository commands."""
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Gitea redirected the authenticated request; check base_url")


def git(directory, *args):
    result = subprocess.run(["git", "-C", str(directory), *args], capture_output=True, timeout=10, check=True)
    return result.stdout.decode().strip()


def repository_url(remote, base):
    parsed = urllib.parse.urlsplit(remote)
    trusted = urllib.parse.urlsplit(base)
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise ValueError("Comments require an HTTP(S) remote matching the configured Gitea base_url")
    if (parsed.scheme, parsed.netloc) != (trusted.scheme, trusted.netloc):
        raise ValueError("Remote does not match the configured Gitea server")
    prefix = trusted.path.rstrip('/') + '/'
    if not parsed.path.startswith(prefix):
        raise ValueError("Remote is outside the configured Gitea base path")
    parts = parsed.path[len(prefix):].removesuffix('.git').strip('/').split('/')
    parts = [urllib.parse.unquote(part) for part in parts]
    if len(parts) != 2 or any(not p or p in ('.', '..') or '/' in p or '\\' in p for p in parts):
        raise ValueError("Expected an owner/repository remote")
    return '/'.join(urllib.parse.quote(p, safe='') for p in parts)


def fetch(filename, all_files=False):
    config_path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'zed/gitea-comments.json'
    config = json.loads(config_path.read_text())
    base = config['base_url'].rstrip('/')
    filename = Path(filename).resolve()
    root = Path(git(filename.parent, 'rev-parse', '--show-toplevel'))
    remote = git(root, 'remote', 'get-url', config.get('remote', 'origin'))
    repo = repository_url(remote, base)
    command = config['token_command']
    if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
        raise ValueError('token_command must be an argument array')
    token = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if not token or '\n' in token or '\r' in token:
        raise ValueError('Credential helper returned an invalid token')
    path = filename.relative_to(root).as_posix()
    content = filename.read_text()
    blob = git(root, 'hash-object', '--', str(filename))
    sha = git(root, 'rev-parse', 'HEAD')
    opener = urllib.request.build_opener(NoRedirect())
    comments = []
    for page in range(1, 101):
        query = {'page': page, 'ref': sha}
        if not all_files:
            query['path'] = path
        url = base + '/api/v1/repos/' + repo + '/commit-comments?' + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={'Authorization': 'token ' + token})
        with opener.open(req, timeout=15) as response:
            batch = json.load(response)
        comments.extend(batch)
        if len(batch) < 100:
            break
    for comment in comments:
        comment['inline'] = comment['path'] == path and comment['blob_sha'] == blob
        comment['url'] = base + '/' + repo + '/src/commit/' + comment['commit_sha'] + '/' + urllib.parse.quote(comment['path'], safe='/') + '#L' + str(comment['start_line'] or 1) if comment['path'] else base + '/' + repo + '/commit/' + comment['commit_sha']
    return {'comments': comments, 'content': content, 'path': path}


if __name__ == '__main__':
    try:
        print(json.dumps(fetch(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == 'all')))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        sys.exit(1)
