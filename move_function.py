from random import randint
from admissible import soundness
from instantgraph import findDependency, final_restore


# extract only admissible nodes not present in the current IG
def admissible_edges(V, W):
    edges = []
    for i in range(0, len(V)):
        for f in range(i + 1, len(V)):
            if (V[i], V[f]) not in W:
                edges.append((V[i], V[f]))
    return edges


def repair_sound(V, W, ad_e, m_dep):
    check_s, inodes, fnodes = soundness(V, W)
    if check_s is False:
        W, ad_e = add_edge_nosound(inodes, fnodes, V, W, ad_e, m_dep)
    return W, ad_e


# add edges to make the ig sound
def add_edge_nosound(inodes, fnodes, V, W, ad_e, dependency):
    # nodes (activity) are ordered by execution
    for node_target in inodes:
        old = []
        i = V.index(node_target)
        if i == 0:
            continue
        while True:
            node_source = V[i - 1]
            edge = (node_source, node_target)
            if edge in ad_e and node_source[1] in dependency[node_target[1]]:
                W.append(edge)
                ad_e.remove(edge)
                if edge[0] in fnodes:
                    fnodes.remove(edge[0])
                break
            else:
                i -= 1
                old.append(edge)
                if i < 1:
                    for edge in old:
                        if edge in ad_e:
                            W.append(edge)
                            ad_e.remove(edge)
                            if edge[0] in fnodes:
                                fnodes.remove(edge[0])
                            break
                    break
                continue
    for node_source in fnodes:
        old = []
        i = V.index(node_source)
        if i == len(V) - 1:
            continue
        while True:
            node_target = V[i + 1]
            edge = (node_source, node_target)
            if edge in ad_e and node_source[1] in dependency[node_target[1]]:
                W.append(edge)
                ad_e.remove(edge)
                break
            else:
                i += 1
                old.append(edge)
                if i == len(V) - 1:
                    for edge in old:
                        if edge in ad_e:
                            W.append(edge)
                            ad_e.remove(edge)
                            break
                    break
                continue
    return W, ad_e


# updates the dependencies each time I remove an arc and restore the path
def local_search(V, W, iW, ad_e, k):
    old = []
    rnd = randint(0, len(W))
    move_done = []
    if rnd == len(W):
        a = "No Edge"
    else:
        a = W[rnd]

    while k:  # chose k arcs to remove
        k -= 1
        while a in old:  # this arc must not already be chosen
            rnd = randint(0, len(W))
            if rnd == len(W):
                a = "No Edge"
            else:
                a = W[rnd]
        old.append(a)

        W, ad_e = remove_edge(a, W, ad_e)
        # find the path to restore
        if a in iW:
            redges = restore_path(a[0], a[1], W, ad_e)
            if redges[0] == a:
                W, ad_e = add_edge(a, W, ad_e)
                move_done.append("No Path")
            else:
                cont = 0
                for red in redges:
                    if red not in W:
                        W, ad_e = add_edge(red, W, ad_e)        # IMPO UPDATE MARZO 2022
                        old.append(red)
                        cont += 1
                move_done.append("Restore "+ str(cont) + " edges")
        elif a != "No Edge":
            move_done.append("Remove edge")
        else:
            move_done.append("No Edge")
        dep = findDependency(V, W)
        W = final_restore(V, W, dep)
    return W, ad_e, move_done


def restore_path(inode, fnode, W, ad_e):
    redges = []
    n1 = inode
    while True:
        arcs = []
        for e in ad_e:
            if e[0] == n1 and e[1][0] <= fnode[0]:
                # take the arcs with n1 == inode if they have for n2 a node with id <= id_fnode
                arcs.append(e)
        # chose random arc from those available
        # if arcs == [] means that arc already exist to restore the path
        if arcs == []:
            for e in W:
                if e[0] == n1 and e[1][0] <= fnode[0]:
                    # chose path considered existing arc
                    arcs.append(e)
        if arcs == []:
            print("Cancel, stop in the rebuilding of path")
            redges.append((inode, fnode))
            break
        if n1 == inode and len(arcs) > 1:
            rnd_id = randint(0, len(arcs) - 2)  # last element is the arc removed before, the last to be added to ad_e
        else:
            rnd_id = randint(0, len(arcs) - 1)  # chose the last if there is only one
        edge = arcs[rnd_id]
        redges.append(edge)
        if edge[1] == fnode:  # not exist alternative path
            break
        else:
            n1 = edge[1]

    return redges


def add_edge(edge, W, ad_e):
    W.append(edge)
    ad_e.remove(edge)
    return W, ad_e


def remove_edge(edge, W, ad_e):
    if edge != "No Edge":
        ad_e.append(edge)
        W.remove(edge)
    return W, ad_e
