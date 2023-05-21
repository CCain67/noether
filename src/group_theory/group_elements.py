"""This module defines several various classes of group elements."""

from __future__ import annotations
from abc import ABC, abstractmethod
from functools import reduce

import math
import numpy
import galois


class GroupElement(ABC):
    """Base class representing elements of arbitrary groups.

    Args:
        None
    """

    @abstractmethod
    def get_order(self):
        """abstract method which computes the order of the group element.

        If g is a group element, then the order of g is the positive
        integer N such that g^N==identity.
        """

    @abstractmethod
    def is_identity(self):
        """abstract method for determining whether or not the GroupElement is
        the identity element of the group.
        """


class CyclicGroupElement(GroupElement):
    """Base class representing elements of cyclic groups."""

    def __init__(self, symbol: str, generator_order: int, power: int) -> None:
        self.symbol = symbol
        self.generator_order = generator_order
        self.power = power % generator_order
        self.order = self.get_order()

    def __repr__(self) -> str:
        if self.power == 0:
            return "1"
        return self.symbol + "^" + str(self.power)

    def __hash__(self):
        return hash((self.symbol, self.generator_order, self.power))

    def __eq__(self, other: CyclicGroupElement) -> bool:
        return all(
            (
                self.symbol == other.symbol,
                self.generator_order == other.generator_order,
                self.power == other.power,
            )
        )

    def __ne__(self, other: CyclicGroupElement) -> bool:
        return any(
            (
                self.symbol != other.symbol,
                self.generator_order != other.generator_order,
                self.power != other.power,
            )
        )

    def __mul__(self, other: CyclicGroupElement) -> CyclicGroupElement:
        if self.symbol != other.symbol or self.generator_order != other.generator_order:
            raise ValueError(
                "the CyclicGroupElements must be elements of the same group for multiplication"
            )
        return CyclicGroupElement(
            self.symbol, self.generator_order, self.power + other.power
        )

    def __pow__(self, power: int):
        if power > 0:
            return reduce(lambda x, y: x * y, [self] * power)
        if power < 0:
            return reduce(lambda x, y: x * y, [~self] * abs(power))
        return CyclicGroupElement(self.symbol, self.generator_order, 0)

    def __invert__(self):
        return CyclicGroupElement(self.symbol, self.generator_order, -1 * self.power)

    def get_order(self):
        return int(self.generator_order / galois.gcd(self.power, self.generator_order))

    def is_identity(self):
        return self.power == 0

    def to_permutation(self) -> Permutation:
        """Converts the cyclic group element to a permutation.

        Returns:
            Permutation: a permutation representation of the cyclic group element.
        """
        generator = {i: i + 1 for i in range(1, self.generator_order)}
        generator[self.generator_order] = 1
        return generator**self.power

    def to_matrix(self) -> Matrix:
        """Converts the cyclic group element into a permutation matrix (with
        Z/2Z coefficients).

        Returns:
            Matrix: a permutation matrix representing the cyclic group element.
        """
        GF = galois.GF(2)
        generator = {i: i + 1 for i in range(1, self.generator_order)}
        generator[self.generator_order] = 1
        matrix_generator = GF.Zeros((self.generator_order, self.generator_order))
        for k in generator.keys():
            matrix_generator[k - 1, generator[k] - 1] = 1
        return Matrix(matrix_generator, 2, 1)


