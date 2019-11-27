from builder import *
import numpy
##import random
from collections import defaultdict
import datetime
from skip_list import *
import lzma
import sys
from measures import edgecoverage 



def update_best_pair(pq, yeast_graph, human_graph, yeast_node, human_node, pairs, sims, delta = 0):
##    nonlocal pq
    paired_yeast_nodes = np.fromiter((pair[0] for pair in pairs), dtype=int)
    paired_human_nodes = np.fromiter((pair[1] for pair in pairs), dtype=int)
    yeast_neighbors = np.setdiff1d(
        yeast_graph.get_neighbors(yeast_node), paired_yeast_nodes)
    human_neighbors = np.setdiff1d(
        human_graph.get_neighbors(human_node), paired_human_nodes)
    # do the check here to save on a function call
    # also, saves on unnecessary enqueueing of empty pairs (-1, [])
    # cost: 2 extra comparisons and 1 boolean operation
##    print("yeast", yeast_neighbors)
##    print("human", human_neighbors)
    if yeast_neighbors.size == 0 or human_neighbors.size == 0:
        return
    
    bp_list = sub_best_pair(yeast_neighbors, human_neighbors, sims, delta)
    for (val, new_pairs) in bp_list:
        if val >= 0:
            for pair in new_pairs:
                pq.add((val, pair))
    
                ##pq.insert((val, pair))
    

def sub_best_pair(yeast_neighbors, human_neighbors, sims, delta):
    """
    sub_best_pair takes takes two sets of yeast and human neighbors
    plus a similarity matrix and returns the highest similarity
    pair of nodes in the two sets of neighbor nodes.
    runtime: O(|Y| * |H|)
    """
    s = sims[np.ix_(yeast_neighbors,human_neighbors)]
    # If the matrix is empty, no pair is found
##    if s.size == 0:
##        return (-1,[])

    #low = 1
    #low = max(s.max() - delta, 0.0)
    low = 0
    answers = []
    while(s.max() >= low):
        y_found, h_found = np.where(s == s.max())
        node_pairs = np.column_stack((yeast_neighbors[y_found], human_neighbors[h_found]))
##    np.random.shuffle(nodes) #do the shuffle when popping instead
        answers.append((s.max(), node_pairs))
        s[y_found, h_found] = -1
    return answers

##    simple dfs is very bad
##    y = random.sample(yeast, 1)[0]
##    h = random.sample(human, 1)[0]
##    return (y,h) + (sims[y][h],)
##
##    (a, b) = random.choice(np.column_stack(found))
##    return (yeast_list[a], human_list[b], s[a][b])
##    list(zip(found[0], found[1])))
##    don't use this for numpy arrays. It runs slower.

def best_pair(pq, delta):
    try:
        pair_list = pq.pop(delta)
    except IndexError:
        raise StopIteration("no more pair values")
    return pair_list[1] 


def fit_in_curr_align(g1, g2, node1, node2, pairs):
    neighbor1 = g1.get_neighbors(node1)
    neighbor2 = g2.get_neighbors(node2)
    flipped = False
    if len(neighbor1) > len(neighbor2):
        g1, g2 = g2, g1
        node1, node2 = node2, node1
        neighbor1, neighbor2 = neighbor2, neighbor1
        flipped = True 
    curr_alignment = {pair[1]:pair[0] for pair in pairs} if flipped else {pair[0]:pair[1] for pair in pairs}

    
    for node in neighbor1:
        if node in curr_alignment and curr_alignment[node] not in neighbor2:
            return False
    return True


def get_neighbor_pairs(g1, g2, node1, node2, g1alignednodes, g2alignednodes, sims):
    result = []
    
    for i in g1.get_neighbors(node1):
        for j in g2.get_neighbors(node2):
            if i not in g1alignednodes and j not in g2alignednodes:
                if sims[i][j] > 0:
        #pairs.add((seed1, seed2, sims[seed1][seed2]))
                    result.append((i,j))
            #if sims[i][j] != 0:
            #    result.append((i,j))
    return result


