#!/usr/bin/env python

"""Solves sudoku puzzles."""

###########
# Imports #
###########

import copy
import re

try:
    from itertools import combinations
except ImportError:
    from permutations import combinations


#############
# Functions #
#############

def cross(ms, ns):
    """Returns a basic cross product matrix of two iters."""
    return [m + n for m in ms for n in ns]


###########
# Classes #
###########

class InvalidCellValue(ValueError):
    """Indicates an invalid value was assigned to a cell."""
    pass


class Sudoku(object):
    """A class representing a sudoku object."""

    digits = frozenset([1, 2, 3, 4, 5, 6, 7, 8, 9])
    valid_chars = frozenset('0.-') | frozenset(map(str, digits))

    rows = cols = 'ABCDEFGHI'

    row_triplets = (rows[:3], rows[3:6], rows[6:])
    col_triplets = (cols[:3], cols[3:6], cols[6:])

    last_row_in_box = (rows[2], rows[5])
    last_col_in_box = (cols[2], cols[5])

    squares = frozenset(cross(rows, cols))

    def __init__(self, cells=None):
        """
        Constructor for Sudoku.  Accepts a string representing a sudoku board.
        """

        # Create lists of sets for all columns, rows, and boxes.
        self.col_list = [set(cross(self.rows, c)) for c in self.cols]
        self.row_list = [set(cross(r, self.cols)) for r in self.rows]
        self.box_list = [set(cross(rs, cs)) for rs in self.row_triplets
                                            for cs in self.col_triplets]

        # It's useful to have a list of all unit sets.
        self.unit_list = self.col_list + self.row_list + self.box_list

        # Compile a set of all units for each given square.
        self.units = dict((s, [u for u in self.unit_list if s in u])
                      for s in self.squares)

        # Compile a set of all peers for each given square.
        # *** IMPORTANT NOTE *** IMPORTANT NOTE *** IMPORTANT NOTE ***
        # NOTE: Once a square is removed from self.peers, it is considered
        # "INKED".  That value is "set" and can will not be altered, or
        # searched on.
        # *** IMPORTANT NOTE *** IMPORTANT NOTE *** IMPORTANT NOTE ***
        self.peers = dict((s, set(s2 for u in self.units[s]
                                     for s2 in u if s2 != s)) for
                          s in self.squares)

        # To start, every square can be any digit.
        self.cells = dict((s, set(self.digits)) for s in self.squares)

        # Parse the cells if one was passed in.
        if not cells is None:
            self.parse_cells(cells)

    def parse_cells(self, cells):
        """Parse a string of 81 values into self.cells."""

        # Read in the cells from the string.
        cells = filter(self.valid_chars.__contains__, cells)
        cells = map(int, re.sub(r'\D', '0', cells))

        # Put each value into the cells.
        for square, value in zip(sorted(self.squares), cells):
            if value in self.digits:
                self.assign(square, value)

    def __str__(self):
        """An ascii representation of the Sudoku."""

        # All cells will be of the same width.
        width = 1 + max(len(self.cells[s]) for s in self.squares)

        # Compile all lines into lines.
        lines = []
        for r in self.rows:

            # Compile all columns into line.
            line = []
            for c in self.cols:
                line.append(''.join(map(str,
                    sorted(self.cells[r + c]))).center(width))

                # If this is the end of the box, add a box separator.
                if c in self.last_col_in_box:
                    line.append('|')

            lines.append(''.join(line))

            # If this is the end of a box, add a box separator.
            if r in self.last_row_in_box:
                lines.append('+'.join(['-' * (width * 3)] * 3))

        return '\n'.join(lines)

    # Now for the "solving logic steps".
    ####################################

    def assign(self, square, value):
        """Set a square's value and eliminate that value from all peers."""

        # Check if the value is valid in the square.
        if value not in self.cells[square]:
            raise InvalidCellValue("%s can't contain %s." % (square, value))

        # Set the value
        self.cells[square] = set((value,))

        # Eliminate value from all of square's peers
        for peer in self.peers[square]:
            self.cells[peer].discard(value)

        # Clean up square from the remaining data.
        # It's no longer needed.
        del self.peers[square]
        del self.units[square]
        for peer in self.peers.values():
            peer.discard(square)
        for unit in self.unit_list:
            unit.discard(square)

    def solve_logic(self):
        """Run through each test, searching for new data."""
        while self.peers:
            if self.find_singletons():
                continue
            if self.hidden_singleton():
                continue
            if self.find_hidden_or_naked(2):
                continue
            if self.find_hidden_or_naked(3):
                continue
            if self.find_hidden_or_naked(4):
                continue
            if self.find_hidden_or_naked(5):
                continue
            return False
        return True

    def find_singletons(self):
        """
        Look for un-decided cells which only contain a single possible value.
        """
        for square in self.peers.keys():
            if 1 == len(self.cells[square]):
                self.assign(square, self.cells[square].copy().pop())
                return True
        return False

    def hidden_singleton(self):
        """
        Look for a number in any unit (row, box, or column) which
        does not appear in any other cell in that unit.
        """
        # NOTE: This function really is a special sub-set of
        # self.find_hidden_naked where count=1
        # But this is most likely more efficient.
        for digit in self.digits:
            for unit in self.unit_list:
                valid_squares = [s for s in unit if digit in self.cells[s]]
                if 1 == len(valid_squares):
                    self.assign(valid_squares[0], digit)
                    return True
        return False

    def find_hidden_or_naked(self, count):
        """
        Look for hidden pairs, triplets, quads, ...
        Look for naked: pairs, triplets, quads, ...
        This also covers intersection removal.
        """
        success = False

        # Begin by running through each unit.
        for unit in self.unit_list:

            # Naked triplets in a unit that only has 2 squares is impossible.
            if len(unit) <= count:
                continue

            # Check each combination of cursor squares in the unit.
            for cursors in map(set, combinations(unit, count)):
                success |= self.check_hidden(cursors, unit)
                success |= self.check_naked(cursors)

        return success

    def check_hidden(self, cursors, unit):
        """Checks to see if cursors contains hidden pairs, or triplets, or..."""
        success = False

        # Determine which values are present in cursors.
        values = set()
        for square in cursors:
            values |= self.cells[square]

        # Keep track of those values, for later comparison.
        old_values = values.copy()

        # Remove the values from all other squares within the unit.
        for square in unit - cursors:
            values -= self.cells[square]

        # If there are the same number of values as there are cursors,
        # the group is a hidden group.
        if len(values) == len(cursors):

            # If old_values is the same as values, it's still a hidden set, but
            # there's no new data gained.  Therefore, there would be no
            # success.
            success |= old_values != values

            # Clear the non-hidden values away from each cursor.
            for square in cursors:
                self.cells[square] &= values

        return success

    def check_naked(self, cursors):
        """Checks to see if cursors contains naked pairs, or triplets, or..."""
        success = False

        # Determine which values are present in cursors.
        values = set()
        for square in cursors:
            values |= self.cells[square]

        # If there the same number of values as there are cursors,
        # the group is a naked group.
        if len(values) == len(cursors):

            # Find all common peers between the cursors.
            valid_peers = set(self.squares)
            for square in cursors:
                valid_peers &= self.peers[square]

            # Keep track of all values within those common peers.
            base = set()
            for peer in valid_peers - cursors:
                base |= self.cells[peer]
                self.cells[peer] -= values

            # If there are common elements between values and the common peers,
            # some changes were made.
            success |= bool(base & values)

        return success

    def solve_guess_n_check(self):
        """
        Sometimes, the available logic can't solve the puzzle.
        If logic fails, try changing one of the available cells.
        Then look for a contradiction.
        """

        # Might as well start with as much knowledge as possible.
        if self.solve_logic():
            return True

        # Select a random non-determined square.
        # There MUST be a better way to do this.
        square = self.peers.iterkeys().next()

        for value in self.cells[square]:

            # Create a working copy of self.
            sample = copy.deepcopy(self)

            # Guess and check.  First guess, ...
            sample.assign(square, value)

            try:
                # ... then check.
                if sample.solve_guess_n_check():

                    # Copy the completely determined cells from the copy.
                    self.cells = sample.cells

                    # Clean up self's internal data structures.
                    self.solve_logic()

                    # Clearly this succeeded.
                    return True

            # If there was a contradiction,
            except InvalidCellValue:
                # There's no need to remove the bad value from the cell.
                # all values will be cycled through, and success will
                # either be found, or the sudoku puzzle is invalid.
                continue

        return False


