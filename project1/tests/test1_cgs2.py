"""
Created on 21.10.2023

CGS2

@author: Jiaye Wei <jiaye.wei@epfl.ch>
"""

from mpi4py import MPI 
import numpy as np
from numpy.linalg import norm
from helpers import matrix_1, loss_of_orthogonality

# Initialize MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

wt = MPI.Wtime()

m = 500
n = 60
local_size = int(m/size)

# Define
W = None
Q = None
R = None
Qkreceived = None
QT = None
P = None
P_square = None
Basis = None
losses = None

if rank == 0:
    W = matrix_1(m, n)
    Q = np.zeros((m,n), dtype = 'd')
    QT = np.zeros((n,m), dtype = 'd')
    Qkreceived = np.zeros((m, 1), dtype = 'd')
    R = np.zeros((n,n), dtype = 'd')
    P = np.eye(m, dtype = 'd') 
    P_square = np.eye(m, dtype='d')
    Basis = np.zeros((m,1), dtype='d')
    losses = np.zeros((n, 1), dtype='d')

# First build Q and R
W_local = np.zeros((local_size, n), dtype = 'd')
q_local = np.zeros((local_size, 1), dtype = 'd')
QT_local = np.zeros((local_size, m), dtype = 'd')
P_local = np.zeros((local_size, m), dtype = 'd')
W_local = comm.bcast(W, root=0)
comm.Scatterv(P_square, P_local, root=0)

# For the first column
q_local = P_local @ W_local[:, 0]
# Normalize
comm.Gather(q_local, Qkreceived, root = 0)
if rank == 0:
    col = Qkreceived[:, 0] /norm(Qkreceived)
    Q[:, 0] = col
    QT[0, :] = col
    Basis[:, 0] = col
    losses[0] = loss_of_orthogonality(Basis)
comm.Barrier()

comm.Scatterv(QT, QT_local, root=0) # We have columns of Q (or rows of Qt)

# Start iterations in columns
for k in range(1, n):
    # Build the projector P
    localMult = 1/size * np.eye(m) - np.transpose(QT_local) @ QT_local
    P = comm.reduce(localMult, op=MPI.SUM, root=0)
    if rank == 0:
        P_square = P @ P
    
    # Scatter the rows of projector to each processor
    comm.Scatterv(P_square, P_local, root=0) 
    
    # Local multiplication
    q_local = P_local @ W_local[:, k]
    
    # Gather local results
    comm.Gather(q_local, Qkreceived, root=0)
    
    # Normalize
    if rank == 0:
        col = Qkreceived[:, 0] /norm(Qkreceived)
        Q[:, k] = col
        QT[k, :] = col
        Basis = np.column_stack((Basis, col))
        losses[k] = loss_of_orthogonality(Basis)
        
    comm.Barrier()
    
    # Scatter QT to prepare for the next iteration
    comm.Scatterv(QT, QT_local, root=0)

# Compute R as R = Q^t*W
W_rows = np.zeros((local_size, n), dtype='d')
Q_local = np.zeros((local_size, n), dtype='d')
comm.Scatterv(W, W_rows, root=0)
comm.Scatterv(Q, Q_local, root=0)
localMult_R = np.transpose(Q_local) @ W_rows
R = comm.reduce(localMult_R, op=MPI.SUM, root=0)

# Print at the root process
if (rank == 0):
    wt = MPI.Wtime() - wt
    print("Q: \n", Q)
    print("R: \n", R)
    print("Time taken: ", wt)
    print(losses)