def strict_align(g1, g2, seed, sims, delta = 0):
    used_node1 = set()
    used_node2 = set()
    stack = []
    pairs = set()
    # initialize
    #print(g1.nodes)
    for seed1, seed2 in seed:
        #pairs.add((seed1, seed2, sims[seed1][seed2]))
        #print(g1.nodes[seed1])
        #print(seed1)
        pairs.add((seed1, seed2, sims[seed1][seed2]))
        used_node1.add(seed1)
        used_node2.add(seed2)
        stack += get_neighbor_pairs(g1,g2,seed1,seed2,sims) 

    # while we still have still nodes to expand
    while stack:
        node1, node2 = stack.pop()
        if node1 not in used_node1 and node2 not in used_node2:
            used_node1.add(node1)
            used_node2.add(node2)
            if fit_in_curr_align(g1,g2,node1,node2,pairs):
                pairs.add((node1,node2,sims[node1][node2]))
                #pairs.add((seed1, seed2, sims[g1.indexes[seed1]][g2.indexes[seed2]]))
                stack += get_neighbor_pairs(g1,g2,node1,node2,sims)
    return (used_node1, used_node2, pairs)


def stop_align2(g1, g2, seed, sims, ec_mode, delta = 0):
    g1alignednodes = set()
    g2alignednodes = set()
    aligned_pairs = set()
    pq = SkipList()
    stack = []
    
    for seed1, seed2 in seed:
        aligned_pairs.add((seed1, seed2, sims[seed1][seed2]))
        g1alignednodes.add(seed1)
        g2alignednodes.add(seed2)
        stack += get_neighbor_pairs(g1,g2,seed1,seed2,sims) 
        update_best_pair(pq, g1, g2, seed1, seed2, aligned_pairs, sims, delta)


    while len(g1alignednodes) < len(g1):
        try:
            curr_pair = best_pair(pq, delta)
            g1node = curr_pair[0]
            g2node = curr_pair[1]
            if g1node in g1alignednodes or g2node in g2alignednodes:
                continue
            if fit_in_curr_align(g1, g2, g1node, g2node, aligned_pairs):
                update_best_pair(pq, g1, g2, g1node, g2node, aligned_pairs, sims, delta)
                aligned_pairs.add((g1node, g2node, sims[g1node][g2node]))
                g1alignednodes.add(g1node)
                g2alignednodes.add(g2node)
        except(StopIteration): 
            break

    return (g1alignednodes, g2alignednodes, aligned_pairs)

def num_edges_back_to_subgraph(graph, node, aligned_nodes):
    edges = 0
   
    for neighbor_node in aligned_nodes:
        if graph.has_edge(node, neighbor_node):
            edges += 1

    '''
    for neighbor_node in graph.get_neighbors(node):
        if neighbor_node in aligned_nodes:
            edges += 1
    '''
    return edges


def num_edge_pairs_back_to_subgraph(g1, g2, g1node, g2node, aligned_pairs):
    edgepairs = 0
    #print("printing edges for M")
    for n1, n2 in aligned_pairs:
        if g1.has_edge(g1node, n1) and g2.has_edge(g2node, n2):
            #print(n1, n2)
            edgepairs += 1

    """
    for n1 in g1.get_neighbors(g1node):
        for n2 in g2.get_neighbors(g2node):
            if (n1, n2) in aligned_pairs:
                edgepairs += 1
    """
    return edgepairs


