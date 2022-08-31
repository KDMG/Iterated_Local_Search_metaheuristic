import time
import random
import pandas as pd
from pm4py.objects.petri_net.importer import importer as pnml_importer
from pm4py.streaming.importer.xes import importer as xes_importer_big
from pm4py.objects.log.importer.xes.variants import iterparse as xes_importer
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.simulation.playout.process_tree import algorithm as tree_playout
from pm4py.objects.conversion.wf_net import converter as wf_net_converter
from admissible import soundness, fitting
from big_v1 import checkTraceConformance, big_algorithm
from big_v2 import BIG
from configuration import search_path, parameters
from generalization_function import acceptance, generalization, count_move, objective_function
from instantgraph import findCausalRelationships, ExtractInstanceGraph, findDependencyNet
from move_function import admissible_edges, local_search, repair_sound
from test_function import file_print, save_graph, import_graph


def metaeuristica(T, iterations, alpha, k, nodes, edges, model_dep, gen_max, aligned_ig):
    iedges = edges.copy()  # initial arcs to evaluate the weight of the moves made

    # Initialize variables
    fo_best = 100000
    fo_curr = 100000
    curr_e = edges.copy()
    best_e = []
    list_best = []
    sa_count = 0
    c_timeout = 0
    c_no_pt = 0
    never_sound = True

    t = time.time()

    # extract admissible edges, those present are not considered
    admiss_e = admissible_edges(nodes, edges)

    # first correction, make the IG sound
    edges, admiss_e = repair_sound(nodes, edges, admiss_e, model_dep)

    check_s, inodes, fnodes = soundness(nodes, edges)

    # if the correction was successful makes the acceptance phase
    if check_s:
        if fitting(nodes, edges, inodes):
            try:
                al_move = count_move(edges, aligned_ig)
                sa_count, curr_e, fo_curr, best_e, fo_best, list_best, c_timeout, c_no_pt, l = \
                    acceptance(nodes, edges, curr_e, 0, al_move, fo_curr, best_e, fo_best,
                               list_best, T, gen_max, beta, gamma)
            except Exception as e:
                print("Acceptance FAIL: ", e)

    meta_init = edges.copy()

    while iterations:
        iterations -= 1
        print("\nMissing iteration at the end : ", iterations, i)
        edges.clear()
        edges += curr_e

        # makes moves in local search and fixes ig to make it sound
        edges, admiss_e, move_done = local_search(nodes, edges, iedges, admiss_e, k)
        edges, admiss_e = repair_sound(nodes, edges, admiss_e, model_dep)

        if fitting(nodes, edges, inodes) is False:
            print("The trace doesn't fit the current IG, next iteration")
            continue

        never_sound = False

        # counts the different arcs between current IG and initial IG
        fo_move = count_move(edges, iedges)

        T = T * alpha
        fo_move -= k * 2
        # counts the different arcs between current IG and the IG from the alignment
        al_move = count_move(edges, aligned_ig)
        # acceptance phase
        sa_count, curr_e, fo_curr, best_e, fo_best, list_best, c_timeout, c_no_pt, l = \
            acceptance(nodes, edges, curr_e, fo_move, al_move, fo_curr, best_e, fo_best,
                       list_best, T, gen_max, beta, gamma, c_timeout, c_no_pt, sa_count)
        # l = list of data of interest that it saves on file
        l.insert(0, i)
        l += move_done
        file_print("IterationData.csv", l)
    t_meta = round(time.time() - t, 2)

    if never_sound: # a valid solution was never found
        move, g_best, g_init, r_best, r_init, fo1, fo2 = '-', '-', '-', '-', '-', 0, 0
    else: # make calculation with the best solution found
        move = count_move(best_e, iedges)
        al_move = count_move(edges, aligned_ig)
        g_best, r_best = generalization(nodes, best_e)
        g_init, r_init = generalization(nodes, meta_init)
        fo1, fo2, na, l = objective_function(nodes, best_e, move, al_move, gen_max, beta, gamma, len(curr_e))

    # --- print final data to file ---
    final_data = [len(nodes), len(best_e), t_meta, g_init, r_init, g_best, r_best, move, fo1, fo2, c_no_pt, sa_count, len(list_best)]

    return tuple(final_data), best_e, list_best


