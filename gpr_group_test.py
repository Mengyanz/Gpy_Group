import GPy
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
from gpr_group_model import GPRegression_Group
from generate_data import generate_data_func
from plot import plot_1d, plot_2d
from sklearn.cluster import KMeans

import scipy.spatial as sp
import tensorflow as tf
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import gp_ent_cluster
import networks
import utils

# np.random.seed(1996)

x_shift = 0

# X_train_range_low = -3. + x_shift
# X_train_range_high = 3. + x_shift
# X_test_range_low = -3.5 + x_shift
# X_test_range_high = 3.5 + x_shift

X_train_range_low = -5. 
X_train_range_high = 5. 
# X_test_range_low = -10.5 
# X_test_range_high = 10.5 

# GPy.plotting.change_plotting_library('plotly')

# 1d model

# np.random.seed(1996)
# X = np.random.uniform(-3.,3.,(50,1))
# Y = np.sin(X) + np.random.randn(50,1)*0.05
# X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size = 0.2, random_state = 4)

num_train = 500
num_test = 500
# num_train = X_train.shape[0]
# TODO: for now, assume num_train/num_group is integer
num_group = 25
noise = 0.1
num_element_in_group = int(num_train/num_group)
dim = 2

# np.random.seed(1996)
# X_train = np.random.uniform(-3.,3.,(num_train,1))
# f_train = np.sin(X_train)
# Y_train = f_train + np.random.randn(num_train,1)*0.05
# X_test = np.random.uniform(-3.5,3.5,(num_test,1))
# f_test = np.sin(X_test)
# Y_test = f_test + np.random.randn(num_test,1)*0.05
if num_test != num_train:
    X_train, f_train, Y_train, X_test, f_test, Y_test = generate_data_func(num_train,num_test,dim=dim, func_type='sin', X_train_range_low= X_train_range_low, X_train_range_high=X_train_range_high, x_shift=x_shift)
else:
    X_train, f_train, Y_train = generate_data_func(num_train,num_test,dim=dim, func_type='sin', X_train_range_low= X_train_range_low, X_train_range_high=X_train_range_high, x_shift=x_shift)
    X_test, f_test, Y_test = X_train, f_train, Y_train
# Generate group matrix A (10 * n_train) and group label Y_group (10 * 1)

def generate_A(grouping_method, num_group = 30):

    # grouping choices: random, bins, evenly, ortho, tridiagonal, spd
    if grouping_method in {'ortho', 'tridiagonal', 'spd', 'diagonal'}:
        num_group = num_train
        print('Set the number of group as the same size of training samples.')

    idx_set = set(range(num_train))
    A = np.zeros((num_group, num_train))
    group_centers = None

    if grouping_method == 'random':
        # Method 1 -> form group: uniformly random 
        for i in range(num_group):
            select_ele = np.random.choice(list(idx_set), size = num_element_in_group, replace=False)
            A[i, np.asarray(select_ele)] = 1
            idx_set -=set(select_ele)
    elif grouping_method == 'cluster':
        # Method 2 -> form group: bins
        # if dim == 1:
        #     bins = np.linspace(X_train_range_low, X_train_range_high, num_group+1)
        #     print(bins)
        #     digitized = np.digitize(X_train, bins)
        #     # print(digitized)
        #     for i in range(num_group):
        #         # print(i)
        #         # print(X_train[digitized == i])
        #         # print('size: ', len(X_train[digitized == i]))
        #         idx = np.asarray(digitized == i+1).reshape(X_train.shape[0],)
        #         A[i, idx] = 1
        # elif dim == 2:
        kmeans = KMeans(n_clusters=num_group, init = 'k-means++', random_state= 0).fit(X_train)
        group_idx = kmeans.labels_
        for idx,i in enumerate(group_idx):
            A[i, idx] = 1
        group_centers = kmeans.cluster_centers_
    elif grouping_method == 'ent':
        # TODO: does not work for now
        # Initialise the GP clusterer
        A = networks.MlpA(X_train.shape[1], num_group)
        cluster = gp_ent_cluster.GPEntCluster(noise, num_group, X_train, X_test, A=A)

        # Minimise the entropy using gradient tape
        c = 0
        while c<=500:
            _, entropy = cluster.train_step(X_train, True, True)
            A = cluster.A(X_train).numpy()
            c += 1
        plt.matshow(np_A.T @ np_A)
        plt.savefig('group_kernel.pdf')
        plt.close()
       
        plt.scatter(X[:, 0], X[:,1], c=utils.project_to_rgb(np_A.T))
        plt.savefig('plt.pdf')
        plt.close()

    elif grouping_method == 'similarY':
        kmeans = KMeans(n_clusters=num_group, init = 'k-means++', random_state= 0).fit(Y_train)
        group_idx = kmeans.labels_
        for idx,i in enumerate(group_idx):
            A[i, idx] = 1
        group_centers = kmeans.cluster_centers_
    elif grouping_method == 'evenly':
        group_idx = 0
        sorted_train_idx = np.argsort(X_train, axis = 0).reshape(X_train.shape[0],)
        for i in sorted_train_idx:
            A[group_idx, i] = 1
            if group_idx < num_group -1:
                group_idx +=1 
            else:
                group_idx = 0
    elif grouping_method == 'diagonal':
        A = np.eye(num_train)
    elif grouping_method == 'tridiagonal':
        from scipy.sparse import diags
        A = diags([1, 1], [-1, 1], shape=(num_group, num_train)).toarray()
        assert np.linalg.matrix_rank(A) == num_train
        assert np.linalg.matrix_rank(A) == num_train
        print(A)
    elif grouping_method == 'ortho':
        from scipy.stats import ortho_group
        A = ortho_group.rvs(num_train)
        assert np.linalg.matrix_rank(A) == num_train
        print(A)
    elif grouping_method == 'spd':
        from sklearn.datasets import make_spd_matrix
        A = make_spd_matrix(num_train)
        assert np.linalg.matrix_rank(A) == num_train
        print(A)
    else:
        print('invalid grouping method!')

    return A, group_centers

