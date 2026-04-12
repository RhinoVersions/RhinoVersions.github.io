import unittest
import os
import sys

# A very basic sanity check on index.html
class TestIndexErrors(unittest.TestCase):
    def test_error_states_exist(self):
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('id="error-latest"', content)
        self.assertIn('id="error-all"', content)
        self.assertIn('window.location.reload()', content)
        self.assertIn('Refresh Page', content)
        self.assertIn('var(--color-error)', content)

if __name__ == '__main__':
    unittest.main()