if __name__ == '__main__':

    seeds = [1, 2, 3]
    all_seed_df = []
    matrix = []
    t_init = time.time()
    npath, lpath = search_path()
    tot, T, iterations, alpha, k, beta, gamma = parameters()

    BIG("log/" + npath, "log/" + lpath)

    # ******* FILE PRINT ********
    index_file = ["seed", "trace id", "nodes", "meta edges", "time meta", "gen meta init", "nopt/timeout",
                  "gen meta", "nopt/timeout", "meta move", "fo1", "fo2", "tot no_pt", "tot sim ann", "tot ig", "diff ig align meta",
                  "big edges", "gen big", "big move", "diff ig align big"]
    file_print("IterationData.csv", ["trace id", "fo curr", "fo now", "fo1", "fo2", "result", "gen", "str_move", "alig_move"], "w")

    net, im, fm = pnml_importer.apply("log\\" + npath)

    # ---Generalization model: used to normalize the ob func ---
    tree = wf_net_converter.apply(net, im, fm)
    playout_variant = tree_playout.Variants.EXTENSIVE
    param = tree_playout.Variants.EXTENSIVE.value.Parameters
    simulated_log = tree_playout.apply(tree, variant=playout_variant,
                                       parameters={param.MAX_TRACE_LENGTH: len(net.transitions),
                                                   param.MAX_LIMIT_NUM_TRACES: 100000})
    gen_max = len(simulated_log)
    # ------

    log = xes_importer.import_log("log\\" + lpath)
    if tot == "max":
        tot = len(log)

    print("\nTraces to analyze: " + str(tot))
    cr = findCausalRelationships(net, im, fm)
    cr = sorted(cr, key=lambda x: x[0])
    model_dep = findDependencyNet(cr, net)
    conf_check = token_replay.apply(log[:tot], net, im, fm)

    # ---- big's log
    log2 = xes_importer_big.apply("log\\" + lpath, variant=xes_importer_big.Variants.XES_TRACE_STREAM)
    i = 0
    log_big = []
    aligned_traces = dict()
    for trace in log2:
        if not conf_check[i]['trace_is_fit']:
            aligned_traces[i] = alignments.apply_trace(trace, net, im, fm)
        log_big.append(trace)
        if i == tot - 1:
            break
        else:
            i += 1
    # ----

    # ---- alignment ig, to analyze the quality of the result
    aligned_igs = dict()
    for t in aligned_traces:
        align = aligned_traces[t]['alignment']
        trace = []
        for a in align:
            if a[1] != ">>" and a[1] != None:
                trace.append(a[1])
        V, W = ExtractInstanceGraph(trace, cr, True)
        aligned_igs[t] = W
    # ----

    exe_name = str(k) + "k_" + str(iterations) + "it_" + str(gamma) + "g_" + str(beta) +"b"

    t1 = time.time()
    for s in seeds:
        print()
        print("**********Seed: ", s)
        data_seed = []
        random.seed(s)

        # while i < tot:
        for i in aligned_igs.keys():
            print("*** Trace: " + str(i) + "/" + str(tot) + " *** Seed: "+ str(s) + "/" + str(len(seeds)))
            nodes, ed_init = ExtractInstanceGraph(log[i], cr)

            # ******************BIG*********************
            # only for first execution
            if s == 1:
                t = time.time()
                D, I = checkTraceConformance(log_big[i], net, im, fm)
                c_event_d = 0
                c_event_i = 0
                for delet in D:
                    c_event_d += len(delet)
                for inser in I:
                    c_event_i += len(inser)
                try:
                    big_best = big_algorithm(nodes, ed_init, D, I, cr)
                    t_big = round(time.time() - t, 2)
                    sound, inodes, fnodes = soundness(nodes, big_best)
                    diff_big = count_move(big_best, aligned_igs[i])

                    save_graph('ig\\big\\' + str(i) + '.g', nodes, big_best, True)
                    if big_best and sound:
                        g_big, r_big = generalization(nodes, big_best)
                        big_move = count_move(big_best, ed_init)
                        file_print('ig\\big\\' + str(i) + '.g', "SOUND")
                    else:
                        g_big, r_big, big_move = '-', '-', '-'
                        file_print('ig\\big\\' + str(i) + '.g', "NOT SOUND")
                except Exception as e:
                    print("Errore con BIG: ", e)
                    t_big = round(time.time() - t, 2)
                    big_best = '-'
                    g_big, r_big, big_move = '-', '-', '-'
                    diff_big = len(aligned_igs[i])

            # ---- take bigs ig from files
            big_nodes, big_best = import_graph("ig/big/" + str(i) + ".g")
            diff_big = count_move(big_best, aligned_igs[i])
            big_move = count_move(big_best, ed_init)
            g_big, r_big = generalization(nodes, big_best)
            # ----

            edges = ed_init.copy()
            l_file, meta_best, meta_list = metaeuristica(T, iterations, alpha, k, nodes, edges, model_dep, gen_max, aligned_igs[i])
            l_file = list(l_file)
            l_file.insert(0, i)
            diff = count_move(meta_best, aligned_igs[i])
            l_file.append(diff)
            print("Differenza fra ig dell'alignment e meta best: ", str(diff))

            l_file += [len(big_best), g_big, big_move, diff_big]
            # l_file += [0, 0, 0, 0, 0, 0, 0]
            # ******************************************

            # ---- PRINT BESTS META TO FILE ---
            ig_path = 'ig\\bpi2012\\ig_' + exe_name + '_id' + str(i) + '.g'
            if s == 1:
                file_print(ig_path, "Parameter: " + exe_name, 'w')
            file_print(ig_path, "*** Seed: " + str(s) + " ***")
            save_graph(ig_path, nodes, meta_best)
            for ig in meta_list:
                save_graph(ig_path, nodes, ig[1])
            # -----

            i += 1
            l_file.insert(0, s)
            data_seed.append(l_file)
        matrix += data_seed

    # total dataframe for every execution seed
    df = pd.DataFrame(matrix, columns=index_file)
    df_avg = df.drop(['seed', 'nodes', 'gen meta init', 'nopt/timeout', 'nopt/timeout'], axis=1)
    avg = []
    trace_ids = list(aligned_igs.keys())
    for trace in trace_ids:
        df_small = df_avg[df_avg['trace id'] == trace]
        avg.append(df_small.mean())
    df_avg = pd.DataFrame(avg, index=trace_ids)
    df_avg.drop('trace id', axis=1, inplace=True)

    with pd.ExcelWriter("output\\multi_seeds.xlsx", mode='a', if_sheet_exists="replace") as writer:
        df_avg.to_excel(writer, sheet_name='avg' + exe_name)

    with pd.ExcelWriter("output\\multi_seeds" + exe_name + ".xlsx") as writer:
        for i in seeds:
            df[df['seed'] == i].to_excel(writer, sheet_name='res_' + str(i), index=False)

    file_print("output\\times.csv", [exe_name, time.time() - t_init])
