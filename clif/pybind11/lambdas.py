# Copyright 2021 Google LLC
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
"""Generates C++ lambda functions inside pybind11 bindings code."""

from typing import Generator, Optional

from clif.protos import ast_pb2
from clif.pybind11 import function_lib
from clif.pybind11 import utils

I = utils.I


def generate_lambda(
    module_name: str, func_decl: ast_pb2.FuncDecl,
    class_decl: Optional[ast_pb2.ClassDecl] = None
) -> Generator[str, None, None]:
  """Entry point for generation of lambda functions in pybind11."""
  params_with_type = _generate_lambda_params_with_types(func_decl, class_decl)
  func_name = func_decl.name.native.rstrip('#')  # @sequential
  yield (f'{module_name}.{function_lib.generate_def(func_decl)}'
         f'("{func_name}", []({params_with_type}) {{')
  yield from _generate_lambda_body(func_decl, class_decl)
  yield f'}}, {function_lib.generate_function_suffixes(func_decl)}'


def _generate_lambda_body(
    func_decl: ast_pb2.FuncDecl,
    class_decl: Optional[ast_pb2.ClassDecl] = None
) -> Generator[str, None, None]:
  """Generates body of lambda expressions."""
  function_call = _generate_function_call(func_decl, class_decl)
  function_call_params = _generate_function_call_params(func_decl)
  function_call_returns = _generate_function_call_returns(func_decl)

  # Generates declarations of return values
  for i, r in enumerate(func_decl.returns):
    yield I + f'{r.type.cpp_type} ret{i}{{}};'

  # Generates call to the wrapped function
  if not func_decl.cpp_void_return and len(func_decl.returns):
    yield I + (f'ret0 = {function_call}({function_call_params});')
  else:
    yield I + f'{function_call}({function_call_params});'

  # Generates returns of the lambda expression
  if func_decl.postproc == '->self':
    yield I + 'return self;'
  elif len(func_decl.returns) > 1:
    yield I + f'return std::make_tuple({function_call_returns});'
  else:
    yield I + f'return {function_call_returns};'


def _generate_function_call_params(func_decl: ast_pb2.FuncDecl) -> str:
  """Generates the parameters of function calls in lambda expressions."""
  params = ', '.join([f'{p.name.cpp_name}' for p in func_decl.params])

  # Ignore the return value of the function itself when generating pointer
  # parameters.
  stard_idx = 0
  if not func_decl.cpp_void_return and len(func_decl.returns):
    stard_idx = 1
  pointer_params_str = ', '.join(
      [f'&ret{i}' for i in range(stard_idx, len(func_decl.returns))])

  if params and pointer_params_str:
    return f'{params}, {pointer_params_str}'
  elif pointer_params_str:
    return pointer_params_str
  else:
    return params


def _generate_function_call_returns(func_decl: ast_pb2.FuncDecl) -> str:
  all_returns_list = []
  for i, r in enumerate(func_decl.returns):
    if r.type.lang_type == 'bytes':
      all_returns_list.append(f'py::bytes(ret{i})')
    else:
      all_returns_list.append(f'ret{i}')
  return ', '.join(all_returns_list)


def needs_lambda(func_decl: ast_pb2.FuncDecl) -> bool:
  return (func_decl.postproc == '->self' or
          _func_needs_implicit_conversion(func_decl) or
          _func_has_pointer_params(func_decl) or
          _has_bytes_return(func_decl))


def _generate_lambda_params_with_types(
    func_decl: ast_pb2.FuncDecl,
    class_decl: Optional[ast_pb2.ClassDecl] = None) -> str:
  params_list = [
      f'{p.type.cpp_type} {p.name.cpp_name}' for p in func_decl.params]
  if class_decl and not func_decl.classmethod:
    params_list = [f'{class_decl.name.cpp_name} &self'] + params_list
  return ', '.join(params_list)


def _generate_function_call(
    func_decl: ast_pb2.FuncDecl,
    class_decl: Optional[ast_pb2.ClassDecl] = None):
  if func_decl.classmethod or not class_decl:
    return func_decl.name.cpp_name
  else:
    return f'self.{func_decl.name.cpp_name}'


def _func_has_pointer_params(func_decl: ast_pb2.FuncDecl) -> bool:
  num_returns = len(func_decl.returns)
  return num_returns >= 2 or (num_returns == 1 and func_decl.cpp_void_return)


def _has_bytes_return(func_decl: ast_pb2.FuncDecl) -> bool:
  for r in func_decl.returns:
    if r.type.lang_type == 'bytes':
      return True
  return False


def _func_needs_implicit_conversion(func_decl: ast_pb2.FuncDecl) -> bool:
  """Check if a function contains an implicitly converted parameter."""
  if len(func_decl.params) == 1:
    param = func_decl.params[0]
    if not utils.is_usable_cpp_exact_type(param.cpp_exact_type):
      # Stop-gap approach. This `if` condition needs to be removed after
      # resolution of b/118736768. Until then this detection function cannot
      # work correctly in this situation (but there are no corresponding unit
      # tests).
      return False
    if (_extract_bare_type(param.cpp_exact_type) !=
        _extract_bare_type(param.type.cpp_type) and
        param.type.cpp_toptr_conversion and
        param.type.cpp_touniqptr_conversion):
      return True
  return False


def _extract_bare_type(cpp_name: str) -> str:
  # This helper function is not general and only meant
  # to be used in _func_needs_implicit_conversion.
  t = cpp_name.split(' ')
  if t[0] == 'const':
    t = t[1:]
  if t[-1] in {'&', '*'}:  # Minimum viable approach. To be refined as needed.
    t = t[:-1]
  return ' '.join(t)