def local_align2(g1, g2, seed, sims, ec_mode, m, delta, debug=False):
    def update_edge_freq(g1node,g2node):
        del_nodes = []
        for n1, n2 in edge_freq:
            if n1 in g1alignednodes or n2 in g2alignednodes:
                del_nodes.append((n1,n2))
                continue

            if g1.has_edge(n1, g1node) and g2.has_edge(n2, g2node):
                edge_freq[(n1,n2)][0] += 1
                edge_freq[(n1,n2)][1] += 1
                edge_freq[(n1, n2)][2] += 1
            elif g1.has_edge(n1, g1node):
                edge_freq[(n1,n2)][0] += 1
            elif g2.has_edge(n2, g2node):
                edge_freq[(n1,n2)][1] += 1
        for node in del_nodes:
            del edge_freq[node]
            
    #m is number of edges in seed graphlet
    g1alignednodes = set()
    g2alignednodes = set()
    aligned_pairs = set()
    #pq = SkipList()

    candidatePairs = []
    ec1 = ec_mode[0]
    ec2 = ec_mode[1]
    E1 = E2 = EA = m
    local_over_global = True 
    if debug:
        print("aligning inital seeds*************************************************************************")
   
    listg1seed = "" 
    listg2seed = ""
    for seed1, seed2 in seed:
        listg1seed += str(g1.nodes[seed1]) + " " 
        listg2seed += str(g2.nodes[seed2]) + " " 
        #aligned_pairs.add((seed1, seed2, sims[seed1][seed2]))
        if debug:
            print((seed1,seed2))
        aligned_pairs.add((seed1, seed2))
        g1alignednodes.add(seed1)
        g2alignednodes.add(seed2)
            
        candidatePairs += get_neighbor_pairs(g1,g2,seed1,seed2,g1alignednodes, g2alignednodes,sims) 
        #update_best_pair(pq, g1, g2, seed1, seed2, aligned_pairs, sims, delta)

    listg1seed += listg2seed
    k = len(aligned_pairs)

    if(debug):
        print("ec1: " + str(ec1))
        print("ec2: " + str(ec2))
        print("local_over_global: " + str(local_over_global))

    done = False
        #candidatePairs = all pairs (u,v) within 1 step of S, u in G1, v in G2.

    edge_freq = {}

    whilecount = 0

    while(not done):

        done = True
        new_candidatePairs = []

        if(local_over_global):
            
            if debug:
                print("Calculating n1,n2,m for cand pairs: len= " + str(len(candidatePairs)), end=" ")
                sys.stdout.flush()

            for g1node, g2node in candidatePairs:
                if (g1node, g2node) in edge_freq:
                    continue
                n1 = num_edges_back_to_subgraph(g1, g1node, g1alignednodes)   
                n2 = num_edges_back_to_subgraph(g2, g2node, g2alignednodes)   
                M = num_edge_pairs_back_to_subgraph(g1, g2, g1node, g2node, aligned_pairs)            
                flag = M <= n1 and M <= n2
                if not flag:
                    print("g1 nieghbors : ")
                    print(g1.get_neighbors(g1node))
                    
                    alignedneighbors1 = [n for n in g1.get_neighbors(g1node) if n in g1alignednodes]

                    print("alignedneighbors g1node") 
                    print(alignedneighbors1) 

                    print("g2 nieghbors : ")
                    print(g2.get_neighbors(g2node))
                    
                    alignedneighbors2 = [n for n in g2.get_neighbors(g2node) if n in g2alignednodes]

                    print("alignedneighbors g2node") 
                    print(alignedneighbors2) 

                    print("aligned pairs:")
                    print(aligned_pairs)
            
                    
                assert(M <= n1 and M <= n2), f"M={M}, n1={n1}, n2={n2}, nodes=({g1node},{g2node})"


                edge_freq[(g1node, g2node)] = [n1, n2, M]
             

            '''
            if debug and whilecount == 0:
                print("edge freq")
                print(edge_freq)
            '''
        


            if ec1 > 0 and ec2 == 0:
                print("ec1 > 0 and ec2")
                candidatePairs = sorted(edge_freq, key = lambda x: (edge_freq[x][2]/edge_freq[x][0]-ec1) )
            elif ec2 > 0 and ec1 == 0:
                candidatePairs = sorted(edge_freq, key = lambda x: (edge_freq[x][2]/edge_freq[x][1]-ec2) )
            elif ec1 > 0 and ec2 > 0:
                candidatePairs = sorted(edge_freq, key = lambda x: (edge_freq[x][2]/(edge_freq[x][0]+edge_freq[x][1])) )
            
            assert(len(candidatePairs) > 0)
        
            if debug:
                print("sorted cand pairs")
                print("aligning cand pairs...")
   
            #if debug and whilecount < 4:
            #    for pair in candidatePairs:
            #        print(edge_freq[pair])
           
            for i in range(len(candidatePairs)-1, -1, -1):
                pair = candidatePairs.pop()
                n1val = edge_freq[pair][0]
                n2val = edge_freq[pair][1]
                mval = edge_freq[pair][2]

                assert n1val >= mval and n2val >= mval, "mval is smaller than n1val and n2val"
                if pair[0] not in g1alignednodes and pair[1] not in g2alignednodes:
                    if ((EA + mval)/(E1 + n1val)) >= ec1 and ((EA + mval)/(E2 + n2val)) >= ec2:
                        aligned_pairs.add(pair)
                        
                        if debug:
                            print("Added New Pair:", str(pair),end=" ")
                        
                        g1alignednodes.add(pair[0])
                        g2alignednodes.add(pair[1])
                        new_candidatePairs += get_neighbor_pairs(g1,g2,pair[0],pair[1], g1alignednodes, g2alignednodes, sims) 
                        #update_best_pair(pq, g1, g2, pair[0], pair[1], aligned_pairs, sims, delta)
                        
                        E1 += n1val
                        E2 += n2val
                        EA += mval
                        update_edge_freq(pair[0], pair[1])

                        if debug:
                            print("E1: " + str(E1),end=" ")
                            print("E2: " + str(E2),end=" ")
                            print("EA: " + str(EA),end=" ")
                        done = False

                        break

                    else:
                        new_candidatePairs.append(pair)
            if debug:
                print("Size of S: " + str(len(aligned_pairs)))

        whilecount += 1
        if len(new_candidatePairs) > 0:
            #done = False
            if debug:
                print("updating candPairs with newcandPairs")
            candidatePairs += new_candidatePairs
        else:
            if debug:
                print("Exiting because no new cand pairs")
            break
    if debug:
        print("whilecount: " + str(whilecount))

        print("E1: " + str(E1) + "E2: " + str(E2) + "EA: " + str(EA), end = " ")  
        print("DONE!!!!!!!!!!!!!!!!!!!!!!!!!!")

    '''
        else: # else use the similarity order
            curr_pair = best_pair(pq, delta)
            g1node = curr_pair[0]
            g2node = curr_pair[1]
            if g1node in g1alignednodes or g2node in g2alignednodes:
                continue
            update_best_pair(pq, g1, g2, g1node, g2node, aligned_pairs, sims, delta)
            aligned_pairs.add((g1node, g2node, sims[g1node][g2node]))
            g1alignednodes.add(g1node)
            g2alignednodes.add(g2node)
    '''
   
    output(k, E1,E2,EA,listg1seed,len(aligned_pairs))
    return (g1alignednodes, g2alignednodes, aligned_pairs)


