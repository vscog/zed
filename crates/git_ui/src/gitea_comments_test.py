import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reader', Path(__file__).with_name('gitea_comments.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class CommentReaderTest(unittest.TestCase):
    def test_repository_origin_and_base_path(self):
        self.assertEqual(reader.repository_url('http://127.0.0.1:3131/valentin/music-viz.git', 'http://127.0.0.1:3131'), 'valentin/music-viz')
        self.assertEqual(reader.repository_url('https://git.example/gitea/a/b.git', 'https://git.example/gitea'), 'a/b')
        for remote in ('http://evil.example/a/b', 'http://127.0.0.1:3132/a/b', 'https://127.0.0.1:3131/a/b', 'http://user:password@127.0.0.1:3131/a/b', 'git@127.0.0.1:a/b', 'http://127.0.0.1:3131/%2e%2e/b', 'http://127.0.0.1:3131/a%2Fb/c'):
            with self.assertRaises(ValueError):
                reader.repository_url(remote, 'http://127.0.0.1:3131')
        with self.assertRaises(ValueError):
            reader.repository_url('https://git.example/elsewhere/a/b', 'https://git.example/gitea')

    def test_redirect_never_forwards_credentials(self):
        with self.assertRaises(ValueError):
            reader.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://evil.example')


if __name__ == '__main__':
    unittest.main()