class PolyhedralGroupElement(GroupElement):
    """Class representing elements of the general polyhedral groups. For now,
    this includes dihedral, quasidihedral, and dicyclic/generalized quaternion
    groups.

    In each of these groups, there are two generators r and s, and all
    elements may be written as a product of the form r^ks^i for some exponent k,
    and i = 0 or 1.

    The generator r can be thought of as a generalized rotation, and the generator
    s can be thought of as a generalized reflection.

    Args:
        exponents tuple(int): a pair (k,i) where k is the power of r,
        and i is the power of s, as above.
        n (int): the parameter n used in the definition of the polyhedral
        group.
    """

    def __init__(self, exponents: tuple(int), n: int) -> None:
        self.exponents = (exponents[0], exponents[1] % 2)
        self.n = n
        self.modulus = None
        self.shift = None
        self.half_shift = None
        self.r_symb = "r"
        self.s_symb = "s"

    def __repr__(self) -> str:
        if self.is_identity():
            return "1"
        r_str = ""
        s_str = ""
        if self.exponents[0] > 0:
            r_str = self.r_symb + "^" + str(self.exponents[0])
        if self.exponents[1] == 1:
            s_str += self.s_symb
        return r_str + s_str

    def __eq__(self, other) -> bool:
        return (self.exponents == other.exponents) and (self.n == other.n)

    def __hash__(self) -> int:
        return hash((self.exponents, self.n))

    def __mul__(self, other):
        k = self.exponents[0]
        i = self.exponents[1]
        m = other.exponents[0]
        j = other.exponents[1]
        n = self.n

        new_r_exponent = (
            k + self.half_shift * i * j * n + self.shift * m
        ) % self.modulus
        new_s_exponent = (i + j) % 2
        return self.__class__((new_r_exponent, new_s_exponent), self.n)

    def __invert__(self):
        k = self.exponents[0]
        i = self.exponents[1]
        n = self.n

        k_inv = (
            (self.modulus - k - self.half_shift * (i**2) * n) * self.shift
        ) % self.modulus
        return self.__class__((k_inv, i), self.n)

    def __pow__(self, power: int):
        if power > 0:
            return reduce(lambda x, y: x * y, [self] * power)
        if power < 0:
            return reduce(lambda x, y: x * y, [~self] * abs(power))
        return self.__class__((0, 0), self.n)

    def get_order(self) -> int:
        count = 1
        product = self
        while not product.is_identity():
            product = product * self
            count += 1
        return count

    def is_identity(self) -> bool:
        return self.exponents == (0, 0)


class DihedralGroupElement(PolyhedralGroupElement):
    """Class representing elements of dihedral groups.

    Args:
        exponents (tuple[int]): a pair of exponents (k,i)
        representing an element r^ks^i of the dihedral group.
        n (int): the order of the rotation r.
    """

    def __init__(self, exponents: tuple(int), n: int) -> None:
        exponents = (exponents[0] % n, exponents[1])
        super().__init__(exponents, n)

        self.modulus = n
        self.shift = (-1) ** exponents[1]
        self.half_shift = 0

    def to_permutation(self) -> Permutation:
        """Method which converts a dihedral group element into a permutation.

        Returns:
            Permutation: permutation representation of the dihedral group element.
        """
        cycle = {**{i: i + 1 for i in range(1, self.n)}, self.n: 1}
        flip = {1: 1, **{2 + i: self.n - i for i in range(self.n - 1)}}

        r = Permutation(cycle)
        s = Permutation(flip)
        return (r ** self.exponents[0]) * (s ** self.exponents[1])

    def to_matrix(self) -> Matrix:
        """Method which converts a dihedral group element into a matrix.

        Returns:
            Matrix: matrix representation of the dihedral group element.
        """
        return self.to_permutation().to_matrix()


class QuasidihedralGroupElement(PolyhedralGroupElement):
    """Class representing elements of quasidihedral groups.

    Args:
        exponents (tuple[int]): a pair of exponents (k,i)
        representing an element r^ks^i of the quasidihedral group.
        n (int): the order of the generalized rotation r.
    """

    def __init__(self, exponents: tuple(int), n: int) -> None:
        exponents = (exponents[0] % (2 ** (n - 1)), exponents[1])
        super().__init__(exponents, n)

        self.modulus = 2 ** (n - 1)
        self.shift = (self.modulus - 1) ** exponents[1]
        self.half_shift = 0


class DicyclicGroupElement(PolyhedralGroupElement):
    """Class representing elements of dicyclic groups.

    Args:
        exponents (tuple[int]): a pair of exponents (k,i)
        representing an element a^kx^i of the dicyclic group.
        n (int): the order of the generalized rotation a.
    """

    def __init__(self, exponents: tuple(int), n: int) -> None:
        exponents = (exponents[0] % (2 * n), exponents[1])
        super().__init__(exponents, n)

        self.modulus = 2 * n
        self.shift = (-1) ** exponents[1]
        self.half_shift = 0
        self.r_symb = "a"
        self.s_symb = "x"


