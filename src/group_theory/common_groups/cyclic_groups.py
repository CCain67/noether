"""This module defines functions for constructing cyclic groups"""

from group_theory.group_elements import CyclicGroupElement
from group_theory.groups import Group


def cyclic_group(
    N: int, generator_symbol: str = "a", representation: str = "symbolic"
) -> Group:
    """Constructs the cyclic group of order N.

    Args:
        N (int): order of the cyclic group to be constructed
        generator_symbol (str): the symbol used to represent the generator of the group.
        representation (str, optional): Representation of the cyclic group elements.
        Defaults to "residue".

    Raises:
        ValueError: Raised if a bad representation option is passed.

    Returns:
        Group: the cyclic group of order N.
    """
    if representation not in ["symbolic", "permutation", "matrix"]:
        raise ValueError(
            'representation must be one of: "symbolic", "permutation", or "matrix"'
        )

    g = CyclicGroupElement(generator_symbol, N, 1)
    if representation == "permutation":
        g = g.to_permutation()
    elif representation == "matrix":
        g = g.to_matrix()

    cyc_group = Group([g**j for j in range(N)])
    cyc_group.canonical_generators = [g]
    return cyc_group
