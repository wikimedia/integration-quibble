from glob import glob
from unittest import mock
import os.path

import pytest
from quibble import cmd
import yaml

PLANS_DIR = os.path.join(os.path.dirname(__file__), 'plans')


def plans():
    for plan_filename in sorted(glob(os.path.join(PLANS_DIR, '*.yaml'))):
        with open(plan_filename) as f:
            test_data = yaml.safe_load(f)

        yield pytest.param(
            test_data.get('plan'),
            test_data.get('args', []),
            test_data.get('env', {}),
            id=os.path.relpath(plan_filename, PLANS_DIR),
        )


@pytest.mark.parametrize('expected,args,env', plans())
def test_plan(expected, args, env):
    with mock.patch.dict('os.environ', env, clear=True):
        cmd_args = cmd._parse_arguments(args)
        plan = cmd.QuibbleCmd().build_execution_plan(cmd_args)

    printable_plan = [str(command) for command in plan]

    assert printable_plan == expected
