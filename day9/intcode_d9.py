from collections import namedtuple, deque
from itertools import permutations, cycle

Opcode = namedtuple('Opcode', ['num_args', 'func'])


def writer(func):
    """Use to tag opcode functions that write to a memory location. Helper for parameter fetching."""
    func._writer = True
    return func


class Intcode:
    def __init__(self, memory, interactive=False, inputs=None, debug=False):
        self.mem = DynamicMem(memory)
        self.pointer = 0
        self.interactive = interactive

        if inputs is None:
            self.inputs = list()
        else:
            self.inputs = inputs.copy()

        if not interactive:
            self.outputs = []

        self.debug = debug
        self.hold_for_input = False
        self.halt = False
        self.relative_base = 0

    def run(self):
        """Run until the system halts or runs out of inputs."""
        while (not self.halt) and (not self.hold_for_input):
            if self.debug:
                print(f'Instruction pointer: {self.pointer}')
            self._fetch_op()

        # Running out of inputs will break out of the run loop,
        # but we want to go back into it next time run() is called,
        # so reset hold_for_input
        self.hold_for_input = False

    def add_inputs(self, inputs):
        """Add [inputs] to the input list."""
        self.inputs.extend(inputs)

    def _fetch_op(self):
        """Fetch opcode at current pointer, fetch parameters, run the operation, advance the pointer."""
        # Parse out the instruction value, parameter modes, and parameter values
        opcode_val = self.mem[self.pointer]
        opcode, param_modes = self._parse_opcode_val(opcode_val)

        if opcode.num_args != 0:
            # Grab the parameters from memory, then fetch their values based on position/immediate mode
            params = self.mem[self.pointer+1:self.pointer+1+opcode.num_args]
            param_vals = self._fetch_params_by_mode(params, param_modes, opcode)

        if self.debug:
            print(f'\tOpcode value: {opcode_val}; Opcode: {opcode}')
            if opcode.num_args != 0:
                print(f'\tParams: {params}; Param modes: {param_modes}')
                print(f'\tParam values (after fetch): {param_vals}')

        # Set the default next instruction pointer location to the end of the
        # current opcode. Opcodes may overwrite this (e.g. jumps)
        self.next_pointer = self.pointer + opcode.num_args + 1

        # Run the instruction
        if opcode.num_args > 0:
            opcode.func(self, param_vals)
        else:
            opcode.func(self)

        # Move the instruction pointer to the next opcode
        self.pointer = self.next_pointer

    def _parse_opcode_val(self, val):
        """Returns (Opcode, [param modes]) given the integer opcode value."""
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
        """Return parameters for an opcode, given the parameter modes."""
        # Fetch all params by position/immediate/relative mode. If the function is a writer,
        # the last param will just be passed as memory location to the function.
        vals = []
        writer = hasattr(opcode.func, '_writer')
        if writer:
            pm_zip = list(zip(params, modes))[:-1]
        else:
            pm_zip = list(zip(params, modes))

        for param, mode in pm_zip:
            if mode == 0:       # Position mode
                vals.append(self.mem[param])
                if self.debug:
                    print(f'\tPositional fetch: mem[{param}]={self.mem[param]}')
            elif mode == 1:     # Immediate mode
                vals.append(param)
            elif mode == 2:     # Relative mode
                target_addr = param + self.relative_base
                vals.append(self.mem[target_addr])
                if self.debug:
                    print(f'\tRelative fetch: mem[{self.relative_base}+{param}={target_addr}]={self.mem[target_addr]}')

        if writer:
            if modes[-1] == 0:       # Position mode
                vals.append(params[-1])
                if self.debug:
                    print(f'Writer in position mode. Write addr = {params[-1]}')
            elif modes[-1] == 2:     # Relative mode
                target_addr = params[-1] + self.relative_base
                vals.append(target_addr)
                if self.debug:
                    print(f'Writer in relative mode. Write addr = {target_addr}')
            else:
                raise ValueError('Memory write in immediate mode')

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
            print(f'\tmult2: {param_vals[0]}*{param_vals[1]}='
                  f'{self.mem[param_vals[2]]}->mem[{param_vals[2]}]')

    @writer
    def _input(self, param_vals):
        if self.interactive:
            in_val = int(input('Enter input: '))
        else:
            try:
                in_val = self.inputs.pop(0)
            except IndexError:  # Raised when input list is empty
                # Keep the instruction pointer from advancing so this op
                # is run again at next run() command, and flag hold
                # to break out of run loop
                self.next_pointer = self.pointer
                self.hold_for_input = True
                return
        self.mem[param_vals[0]] = in_val
        if self.debug:
            print(f'\t_input: {in_val}->mem[{param_vals[0]}]')

    def _output(self, param_vals):
        if not self.interactive:
            self.outputs.append(param_vals[0])
            if self.debug:
                print(f'\t_output:{param_vals[0]} added to output list')
                print(f'\t  Output list:{self.outputs}')
        else:
            print(f'Output: {param_vals[0]}')

    def _jump_if_true(self, param_vals):
        if param_vals[0]:
            self.next_pointer = param_vals[1]
            if self.debug:
                print(f'\t_jump_if_true: {param_vals[0]} true, next_pointer set to {param_vals[1]}')
        elif self.debug:
            print(f'\t_jump_if_true: {param_vals[0]} not true, next_pointer unchanged')

    def _jump_if_false(self, param_vals):
        if not param_vals[0]:
            self.next_pointer = param_vals[1]
            if self.debug:
                print(f'\t_jump_if_false: {param_vals[0]} false, next_pointer set to {param_vals[1]}')
        elif self.debug:
            print(f'\t_jump_if_false: {param_vals[0]} not false, next_pointer unchanged')

    @writer
    def _less_than(self, param_vals):
        result = int(param_vals[0] < param_vals[1])
        self.mem[param_vals[2]] = result
        if self.debug:
            print(f'\t_less_than: {param_vals[0]}<{param_vals[1]}={result} -> mem[{param_vals[2]}]')

    @writer
    def _equal(self, param_vals):
        result = int(param_vals[0] == param_vals[1])
        self.mem[param_vals[2]] = result
        if self.debug:
            print(f'\t_equal: {param_vals[0]}=={param_vals[1]}={result} -> mem[{param_vals[2]}]')

    def _rel_base_offset(self, param_vals):
        self.relative_base += param_vals[0]
        if self.debug:
            print(f'\t_rel_base_offset: Adjusted by {param_vals[0]}, now {self.relative_base}')

    def _halt(self):
        self.halt = True

    _OPCODES = {1: Opcode(num_args=3, func=_add2),
                2: Opcode(num_args=3, func=_mult2),
                3: Opcode(num_args=1, func=_input),
                4: Opcode(num_args=1, func=_output),
                5: Opcode(num_args=2, func=_jump_if_true),
                6: Opcode(num_args=2, func=_jump_if_false),
                7: Opcode(num_args=3, func=_less_than),
                8: Opcode(num_args=3, func=_equal),
                9: Opcode(num_args=1, func=_rel_base_offset),
                99: Opcode(num_args=0, func=_halt)}


