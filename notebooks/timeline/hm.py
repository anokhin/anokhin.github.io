import numpy as np
from sklearn.base import BaseEstimator, ClusterMixin, TransformerMixin
from sklearn.metrics.pairwise import pairwise_distances
from sklearn.utils import check_array, check_random_state
from sklearn.utils.validation import check_is_fitted


class HMedoids(BaseEstimator, ClusterMixin, TransformerMixin):
    """
    k-medoids class.

    Parameters
    ----------
    n_clusters : int, optional, default: 8
        How many medoids. Must be positive.

    max_iter : int, optional, default : 300
        Specify the maximum number of iterations when fitting.

    random_state : int, optional, default: None
        Specify random state for the random number generator.
    """

    def __init__(self, n_clusters=8, max_iter=300, random_state=None, threshold=0.5, verbose=0):

        self.n_clusters = n_clusters

        self.distance_func = lambda X, Y: pairwise_distances(X, Y, metric='hamming', n_jobs=-3)

        self.random_state = random_state

        self.max_iter = max_iter

        self.n_iter_ = 0

        self.medoids_ = None

        self.labels_ = None
        
        self.threshold_ = threshold

        self.verbose_ = verbose

    def _check_init_args(self):

        # Check n_clusters
        if self.n_clusters is None or self.n_clusters <= 0 or \
                not isinstance(self.n_clusters, int):
            raise ValueError("n_clusters has to be nonnegative integer")

        # Check random state
        self.random_state_ = check_random_state(self.random_state)

    def fit(self, X, y=None):
        """Fit K-Medoids to the provided data.

        Parameters
        ----------
        X : array-like or sparse matrix, shape=(n_samples, n_features)

        Returns
        -------
        self
        """

        self._check_init_args()
        X = self._check_array(X)

        self.medoids_ = self._get_initial_medoids(X)
        old_medoids = np.zeros((self.n_clusters, X.shape[1]))

        self.n_iter_ = 0
        while not np.all(old_medoids == self.medoids_) and self.n_iter_ < self.max_iter:
            self.n_iter_ += 1
            if self.verbose_:
                print "Iter %d" % self.n_iter_

            old_medoids = np.copy(self.medoids_)
            cluster_ind = self._get_cluster_ind(X)
            self._update_medoids(X, cluster_ind)

            if self.verbose_:
                print "Old medoids:\n%s" % old_medoids
                print "New medoids:\n%s" % self.medoids_

            self.labels_ = cluster_ind

        return self

    def _check_array(self, X):
        X = check_array(X)
        # Check that the number of clusters is less than or equal to
        # the number of samples
        if self.n_clusters > X.shape[0]:
            raise ValueError("The number of medoids ({}) ".format(self.n_clusters) + "must be larger than the number of samples ({})".format(X.shape[0]))
        return X

    def _get_initial_medoids(self, X, p=0.25):
        return np.random.binomial(1, p, size=(self.n_clusters, X.shape[1]))

    def _get_cluster_ind(self, X):
        D = self.distance_func(X, self.medoids_)
        assert D.shape == (X.shape[0], self.medoids_.shape[0])
        ind = np.argmin(D, axis=1)        
        assert ind.shape == (X.shape[0],)
        return ind

    def _update_medoids(self, X, cluster_ind):
        for k in xrange(self.n_clusters):
            X_k = X[cluster_ind == k]
            self.medoids_[k] = (X_k.sum(axis=0) > X_k.shape[0] * self.threshold_).astype(int)

    def transform(self, X):
        """Transforms X to cluster-distance space.

        Parameters
        ----------
        X : array-like or sparse matrix, shape=(n_samples, n_features)
            Data to transform.

        Returns
        -------
        X_new : array, shape=(n_samples, n_clusters)
            X transformed in the new space.
        """

        check_is_fitted(self, "medoids_")

        # Apply distance metric wrt. cluster centers (medoids),
        # and return these distances
        return self.distance_func(X, self.medoids_)

    def predict(self, X):
        check_is_fitted(self, "medoids_")
        X = check_array(X)
        return self._get_cluster_ind(X)

    def inertia(self, X):

        # Map the original X to the distance-space
        Xt = self.transform(X)

        # Define inertia as the sum of the sample-distances
        # to closest cluster centers
        inertia = np.sum(np.min(Xt, axis=1))

        return inertia
