from collections import namedtuple, deque
from itertools import permutations, cycle

Opcode = namedtuple('Opcode', ['num_args', 'func'])


def writer(func):
    func._writer = True
    return func


class Intcode:
    def __init__(self, memory, interactive=False, inputs=None, debug=False):
        self.mem = memory
        self.pointer = 0
        self.interactive = interactive

        if inputs is None:
            self.inputs = list()
        else:
            self.inputs = inputs.copy()

        if not interactive:
            self.output_list = []

        self.debug = debug
        self.hold_for_input = False
        self.halt = False

    def run(self):
        # Run until halt or we run out of inputs
        while (not self.halt) and (not self.hold_for_input):
            if self.debug:
                print(f'Memory: {self.mem}')
                print(f'Instruction pointer: {self.pointer}')
            self._fetch_op()

        # Running out of inputs will break out of the run loop,
        # but we want to go back into it next time run() is called,
        # so reset hold_for_input
        self.hold_for_input = False

    def add_inputs(self, inputs):
        self.inputs.extend(inputs)

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
            print(f'_input: {in_val}->mem[{param_vals[0]}]')

    def _output(self, param_vals):
        if not self.interactive:
            self.output_list.append(param_vals[0])
            if self.debug:
                print(f'_output:{param_vals[0]} added to output list')
                print(f'  Output list:{self.output_list}')
        else:
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
        self.halt = True

    _OPCODES = {1: Opcode(num_args=3, func=_add2),
                2: Opcode(num_args=3, func=_mult2),
                3: Opcode(num_args=1, func=_input),
                4: Opcode(num_args=1, func=_output),
                5: Opcode(num_args=2, func=_jump_if_true),
                6: Opcode(num_args=2, func=_jump_if_false),
                7: Opcode(num_args=3, func=_less_than),
                8: Opcode(num_args=3, func=_equal),
                99: Opcode(num_args=0, func=_halt)}


def run_amps_nofb(code_str):
    code = [int(s) for s in code_str.split(',')]

    # results will hold the output value for each phase sequence, then we'll find the max
    results = []

    # Iterate through every permutation of [0, 1, 2, 3, 4]
    for phase_seq in permutations(range(5)):
        # inputs[0] = phase value, inputs[1] = input signal
        inputs = [0, 0]
        for phase in phase_seq:
            inputs[0] = phase
            amp = Intcode(code.copy(), interactive=False, inputs=inputs)
            amp.run()
            # Set the input signal of the next amp to the output signal of this amp
            inputs[1] = amp.output_list[0]
        # Add the phase seq and the output signal of the final amp to results
        results.append((phase_seq, amp.output_list[0]))
    # Find the max output signal, print that value and corresponding phase sequence
    print(max(results, key=lambda x: x[1]))


def run_amps_fb(code_str):
    code = [int(s) for s in code_str.split(',')]

    # results will hold the output value for each phase sequence, then we'll find the max
    results = []

    # Iterate through every permutation of [5, 6, 7, 8, 9]
    for phase_seq in permutations(range(5, 10)):
        amps = []
        # Initialize all the amps, with their phase as their first input
        for phase in phase_seq:
            amp = Intcode(code.copy(), inputs=[phase])
            amps.append(amp)
        # Add the initial 0 signal to the first amp's inputs
        amps[0].add_inputs([0])

        # Loop through the amps until they've all halted.
        # Each amp will run until it halts or runs out of inputs.
        # By the next time that amp is reached, the previous amp should
        # have generated new inputs for it.
        i = 0
        amp = amps[0]
        amp.run()
        while any(not amp.halt for amp in amps):
            # Previous amp might not have generated an output yet.
            # Not sure this will ever happen, but can't hurt
            if amp.output_list:
                outputs = amp.output_list.copy()
                amp.output_list = []
            else:
                outputs = None
            # Grab next amp in the list, looping back to the beginning
            # after the last
            i = (i + 1) % 5
            amp = amps[i]
            if outputs:
                # Previous amp's outputs become next amp's inputs
                amp.add_inputs(outputs)
            amp.run()

        results.append((phase_seq, amp.output_list[0]))

    print(max(results, key=lambda x: x[1]))


if __name__ == "__main__":
    # Ex 1: 43210 at sequence 4,3,2,1,0
    nofb_ex1 = "3,15,3,16,1002,16,10,16,1,16,15,15,4,15,99,0,0"
    # Ex 2: 54321 at sequence 0,1,2,3,4
    nofb_ex2 = "3,23,3,24,1002,24,10,24,1002,23,-1,23,101,5,23,23,1,24," \
               "23,23,4,23,99,0,0"
    # Ex 3: 65210 at sequencye 1,0,4,3,2
    nofb_ex3 = "3,31,3,32,1002,32,10,32,1001,31,-2,31,1007,31,0,33,1002," \
               "33,7,33,1,33,31,31,1,32,31,31,4,31,99,0,0,0"

    # Part 1: Result is 20413 at phase seq 4,1,0,2,3
    with open('day7_input.txt', 'r') as infile:
        input_str = infile.read()

    # Part 2 Ex 1: Result is 139629729 at seq 9 8 7 6 5
    fb_ex1 = "3,26,1001,26,-4,26,3,27,1002,27,2,27,1,27,26,27,4,27,1001,28," \
             "-1,28,1005,28,6,99,0,0,5"
    # Part 2 Ex 2: Result is 18216 at seq 9 7 8 5 6
    fb_ex2 = "3,52,1001,52,-5,52,3,53,1,52,56,54,1007,54,5,55,1005,55,26," \
             "1001,54,-5,54,1105,1,12,1,53,54,53,1008,54,0,55,1001,55,1," \
             "55,2,53,55,53,4,53,1001,56,-1,56,1005,56,6,99,0,0,0,0,10"

    # run_amps_nofb(nofb_ex3)
    run_amps_fb(input_str)