class Permutation(GroupElement):
    """Class representing an element of a permutation group.

    Args:
        permutation (dict): a dictionary representation of the permutation.

    Examples:
        The permutation on the symbols 1,2,3,4,5 which sends:

        1 -> 2
        2 -> 3
        3 -> 1
        4 -> 5
        5 -> 1

        is represented by the dictionary {1:2, 2:3, 3:1, 4:5, 5:4}.
    """

    def __init__(self, permutation: dict):
        self.permutation = permutation
        self.num_letters = len(self.permutation)

        # properties
        self._cycle_decomposition = None
        self._cycle_notation = None
        self._cycle_type = None
        self._order = None
        self._sign = None

    def __repr__(self) -> str:
        return self.cycle_notation

    def __getitem__(self, key):
        return self.permutation[key]

    def __len__(self):
        length = len({k: self[k] for k in self.permutation.keys() if k != self[k]})
        if length == 0:
            return 1
        return length

    def __eq__(self, other):
        return self.permutation == other.permutation

    def __ne__(self, other):
        return not self.permutation == other.permutation

    def __hash__(self):
        return hash(frozenset(self.permutation.items()))

    def __mul__(self, other):
        composition = {
            i: self.permutation[other.permutation[i]] for i in self.permutation
        }
        return Permutation(composition)

    def __pow__(self, power: int):
        if power > 0:
            return reduce(lambda x, y: x * y, [self] * power)
        if power < 0:
            return reduce(lambda x, y: x * y, [~self] * abs(power))
        return Permutation({i: i for i in range(1, self.num_letters + 1)})

    def __invert__(self):
        inverse = {self.permutation[k]: k for k in self.permutation.keys()}
        return Permutation(inverse)

    def find_cycle_dict(self, start: int) -> dict:
        """iterates through the permutation beginning at the starting integer provided, and
        returns the cycle which starts at the provided integer.

        Args:
            start (int): the starting symbol of the cycle

        Returns:
            dict: dictionary representing the cycle

        Example:
            Consider the permutation on the symbols 1,2,3,4,5 represented by the dictionary:

            p = {1:2, 2:3, 3:1, 4:5, 5:4}.

            If the starting point 1 is provided, then find_cycle_dict(1) returns:

            {1:2, 2:3, 3:1}.

            If the starting point 4 is provided, then find_cycle_dict(4) returns:

            {4:5 ,5:4}.
        """
        current_key = start
        cycle = {}
        while self.permutation[current_key] != start:
            cycle[current_key] = self.permutation[current_key]
            current_key = self.permutation[current_key]
        cycle[current_key] = self.permutation[current_key]

        return cycle

    def get_cycle_notation(self) -> str:
        """Produces the cycle decomposition of the permutation as a string

        Returns:
            str: string representing the cycle decomposition

        Example:
            Consider the permutation on the symbols 1,2,3,4,5 represented by the dictionary:

            p = {1:2, 2:3, 3:1, 4:5, 5:4}.

            then get_cycle_notation() returns:

            (4 5)(1 2 3).
        """
        if self.is_identity():
            return "1"
        key_set = set(self.permutation.keys())
        updated_key_set = key_set
        cycle_list = []
        while len(updated_key_set) > 0:
            for k in key_set:
                if k in updated_key_set:
                    cycle = self.find_cycle_dict(start=k)
                    if len(cycle) > 1:  # ignore cycles of the form (j)
                        cycle_string = "(" + " ".join([str(i) for i in cycle]) + ")"
                        cycle_list.append(cycle_string)
                    updated_key_set = updated_key_set - set(cycle.keys())
        return "".join(cycle_list[::-1])

    def get_cycle_decomposition(self) -> list[Permutation]:
        """Produces the cycle decomposition of the permutation.

        Returns:
            list: list of Permutations in the cycle decomposition

        Example:
            Consider the permutation on the symbols 1,2,3,4,5 represented by the dictionary:

            p = {1:2, 2:3, 3:1, 4:5, 5:4}.

            then get_cycle_decomposition() returns:

            [Permutation({1:1, 2:2, 3:3, 4:5, 5:4}), Permutation({1:2, 2:3, 3:1, 4:4, 5:5})].
        """
        key_set = set(self.permutation.keys())
        updated_key_set = key_set
        cycle_list = []
        while len(updated_key_set) > 0:
            for k in key_set:
                if k in updated_key_set:
                    cycle = self.find_cycle_dict(start=k)
                    updated_key_set = updated_key_set - set(cycle.keys())
                    for i in set(self.permutation.keys()) - set(cycle.keys()):
                        cycle[i] = i
                    cycle_list.append(Permutation(cycle))

        return cycle_list

    def get_cycle_type(self) -> list[int]:
        """Produces the cycle type of the permutation.

        Returns:
            list: list of integers

        Example:
            Consider the permutation on the symbols 1,2,3,4,5 represented by the dictionary:

            p = {1:2, 2:3, 3:1, 4:5, 5:4}.

            then get_cycle_type() returns:

            [2, 3].
        """
        return sorted([len(p) for p in self.cycle_decomposition])

    @property
    def cycle_decomposition(self):
        """Fetches the cycle decomposition property"""
        if self._cycle_decomposition is None:
            self._cycle_decomposition = self.get_cycle_decomposition()
            return self._cycle_decomposition
        return self._cycle_decomposition

    @property
    def cycle_notation(self):
        """Fetches the cycle notation property"""
        if self._cycle_notation is None:
            self._cycle_notation = self.get_cycle_notation()
            return self._cycle_notation
        return self._cycle_notation

    @property
    def cycle_type(self):
        """Fetches the cycle type property"""
        if self._cycle_type is None:
            self._cycle_type = self.get_cycle_type()
            return self._cycle_type
        return self._cycle_type

    def get_order(self):
        count = 1
        product = self
        while not product.is_identity():
            product = product * self
            count += 1
        return count

    @property
    def order(self):
        """Fetches the order property"""
        if self._order is None:
            self._order = self.get_order()
            return self._order
        return self._order

    @property
    def sign(self):
        """Fetches the sign property"""
        if self._sign is None:
            self._sign = numpy.linalg.det(self.to_matrix().matrix)
            return self._sign
        return self._sign

    def is_transposition(self) -> bool:
        """Determines whether or not the permutation is a transposition,
        i.e., if the permutation acts via swapping only two symbols.

        Examples:
            The permutation (3 4) is a transposition, while (1 4 5) is not.

        Returns:
            bool: True if the permutation is a transposition, False otherwise.
        """
        return (
            len([i for i in self.permutation.keys() if i != self.permutation[i]]) == 2
        )

    def is_cycle(self) -> bool:
        """Determines whether or not the permutation is a cycle.

        Examples:
            The permutation (3 4 1) is a cycle, while (1 4)(3 5) is not.

        Returns:
            bool: True if the permutation is a cycle, False otherwise.
        """
        if len(self.cycle_decomposition) == 1:
            return True
        return False

    def is_identity(self):
        """Determines whether or not the permutation is the identity permutation.

        Returns:
            bool: True if the permutation is the identity, False otherwise.
        """
        return self.permutation == {i: i for i in self.permutation.keys()}

    def to_matrix(self):
        """Converts the permutation into a matrix.

        Example:
            The permutation matrix associated with the permutation (2 3) on
            3 symbols 1,2,3 is:

            [[1, 0, 0],
             [0, 0, 1],
             [0, 1, 0]].

        Returns:
            Matrix: the permutation matrix associated to the permutation.
        """
        shape = (self.num_letters, self.num_letters)
        matrix = numpy.zeros(shape)
        for k in self.permutation.keys():
            matrix[k - 1, self.permutation[k] - 1] = 1
        return Matrix(matrix, characteristic=2, degree=1)


