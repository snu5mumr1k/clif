# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from absl.testing import absltest
from clif.testing.python import simple_type_conversions as mut


class SimpleTypeConversions(absltest.TestCase):

  def testSignedCharManipulation(self):
    self.assertEqual(mut.SignedCharManipulation(2), 29)
    for inp in [-129, 128]:
      with self.assertRaises(ValueError) as ctx:
        mut.SignedCharManipulation(inp)
      self.assertEqual(
          str(ctx.exception),
          'SignedCharManipulation() argument inp is not valid:'
          ' value %d is out of range for signed char' % inp)

  def testUnsignedCharManipulation(self):
    self.assertEqual(mut.UnsignedCharManipulation(3), 39)
    with self.assertRaises(ValueError) as ctx:
      mut.UnsignedCharManipulation(256)
    self.assertEqual(
        str(ctx.exception),
        'UnsignedCharManipulation() argument inp is not valid:'
        ' value 256 is too large for unsigned char')


if __name__ == '__main__':
  absltest.main()
