import numpy as np
from resample.utils import eqf


def jackknife(a, f=None):
    """
    Calcualte jackknife estimates for a given sample
    and estimator

    Parameters
    ----------
    a : array-like
        Sample
    f : callable
        Estimator

    Returns
    -------
    y | X : np.array
        Jackknife estimates
    """
    n = len(a)
    X = np.reshape(np.delete(np.tile(a, n),
                             [i * n + i for i in range(n)]),
                   newshape=(n, n - 1))

    if f is None:
        return X
    else:
        return np.apply_along_axis(func1d=f,
                                   arr=X,
                                   axis=1)


def jackknife_bias(a, f):
    """
    Calculate jackknife estimate of bias

    Parameters
    ----------
    a : array-like
        Sample
    f : callable
        Estimator

    Returns
    -------
    y : float
        Jackknife estimate of bias
    """
    return (len(a) - 1) * np.mean(jackknife(a, f) - f(a))


def jackknife_variance(a, f):
    """
    Calculate jackknife estimate of variance

    Parameters
    ----------
    a : array-like
        Sample
    f : callable
        Estimator

    Returns
    -------
    y : float
        Jackknife estimate of variance
    """
    x = jackknife(a, f)

    return (len(a) - 1) * np.mean((x - np.mean(x))**2)


def empirical_influence(a, f):
    """
    Calculate the empirical influence function for a given
    sample and estimator using the jackknife method

    Parameters
    ----------
    a : array-like
        Sample
    f : callable
        Estimator

    Returns
    -------
    y : np.array
        Empirical influence values
    """
    return (len(a) - 1) * (f(a) - jackknife(a, f))


def bootstrap(a, f=None, b=100, method="balanced"):
    """
    Calculate function values from bootstrap samples or
    optionally return bootstrap samples themselves

    Parameters
    ----------
    a : array-like
        Original sample
    f : callable or None
        Function to be bootstrapped
    b : int
        Number of bootstrap samples
    method : string
        * 'ordinary'
        * 'balanced'

    Returns
    -------
    y | X : np.array
        Function applied to each bootstrap sample
        or bootstrap samples if f is None
    """
    a = np.asarray(a)

    if method == "ordinary":
        X = np.reshape(a[np.random.choice(range(a.shape[0]),
                                          a.shape[0] * b)],
                       newshape=(b,) + a.shape)
    elif method == "balanced":
        r = np.reshape([a] * b,
                       newshape=(b * a.shape[0],) + a.shape[1:])
        X = np.reshape(r[np.random.permutation(range(r.shape[0]))],
                       newshape=(b,) + a.shape)
    else:
        raise ValueError("method must be either 'ordinary'"
                         " , or 'balanced', '{method}' was"
                         " supplied".format(method=method))

    if f is None:
        return X
    else:
        return np.asarray([f(x) for x in X])


def bootstrap_ci(a, f=None, p=0.95, b=100, ci_method="percentile", 
                 boot_method="balanced", boot=True):
    """
    Calculate bootstrap confidence intervals

    Parameters
    ----------
    a : array-like
        Original sample
    f : callable
        Function to be bootstrapped
    p : float
        Confidence level
    b : int
        Number of bootstrap samples
    ci_method : string
        * 'percentile'
        * 'bca'
        * 't'
        * 'abc'
    boot_method : string
        * 'ordinary'
        * 'balanced'
    boot : boolean
        Whether or not to perform bootstrapping
        or use a as the bootstrap replicates

    Returns
    -------
    """
    if not (0 < p < 1):
        raise ValueError("p must be between zero and one")

    if boot_method not in ["ordinary", "balanced"]:
        raise ValueError(("boot_method must be 'ordinary'"
                          " or 'balanced', {method} was"
                          " supplied".
                         format(method=boot_method)))

    if (f is None) and boot:
        # f is needed to compute bootstrap replicates
        raise ValueError("f is required when boot is True")

    if boot:
        boot_est = bootstrap(a=a, f=f, b=b, method=boot_method)
    else:
        boot_est = a

    q = eqf(boot_est)
    alpha = 1 - p

    if ci_method == "percentile":
        return (q(alpha/2), q(1 - alpha/2))
    elif ci_method == "bca":
        if boot is False:
            # boot must be True since we need original sample
            raise ValueError("boot must be True when"
                             " ci_method is 'bca'")

        theta = f(a)
        # bias correction
        z_naught = norm.ppf(np.mean(boot_est <= theta))
        z_low = norm.ppf(alpha)
        z_high = norm.ppf(1 - alpha)
        # acceleration
        jack_est = jackknife(a, f)
        jack_mean = np.mean(jack_est)
        acc = (np.sum((jack_mean - jack_est)**3) /
               (6 * np.sum((jack_mean - jack_est)**2)**(3/2)))
        p1 = (norm.cdf(z_naught + (z_naught + z_low) /
                       (1 - acc * (z_naught + z_low))))
        p2 = (norm.cdf(z_naught + (z_naught + z_high) /
                       (1 - acc * (z_naught + z_high))))

        return (q(p1), q(p2))
    elif ci_method == "t":
        if boot is False:
            # boot must be True since we need original sample
            raise ValueError("boot must be True when"
                             " ci_method is 't'")

        theta = f(a)
        theta_std = np.mean(boot_est)

        # quantile function of studentized bootstrap estimates
        tq = eqf((boot_est - theta) / theta_std)
        t1 = tq(1 - alpha)
        t2 = tq(alpha)

        return (theta - theta_std * t1, theta + theta_std * t2)
    elif ci_method == "abc":
        return None
    else:
        raise ValueError(("ci_method must be 'percentile'"
                          " 'bca', 't', or 'abc', {method}"
                          " was supplied".
                          format(method=ci_method)))
