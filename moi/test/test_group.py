# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from json import dumps
from unittest import TestCase, main

from moi import r_client
from moi.group import Group


class GroupTests(TestCase):
    def setUp(self):
        r_client.hset('user-id-map', 'testing', 'testing')
        r_client.sadd('testing:children', 'a')
        r_client.sadd('testing:children', 'b')
        r_client.sadd('testing:children', 'c')
        r_client.set('a', '{"type": "job", "id": "a", "name": "a"}')
        r_client.set('b', '{"type": "job", "id": "b", "name": "b"}')
        r_client.set('c', '{"type": "job", "id": "c", "name": "c"}')
        r_client.set('d', '{"type": "job", "id": "d", "name": "other job"}')
        r_client.set('e', '{"type": "job", "id": "e", "name": "other job e"}')
        self.obj = Group('testing')
        self.to_delete = ['testing', 'testing:jobs', 'testing:children',
                          'user-id-map', 'a', 'b', 'c', 'd', 'e']

    def tearDown(self):
        for key in self.to_delete:
            r_client.delete(key)

    def test_init(self):
        self.assertEqual(self.obj.group_children, 'testing:children')
        self.assertEqual(self.obj.group_pubsub, 'testing:pubsub')
        self.assertEqual(self.obj.forwarder('foo'), None)

    def test_traverse_simple(self):
        exp = {'a', 'b', 'c'}
        obs = {obj['id'] for obj in self.obj._traverse('testing')}
        self.assertEqual(obs, exp)

    def test_traverse_removed_child(self):
        r_client.delete('b')
        exp = {'a', 'c'}
        obs = {obj['id'] for obj in self.obj._traverse('testing')}
        self.assertEqual(obs, exp)
        self.assertEqual(r_client.smembers('testing:children'), exp)

    def test_traverse_complex(self):
        r_client.sadd('testing:children', 'd')
        r_client.sadd('d:children', 'd_a', 'd_b')
        r_client.set('d', '{"type": "group", "id": "d", "name": "d"}')
        r_client.set('d_a', '{"type": "job", "id": "d_a", "name": "d_a"}')
        r_client.set('d_b', '{"type": "job", "id": "d_b", "name": "d_b"}')
        self.to_delete.append('d:children')
        self.to_delete.append('d_a')
        self.to_delete.append('d_b')
        exp = {'a', 'b', 'c', 'd', 'd_a', 'd_b'}
        obs = {obj['id'] for obj in self.obj._traverse('testing')}
        self.assertEqual(obs, exp)

    def test_del(self):
        pass  # unsure how to test

    def test_close(self):
        pass  # unsure how to test

    def test_decode(self):
        obs = self.obj._decode(dumps({'foo': ['bar']}))
        self.assertEqual(obs, {'foo': ['bar']})

    def test_listen_for_updates(self):
        pass  # nothing to test...

    def test_listen_to_node(self):
        self.assertEqual(sorted(self.obj._listening_to.items()),
                         [('a:pubsub', 'a'),
                          ('b:pubsub', 'b'),
                          ('c:pubsub', 'c')])

    def test_unlisten_to_node(self):
        self.assertEqual(self.obj.unlisten_to_node('b'), 'b')
        self.assertEqual(sorted(self.obj._listening_to.items()),
                         [('a:pubsub', 'a'),
                          ('c:pubsub', 'c')])
        self.assertEqual(self.obj.unlisten_to_node('foo'), None)

    def test_callback(self):
        class forwarder(object):
            def __init__(self):
                self.result = None

            def __call__(self, data):
                self.result = list(data)

        fwd = forwarder()
        self.obj.forwarder = fwd

        self.obj.callback(('message', 'testing:pubsub', dumps({'get': ['b']})))
        self.assertEqual(fwd.result,
                         [{'get': {u'id': u'b',
                                   u'name': u'b',
                                   u'type': u'job'}}])
        self.obj.callback(('message', 'a:pubsub', dumps({'update': ['a']})))
        self.assertEqual(fwd.result, [{'update': {u'id': u'a',
                                                  u'name': u'a',
                                                  u'type': u'job'}}])

        with self.assertRaises(ValueError):
            self.obj.callback(('message', 'testing:pubsub',
                              dumps({'foo': ['bar']})))

        self.assertEqual(self.obj.callback(('a', 'b', 'c')), None)

    def test_action(self):
        class forwarder(object):
            def __init__(self):
                self.result = None

            def __call__(self, data):
                self.result = list(data)

        fwd = forwarder()
        self.obj.forwarder = fwd

        self.obj.action('add', ['d', 'e'])
        self.assertEqual(sorted(fwd.result), sorted([
            {'add': {u'id': u'd', u'name': u'other job', u'type': u'job'}},
            {'add': {u'id': u'e', u'name': u'other job e', u'type': u'job'}}]))
        self.obj.action('remove', ['e', 'd'])
        self.assertEqual(sorted(fwd.result), sorted([
            {'remove':
                {u'id': u'e', u'name': u'other job e', u'type': u'job'}},
            {'remove':
                {u'id': u'd', u'name': u'other job', u'type': u'job'}}]))
        self.obj.action('remove', ['d'])
        self.assertEqual(fwd.result, [])

        with self.assertRaises(TypeError):
            self.obj.action('add', 'foo')

        with self.assertRaises(ValueError):
            self.obj.action('foo', ['d'])

    def test_job_action(self):
        class forwarder(object):
            def __init__(self):
                self.result = None

            def __call__(self, data):
                self.result = list(data)

        fwd = forwarder()
        self.obj.forwarder = fwd

        self.obj.job_action('update', ['a', 'b'])
        self.assertEqual(fwd.result, [{'update': {u'id': u'a',
                                                  u'name': u'a',
                                                  u'type': u'job'}},
                                      {'update': {u'id': u'b',
                                                  u'name': u'b',
                                                  u'type': u'job'}}])

        with self.assertRaises(TypeError):
            self.obj.job_action('add', 'foo')

        with self.assertRaises(ValueError):
            self.obj.job_action('foo', ['d'])

    def test_action_add(self):
        resp = self.obj._action_add(['d', 'f', 'e'])
        self.assertEqual(sorted(resp), sorted([
            {u'id': u'd', u'name': u'other job', u'type': u'job'},
            {u'id': u'e', u'name': u'other job e', u'type': u'job'}]))
        self.assertIn('d:pubsub', self.obj._listening_to)
        self.assertIn('e:pubsub', self.obj._listening_to)
        self.assertNotIn('f:pubsub', self.obj._listening_to)

    def test_action_remove(self):
        self.obj._action_add(['d', 'f', 'e'])
        resp = self.obj._action_remove(['a', 'd', 'f', 'c', 'e'])
        self.assertEqual(sorted(resp), sorted([
            {u'id': u'a', u'name': u'a', u'type': u'job'},
            {u'id': u'd', u'name': u'other job', u'type': u'job'},
            {u'id': u'c', u'name': u'c', u'type': u'job'},
            {u'id': u'e', u'name': u'other job e', u'type': u'job'}]))

        self.assertNotIn('a:pubsub', self.obj._listening_to)
        self.assertNotIn('c:pubsub', self.obj._listening_to)
        self.assertNotIn('d:pubsub', self.obj._listening_to)
        self.assertNotIn('e:pubsub', self.obj._listening_to)
        self.assertNotIn('f:pubsub', self.obj._listening_to)
        self.assertEqual(r_client.smembers('testing:children'), {'b'})

    def test_action_get(self):
        resp = self.obj._action_get(['d', 'f', 'e', None])
        self.assertEqual(sorted(resp), sorted([
            {u'id': u'd', u'name': u'other job', u'type': u'job'},
            {u'id': u'e', u'name': u'other job e', u'type': u'job'}]))


if __name__ == '__main__':
    main()