def output(k, E1, E2, EA, seed, size):
    print("k:" + str(k) +  " size:" + str(size) + " E1:" + str(E1) + " E2:" + str(E2) + " EA:" + str(EA) + " seed: " + str(seed))



def local_align(g1, g2, seed, sims, ec_mode, m, delta, debug=False):
    #m is number of edges in seed graphlet
    g1alignednodes = set()
    g2alignednodes = set()
    aligned_pairs = set()
    pq = SkipList()

    candidatePairs = []
    ec1 = ec_mode[0]
    ec2 = ec_mode[1]
    E1 = E2 = EA = m
    local_over_global = False 
    if debug:
        print("aligning inital seeds*************************************************************************")

    for seed1, seed2 in seed:
        aligned_pairs.add((seed1, seed2, sims[seed1][seed2]))
        g1alignednodes.add(seed1)
        g2alignednodes.add(seed2)
        candidatePairs += get_neighbor_pairs(g1,g2,seed1,seed2,sims) 
        #update_best_pair(pq, g1, g2, seed1, seed2, aligned_pairs, sims, delta)

    if(debug):
        print("ec1: " + str(ec1))
        print("ec2: " + str(ec2))
        print("local_over_global: " + str(local_over_global))

    done = False
    while(not done):
        done = True
        new_candidatePairs = []
        #candidatePairs = all pairs (u,v) within 1 step of S, u in G1, v in G2.
        if(local_over_global):
            edge_freq = {}
            
            if debug:
                print("Calculating n1,n2,m for cand pairs: len= " + str(len(candidatePairs)), end=" ")
                sys.stdout.flush()

            for g1node, g2node in candidatePairs:
                n1 = num_edges_back_to_subgraph(g1, g1node, g1alignednodes)   
                n2 = num_edges_back_to_subgraph(g2, g2node, g2alignednodes)   
                M = num_edge_pairs_back_to_subgraph(g1, g2, g1node, g2node, aligned_pairs)            
                edge_freq[(g1node, g2node)] = (n1, n2, M)


            if ec1 > 0 and ec2 == 0:
                print("ec1 > 0 and ec2")
                candidatePairs = sorted(edge_freq, key = lambda x: -(edge_freq[x][2]/edge_freq[x][0]-ec1) )
            elif ec2 > 0 and ec1 == 0:
                candidatePairs = sorted(edge_freq, key = lambda x: -(edge_freq[x][2]/edge_freq[x][1]-ec2) )
            elif ec1 > 0 and ec2 > 0:
                candidatePairs = sorted(edge_freq, key = lambda x: -(edge_freq[x][2]/(edge_freq[x][0]+edge_freq[x][1])) )
            
            assert(len(candidatePairs) > 0)
        
            if debug:
                print("sorted cand pairs")
                print("aligning cand pairs...")
                
            for pair in candidatePairs:
                n1val = edge_freq[pair][0]
                n2val = edge_freq[pair][1]
                mval = edge_freq[pair][2]
                if ((EA + mval)/(E1 + n1val)) >= ec1 and ((EA + mval)/(E2 + n2val)):
                    if pair not in aligned_pairs:
                        aligned_pairs.add(pair)
                        if debug:
                            print(str(pair),end=" ")
                        g1alignednodes.add(pair[0])
                        g2alignednodes.add(pair[1])
                        new_candidatePairs += get_neighbor_pairs(g1,g2,pair[0],pair[1],sims) 
                        #update_best_pair(pq, g1, g2, pair[0], pair[1], aligned_pairs, sims, delta)
                        E1 += n1val
                        E2 += n2val
                        EA += mval
                        if debug:
                            print("E1: " + str(E1),end=" ")
                            print("E2: " + str(E2),end=" ")
                            print("EA: " + str(EA),end=" ")
                        done = False

                #else:
                    #new_candidatePairs.append(pair)
            print("Size of S: " + str(len(aligned_pairs)))
        else: # else use the similarity order
            curr_pair = best_pair(pq, delta)
            g1node = curr_pair[0]
            g2node = curr_pair[1]
            if g1node in g1alignednodes or g2node in g2alignednodes:
                continue
            update_best_pair(pq, g1, g2, g1node, g2node, aligned_pairs, sims, delta)
            aligned_pairs.add((g1node, g2node, sims[g1node][g2node]))
            g1alignednodes.add(g1node)
            g2alignednodes.add(g2node)
         
        if len(new_candidatePairs) != 0:
            #done = False
            print("updating candPairs with newcandPairs")
            candidatePairs = new_candidatePairs
        if len(new_candidatePairs) == 0:
            break

    #print("DONE!!!!!!!!!!!!!!!!!!!!!!!!!!")
    return (g1alignednodes, g2alignednodes, aligned_pairs)