class Matrix(GroupElement):
    """Class representing matrices over finite fields.

    Args:
        - matrix (galois.FieldArray): a square matrix (FieldArray) from the galois package
        - characteristic (int): the characteristic of the ground field the matrix is over
        - degree (int): for every finite field of prime power order p^n, the positive integer
        n is usually referred to as the "degree".

    Examples:
        The matrix:

        [[1, 2, 0],
         [0, 1, 5],
         [0, 0, 3]]

         is a matrix over the field Z/7Z of characteristic 7 and degree 1.
    """

    def __init__(self, matrix: galois.FieldArray, characteristic: int, degree: int):
        self.matrix = matrix
        self.characteristic = characteristic
        self.degree = degree
        self.dimension = self.matrix.shape[0]

        self._order = None

    def __repr__(self):
        rep = self.matrix.__repr__()
        return rep

    def __eq__(self, other):
        return (self.matrix == other.matrix).all()

    def __ne__(self, other):
        return (self.matrix != other.matrix).all()

    def __hash__(self) -> int:
        return hash((self.matrix.tostring(), self.characteristic, self.degree))

    def __mul__(self, other):
        return Matrix(self.matrix @ other.matrix, self.characteristic, self.degree)

    def __invert__(self):
        return Matrix(numpy.linalg.inv(self.matrix), self.characteristic, self.degree)

    def __pow__(self, power: int):
        if power > 0:
            return reduce(lambda x, y: x * y, [self] * power)
        if power < 0:
            return reduce(lambda x, y: x * y, [~self] * abs(power))
        return Matrix(numpy.eye(self.dimension), self.characteristic, self.degree)

    def get_order(self):
        matrix_product = self
        i = 1
        while not matrix_product.is_identity():
            matrix_product *= self
            i += 1
        return i

    @property
    def order(self):
        """Fetches the order of the matrix in GL(n,q). Here, q is the prime power
        equal to:
            q = characteristic^degree
        """
        if self._order is None:
            self._order = self.get_order()
            return self._order
        return self._order

    def is_identity(self):
        return (
            self.matrix
            == galois.GF(self.characteristic, self.degree).Identity(self.dimension)
        ).all()