if __name__ == '__main__':
    sample_grids = (
        '''--1 --7 -9-
           59- -8- --1
           -3- --- -8-

           --- --5 8--
           -5- -6- -2-
           --4 1-- ---

           -8- --- -3-
           1-- -2- -79
           -2- 7-- 4--''',


        '''38. ... ...
           ... 4.. 785
           ..9 .2. 3..

           .6. .9. ...
           8.. 3.2 ..9
           ... .4. .7.

           ..1 .7. 5..
           495 ..6 ...
           ... ... .92''',


        '''043 080 250
           600 000 000
           000 001 094

           900 004 070
           000 608 000
           010 200 003

           820 500 000
           000 000 005
           034 090 710''',


        """1-- 92- ---
           524 -1- ---
           --- --- -7-

           -5- --8 1-2
           --- --- ---
           4-2 7-- -9-

           -6- --- ---
           --- -3- 945
           --- -71 --6""",

        """--- -1- ---
           9-- --3 4-8
           67- 5-- -21

           --- 13- 78-
           -15 --- 24-
           -47 -65 ---

           75- --6 -14
           --2 4-- --9
           --- -9- ---""",

        """--- 5-- 2-1
           8-- --6 --5
           --5 2-7 -8-

           -17 96- 8-4
           --- --- ---
           9-8 -74 61-

           -8- 4-5 3--
           7-- 6-- --9
           5-4 --9 ---""",

        # The Riddle of Sho
        """--- --- 6-5
           --- 3-- -9-
           -8- --4 --1

           -4- -2- 97-
           --- --- ---
           -31 -8- -6-

           9-- 6-- -2-
           -1- --7 ---
           5-4 --- ---""",
    )

    for sample_grid in sample_grids:
        sudoku = Sudoku(sample_grid)
        #print sudoku
        print
        sudoku.solve_logic()
        print sudoku
        print
        sudoku.solve_guess_n_check()
        print sudoku
        print
        print 'pdbq' * 20
        print

    # The idea is to add more logic such that the solve_brute_force is never
    # necessary.
