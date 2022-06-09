from typing import Iterable, List, Tuple

import relic.sga
from relic.sga import v2, v5, v9, vX
import pytest

MODULES = [v2, v5, v9]
ATTRS = vX.required_attrs
APIS = relic.sga.APIS.values()


def _permutate(*items: List):
    def inner_permutate(subset: List, remaining: Tuple[List]) -> Iterable:
        for item in subset:
            if len(remaining) > 1:
                for sub_items in inner_permutate(remaining[0], remaining[1:]):
                    yield item, *sub_items  # Not possiblie in 3.7-, but we target 3.9+
            else:
                for sub_item in remaining[0]:
                    yield item, sub_item

    if len(items) == 0:
        return []
    elif len(items) == 1:
        return items[0]
    else:
        return inner_permutate(items[0], items[1:])


@pytest.mark.parametrize(["module"], [(m,) for m in MODULES])
def test_module_is_vX_api(module):
    assert vX.is_module_api(module)


@pytest.mark.parametrize(["module", "attr"], _permutate(MODULES, ATTRS))
def test_module_has_required_vX_attr(module, attr: str):
    assert hasattr(module, attr)


@pytest.mark.parametrize(["api", "attr"], _permutate(APIS, ATTRS))
def test_api_has_required_vX_attr(api, attr: str):
    assert hasattr(api, attr)
