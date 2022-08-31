from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments


def checkTraceConformance(trace, net, initial_marking, final_marking):
    aligned_traces = alignments.apply_trace(trace, net, initial_marking, final_marking)
    D = []
    I = []
    id = 0
    temp_d = []
    temp_i = []
    prev_d = False
    curr_d = False
    prev_i = False
    curr_i = False
    for edge in aligned_traces['alignment']:
        id += 1
        if edge[1] is None:
            id -= 1
            continue
        if edge[0] == '>>':
            temp_d.append((id, edge[1]))
            curr_d = True
            id -= 1
        if edge[1] == '>>':
            temp_i.append((id, edge[0]))
            curr_i = True

        if (prev_i and not curr_i):
            if len(temp_i) > 0:
                I.append(temp_i)
            temp_i = []
        prev_i = curr_i
        curr_i = False
        if (prev_d and not curr_d):
            if len(temp_d) > 0:
                D.append(temp_d)
            temp_d = []

        prev_d = curr_d
        curr_d = False
    if len(temp_i) > 0:
        I.append(temp_i)
    if len(temp_d) > 0:
        D.append(temp_d)
    return D, I


def irregularGraphRepairing(V, W, D, I, cr):
  Wi=W
  all_deleted_labels = []
  for d_element in D:
      for element in d_element:
        if element[1] not in all_deleted_labels:
          all_deleted_labels.append(element[1])
  for d_element in D:
    Wi=DeletionRepair(Wi, V, d_element,cr, all_deleted_labels)

  all_inserted = []
  for i_element in I:
    for i in i_element:
      if i not in all_inserted:
        all_inserted.append(i)
  for i_elements in I:
    Wi=InsertionRepair(Wi,V,i_elements,cr, all_inserted)
  return Wi


def isReachable(V, W, s, d):
    # Mark all the vertices as not visited
    visited = [False] * (len(V))

    # Create a queue for BFS
    queue = []

    # Mark the source node as visited and enqueue it
    queue.append(s)
    visited[s[0] - 1] = True

    while queue:

        # Dequeue a vertex from queue
        j = queue.pop(0)

        # If this adjacent node is the destination node, then return true
        if j == d:
            return True

        # Else, continue to do BFS
        for edge in W:
            if edge[0] == j:
                if visited[edge[1][0] - 1] == False:
                    queue.append(edge[1])
                    visited[edge[1][0] - 1] = True

    # If BFS is complete without visited dep
    return False


def DeletionRepair(Wi, V, d_elements, cr, all_deleted):
  v_len = len(V)
  Wr1 = []
  Wr2 = []
  i = d_elements[0][0]

  if i <= v_len:
    for edge in Wi:
      if edge[1][0] == i and edge[0][0] < i and (d_elements[-1][1],V[i-1][1]) in cr:
        for h in range(edge[0][0], i):
          if (V[h-1][1],d_elements[0][1]) in cr:
            Wr1.append(edge)
            break

      if edge[0][0] < i and edge[1][0] > i and (d_elements[-1][1],edge[1][1]) in cr:
        if edge[0][1] in all_deleted:
          Wr2.append(edge)
        elif (edge[0][1],d_elements[0][1])  in cr:
          for l in range(i+1, edge[1][0]):
            if (V[l-1],edge[1]) in Wi:
              Wr2.append(edge)
              break

  Wi = list(set(Wi) - set(Wr1 + Wr2))
  for k in range(i - 1, 0, -1):
    for j in range(i, v_len+1):
      if (V[k-1][1],d_elements[0][1]) in cr:
        if (d_elements[-1][1], V[j-1][1]) in cr:
          if not isReachable(V, Wi, V[k-1], V[j-1]):
            flag1 = True
            for l in range(k + 1, j):
              if (V[k-1],V[l-1]) in Wi:
                flag1 = False
                break
            flag2 = True
            for m in range(k + 1, i):
              if (V[m-1],V[j-1]) in Wi:
                flag2 = False
                break
            if flag1 or flag2:
              Wi.append((V[k-1],V[j-1]))
  return Wi


def InsertionRepair(W, V, i_elements, cr, all_inserted):
    v_len = len(V)
    Wr1 = []
    Wr2 = []
    Wr3 = []
    Wr4 = []
    Wr5 = []
    Wa1 = []
    Wa2 = []
    Wa3 = []
    i = i_elements[0][0]
    j = i + len(i_elements) - 1
    Wi = W.copy()

    for edge in Wi:
        if edge[0][0] < i and edge[1][0] >= i and edge[1][0] <= j:
            Wr1.append(edge)
        if edge[0][0] >= i and edge[0][0] <= j and edge[1][0] > j:
            Wr2.append(edge)
        if edge[0][0] >= i and edge[0][0] <= j and edge[1][0] >= i and edge[1][0] <= j:
            Wr3.append(edge)
    Wi = list(set(Wi) - set(Wr1 + Wr2 + Wr3))

    for k in range(j + 1, v_len + 1):
        if V[k - 1] not in all_inserted:
            if (V[i - 2][1], V[k - 1][1]) in cr or (V[i - 2], V[k - 1]) in Wi:
                if not isReachable(V, Wi, V[j - 1], V[k - 1]):
                    Wi.append((V[j - 1], V[k - 1]))
                    Wa1.append((V[j - 1], V[k - 1]))

    if i == v_len or (V[i - 2][1], V[i][1]) not in cr:
        Wi.append((V[i - 2], V[i - 1]))
        Wa2.append((V[i - 2], V[i - 1]))
    else:
        for k in range(i - 1, 0, -1):
            if V[k - 1] not in all_inserted:
                if j < v_len and ((V[k - 1][1], V[j][1]) in cr or (V[k - 1], V[j]) in Wi):
                    if not isReachable(V, Wi, V[k - 1], V[i - 1]):
                        Wi.append((V[k - 1], V[i - 1]))
                        Wa2.append((V[k - 1], V[i - 1]))

    for k in range(i, j):
        Wa3.append((V[k - 1], V[k]))
    if len(Wa3) > 0:
        Wi = Wi + Wa3

    for edge in Wa2:
        for edge2 in Wa1:
            if edge[1][0] >= i and edge[1][0] <= j:
                if edge2[0][0] >= i and edge2[0][0] <= j:
                    Wr4.append((edge[0], edge2[1]))
    Wi = list(set(Wi) - set(Wr4))

    if i == v_len or (V[i - 2][1], V[i][1]) not in cr:
        for edge in Wi:
            if edge[1][0] > i and edge[0][0] == i - 1:
                Wr5.append(edge)
        Wi = list(set(Wi) - set(Wr5))
    return Wi


def big_algorithm(V, W, D, I, cr):

    if len(D) + len(I) > 0:
        W = irregularGraphRepairing(V, W, D, I, cr)

    return W