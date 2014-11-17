# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------


import json
from unittest import TestCase, main
from time import sleep

from moi import r_client, ctxs
from moi.job import (_status_change, _redis_wrap, submit, _submit,
                     submit_nouser, _deposit_payload, system_call)


class MOITests(TestCase):
    def setUp(self):
        self.test_id = '_moi_test_id'
        self.test_pubsub = '_moi_test_pubsub'
        self.test_keys = [self.test_id, self.test_pubsub]

        self.test_job_info = {'status': 'old status',
                              'id': self.test_id,
                              'pubsub': self.test_pubsub}

    def tearDown(self):
        for k in self.test_keys:
            r_client.delete(k)

    def test_status_change(self):
        new_status = 'new status'

        r_client.set(self.test_id, json.dumps(self.test_job_info))

        obs = _status_change(self.test_id, new_status)
        self.assertEqual(obs, self.test_job_info['status'])

    def test_deposit_payload(self):
        _deposit_payload(self.test_job_info)
        obs = json.loads(r_client.get(self.test_id))
        self.assertEqual(obs, self.test_job_info)

    def test_redis_wrap(self):
        def foo(a, b, **kwargs):
            return a+b

        r_client.set(self.test_job_info['id'], json.dumps(self.test_job_info))
        _redis_wrap(self.test_job_info, foo, 1, 2)

        sleep(2)
        obs = json.loads(r_client.get(self.test_job_info['id']))
        self.assertEqual(obs['result'], 3)
        self.assertEqual(obs['status'], 'Success')
        self.assertNotEqual(obs['date_start'], None)
        self.assertNotEqual(obs['date_end'], None)

        r_client.set(self.test_job_info['id'], json.dumps(self.test_job_info))
        _redis_wrap(self.test_job_info, foo, 1, 2, 3)

        sleep(2)
        obs = json.loads(r_client.get(self.test_job_info['id']))
        self.assertEqual(obs['result'][0],
                         u'Traceback (most recent call last):\n')
        self.assertEqual(obs['status'], 'Failed')
        self.assertNotEqual(obs['date_start'], None)
        self.assertNotEqual(obs['date_end'], None)

    def test_submit(self):
        def foo(a, b, c=10, **kwargs):
            return a+b+c

        for ctx in ctxs:
            id_, pid_ = submit(ctx, 'no parent', 'test', '/', foo, 1, 2, c=15)
            self.test_keys.append(id_)
            self.test_keys.append(pid_)

            sleep(2)

            obs = json.loads(r_client.get(id_))
            self.assertEqual(obs['result'], 18)
            self.assertEqual(obs['status'], 'Success')
            self.assertNotEqual(obs['date_start'], None)
            self.assertNotEqual(obs['date_end'], None)

    def test__submit(self):
        ctx = ctxs.values()[0]
        cmd = 'echo "hello"'
        id_, pid_ = _submit(ctx, 'no parent', 'test', '/', system_call, cmd)
        self.test_keys.append(id_)
        self.test_keys.append(pid_)
        sleep(2)

        obs = json.loads(r_client.get(id_))
        self.assertEqual(obs['result'], [u"hello\n", u"", 0])
        self.assertEqual(obs['status'], 'Success')
        self.assertNotEqual(obs['date_start'], None)
        self.assertNotEqual(obs['date_end'], None)

    def test_submit_nouser(self):
        def foo(a, b, c=10, **kwargs):
            return a+b+c

        id_, pid_ = submit_nouser(foo, 1, 2, c=20)
        self.test_keys.append(id_)
        self.test_keys.append(pid_)

        sleep(2)

        obs = json.loads(r_client.get(id_))
        self.assertEqual(obs['result'], 23)
        self.assertEqual(obs['status'], 'Success')
        self.assertNotEqual(obs['date_start'], None)
        self.assertNotEqual(obs['date_end'], None)


if __name__ == '__main__':
    main()
