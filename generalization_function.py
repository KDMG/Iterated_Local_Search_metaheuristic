import sys

from pm4py.objects.petri_net.utils import petri_utils
from pm4py.algo.simulation.playout.process_tree import algorithm as tree_playout
from pm4py.objects.conversion.wf_net import converter as wf_net_converter
import math
from random import randint, random
import time
from collections import Counter
from pm4py.objects import petri_net
from pm4py.objects.petri_net.obj import PetriNet, Marking
from test_function import save_graph, division, file_print


def create_petrinet(nodes, edges):
    net = PetriNet("Instant Graph")
    # build a transaction for each node
    tran = []
    i = 0
    for n in nodes:
        tran.append(PetriNet.Transition(n, n))
        net.transitions.add(tran[i])
        i += 1
    # for every arc build a place and two arcs
    # build also source and sink
    places = []
    i = 0
    for a in edges:
        name = "p_" + str(i + 1)
        places.append(PetriNet.Place(name))
        net.places.add(places[i])
        a1 = nodes.index(a[0])
        a2 = nodes.index(a[1])
        petri_utils.add_arc_from_to(tran[a1], places[i], net)
        petri_utils.add_arc_from_to(places[i], tran[a2], net)
        i += 1
    source = PetriNet.Place("source")
    sink = PetriNet.Place("sink")
    net.places.add(source)
    net.places.add(sink)
    petri_utils.add_arc_from_to(source, tran[0], net)
    petri_utils.add_arc_from_to(tran[len(tran) - 1], sink, net)
    # names initial and final marking
    im = Marking()
    im[source] = 1
    fm = Marking()
    fm[sink] = 1
    return net, im, fm


# function that evaluates the quality of the current solution
def objective_function(V, W, struct_move, align_move, gen_max, beta, gamma, m):
    gen1, d = generalization(V, W)
    if d == "t_out":
        return 0, 0, d, 0

    # ----- normalizing values ------
    if struct_move < 0:
        struct_move = 0
    else:
        struct_move = struct_move / (m * 2)

    if align_move < 0:
        struct_move = 0
    else:
        align_move = align_move / (m * 2)

    gen = gen1 / gen_max

    fo1 = beta * gen
    fo2 = (1 - beta) * (gamma * struct_move + (1 - gamma) * align_move)
    return fo1, fo2, d, gen1


# function that holds or discards igs based on the result of the objective function
def acceptance(V, W, curr_e, struct_move, align_move, fo_curr, best_e, fo_best,
               list_best, T, gen_max, beta, gamma, c_timeout=0, c_no_pt=0, sa_count=0):

    fo1, fo2, d, gen= objective_function(V, W, struct_move, align_move, gen_max, beta, gamma, len(curr_e))
    if d == "t_out":
        c_timeout += 1
        c_no_pt += 1
        return sa_count, curr_e, fo_curr, best_e, fo_best, list_best, c_timeout, c_no_pt, []
    elif d == "no_pt":
        c_no_pt += 1

    fo = fo1 + fo2

    ris = 0      # ris = 0 reject the solution
    if fo == fo_curr:
        ris = randint(0, 1)
    if ris:
        ris = 2  # ris = 2 take the new one, fo are equal
    if fo > fo_curr:
        ris, prob, z = simulatedannealing(fo_curr, fo, T)
        if ris:  # ris = 1 take from sim annealing
            sa_count += 1

    if fo < fo_curr:
        ris = 3  # ris = 3 the new one is better

    if ris > 0:
        # update IG CURR values
        curr_e.clear()
        curr_e += W
        fo_curr = fo
        if fo < fo_best:
            ris = 4  # ris = 4 the new one is the best
            fo_best = fo
            list_best.clear()
            list_best.append((V, W))
            best_e.clear()
            best_e += W

    check_eq = False
    if fo == fo_best:
        for (nod, edg) in list_best:  # scroll all the igs best
            for e in W:  # for all the edge in the current ig check if is in the ig best in the list
                if e not in edg:
                    check_eq = True
                    break
            if check_eq:
                break
        if check_eq:
            list_best.append((V, W))

    list = [fo_curr, fo, fo1, fo2, ris, gen, struct_move, align_move] # data to save in csv file
    return sa_count, curr_e, fo_curr, best_e, fo_best, list_best, c_timeout, c_no_pt, list


# return 1 if take IG' like new IG, 0 otherwise
def simulatedannealing(fo_curr, fo1, a):
    div = division((fo_curr - fo1), a, 5)
    prob = math.exp(div)
    z = random()
    if z < prob:
        return 1, prob, z
    else:
        return 0, prob, z


# count the different arcs between the two igs considered
def count_move(curr, start):
    count = 0
    for e in start:
        if e not in curr:
            count += 1  # count remove
    for e in curr:
        if e not in start:
            count += 1  # count add
    return count


def simulator_apply(net, im, fm, max_trace_length=1000):
    max_marking_occ = sys.maxsize
    semantics = petri_net.semantics.ClassicSemantics()

    t_init = time.time()
    feasible_elements = []

    to_visit = [(im, (), ())]
    visited = set()

    while len(to_visit) > 0:
        t_curr = time.time() - t_init
        # ***** TIMEOUT *****
        if t_curr > 1:
            return 0, 1

        state = to_visit.pop(0)

        m = state[0]
        trace = state[1]
        elements = state[2]

        try:
            if trace in visited:
                continue
            visited.add((m, trace))
        except Exception as e:
            print("Failed simulator_apply:", e)
            return 0, 1

        en_t = semantics.enabled_transitions(net, m)

        if (fm is not None and m == fm) or (fm is None and len(en_t) == 0):
            if len(trace) <= max_trace_length:
                feasible_elements.append(elements)

        for t in en_t:
            new_elements = elements + (m,)
            new_elements = new_elements + (t,)

            counter_elements = Counter(new_elements)

            if counter_elements[m] > max_marking_occ:
                continue

            new_m = semantics.weak_execute(t, net, m)
            if t.label is not None:
                new_trace = trace + (t.label,)
            else:
                new_trace = trace

            new_state = (new_m, new_trace, new_elements)

            if new_state in visited or len(new_trace) > max_trace_length:
                continue
            to_visit.append(new_state)

    return len(feasible_elements), 0


# calculates the generalization of one ig
def generalization(nodes, edges):
    new_nodes = []
    new_edges = []
    for n in nodes:
        new_nodes.append(str(n[0]) + '_' + n[1])
    for e in edges:
        new_edges.append((str(e[0][0]) + '_' + e[0][1], str(e[1][0]) + '_' + e[1][1]))
    net, im, fm = create_petrinet(new_nodes, new_edges)

    try:
        tree = wf_net_converter.apply(net, im, fm)
        playout_variant = tree_playout.Variants.EXTENSIVE
        param = tree_playout.Variants.EXTENSIVE.value.Parameters
        simulated_log = tree_playout.apply(tree, variant=playout_variant,
                                           parameters={param.MAX_TRACE_LENGTH: len(nodes),
                                                       param.MAX_LIMIT_NUM_TRACES: 100000})
        gen = len(simulated_log)
        return gen, "-"

    except Exception as e:
        if e.args[0] == "The Petri net provided is not a WF-net":
            save_graph("not_wf_net.g", nodes, edges)
            return 1000000, 'no_wf_net'
        gen, timeout = simulator_apply(net, im, fm, len(nodes))

        if timeout:
            res = "t_out"
        else:
            res = "no_pt"
        return gen, res