class CartesianProductElement(GroupElement):
    """Class representing an element of a cartesian product of groups.

    Args:
        elements (tuple): a tuple of group elements.

    Example:
        If G and H are groups, then an element of the cartesian product GxH
        is a tuple of the form (g,h) where g is an element of G and h is an element of H.

        For two CartesianProductElements (a,b) and (x,y) (so a,x are in G and b,y are in H)
        multiplication is carried out via:

        (a,b)*(x,y) = (a*x, b*y)

        where the multiplication in the first coordinate is carried out in G, and multiplication
        in the second coordinate is carried out in H.
    """

    def __init__(self, elements: tuple[GroupElement]) -> None:
        self.elements = self._flatten_nested_tuple(elements)
        self.num_elements = len(self.elements)

    def _flatten_nested_tuple(self, nested_tuple: tuple) -> tuple[GroupElement]:
        """Reduces a nested tuple into a single tuple. Example:

        (((1,2),3),4) -> (1,2,3,4)

        Args:
            nested_tuple (tuple): a nested tuple of the form shown above.

        Returns:
            tuple[GroupElement]: a flattened tuple.
        """

        def reducer(acc, val):
            if isinstance(val, CartesianProductElement):
                return acc + self._flatten_nested_tuple(val)
            return acc + (val,)

        return reduce(reducer, nested_tuple, ())

    def __repr__(self):
        return str(tuple(x for x in self.elements))

    def __hash__(self):
        return hash(self.elements)

    def __eq__(self, other):
        return self.elements == other.elements

    def __ne__(self, other):
        return not self.elements == other.elements

    def __mul__(self, other):
        if len(self.elements) != len(other.elements):
            raise ValueError("the length of the cartesian products do not match")
        product = tuple(x * y for x, y in zip(self.elements, other.elements))
        return CartesianProductElement(product)

    def __invert__(self):
        inv = tuple(~x for x in self.elements)
        return CartesianProductElement(inv)

    def __getitem__(self, key):
        return self.elements[key]

    def __iter__(self):
        return iter(self.elements)

    def get_order(self):
        return math.lcm(*[x.order for x in self.elements])

    def is_identity(self):
        return [x.is_identity() for x in self.elements] == [True] * self.num_elements
