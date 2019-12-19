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
        # Grab the opcode and arguments
        opcode_val = self.mem[self.pointer]
        arg_start_loc = self.pointer + 1
        opcode = self._OPCODES[opcode_val]
        args = self.mem[arg_start_loc:arg_start_loc+opcode.num_args]
        if self.debug:
            print(f'Fetching: '
                  f'Opcode value: {opcode_val}\n'
                  f'Opcode: {opcode}\n'
                  f'Args: {args}')

        opcode.func(self, *args)

        # Move the mem pointer to the next opcode
        self.pointer += opcode.num_args + 1

    def _add2(self, p1, p2, res):
        p1_val = self.mem[p1]
        p2_val = self.mem[p2]
        self.mem[res] = p1_val + p2_val
        if self.debug:
            print(f'add2 locs: {p1}+{p2}->{res}\n'
                  f'add2 values: {p1_val}+{p2_val}={self.mem[res]}')

    def _mult2(self, p1, p2, res):
        p1_val = self.mem[p1]
        p2_val = self.mem[p2]
        self.mem[res] = p1_val * p2_val
        if self.debug:
            print(f'mult2 locs: {p1}*{p2}->{res}\n'
                  f'mult2 values: {p1_val}*{p2_val}={self.mem[res]}')

    def _halt(self):
        self.pointer = -100

    _OPCODES = {1: Opcode(num_args=3, func=_add2),
                2: Opcode(num_args=3, func=_mult2),
                99: Opcode(num_args=0, func=_halt)}
