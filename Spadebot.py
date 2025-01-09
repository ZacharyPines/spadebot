import om
import zipfile

PRINT_DEBUG_MESSAGES = False

def spadehandler(puzzle, puzzle_num):
    global success, failure
    all_product_atoms = set([item.type for sublist in puzzle.products for item in sublist.atoms])
    all_reagent_atoms = set([item.type for sublist in puzzle.reagents for item in sublist.atoms])
    if not all_product_atoms.issubset(all_reagent_atoms):
        print(f"❌ - Puzzle #{puzzle_num} failed: Not all product atoms are contained within the reagent atoms")
        return None
    for product in puzzle.products:
        for bond in product.bonds:
            if bond.type != 1:
                print(f"❌ - Puzzle #{puzzle_num} failed: At least one of the product bonds is irregular")
                return None
    return spadebot(puzzle)

def spadebot(puzzle):

    # ----------------------------------------------------------------------------------------------------
    # Scope Setting: Even though partlist is an array, this makes it feel cleaner lol
    # ----------------------------------------------------------------------------------------------------

    global PRINT_DEBUG_MESSAGES
    global count
    global lockedcount
    global partlist

    count = 0
    lockedcount = 0
    partlist = []

    # ----------------------------------------------------------------------------------------------------
    # Conditional Print: Sometimes reading the method explains the method
    # ----------------------------------------------------------------------------------------------------

    def ConditionalPrint(Message, end="\n"):
        if PRINT_DEBUG_MESSAGES:
            print(Message, end=end)

    # ----------------------------------------------------------------------------------------------------
    # Translation Guide: Some of these are purely for debugging, but it made my life a lot easier
    # ----------------------------------------------------------------------------------------------------


    element_dict = {1: "SALT", 2: "AIR", 3: "EARTH", 4: "FIRE", 5: "WATER", 6: "QUICKSILVER", 7: "GOLD", 8: "SILVER",
                    9: "COPPER", 10: "IRON", 11: "TIN", 12: "LEAD", 13: "VITAE", 14: "MORS", 16: "QUINTESSENCE"}

    command_dict = {"ROTATE_CW": b'R', "ROTATE_CCW": b'r', "EXTEND": b'E', "RETRACT": b'e', "GRAB": b'G',
                    "DROP": b'g', "TRACK_PLUS": b'A', "TRACK_MINUS": b'a', "REPEAT": b'C', "RESET": b'X'}

    # ----------------------------------------------------------------------------------------------------
    # Item Methods: Methods for placing regular items, arms, and tracks, for cleaner future code
    # ----------------------------------------------------------------------------------------------------

    def addreg(name, pos, rot=0):
        partlist.append(om.Part(name=getattr(om.Part, name),
                                position=pos,
                                rotation=rot))

    def addarm(name, pos, rot, len, armlist):
        partlist.append(om.Part(name=getattr(om.Part, name),
                                position=pos,
                                rotation=rot,
                                length=len))
        armlist.append(partlist[-1])

    def addtrack(pos_list):
        if len(pos_list):
            partlist.append(om.Part(name=om.Part.TRACK,
                                    track_hexes=pos_list))

    def addelem(name, pos, rot, num):

        partlist.append(om.Part(name=getattr(om.Part, name),
                                position=pos,
                                rotation=rot,
                                which_reagent_or_product=num))

    # ----------------------------------------------------------------------------------------------------
    # Instruction Methods: Methods for generating instructions for an arm list with an instruction array
    # ----------------------------------------------------------------------------------------------------

    def addcount(num, changelocked):
        global count, lockedcount
        count += num
        if changelocked:
            lockedcount = count

    def setcount(value, setlock):
        global count, lockedcount
        count = value
        if setlock:
            lockedcount = value

    def addinstr(loadcount, savecount, armlist, instr, num):
        global count, lockedcount
        if loadcount:
            count = lockedcount
        for i in range(num):
            for arm in armlist:
                if instr != "x" and isinstance(instr, str):
                    instr = command_dict[instr]
                arm.instructions.append(om.Instruction(count, instr))
            count += 1
        if savecount:
            lockedcount = count

    def addinstrlist(loadcount, savecount, armlist, instrlist):
        global count, lockedcount
        if loadcount:
            count = lockedcount
        for instr in instrlist:
            for arm in armlist:
                if instr != "x":
                    if isinstance(instr, str):
                        instr = command_dict[instr]
                    arm.instructions.append(om.Instruction(count, instr))
            count += 1
        if savecount:
            lockedcount = count

    # ----------------------------------------------------------------------------------------------------
    # Index Methods: Used for aligning coordinates from the regular grid to the unusual slant grid
    # ----------------------------------------------------------------------------------------------------

    def index(x, y, slant):
        if slant == 1: return (-y, x + y)
        if slant == 0: return (x, y)
        if slant == 2: return (x + y, -x)
        if slant == 3: return (y, -x - y)

    def indexutility(num):
        if num == 0: return 1
        if num == 1: return 0
        return num

    def indexlist(start, end, slant, height, flipped):
        if slant == 1: return [(-height, -i) for i in range(start - height, end - height)][::(2 * flipped - 1)]
        if slant == 0: return [(-i, height) for i in range(start, end)][::(2 * flipped - 1)]
        if slant == 2: return [(-i + height, i) for i in range(start, end)][::(2 * flipped - 1)]
        if slant == 3: return [(height, i) for i in range(start - height, end - height)][::(2 * flipped - 1)]

    def index2(x, y, offset, slant):
        if slant == 0: return (x, y)
        if slant == 1: return (offset - y, x + y - offset)
        if slant == 2: return (x + y, offset - x)
        if slant == 3: return (y + offset, offset - x - y)

    def indexlist2(start, end, slant, height, flipped, offset):
        untilted_list = indexlist(-end, -start, 0, height, flipped)
        return [index2(x, y, offset, slant) for (x, y) in untilted_list]

    def indexutility2(num):
        if num == 2: return num + 3
        if num == 3: return num + 1
        return num

    # ----------------------------------------------------------------------------------------------------
    # Input Parsing: Takes in the inputs and calculates variables for the future, as well as atom sorting
    # ----------------------------------------------------------------------------------------------------

    reagent_masterlist = [{} for reagent in puzzle.reagents]
    reagent_atom_masterlist = [[] for reagent in puzzle.reagents]

    ConditionalPrint("-" * 100)
    for reagent_num, reagent in enumerate(puzzle.reagents):

        reagent_height_set = {a.position[1] for a in reagent.atoms}
        height = max(reagent_height_set) - min(reagent_height_set) + 1
        reagent_masterlist[reagent_num]["Height"] = height
        reagent_masterlist[reagent_num]["Y-Offset"] = -min(reagent_height_set)

        reagent_width_set = {a.position[0] for a in reagent.atoms}
        width = max(reagent_width_set) - min(reagent_width_set) + 1
        reagent_masterlist[reagent_num]["Width"] = width
        reagent_masterlist[reagent_num]["X-Offset"] = max(reagent_width_set)

        reagent_masterlist[reagent_num]["Decomposition Time"] = 2 * width + 2 * width * height + 8 * height

        reagent_atom_list = []
        for atom in reagent.atoms:
            x = -atom.position[0] + reagent_masterlist[reagent_num]["X-Offset"]
            y = atom.position[1] + reagent_masterlist[reagent_num]["Y-Offset"]
            reagent_width = reagent_masterlist[reagent_num]["Width"]
            reagent_atom_list.append([2*reagent_width + 2*reagent_width*y + 8*y + 2*x + 10, atom, (x, y)])
        reagent_atom_list = sorted(reagent_atom_list, key=lambda x: x[0])

        for atom_num, atom in enumerate(reagent_atom_list):
            atom_dictionary = {}
            atom_dictionary["Reagent Num"] = reagent_num
            atom_dictionary["Position"] = atom[0]
            atom_dictionary["Object"] = atom[1]
            atom_dictionary["Coordinates"] = atom[2]
            atom_dictionary["Type"] = element_dict[atom[1].type]
            atom_dictionary["Order"] = atom_num
            reagent_atom_masterlist[reagent_num].append(atom_dictionary)

    for reagent_num, (reagent_info, reagent_atom_info) in enumerate(zip(reagent_masterlist, reagent_atom_masterlist)):
        ConditionalPrint(f"Reagent# {reagent_num + 1}")
        ConditionalPrint(f" - {reagent_info = }")
        ConditionalPrint(f" - {reagent_atom_info = }")

    # ----------------------------------------------------------------------------------------------------
    # Output Parsing: Takes in the outputs and calculates variables for the future, as well as atom sorting
    # ----------------------------------------------------------------------------------------------------

    product_masterlist = [{} for _ in puzzle.products]
    product_atom_masterlist = [[] for _ in puzzle.products]

    ConditionalPrint("-" * 100)
    for product_num, product in enumerate(puzzle.products):
        product_height_set = {a.position[1] for a in product.atoms}
        product_masterlist[product_num]["Height"] = max(product_height_set) - min(product_height_set) + 1
        product_masterlist[product_num]["Y-Offset"] = -min(product_height_set)

        product_width_set = {a.position[0] for a in product.atoms}
        product_masterlist[product_num]["Width"] = max(product_width_set) - min(product_width_set) + 1
        product_masterlist[product_num]["X-Offset"] = max(product_width_set)

        product_atom_list = [[-10 * a.position[1] - a.position[0], a] for a in product.atoms]
        product_atom_list = sorted(product_atom_list, key=lambda x: x[0])
        product_atom_list = [a[1] for a in product_atom_list]

        for atom in product_atom_list:
            atom_dictionary = {}
            adjusted_x = -atom.position[0] + product_masterlist[product_num]["X-Offset"]
            adjusted_y = atom.position[1] + product_masterlist[product_num]["Y-Offset"]
            atom_dictionary["Coordinates"] = (adjusted_x, adjusted_y)
            atom_dictionary["Object"] = atom
            atom_dictionary["Type"] = element_dict[atom.type]
            atom_dictionary["Product Num"] = product_num
            product_atom_masterlist[product_num].append(atom_dictionary)

    for product_num, (product_info, product_atom_info) in enumerate(zip(product_masterlist, product_atom_masterlist)):
        ConditionalPrint(f"Product# {product_num + 1}")
        ConditionalPrint(f" - {product_info = }")
        ConditionalPrint(f" - {product_atom_info = }")

    # ----------------------------------------------------------------------------------------------------
    # Building: Places all the glyphs for the input phase of the solve, including track and arms
    # ----------------------------------------------------------------------------------------------------

    toparmlist_list = []
    bottomarmlist_list = []
    prodarmlist_list = []
    wastearmlist_list = []
    outputarmlist_list = []

    for reagent_num in range(len(puzzle.reagents)):

        reagent_width = reagent_masterlist[reagent_num]["Width"]
        reagent_xoffset = reagent_masterlist[reagent_num]["X-Offset"]
        reagent_yoffset = reagent_masterlist[reagent_num]["Y-Offset"]

        addelem("INPUT", index(-2 * reagent_width - 9 - reagent_xoffset, 3 + reagent_yoffset, reagent_num), 1 - indexutility(reagent_num), reagent_num)

        addtrack(indexlist(8, 3 * reagent_width + 9, reagent_num, 1, 0))
        addtrack(indexlist(7, 3 * reagent_width + 9, reagent_num, 0, 0))
        addtrack(indexlist(reagent_width + 10, 3 * reagent_width + 8, reagent_num, -1, 1))

        addreg("UNBONDER", index(-reagent_width - 9, 3, reagent_num), 2 - indexutility(reagent_num))
        addreg("UNBONDER", index(-reagent_width - 7, 3, reagent_num), 4 - indexutility(reagent_num))
        addreg("UNBONDER", index(-reagent_width - 6, 3, reagent_num), 3 - indexutility(reagent_num))

        addreg("BONDER", index(-2 * reagent_width - 9, 2, reagent_num), 1 - indexutility(reagent_num))

        toparmlist = []
        bottomarmlist = []
        wastearmlist = []
        outputarmlist = []

        for i in range(-3 * reagent_width - 8, -2 * reagent_width - 8):
            addarm("PISTON", index(i, 1, reagent_num), 2 - indexutility(reagent_num), 3, toparmlist)
        for i in range(-3 * reagent_width - 8, -2 * reagent_width - 8):
            addarm("PISTON", index(i, 0, reagent_num), 2 - indexutility(reagent_num), 3, bottomarmlist)
        for i in range(-2 * reagent_width - 8, -reagent_width - 9):
            addarm("ARM1", index(i, -1, reagent_num), 2 - indexutility(reagent_num), 3, wastearmlist)
        addarm("ARM1", index(-7, 0, reagent_num), 2 - indexutility(reagent_num), 2, outputarmlist)

        prodarmlist = toparmlist + bottomarmlist

        toparmlist_list.append(toparmlist)
        bottomarmlist_list.append(bottomarmlist)
        prodarmlist_list.append(prodarmlist)
        wastearmlist_list.append(wastearmlist)
        outputarmlist_list.append(outputarmlist)

    # ----------------------------------------------------------------------------------------------------
    # Bonding calculation: Calculates what atoms in the product are bonded, and stores that information
    # ----------------------------------------------------------------------------------------------------

    ConditionalPrint("-" * 100)

    for product_num, product in enumerate(puzzle.products):

        bond_list = []
        for bond in product.bonds:
            bond = bond.positions

            xoffset = product_masterlist[product_num]["X-Offset"]
            yoffset = product_masterlist[product_num]["Y-Offset"]

            pos1, pos2 = bond
            pos1_x, pos1_y = pos1
            pos2_x, pos2_y = pos2

            pos1_x = -pos1_x
            pos2_x = -pos2_x

            if pos1_y > pos2_y:
                pos1_y, pos2_y = pos2_y, pos1_y
                pos1_x, pos2_x = pos2_x, pos1_x
            elif (pos1_y == pos2_y and pos1_x > pos2_x):
                pos1_y, pos2_y = pos2_y, pos1_y
                pos1_x, pos2_x = pos2_x, pos1_x

            bond_list.append(((pos1_x + xoffset, pos1_y + yoffset), (pos2_x + xoffset, pos2_y + yoffset)))

        atom_info = product_atom_masterlist[product_num]
        for atom in atom_info:

            bond_values = [0, 0, 0]
            atom_loc = atom["Coordinates"]

            for pair in bond_list:

                if atom_loc == pair[0]:
                    pos1_x, pos1_y = pair[0]
                    pos2_x, pos2_y = pair[1]

                    if (pos1_x + 1 == pos2_x and pos1_y == pos2_y):
                        bond_values[0] = 1
                    if (pos1_x + 1 == pos2_x and pos1_y + 1 == pos2_y):
                        bond_values[1] = 1
                    if (pos1_x == pos2_x and pos1_y + 1 == pos2_y):
                        bond_values[2] = 1
            atom["Bonds"] = bond_values
            ConditionalPrint(f"{bond_values = }")

    # ----------------------------------------------------------------------------------------------------
    # Theoretical Minimum Calculation: Calculates the fastest possible way each reagent atom can be sent
    # ----------------------------------------------------------------------------------------------------

    ConditionalPrint("-" * 100)
    min_cycle_gap = 6
    for atom_list in product_atom_masterlist:
        row_delay = 0
        for atom_num in range(len(atom_list) - 1):

            atom_info = atom_list[atom_num]
            next_info = atom_list[atom_num + 1]

            atom_info["Row End"] = atom_info["Coordinates"][1] != next_info["Coordinates"][1]
            row_delay += atom_info["Bonds"][1] + atom_info["Bonds"][2]

            if (atom_info["Coordinates"][1] != next_info["Coordinates"][1]):
                atom_info["Row Delay"] = row_delay
                row_delay = 0
            else:
                atom_info["Row Delay"] = 0

        atom_list[-1]["Row End"] = True
        atom_list[-1]["Row Delay"] = row_delay

    shifting_value = 0
    for product_num, atom_list in enumerate(product_atom_masterlist):

        last_atom_reset_time = shifting_value
        shifting_value = min_cycle_gap

        bond_total = 0

        for atom_info in atom_list:
            x = atom_info["Coordinates"][0]

            bond_total += (atom_info["Bonds"][1] + atom_info["Bonds"][2])

            atom_movement_time = (2 * (product_masterlist[product_num]["Width"] - atom_info["Coordinates"][0]) + 2) * (atom_info["Bonds"][0] ^ 1)

            if atom_info["Row End"]:
                row_reset_time = (((4 * product_masterlist[product_num]["Width"]) + atom_movement_time // 2 + 2 * bond_total) if atom_info["Row End"] else 0)
                bond_total = 0
            else:
                row_reset_time = 0

            ConditionalPrint(f"row_reset_time = max ( {min_cycle_gap = }, {atom_movement_time = }, {row_reset_time = })  =  {max(min_cycle_gap, atom_movement_time, row_reset_time)}")

            row_reset_time = max(min_cycle_gap, atom_movement_time, row_reset_time)
            current_atom_reset_time = row_reset_time
            atom_info["Last Atom Reset Time"] = last_atom_reset_time
            last_atom_reset_time = current_atom_reset_time

    ConditionalPrint(("-" * 44) + " Debug Info " + ("-" * 44))
    for product_num, (product_info, product_atom_info) in enumerate(zip(product_masterlist, product_atom_masterlist)):
        ConditionalPrint(f"Product# {product_num + 1}")
        ConditionalPrint(f" - {product_info = }")
        ConditionalPrint(f" - {product_atom_info = }")

    # ----------------------------------------------------------------------------------------------------
    # Precomputation: Given the inputs and outputs, solve for what order elements must be grabbed in
    # ----------------------------------------------------------------------------------------------------

    cycle = 0
    last_reagent_num = -1
    loops_list = [0, 0, 0, 0]
    position_list = [(-1, -1), (-1, -1), (-1, -1), (-1, -1)]
    past_row_delay_list = [[], [], [], []]
    current_row_delay_dict = [{}, {}, {}, {}]
    future_row_delay_list = [[], [], [], []]
    current_row_list = [[], [], [], []]
    delay_array = [[], [], [], []]
    split_master_atom_list = [[], [], [], []]
    whole_master_atom_list = []

    for product_num, product_atom_list in enumerate(product_atom_masterlist):
        for product_atom_info in product_atom_list:

            ConditionalPrint("-" * 100)
            needed_atom = product_atom_info["Type"]
            possible_atom_list = []
            ConditionalPrint(f" - It is cycle {cycle} and we need {needed_atom}")

            min_cycle_gap = product_atom_info["Last Atom Reset Time"]

            for reagent_atom_list in reagent_atom_masterlist:
                for atom_info in reagent_atom_list:
                    atom_cyclevalue = atom_info["Position"]
                    atom_x, atom_y = atom_info["Coordinates"]
                    reagent_num = atom_info["Reagent Num"]

                    if atom_info["Type"] == needed_atom:

                        atom_is_upcoming = atom_y > position_list[reagent_num][1] or (atom_x > position_list[reagent_num][0] and atom_y == position_list[reagent_num][1])
                        decompose_num = loops_list[reagent_num] + (1 - atom_is_upcoming)

                        value = atom_cyclevalue
                        value += reagent_masterlist[reagent_num]["Decomposition Time"] * (loops_list[reagent_num] + (1 - atom_is_upcoming))

                        value += sum((past_row_delay_list[reagent_num][:] if (not current_row_delay_dict[reagent_num].get((reagent_num, atom_y, decompose_num), 0)) else past_row_delay_list[reagent_num][:-1]))
                        value += current_row_delay_dict[reagent_num].get((reagent_num, atom_y, decompose_num), 0)

                        ConditionalPrint(f"We can get {needed_atom} from {(atom_x, atom_y)} of reagent {reagent_num} on cycle {value}: (value = {atom_cyclevalue}, loops = {reagent_masterlist[reagent_num]["Decomposition Time"] * (loops_list[reagent_num] + (1 - atom_is_upcoming))}, past rows = {sum((past_row_delay_list[reagent_num][:] if (not current_row_delay_dict[reagent_num].get((reagent_num, atom_y, decompose_num), 0)) else past_row_delay_list[reagent_num][:-1]))}, current row = {current_row_delay_dict[reagent_num].get((reagent_num, atom_y, decompose_num), 0)})")

                        possible_atom_list.append((value, atom_info, atom_is_upcoming))

            chosen_atom = min(possible_atom_list, key=lambda x: x[0])

            value = chosen_atom[0]
            atom = chosen_atom[1]
            atom_is_upcoming = chosen_atom[2]
            (atom_x, atom_y) = atom["Coordinates"]
            reagent_num = atom["Reagent Num"]

            ConditionalPrint(f" - We have picked the {atom["Type"]} from {atom["Coordinates"]} of reagent {atom["Reagent Num"]}")
            ConditionalPrint(f"We believe the atom will be ready on cycle {value}")

            delay = max(cycle + min_cycle_gap - value, 0)
            value += delay
            cycle = value

            ConditionalPrint(f"We are adding {delay} cycles to account for the {min_cycle_gap} cycle minimum gap ({value-delay} + {delay} = {cycle})")

            decompose_num = loops_list[reagent_num] + (1 - atom_is_upcoming)
            hash_is_new = not current_row_delay_dict[reagent_num].get((reagent_num, atom_y, decompose_num), 0)

            if not atom_is_upcoming:
                loops_list[reagent_num] += 1

            if hash_is_new:
                past_row_delay_list[reagent_num].append(3)
                current_row_list[reagent_num] = []
                delay_array[reagent_num] = []

            ConditionalPrint(" - Now, we need to set up the future atoms")
            ConditionalPrint(f"Atoms in the same row will wait {(2 * atom_x + 6)} for slowness and {delay} for delay: {(2 * atom_x + 6)} + {delay} = {(2 * atom_x + 6) + delay}: {current_row_delay_dict} -> ", end="")

            current_row_delay_dict[reagent_num].setdefault((reagent_num, atom_y, loops_list[reagent_num]), 0)
            current_row_delay_dict[reagent_num][(reagent_num, atom_y, loops_list[reagent_num])] = current_row_delay_dict[reagent_num][(reagent_num, atom_y, loops_list[reagent_num])] + ((2 * atom_x + 6) + delay)
            position_list[reagent_num] = (atom_x, atom_y)
            current_row_list[reagent_num].append(atom_x + 1)

            ConditionalPrint(current_row_delay_dict)

            passed_delay = 0
            for element in current_row_list[reagent_num]:
                passed_delay += 2 * element + 4
            passed_delay -= (current_row_list[reagent_num][-1] + 3) + (reagent_masterlist[reagent_num]["Width"] + 5 + 2)
            passed_delay = max(passed_delay, 0)

            delay_array[reagent_num].append(delay)

            ConditionalPrint(f"Atoms in other rows will wait {passed_delay} for slowness and {delay} for sync: {sum(delay_array[reagent_num])} + {delay} + {3} = {sum(delay_array[reagent_num]) + delay + 3}: {past_row_delay_list} -> ", end="")
            past_row_delay_list[reagent_num][-1] = sum(delay_array[reagent_num]) + passed_delay + 3
            ConditionalPrint(past_row_delay_list)

            new_atom_dict = {}
            new_atom_dict["Type"] = atom["Type"]
            new_atom_dict["Object"] = atom["Object"]
            new_atom_dict["Reagent Num"] = atom["Reagent Num"]
            new_atom_dict["Position"] = atom["Position"]
            new_atom_dict["Coordinates"] = atom["Coordinates"]
            new_atom_dict["Order"] = atom["Order"]
            new_atom_dict["Cycle"] = value
            new_atom_dict["Delay"] = delay

            split_master_atom_list[reagent_num].append(new_atom_dict)
            whole_master_atom_list.append(new_atom_dict)

            if last_reagent_num != reagent_num:
                future_row_delay_list[reagent_num].append(delay)
            else:
                future_row_delay_list[reagent_num].append(0)
            last_reagent_num = reagent_num

    ConditionalPrint("-" * 100)
    ConditionalPrint(f"{split_master_atom_list = }")
    ConditionalPrint(f"{whole_master_atom_list = }")

    ConditionalPrint("-" * 100)
    for atom_into in whole_master_atom_list:
        ConditionalPrint(f"{atom_into = }")

    # ----------------------------------------------------------------------------------------------------
    # Sequencing: Using the theoretical minimum calculation, choose atoms in order by cycle available
    # ----------------------------------------------------------------------------------------------------

    ConditionalPrint("-" * 100)
    ConditionalPrint(f"{split_master_atom_list = }")
    ConditionalPrint(f"{reagent_atom_masterlist = }")

    grablist_list = []
    for reagent in split_master_atom_list:
        grablist = [atom["Order"] for atom in reagent]
        grablist.append("X")
        grablist_list.append(grablist)
    ConditionalPrint(f"{grablist_list = }")
    ConditionalPrint("-" * 100)

    pulldown_list = []
    loops_list = []
    delayarray_list = []

    for reagent_num in range(len(puzzle.reagents)):

        grablist = grablist_list[reagent_num]
        reagent_height = reagent_masterlist[reagent_num]["Height"]
        reagent_atom_list = reagent_atom_masterlist[reagent_num]

        pulldown = []
        loops = 0
        while len(grablist) != 1:
            for _ in range(reagent_height):
                pulldown.append([])
            for atom_num, atom in enumerate(reagent_atom_list):
                if (atom["Order"] % (reagent_atom_list[-1]["Order"] + 1)) == grablist[0]: #----------------------------------------------------------------- Assumes first is right
                    grablist.pop(0)
                    pulldown[loops * reagent_height + int(atom["Coordinates"][1])].append(int(atom["Coordinates"][0]) + 1)
            loops += 1
            if len(pulldown) > 100:
                raise Exception("Inappropriate Grablist")

        delayarray = []
        for box in pulldown:
            if len(box) == 0:
                delayarray.append(0)
            else:
                output = 0
                for element in box:
                    output += 2 * element + 4
                output -= (box[-1] + 3) + (reagent_masterlist[reagent_num]["Width"] + 5 + 2)
                output = max(output, 0)

                delayarray.append(output)

        pulldown_list.append(pulldown)
        loops_list.append(loops)
        delayarray_list.append(delayarray)

    # ----------------------------------------------------------------------------------------------------
    # Programing: Given the procomputed values, program the arms to execute the solution
    # ----------------------------------------------------------------------------------------------------

    for reagent_num in range(len(puzzle.reagents)):

        setcount(0, 1)

        reagent_width = reagent_masterlist[reagent_num]["Width"]
        reagent_height = reagent_masterlist[reagent_num]["Height"]

        toparmlist = toparmlist_list[reagent_num]
        bottomarmlist = bottomarmlist_list[reagent_num]
        prodarmlist = prodarmlist_list[reagent_num]
        wastearmlist = wastearmlist_list[reagent_num]
        outputarmlist = outputarmlist_list[reagent_num]

        pulldown = pulldown_list[reagent_num]
        loops = loops_list[reagent_num]
        delayarray = delayarray_list[reagent_num]

        for outerloop in range(loops):

            addinstr(0, 0, prodarmlist, "GRAB", 1)
            addinstr(0, 0, prodarmlist, "TRACK_PLUS", reagent_width)

            for innerloop in range(reagent_height):

                cycle = outerloop * reagent_height + innerloop
                pulldowns = pulldown[cycle]
                delay = delayarray[cycle]

                if innerloop != 0:
                    addinstr(0, 0, prodarmlist, "GRAB", 1)

                addinstr(0, 1, prodarmlist, "TRACK_PLUS", reagent_width + 1)

                stall_total = 0

                if len(pulldowns) != 0:

                    addcount(3, 0)

                    for value in pulldown[cycle]:
                        if future_row_delay_list[reagent_num]:
                            addcount(future_row_delay_list[reagent_num][0], False)
                            stall_total += future_row_delay_list[reagent_num].pop(0)

                    for armnum, arm in enumerate(bottomarmlist):
                        if (reagent_width - armnum) in pulldowns:
                            addinstrlist(1, 0, [arm], ["RETRACT", "DROP", "EXTEND"])

                addinstr(0, 0, prodarmlist, "TRACK_MINUS", reagent_width + 1)

                addcount(delay + stall_total, 1)

                addinstr(0, 0, prodarmlist, "RETRACT", 1)

                addinstr(0, 1, bottomarmlist, "TRACK_MINUS", 1)

                for armnum, arm in enumerate(wastearmlist):

                    addinstr(1, 0, [arm], "GRAB", 1)

                    for j in range(reagent_width - 1):
                        if armnum == j:
                            addinstrlist(0, 0, [arm], ["TRACK_PLUS", "DROP"])
                        else:
                            addinstrlist(0, 0, [arm], ["TRACK_PLUS", "x"])

                addinstr(0, 0, wastearmlist, "TRACK_MINUS", reagent_width - 1)

                addinstr(1, 0, toparmlist, "DROP", 1)
                addinstrlist(1, 0, bottomarmlist, ["DROP", "TRACK_PLUS"])

                addinstr(0, 0, prodarmlist, 'EXTEND', 1)

            addinstr(0, 0, prodarmlist, "TRACK_MINUS", reagent_width)

    # ----------------------------------------------------------------------------------------------------
    # Full Centralization: Take the atoms from the independent reagents and pipeline them with 2Arms
    # ----------------------------------------------------------------------------------------------------

    center_helico_list = []
    center_piston_list = []
    start_helico_container = []
    end_helico_container = []

    for reagent_num in range(len(puzzle.reagents)):
        addarm("ARM2", index(-3, 0, reagent_num), 1 - indexutility(reagent_num), 2, center_helico_list)
        addarm("PISTON", index(-2, 0, reagent_num), 1 - indexutility(reagent_num), 1, center_piston_list)
    addarm("ARM2", (2, 0), 0, 2, start_helico_container)
    addarm("ARM2", (6, 0), 0, 2, end_helico_container)

    for atom_info in whole_master_atom_list:

        arm_num = atom_info["Reagent Num"]
        outputarmlist = outputarmlist_list[arm_num]

        value = atom_info["Coordinates"][0] + 1
        cycle = atom_info["Cycle"] - 2 * value - 3


        setcount(cycle, True)

        addinstr(0, 0, outputarmlist, "TRACK_MINUS", value)
        addinstr(0, 0, outputarmlist, "GRAB", 1)
        addinstr(0, 0, outputarmlist, "TRACK_PLUS", value)
        addinstrlist(0, 0, outputarmlist, ["ROTATE_CW", "DROP", "ROTATE_CCW"])

    for atom_info in whole_master_atom_list:
        cycle = atom_info["Cycle"]
        arm_num = atom_info["Reagent Num"]

        setcount(cycle - 1, False)
        addinstrlist(0, 0, [center_helico_list[arm_num]], ["GRAB", "ROTATE_CW", "ROTATE_CW", "ROTATE_CW", "DROP"])
        setcount(cycle + 3, False)
        addinstrlist(0, 0, [center_piston_list[arm_num]], ["GRAB", "EXTEND", "DROP", "RETRACT"])
        setcount(cycle + 5, False)
        addinstrlist(0, 0, start_helico_container, ["GRAB", "ROTATE_CCW", "ROTATE_CCW", "ROTATE_CCW", "DROP"])
        setcount(cycle + 5 + 4, False)
        addinstrlist(0, 0, end_helico_container, ["GRAB", "ROTATE_CW", "ROTATE_CW", "ROTATE_CW", "DROP"])

    # ----------------------------------------------------------------------------------------------------
    # Full Output: Full decentralization from pipeline and molecule construction
    # ----------------------------------------------------------------------------------------------------

    input_arm_container_masterlist = []
    end_piston_masterlist = []
    end_helico_masterlist = []
    botharmlist_masterlist = []

    myoffset = 8

    for product_num in range(len(puzzle.products)):

        end_piston_container = []
        end_helico_container = []
        input_arm_container = []
        botharmlist = []

        addarm("PISTON", index2(10, 0, myoffset, product_num), indexutility2(product_num) + 3, 1, end_piston_container)
        addarm("ARM2", index2(11, 0, myoffset, product_num), indexutility2(product_num), 2, end_helico_container)
        for i in range(product_masterlist[product_num]["Width"]):
            addarm("PISTON", index2(14 + i, -1, myoffset, product_num), indexutility2(product_num) + 1, 2, botharmlist)
        for i in range(product_masterlist[product_num]["Width"]):
            addarm("PISTON", index2(14 + i, -2, myoffset, product_num), indexutility2(product_num) + 1, 2, botharmlist)
        addarm("ARM1", index2(16, -3, myoffset, product_num), indexutility2(product_num) + 2, 3, input_arm_container)

        addreg("BONDER", index2(13, 0, myoffset, product_num), indexutility2(product_num))

        addreg("BONDER", index2(14 + product_masterlist[product_num]["Width"], 0, myoffset, product_num), indexutility2(product_num) + 1)
        if product_masterlist[product_num]["Width"] > 1:
            addreg("BONDER", index2(14 + 2 * product_masterlist[product_num]["Width"], 0, myoffset, product_num), indexutility2(product_num) + 2)

        addtrack(indexlist2(13, 13 + 3 * product_masterlist[product_num]["Width"] - 1, product_num, -1, 0, myoffset))
        addtrack(indexlist2(13, 13 + 3 * product_masterlist[product_num]["Width"] - 1, product_num, -2, 0, myoffset))
        addtrack(indexlist2(15, 15 + product_masterlist[product_num]["Width"] + 1, product_num, -3, 0, myoffset))

        indexlist2(6, 9, product_num, 0, 0, 5)

        addelem("OUTPUT_STANDARD", index2(13 + product_masterlist[product_num]["Width"] - product_masterlist[product_num]["X-Offset"], 1 + product_masterlist[product_num]["Y-Offset"], myoffset, product_num), indexutility2(product_num), product_num)

        input_arm_container_masterlist.append(input_arm_container)
        botharmlist_masterlist.append(botharmlist)
        end_piston_masterlist.append(end_piston_container)
        end_helico_masterlist.append(end_helico_container)

    info_so_far = []
    val = 0

    product_atom_list = []
    for atom_list in product_atom_masterlist:
        for atom_info in atom_list:
            product_atom_list.append(atom_info)

    for timing_info, atom_info in zip(whole_master_atom_list, product_atom_list):

        product_num = atom_info["Product Num"]

        ConditionalPrint(f" - Product #{product_num}")
        ConditionalPrint(f"{timing_info = }")
        ConditionalPrint(f"{atom_info = }")

        input_arm_container = input_arm_container_masterlist[product_num]
        botharmlist = botharmlist_masterlist[product_num]
        end_piston_container = end_piston_masterlist[product_num]
        end_helico_container = end_helico_masterlist[product_num]

        info_so_far.append([atom_info["Bonds"], atom_info["Coordinates"][0]])

        setcount(timing_info["Cycle"] + 12, True)

        addinstrlist(0, 0, end_piston_container, ["EXTEND", "GRAB", "RETRACT", "DROP"])

        addcount(-1, True)

        addinstrlist(0, 0, end_helico_container, ["GRAB", "ROTATE_CW", "ROTATE_CW", "ROTATE_CW", "DROP"])

        addcount(-1, True)

        addinstr(0, 0, input_arm_container, "GRAB", 1)

        if atom_info["Bonds"][0]:
            addinstrlist(0, 0, input_arm_container, ["TRACK_PLUS", "DROP", "TRACK_MINUS"])
        else:
            addinstr(0, 0, input_arm_container, "TRACK_PLUS", product_masterlist[product_num]["Width"] - atom_info["Coordinates"][0])

            val = count

            addinstr(0, 0, input_arm_container, "DROP", 1)
            addinstr(0, 0, input_arm_container, "TRACK_MINUS", product_masterlist[product_num]["Width"] - atom_info["Coordinates"][0])

        if atom_info["Row End"]:

            setcount(val, True)

            addinstrlist(0, 0, botharmlist, ["GRAB", "EXTEND"])

            droplist = [0 for _ in range(2 * product_masterlist[product_num]["Width"] - 1)]
            for info in info_so_far:
                droplist[info[1]] = info[0][2]
            for info in info_so_far:
                if info[1] != product_masterlist[product_num]["Width"] - 1:
                    droplist[info[1] + product_masterlist[product_num]["Width"]] = info[0][1]

            for value in droplist:
                if value:
                    addinstrlist(0, 0, botharmlist, ["TRACK_PLUS", "RETRACT", "EXTEND"])
                else:
                    addinstr(0, 0, botharmlist, "TRACK_PLUS", 1)

            addinstr(0, 0, botharmlist, "TRACK_MINUS", 2 * product_masterlist[product_num]["Width"] - 1)
            addinstrlist(0, 0, botharmlist, ["DROP", "RETRACT"])
            info_so_far = []

    return partlist


# ----------------------------------------------------------------------------------------------------

Successes = 0
with zipfile.ZipFile("24hour-1-test.zip", "r") as puzzle_zip:
    for name in puzzle_zip.namelist():
        puzzle_bytes = puzzle_zip.read(name)
        if len(puzzle_bytes) == 0:
            continue

        puzzle_num = name[17:20]
        puzzle = om.Puzzle(puzzle_bytes)

        solution = om.Solution()
        solution.puzzle = puzzle.name
        solution.name = b"SpadeBot"
        solution.parts = spadehandler(puzzle, puzzle_num)

        if not solution.parts:
            continue

        solution_data = om.Sim(puzzle, solution)

        try:
            print(f"✅ - Puzzle #{puzzle_num} Succeeded! Cost: {solution_data.metric("cost")}, Cycles: {solution_data.metric("cycles")}, Area: {solution_data.metric("area")}")
            Successes += 1
        except:
            print(f"❓ - Puzzle #{puzzle_num} Failed: Elements are in order, go fix it bozo")
print(f"Final Tally: {Successes}/1000")