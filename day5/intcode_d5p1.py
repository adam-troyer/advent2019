from collections import namedtuple

Opcode = namedtuple('Opcode', ['num_args', 'func'])


class Intcode:
    def __init__(self, memory, debug=False):
        self.mem = memory
        self.pointer = 0
        self.debug = debug

    def run(self):
        # Halt will set pointer negative to stop run
        while self.pointer >= 0:
            if self.debug:
                print(f'Memory: {self.mem}')
                print(f'Instruction pointer: {self.pointer}')
            self._fetch_op()

    def _fetch_op(self):
        # Parse out the instruction value, parameter modes, and parameter values
        if self.pointer >= len(self.mem):
            raise IndexError(f'Instruction pointer out of bounds: '
                             f'pointer={self.pointer}, mem length={len(self.mem)}')
        opcode_val = self.mem[self.pointer]
        opcode, param_modes = self._parse_opcode_val(opcode_val)
        param_vals = self.mem[self.pointer+1:self.pointer+1+opcode.num_args]

        if self.debug:
            print(f'Fetching: '
                  f'Opcode value: {opcode_val}; '
                  f'Opcode: {opcode}; '
                  f'Param modes: {param_modes}; '
                  f'Param mem values: {param_vals}')

        # Run the instruction
        if opcode.num_args > 0:
            opcode.func(self, param_vals, param_modes)
        else:
            opcode.func(self)

        # Move the mem pointer to the next opcode
        self.pointer += opcode.num_args + 1

    def _parse_opcode_val(self, val):
        val_str = str(val)
        opcode = self._OPCODES[int(val_str[-2:])]
        modes_str = val_str[:-2]

        # Prepend leading 0s for parameter modes
        if len(modes_str) < opcode.num_args:
            modes_str = '0'*(opcode.num_args - len(modes_str)) + modes_str

        # Parse the parameter mode values, right to left
        param_modes = [int(v) for v in modes_str[::-1]]

        return opcode, param_modes

    def _add2(self, param_vals, param_modes):
        if param_modes[2] != 0:
            raise ValueError('Parameter 3 (result) must be in Position mode')
        p1 = self.mem[param_vals[0]] if param_modes[0] == 0 else param_vals[0]
        p2 = self.mem[param_vals[1]] if param_modes[1] == 0 else param_vals[1]
        self.mem[param_vals[2]] = p1 + p2
        if self.debug:
            print(f'add2: {p1}+{p2}={self.mem[param_vals[2]]}->mem[{param_vals[2]}]')

    def _mult2(self, param_vals, param_modes):
        if param_modes[2] != 0:
            raise ValueError('Parameter 3 (result) must be in Position mode')
        p1 = self.mem[param_vals[0]] if param_modes[0] == 0 else param_vals[0]
        p2 = self.mem[param_vals[1]] if param_modes[1] == 0 else param_vals[1]
        self.mem[param_vals[2]] = p1 * p2
        if self.debug:
            print(f'mult2: {p1}*{p2}={self.mem[param_vals[2]]}->mem[{param_vals[2]}]')

    def _input(self, param_vals, param_modes):
        if param_modes[0] != 0:
            raise ValueError('Parameter must be in Position mode (0)')
        user_in = input('Enter input: ')
        self.mem[param_vals[0]] = int(user_in)

    def _output(self, param_vals, param_modes):
        val = self.mem[param_vals[0]] if param_modes[0] == 0 else param_vals[0]
        print(f'Output: {val}')

    def _halt(self):
        self.pointer = -100

    _OPCODES = {1: Opcode(num_args=3, func=_add2),
                2: Opcode(num_args=3, func=_mult2),
                3: Opcode(num_args=1, func=_input),
                4: Opcode(num_args=1, func=_output),
                99: Opcode(num_args=0, func=_halt)}


if __name__ == "__main__":
    with open('input_day5.txt', 'r') as infile:
        prog = [int(s) for s in infile.read().split(',')]
        intcode = Intcode(prog, debug=False)
        intcode.run()