class DynamicMem:
    """List that auto-expands if reads/writes try to go above the last element. Treat like a list."""
    def __init__(self, content):
        self._mem = content.copy()

    def __get__(self):
        return self._mem

    def __getitem__(self, indices):
        """Get slice/index from the memory, expanding and filling with 0s if needed."""
        if type(indices) is slice:
            min_ind = indices.start
            max_ind = indices.stop - 1
        else:   # Single index
            min_ind = max_ind = indices
        if min_ind < 0:
            raise IndexError('Memory locations < 0 are not valid')
        self._expand_mem(max_ind)
        return self._mem[indices]

    def __setitem__(self, index, value):
        """Set value at index, expanding and filling with 0s if needed."""
        if index < 0:
            raise IndexError('Memory locations < 0 are not valid')
        self._expand_mem(index)
        self._mem[index] = value

    def __len__(self):
        return len(self._mem)

    def __str__(self):
        return str(self._mem)

    def _expand_mem(self, index):
        """If index is out of bounds expand memory to fit, filling with 0s."""
        if len(self._mem) < index + 1:
            self._mem.extend([0]*(index - len(self._mem) + 1))


if __name__ == "__main__":
    # Outputs copy of itself
    ex1_str = "109,1,204,-1,1001,100,1,100,1008,100,16,101,1006,101,0,99"
    # Outputs 1219070632396864
    ex2_str = "1102,34915192,34915192,7,4,7,99,0"
    # Outputs 1125899906842624
    ex3_str = "104,1125899906842624,99"
    # Part 1 & 2 input
    with open('day9_input.txt', 'r') as infile:
        input_str = infile.read()

    code_str = input_str

    code = [int(s) for s in code_str.strip().split(',')]
    intcode = Intcode(code, interactive=True)
    intcode.run()
