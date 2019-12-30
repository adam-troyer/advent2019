from collections import namedtuple

Opcode = namedtuple('Opcode', ['num_args', 'func'])


def writer(func):
    func._writer = True
    return func


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

        if opcode.num_args != 0:
            # Grab the parameters from memory, then fetch their values based on position/immediate mode
            params = self.mem[self.pointer+1:self.pointer+1+opcode.num_args]
            param_vals = self._fetch_params_by_mode(params, param_modes, opcode)

        if self.debug:
            print(f'Fetching: '
                  f'Opcode value: {opcode_val}; '
                  f'Opcode: {opcode}; '
                  f'Param modes: {param_modes}; ')
            if opcode.num_args != 0:
                print(f'\tParam values (after fetch): {param_vals}')

        # Set the default next instruction pointer location to the end of the
        # current opcode. jump opcodes will overwrite this if the jump
        # condition is satisfied
        self.next_pointer = self.pointer + opcode.num_args + 1

        # Run the instruction
        if opcode.num_args > 0:
            opcode.func(self, param_vals)
        else:
            opcode.func(self)

        # Move the instruction pointer to the next opcode
        self.pointer = self.next_pointer

    def _parse_opcode_val(self, val):
        val_str = str(val)
        opcode = self._OPCODES[int(val_str[-2:])]
        modes_str = val_str[:-2]

        # Prepend leading 0s for parameter modes
        if len(modes_str) < opcode.num_args:
            modes_str = '0'*(opcode.num_args - len(modes_str)) + modes_str

        # Parse the parameter mode values, right to left
        # 0 = position mode, 1 = immediate mode
        param_modes = [int(v) for v in modes_str[::-1]]

        return opcode, param_modes

    def _fetch_params_by_mode(self, params, modes, opcode):
        # Fetch all params by position/immediate mode except the final one
        vals = [self.mem[param] if mode == 0 else param for param, mode in list(zip(params, modes))[:-1]]

        # For the last parameter, check if the opcode function is a writer.
        # If so, ignore the mode and add the parameter value directly so
        # the opcode properly gets pointed to the memory address for its result
        if hasattr(opcode.func, "_writer"):
            vals.append(params[-1])
        else:
            param = params[-1]
            mode = modes[-1]
            val = self.mem[param] if mode == 0 else param
            vals.append(val)
        return vals

    @writer
    def _add2(self, param_vals):
        self.mem[param_vals[2]] = param_vals[0] + param_vals[1]
        if self.debug:
            print(f'add2: {param_vals[0]}+{param_vals[1]}='
                  f'{self.mem[param_vals[2]]}->mem[{param_vals[2]}]')

    @writer
    def _mult2(self, param_vals):
        self.mem[param_vals[2]] = param_vals[0] * param_vals[1]
        if self.debug:
            print(f'mult2: {param_vals[0]}*{param_vals[1]}='
                  f'{self.mem[param_vals[2]]}->mem[{param_vals[2]}]')

    @writer
    def _input(self, param_vals):
        user_in = int(input('Enter input: '))
        self.mem[param_vals[0]] = user_in
        if self.debug:
            print(f'_input: {user_in}->mem[{param_vals[0]}]')

    def _output(self, param_vals):
        print(f'Output: {param_vals[0]}')

    def _jump_if_true(self, param_vals):
        if param_vals[0]:
            self.next_pointer = param_vals[1]
            if self.debug:
                print(f'_jump_if_true: {param_vals[0]} true, next_pointer set to {param_vals[1]}')
        elif self.debug:
            print(f'_jump_if_true: {param_vals[0]} not true, next_pointer unchanged')

    def _jump_if_false(self, param_vals):
        if not param_vals[0]:
            self.next_pointer = param_vals[1]
            if self.debug:
                print(f'_jump_if_false: {param_vals[0]} false, next_pointer set to {param_vals[1]}')
        elif self.debug:
            print(f'__jump_if_false: {param_vals[0]} not false, next_pointer unchanged')

    @writer
    def _less_than(self, param_vals):
        result = int(param_vals[0] < param_vals[1])
        self.mem[param_vals[2]] = result
        if self.debug:
            print(f'_less_than: {param_vals[0]}<{param_vals[1]}={result} -> mem[{param_vals[2]}')

    @writer
    def _equal(self, param_vals):
        result = int(param_vals[0] == param_vals[1])
        self.mem[param_vals[2]] = result
        if self.debug:
            print(f'_equal: {param_vals[0]}=={param_vals[1]}={result} -> mem[{param_vals[2]}')

    def _halt(self):
        self.next_pointer = -100

    _OPCODES = {1: Opcode(num_args=3, func=_add2),
                2: Opcode(num_args=3, func=_mult2),
                3: Opcode(num_args=1, func=_input),
                4: Opcode(num_args=1, func=_output),
                5: Opcode(num_args=2, func=_jump_if_true),
                6: Opcode(num_args=2, func=_jump_if_false),
                7: Opcode(num_args=3, func=_less_than),
                8: Opcode(num_args=3, func=_equal),
                99: Opcode(num_args=0, func=_halt)}


if __name__ == "__main__":
    # prog = [int(v) for v in '3,12,6,12,15,1,13,14,13,4,13,99,-1,0,1,9'.split(',')]
    with open('input_day5.txt', 'r') as infile:
        prog = [int(v) for v in infile.read().split(',')]
    intcode = Intcode(prog)
    intcode.run()
