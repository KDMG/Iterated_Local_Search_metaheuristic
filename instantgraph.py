from pm4py.algo.discovery.footprints import algorithm as footprints_discovery
import os


def findCausalRelationships(net, im, fm):
    fp_net = footprints_discovery.apply(net, im, fm)
    return list(fp_net.get('sequence'))


def findDependency(V, W, tipo='ig'):
    edges = W.copy()
    edges.sort(key=lambda x: x[1])
    dep = {}
    if tipo == 'net':
        j = 1
    else:
        j = 0
    for n in V:
        dep[n[j]] = []

    for e in edges:
        n1 = e[0][j]  # node's input arc
        n2 = e[1][j]  # node's output arc
        for d in dep[n1]:
            if d not in dep[n2]:
                dep[n2].append(d)
        if n1 not in dep[n2]:
            dep[n2].append(n1)

    return dep


# find the dependency in the model's Petri net
def findDependencyNet(causal_rel, net):
    V = []
    nodes = []
    ts = net.transitions
    l = list(ts)
    transitions = sorted(l, key=lambda x: x.name)
    i = 1
    for t in transitions:
        if t.label:
            V.append((i, t.label))
            nodes.append(t.label)
            i += 1

    W = []
    for cr in causal_rel:
        id_n = nodes.index(cr[0])
        n1 = V[id_n]
        id_n = nodes.index(cr[1])
        n2 = V[id_n]
        W.append((n1, n2))

    dep = findDependency(V, W, 'net')
    return dep


def ExtractInstanceGraph(trace, cr, alignment=False):
    V = []
    W = []
    id = 0
    for event in trace:
        if alignment:
            V.append((id, event))
        else:
            V.append((id, event.get("concept:name")))
        id += 1
    for i in range(len(V)):
        for k in range(i, len(V)):
            e1 = V[i]
            e2 = V[k]
            if e1[0] == e2[0]:
                continue
            if (e1[1], e2[1]) in cr:
                flag_e1 = True
                for s in range(i + 1, k):
                    e3 = V[s]
                    if (e1[1], e3[1]) in cr:
                        flag_e1 = False
                flag_e2 = True
                for s in range(i + 1, k):
                    e3 = V[s]
                    if (e3[1], e2[1]) in cr:
                        flag_e2 = False

                if flag_e1 or flag_e2:
                    W.append((e1, e2))
    return V, W


# save ig from file, if there are more take the last one
def read_ig(path):
    list_dir = os.listdir()
    if path in list_dir:
        with open(path) as file:
            node_id = 0
            edge_id = 0
            while True:
                line = file.readline()
                if not line:
                    break
                elif line.strip() == 'XP':
                    # new ig
                    nodes = []
                    arcs = []
                    continue
                else:
                    line = line.strip().replace("\n", '')
                    dat = line.split(' ')
                    if dat[0] == 'v':
                        nodes.append((node_id, dat[2]))
                        node_id += 1
                    elif dat[0] == 'e':
                        arcs.append(((dat[1], dat[3]), (dat[2], dat[4])))
                        edge_id += 1
        return nodes, arcs
    else:
        print("Impossible to extract ig , inexistent path")
        return False


def final_restore(V, W, dep):
    new_ig = W.copy()
    for w in W:
        n1 = w[0]
        n2 = w[1]
        for d in dep[n1[0]]:
            e = (V[d], n2)
            if e in new_ig:
                new_ig.remove(e)
    return new_ig