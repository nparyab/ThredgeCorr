from __future__ import print_function
import numpy as np
import scipy as sp
import scipy.sparse as sprs

from scipy.optimize import newton

from numpy.random import multivariate_normal

def ccdf(x):
    return 1 - 0.5*(1 + sp.special.erf(x/np.sqrt(2)))

class ThredgeCorrGraph:

    def __init__(self,N,covariance,mean_degree=None,threshold=None):


        if (mean_degree is None) and (threshold is not None):
            self.t = threshold
        elif (mean_degree is not None) and (threshold is None):
            p = mean_degree / (N-1.0)
            self.t = sp.optimize.newton(lambda x: ccdf(x) - p, 0)

        self.N = N
        self.m = int(N*(N-1)/2)

        self.update_covariance(covariance)

        self.X = None

    def set_threshold(self, threshold):
        self.t = threshold

    def set_mean_degree(self, mean_degree):
        p = mean_degree / (self.N-1.0)
        self.t = sp.optimize.newton(lambda x: ccdf(x) - p, 0)


    def edge_index(self,i,j):
        return int(i*self.N + j - (i+2)*(i+1) * 0.5)

    def node_indices_slow(self,e):
        marker = e
        for i in range(self.N):
            delta = self.N - 1 - i
            if marker - delta < 0:
                break
            else:
                marker -= delta
        j = int(e - i * self.N + 0.5*(i+1)*(i+2))
        return i, j

    def node_indices(self,e):
        N = self.N

        lower_bound = (N-1.5) - np.sqrt( (N-1.5)**2 -2*e-4+2*N )
        i = int(np.ceil(lower_bound))
        j = int(e - i * N + 0.5*(i+1)*(i+2))

        return i,j

    def update_covariance_slow(self,covariance):
        """Create the covariance matrix and the cholesky matrix subsequently"""

        self.b = b = covariance

        C = np.eye(self.m)

        for e1 in range(self.m):
            i1, j1 = self.node_indices(e1)
            for e2 in range(e1+1, self.m):
                i2, j2 = self.node_indices(e2)

                if (i1 == i2) or (i1 == j2) or (j1 == i2) or (j1 == j2):
                    C[e1, e2] = b
                    C[e2, e1] = b


        self.C = C
        self.L = np.linalg.cholesky(C)

    def update_covariance(self,covariance):
        """Create the covariance matrix and the cholesky matrix subsequently"""

        self.b = b = covariance

        C = np.eye(self.m)

        for node in range(self.N):
            for neighbor1 in range(node+1,self.N-1):
                edge1 = self.edge_index(node,neighbor1)
                for neighbor2 in range(neighbor1+1,self.N):
                    edge2 = self.edge_index(node,neighbor2)
                    edge3 = self.edge_index(neighbor1,neighbor2)

                    C[edge1, edge2] = b
                    C[edge2, edge1] = b
                    C[edge1, edge3] = b
                    C[edge3, edge1] = b
                    C[edge2, edge3] = b
                    C[edge3, edge2] = b
                    
        self.C = C
        self.L = np.linalg.cholesky(C)

    def generate_weight_vector(self):
        #self.X = self.L.dot( np.random.normal(0,1,self.m) )
        self.X = self.L.dot( np.random.randn(self.m) )

    def threshold_and_get_edgelist(self,threshold):
        if self.X is None:
            self.generate_weight_vector()

        ndx = np.where(self.X>=threshold)[0]

        edges = []
        for e in ndx:
            edges.append( self.node_indices(e) )

        return edges

    def get_new_edge_list(self):
        self.X = None
        return self.threshold_and_get_edgelist(self.t)

    def get_new_adjacency_matrix(self,sparse=False):
        self.X = None
        edges = self.threshold_and_get_edgelist(self.t)

        if sparse:
            rowcol = np.array(edges,dtype=int)
            if len(rowcol) == 0:
                return np.zeros(N)
            A = sprs.csr_matrix((np.ones(len(edges)),(rowcol[:,0], rowcol[:,1])),shape=(N,N),dtype=int)
            A += A.T
            return A
        else:
            A = np.zeros((self.N, self.N))
            for i, j in edges:
                A[i, j] = 1
            A += A.T
            return A




class NumpyThredgeCorrGraph(ThredgeCorrGraph):

    def get_n_edge_lists(self,n):

        X = multivariate_normal(np.zeros(self.C.shape[:1]),self.C,size=n)

        edges = []
        for meas in range(n):
            these_edges = []
            ndx = np.where(X[meas,:]>self.t)[0]
            these_dges = []
            for e in ndx:
                these_edges.append( self.node_indices(e) )
            edges.append(these_edges)

        return edges


def get_degrees_from_edge_list(N,edges):
    rowcol = np.array(edges,dtype=int)
    if len(rowcol) == 0:
        return np.zeros(N)
    A = sprs.csr_matrix((np.ones(len(edges)),(rowcol[:,0], rowcol[:,1])),shape=(N,N),dtype=int)
    A += A.T
    k = np.asarray(A.sum(axis=1)).flatten()
    return k
        

if __name__ == "__main__":

    
    N = 100 

    from time import time

    start = time()
    A = ThredgeCorrGraph(N,0.4,.5)
    #T = NumpyThredgeCorrGraph(N,0.49,.5)
    end = time()

    print("fast method; N =", N, '; took', end-start, 'seconds')

    #start = time()
    #A.update_covariance_slow(0.1)
    #end = time()

    #print("slow method; N =", N, '; took', end-start, 'seconds')


    import networkx as nx
    import matplotlib.pyplot as pl

    k1 = []
    C1 = []
    k2 = []
    C2 = []

    #np_edges = T.get_n_edge_lists(500)
    
    for meas in range(500):
        edges = A.get_new_edge_list()
        ks = get_degrees_from_edge_list(N,edges)
        k1.extend( ks.tolist())
        """
        G = nx.Graph()
        G.add_nodes_from(range(N))
        G.add_edges_from(edges)

        ks = [ d[1] for d in list(G.degree())]
        C1.append(nx.average_clustering(G))
        k1.extend(ks)

        """

        #edges = np_edges[meas]
        #k2.extend(ks)

    #print(np.array(k).mean())
    #print(np.array(C).mean())

    from rocsNWL.drawing import draw

    pl.figure()
    pl.hist(k1,histtype='step',bins=max(k1))
    #pl.hist(k2,histtype='step',bins=max(k2))
    pl.xscale('log')
    pl.yscale('log')
    print(np.mean(k1))

    #pl.figure()
    #pl.hist(C1,histtype='step')
    #pl.hist(C2,histtype='step')

    pl.figure()

    G = nx.Graph()
    G.add_nodes_from(range(N))
    G.add_edges_from(edges)
    #draw(G,labels=list(range(N)))
    draw(G)

    fig,ax = pl.subplots(1,2,figsize=(10,5))
    ax[0].set_title("bruteforce")
    ax[0].spy(A.C)

    #ax[1].set_title("sophisticated")
    #ax[1].spy(A.C2)

    print(A.L[-3:,-3:])

    pl.figure()
    pl.spy(A.L)

    pl.show()

    """
    for node in range(N-1):
        for neigh in range(node+1,N):
            print("===========")
            print(node, neigh)
            print(A.edge_index(node,neigh))
            print(A.node_indices(A.edge_index(node,neigh)))
            """