from json import dumps
from unittest import TestCase, main

from moi import r_client
from moi.group import Group


class GroupTests(TestCase):
    def setUp(self):
        r_client.sadd('testing:jobs', 'a')
        r_client.sadd('testing:jobs', 'b')
        r_client.sadd('testing:jobs', 'c')
        r_client.set('a', '"job a"')
        r_client.set('b', '"job b"')
        r_client.set('c', '"job c"')
        r_client.set('d', '"other job"')
        r_client.set('e', '"other job e"')
        self.obj = Group('testing')

    def tearDown(self):
        r_client.delete('testing:jobs')

    def test_init(self):
        self.assertEqual(self.obj.group_jobs, 'testing:jobs')
        self.assertEqual(self.obj.group_pubsub, 'testing:pubsub')
        self.assertEqual(self.obj.forwarder('foo'), None)

    def test_del(self):
        pass  # unsure how to test

    def test_close(self):
        pass  # unsure how to test

    def test_decode(self):
        obs = self.obj._decode(dumps({'foo': ['bar']}))
        self.assertEqual(obs, {'foo': ['bar']})

    def test_listen_for_updates(self):
        pass  # nothing to test...

    def test_listen_to_job(self):
        self.assertEqual(sorted(self.obj._listening_to.items()),
                         [('a:pubsub', 'a'),
                          ('b:pubsub', 'b'),
                          ('c:pubsub', 'c')])

    def test_unlisten_to_job(self):
        self.assertEqual(self.obj.unlisten_to_job('b'), 'b')
        self.assertEqual(sorted(self.obj._listening_to.items()),
                         [('a:pubsub', 'a'),
                          ('c:pubsub', 'c')])
        self.assertEqual(self.obj.unlisten_to_job('foo'), None)

    def test_callback(self):
        class forwarder(object):
            def __init__(self):
                self.result = None
            def __call__(self, data):
                self.result = list(data)

        fwd = forwarder()
        self.obj.forwarder = fwd

        self.obj.callback(('message', 'testing:pubsub', dumps({'get': ['b']})))
        self.assertEqual(fwd.result, [{'get': ["job b"]}])
        self.obj.callback(('message', 'a:pubsub', dumps({'update': ['a']})))
        self.assertEqual(fwd.result, [{'update': ["job a"]}])

        with self.assertRaises(ValueError):
            self.obj.callback(('message', 'testing:pubsub',
                              dumps({'foo': ['bar']})))

        self.assertEqual(self.obj.callback(('a', 'b', 'c')), None)

    def test_action(self):
        resp = self.obj.action('add', ['d', 'e'])
        self.assertEqual(resp, {'add': ["other job", "other job e"]})
        resp = self.obj.action('remove', ['e', 'd'])
        self.assertEqual(resp, {'remove': ["other job e", "other job"]})
        resp = self.obj.action('remove', ['d'])
        self.assertEqual(resp, {'remove': []})

        with self.assertRaises(TypeError):
            self.obj.action('add', 'foo')

        with self.assertRaises(ValueError):
            self.obj.action('foo', ['d'])

    def test_job_action(self):
        resp = self.obj.job_action('update', ['a', 'b'])
        self.assertEqual(resp, {'update': ["job a", "job b"]})

        with self.assertRaises(TypeError):
            self.obj.job_action('add', 'foo')

        with self.assertRaises(ValueError):
            self.obj.job_action('foo', ['d'])

    def test_action_add(self):
        resp = self.obj._action_add(['d', 'f', 'e'])
        self.assertEqual(resp, ['other job', 'other job e'])
        self.assertIn('d:pubsub', self.obj._listening_to)
        self.assertIn('e:pubsub', self.obj._listening_to)
        self.assertNotIn('f:pubsub', self.obj._listening_to)

    def test_action_remove(self):
        self.obj._action_add(['d', 'f', 'e'])
        resp = self.obj._action_remove(['a', 'd', 'f', 'c', 'e'])
        self.assertEqual(resp, ['job a', 'other job', 'job c', 'other job e'])
        self.assertNotIn('a:pubsub', self.obj._listening_to)
        self.assertNotIn('c:pubsub', self.obj._listening_to)
        self.assertNotIn('d:pubsub', self.obj._listening_to)
        self.assertNotIn('e:pubsub', self.obj._listening_to)
        self.assertNotIn('f:pubsub', self.obj._listening_to)
        self.assertEqual(r_client.smembers('testing:jobs'), {'b'})

    def test_action_get(self):
        resp = self.obj._action_get(['d', 'f', 'e', None])
        self.assertEqual(resp, ['other job', 'other job e'])


if __name__ == '__main__':
    main()