def dijkstra(yeast_graph, human_graph, seed, sims, delta, num_seeds = 1):
    #global delta
    #delta above 0.01 takes a very long time to finish
    pq = SkipList() 
    pairs = set()
    yeast_nodes = set()
    human_nodes = set()

    seed_H, seed_Y = -1, -1

    while len(yeast_nodes) < len(yeast_graph):
        for _ in range(num_seeds):
            try: 
                seed_Y, seed_H = next(seed)
                while seed_Y in yeast_nodes or seed_H in human_nodes: #throw away bad seeds until you get a good one
                    seed_Y, seed_H = next(seed)
            except StopIteration: #no more seeds, end the loop
                return (yeast_nodes, human_nodes, pairs)

            yeast_nodes.add(seed_Y)
            human_nodes.add(seed_H)
            pairs.add((seed_Y, seed_H, sims[seed_Y][seed_H]))

        update_best_pair(pq, yeast_graph, human_graph, seed_Y, seed_H, pairs, sims, delta)
        while(True):
            try:
                curr_pair = best_pair(pq,delta)
                while curr_pair[0] in yeast_nodes or curr_pair[1] in human_nodes : #reject loop
                    curr_pair = best_pair(pq,delta)
                update_best_pair(pq, yeast_graph, human_graph, curr_pair[0], curr_pair[1], pairs, sims, delta)
                
                pairs.add(tuple(curr_pair) + (sims[curr_pair[0]][curr_pair[1]],))
                yeast_nodes.add(curr_pair[0])
                human_nodes.add(curr_pair[1])
            except StopIteration:
                break;

    return (yeast_nodes, human_nodes, pairs)




