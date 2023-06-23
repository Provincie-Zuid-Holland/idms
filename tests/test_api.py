# the inclusion of the tests module is not meant to offer best practices for
# testing in general, but rather to support the `find_packages` example in
# setup.py that excludes installing the "tests" package

import unittest

import idms.api.contentserver as cs


class TestContentServer(unittest.TestCase):
    def test_object_init(self):
        self.assertTrue(isinstance(cs.crawler, object))


if __name__ == "__main__":
    unittest.main()