# for now, it is better to keep group aggregation over noiseless output and then add noise after group label is created. Since we do not want the noise level to be proportional to the group size, this introduce more things to deal with when we think of how to form a group.

def run_gprg(A, A_ast = None):
    # TODO: at some time, we want to introduce noise for individual level as well
    Y_group = A.dot(f_train) + np.random.randn(num_group,1) * noise
    # Y_group = A.dot(Y_train)

    kernel = GPy.kern.RBF(input_dim=dim, variance=1., lengthscale=1.)
    # kernel = GPy.kern.Poly(input_dim=dim, variance=1., scale=1., order = 1)

    m = GPRegression_Group(X_train,Y_group,kernel, noise_var=0.005, A = A)
    # m.optimize(messages=False,max_f_eval = 1000)
    # m.optimize_restarts(num_restarts = 10)

    Y_test_pred, Y_test_var = m.predict(X_test, A_ast=A_ast)

    return Y_test_pred, Y_test_var

def run_gprg_online(A, A_ast = None):
    # REVIEW: for now, test each row of A is a data point
    # the input X_train is the same for each round
    # only A and f_group is different 

    Y_group = A.dot(f_train) + np.random.randn(num_group,1)* noise
    # Y_group = A.dot(Y_train)

    kernel = GPy.kern.RBF(input_dim=dim, variance=1., lengthscale=1.)
    # kernel = GPy.kern.Poly(input_dim=dim, variance=1., scale=1., order = 1)
    m = GPRegression_Group(X_train,Y_group[0,:].reshape(1,1),kernel, noise_var=0.005, A = A[0,:].reshape(1, A.shape[1]))
    # m.optimize(messages=False,max_f_eval = 1000)
    # m.optimize_restarts(num_restarts = 10)

    for i in range(1, A.shape[0]):
        # REVIEW: gpy package only support reset XY, but not online update
        # could be computational expensive 
        m.set_XY_group(X=X_train, Y= Y_group[:i+1,:], A= A[:i+1,:].reshape(i+1, A.shape[1]))
        
    Y_test_pred, Y_test_var = m.predict(X_test,A_ast=A_ast)

    return Y_test_pred, Y_test_var
#------------------------------------------------------

# A_diagonal = generate_A('diagonal')
# A_ortho = generate_A('ortho')
# # print(A.sum(axis=0))
# # print(A.sum(axis=1))

# Y_test_pred_dia, Y_test_var_dia = run_gprg(A_diagonal)
# Y_test_pred_ortho, Y_test_var_ortho = run_gprg(A_ortho)

# fig,ax = plt.subplots(1, 2, figsize = (10,5))
# ax[0].hist(Y_test_pred_dia - Y_test_pred_ortho)
# ax[0].set_title('Y_test_pred_diagonal - Y_test_pred_ortho hist')
# ax[1].hist(Y_test_var_dia - Y_test_var_ortho)
# ax[1].set_title('Y_test_var_diagonal - Y_test_var_ortho hist')
# plt.show()

#-------------------------------------------------
grouping_method = 'cluster' # 'cluster' # 'similarY' # 
A, group_centers = generate_A(grouping_method, num_group)
print('group centers: ', group_centers)
# A_ast = np.identity(Y_test.shape[0])

# Y_test_pred, Y_test_var = run_gprg_online(A)

# print('test label: ', Y_test)
# print('test pred: ', Y_test_pred)
# print('test var: ', Y_test_var)

#---------------------------------------------------------
print('Prediction for individual:')
Y_test_pred, Y_test_var = run_gprg_online(A, np.identity(Y_test.shape[0]))
# print('Y test: ', Y_test)
# print('Y test pred: ', Y_test_pred)
mse_test = mean_squared_error(Y_test, Y_test_pred)
print('mean squared error: ', mse_test)
r2_score_test = r2_score(Y_test, Y_test_pred)
print('r2 score: ', r2_score_test)
#---------------------------------------------------------
# TODO: extend the evaluation into A_ast != A
print('Prediction for group (select A_ast = A):')
group_test = A.dot(Y_test)
print(group_test)
group_test_pred, group_test_var = run_gprg_online(A, A)
mse_test = mean_squared_error(group_test, group_test_pred)
print('mean squared error: ', mse_test)
r2_score_test = r2_score(group_test, group_test_pred)
print('r2 score: ', r2_score_test)

if dim == 1:
    plot_1d(X_train, X_test, f_train, Y_train, f_test, Y_test, Y_test_pred, Y_test_var, A, 
    group_centers, group_test, group_test_pred, group_test_var, 
    'gprg', num_group, grouping_method, X_train_range_low, X_train_range_high, x_shift)  
if dim == 2:
    plot_2d(X_train, X_test, f_train, Y_train, f_test, Y_test, Y_test_pred, Y_test_var, A, 
    group_centers, group_test, group_test_pred, group_test_var,  
    'gprg', num_group, grouping_method, X_train_range_low, X_train_range_high, x_shift)