def induced_subgraph(graph1, graph2, aligned_pairs):
    result = []
    while aligned_pairs:
        p = aligned_pairs.pop()
        result.extend(
            [((p[0], q[0]), (p[1], q[1]))
                 for q in aligned_pairs
                    if graph1.has_edge(p[0],q[0])
                        and graph2.has_edge(p[1],q[1])])
    return result


def coverage(yeast, human, subgraph):
    y = len(subgraph) / (yeast.num_edges() / 2) * 100.0
    h = len(subgraph) / (human.num_edges() / 2) * 100.0
    return (y,h)

def unaligned_edges_g2_in(graph1, graph2, aligned_pairs, subgraph):
    uedges = []
    while aligned_pairs:
        p = aligned_pairs.pop()
        uedges.extend( [ (p[1], q[1]) for q in aligned_pairs if graph2.has_edge(p[1], q[1]) and ((p[0], q[0]), (p[1], q[1])) not in subgraph ]   )
    return uedges


def s3score(g1, g2, pairs, subgraph):
    aligned_edges = len(subgraph)
    u2in = unaligned_edges_g2_in(g1, g2, pairs, subgraph)
    denom = aligned_edges + (g1.num_edges() / 2) + len(u2in) 
    return aligned_edges/denom




def write_result(filename, pairs, graph1, graph2):
    #print('############',filename, len(pairs))
    #for pair in pairs:
    #    print(pair)
        
    with open(filename, 'w+')as f:
        #f.write(str(len(d)) + ' ' + str(coverage(yeast_graph, human_graph,d)) + '\n')
        for x in pairs:
            print(str(graph1.nodes[x[0]]) + ' ' + str(graph2.nodes[x[1]]))
            f.write(str(graph1.nodes[x[0]]) + ' ' + str(graph2.nodes[x[1]]) + '\n')
        #for g1node, g2node in pairs:
        #    print(str(graph1.nodes[g1node]) + ' ' + str(graph2.nodes[g2node]) + '\n')
        #    f.write(str(graph1.nodes[g1node]) + ' ' + str(graph2.nodes[g2node]) + '\n')


def to_name(pairs, yd, hd):
    return [(yd[yeast_graph], hd[human_graph]) for (yeast_graph, human_graph, sims) in pairs]


#import datetime
def log_file_name(start = 'bionet_yeast_human', ext = '.txt'):
    dtime = datetime.datetime.now()
    return start + '_' +dtime.strftime("%Y-%m-%d_%H-%M-%S") + ext