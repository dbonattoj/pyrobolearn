# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""Defines the metrics used in reinforcement learning (RL).
"""

import numpy as np
import matplotlib.pyplot as plt

from pyrobolearn.tasks import RLTask
from pyrobolearn.metrics import Metric
from pyrobolearn.losses import BatchLoss


__author__ = "Brian Delhaisse"
__copyright__ = "Copyright 2019, PyRoboLearn"
__credits__ = ["Brian Delhaisse"]
__license__ = "GNU GPLv3"
__version__ = "1.0.0"
__maintainer__ = "Brian Delhaisse"
__email__ = "briandelhaisse@gmail.com"
__status__ = "Development"


class RLMetric(Metric):
    r"""Reinforcement Learning (abstract) Metric

    Metrics used in reinforcement learning.

    References:
        - [1] "Deep Reinforcement Learning that Matters", Henderson et al., 2018
    """

    def __init__(self):
        """
        Initialize the RL metric.
        """
        super(RLMetric, self).__init__()


class AverageReturnMetric(RLMetric):
    r"""Average / Expected return metric.

    This computes the average / expected RL return given by:

    .. math:: J(\pi_{\theta}) = \mathcal{E}_{\tau \sim \pi_{\theta}}[ R(\tau) ]

    where :math:`R(\tau) = \sum_{t=0}^T \gamma^t r_t` is the discounted return.

    References:
        - [1] "Deep Reinforcement Learning that Matters", Henderson et al., 2018
    """

    def __init__(self, task, gamma=1., num_rollouts=10, num_steps=100):
        """
        Initialize the average return metric.

        Args:
            gamma (float): discount factor
        """
        super(AverageReturnMetric, self).__init__()
        self.gamma = gamma
        self.task = task
        self.returns = []
        self._num_steps = num_steps
        self._num_rollouts = num_rollouts

    ##############
    # Properties #
    ##############

    @property
    def gamma(self):
        """Return the discount factor"""
        return self._gamma

    @gamma.setter
    def gamma(self, gamma):
        """Set the discount factor"""
        if gamma > 1.:
            gamma = 1.
        elif gamma < 0.:
            gamma = 0.

        self._gamma = gamma

    @property
    def task(self):
        """Return the RL task."""
        return self._task

    @task.setter
    def task(self, task):
        """Set the RL task."""
        if not isinstance(task, RLTask):
            raise TypeError("Expecting the given 'task' to be an instance of `RLTask`, instead got: "
                            "{}".format(type(task)))
        self._task = task

    ###########
    # Methods #
    ###########

    def _get_data(self):
        """Return the average rewards."""
        return self.returns

    def _end_episode_update(self, episode_idx=None, num_episodes=None):
        """Update the metric at the end of an episode."""
        rewards = []
        for _ in range(self._num_rollouts):
            reward = self.task.run(num_steps=self._num_steps)
            rewards.append(reward)

        rewards = np.asarray(rewards).mean()

        print("\nAverage return metric: {}".format(rewards))

        self.returns.append(rewards)

    def _plot(self, ax):
        """
        Plot the average return metric in the given axis.
        """
        ax.set_title('Average Return per episode')  # per epoch, per iteration=epoch*batch
        ax.set_xlabel('episodes')
        ax.set_ylabel('Average return')
        ax.plot(self.returns)
        ax.set_ylim(bottom=0)


class LossMetric(RLMetric):
    r"""Loss Metric

    This provides the loss value with respect to the number of episodes/iterations.

    Warnings: As described in [1] and copied-pasted here for completeness:

    This loss metric should not be confused with "a loss function in the typical sense from supervised learning. There
    are two main differences from standard loss functions.

    1. The data distribution depends on the parameters. A loss function is usually defined on a fixed data distribution
      which is independent of the parameters we aim to optimize. Not so here, where the data must be sampled on the
      most recent policy.

    2. It doesn't measure performance. A loss function usually evaluates the performance metric that we care about.
      Here, we care about expected return, :math:`J(\pi_{\theta})`, but our 'loss' function does not approximate this
      at all, even in expectation. This 'loss' function is only useful to us because, when evaluated at the current
      parameters, with data generated by the current parameters, it has the negative gradient of performance.

    But after that first step of gradient descent, there is no more connection to performance. This means that
    minimizing this 'loss' function, for a given batch of data, has no guarantee whatsoever of improving expected
    return. You can send this loss to :math:`-\infty` and policy performance could crater; in fact, it usually will.
    Sometimes a deep RL researcher might describe this outcome as the policy 'overfitting' to a batch of data.
    This is descriptive, but should not be taken literally because it does not refer to generalization error.

    We raise this point because it is common for ML practitioners to interpret a loss function as a useful signal
    during training - 'if the loss goes down, all is well.' In policy gradients, this intuition is wrong, and you
    should only care about average return. The loss function means nothing." [1]

    References:
        - [1] https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html
    """

    def __init__(self, loss, wrt='iteration'):
        """
        Initialize the loss metric.

        Args:
            loss (BatchLoss): batch loss.
            wrt (str): string that specify with respect to what we want to plot; the number of episodes, the number of
                epochs (episodes * epochs), or the total number of iterations (episodes * epochs * batches). Select
                between {'episode', 'epoch', 'batch'/'iteration'}. If set to something else, it will be set to
                'iteration' by default.
        """
        super(LossMetric, self).__init__()
        self.loss = loss
        self.batch_losses = []
        self.epoch_losses = []
        self.losses = []
        self.wrt = wrt

    ##############
    # Properties #
    ##############

    @property
    def loss(self):
        """Return the loss instance."""
        return self._loss

    @loss.setter
    def loss(self, loss):
        """Set the loss instance."""
        if not isinstance(loss, BatchLoss):
            raise TypeError("Expecting the given 'loss' to be an instance of `BatchLoss`, but got instead: "
                            "{}".format(type(loss)))
        self._loss = loss

    @property
    def wrt(self):
        """Return with respect to what we plot the loss."""
        return self._wrt

    @wrt.setter
    def wrt(self, wrt):
        """Set with respect to what we plot the loss."""
        if wrt is None:
            wrt = 'iteration'
        else:
            wrt = wrt.lower()
            if wrt[:7] == 'episode':
                wrt = 'episode'
            elif wrt[:5] == 'epoch':
                wrt = 'epoch'
            else:
                wrt = 'iteration'
        self._wrt = wrt

    ###########
    # Methods #
    ###########

    def _get_data(self):
        """Return the losses."""
        return self.losses

    def _end_batch_update(self, batch_idx=None, num_batches=None):
        """Update the metric at the end of a batch."""
        # print("Adding loss value: {}, {}, {}".format(self.loss.value, self.loss.value.detach(),
        #                                              self.loss.value.item()))
        self.batch_losses.append(self.loss.value.item())

    def _end_epoch_update(self, epoch_idx=None, num_epochs=None):
        """Update the metric at the end of an epoch."""
        self.epoch_losses.append(self.batch_losses)
        self.batch_losses = []

    def _end_episode_update(self, episode_idx=None, num_episodes=None):
        """Update the metric at the end of an episode."""
        self.losses.append(self.epoch_losses)
        self.epoch_losses = []

    def _plot(self, ax):
        """
        Plot the loss in the given axis.
        """
        ax.set_title(self.loss.__class__.__name__ + ' per ' + self.wrt)
        ax.set_xlabel(self.wrt + 's')
        ax.set_ylabel('Loss')

        losses = np.asarray(self.losses)  # (num_episode, num_epoch, num_batch)

        if self.wrt == 'iteration':  # iteration / batch
            losses = losses.reshape(-1)
        elif self.wrt == 'epoch':  # epoch
            losses = losses.mean(axis=2).reshape(-1)
        elif self.wrt == 'episode':  # episode
            losses = losses.mean(axis=2).mean(axis=1)

        ax.plot(losses)


class NumberOfIterationsMetric(RLMetric):
    r"""Number of iterations metric.

    This metric checked the number of iterations it took to solve the RL task, or achieved a certain performance
    threshold level.

    References:
        - [1] "Deep Reinforcement Learning that Matters", Henderson et al., 2018
    """

    def __init__(self, threshold=None):
        """
        Initialize the number of iterations metric.

        Args:
            (float, None): desired performance threshold level.
        """
        super(NumberOfIterationsMetric, self).__init__()


class MaxAverageReturnMetric(RLMetric):
    r"""Max average return metric.

    This metric checked the max average return per episode / iteration.

    References:
        - [1] "Deep Reinforcement Learning that Matters", Henderson et al., 2018
    """

    def __init__(self):
        """
        Initialize the max average return metric.
        """
        super(MaxAverageReturnMetric, self).__init__()


class ExplorationMetric(RLMetric):
    r"""Exploration metric.

    This measures how much an agent explores in an environment as the number of episodes / iterations increases. This
    is useful for instance if the policy (given the state) predicts as well the variance / covariance of its actions.
    We can use the entropy to measure the uncertainty on each action.
    """

    def __init__(self):
        """
        Initialize the exploration metric.
        """
        super(ExplorationMetric, self).__init__()


class KLMetric(RLMetric):
    r"""KL divergence metric.

    This measures how much the distance between two distributions decreases as the number of episodes / iterations
    increases. For instance, it can be used to check how distant is the learned policy :math:`\pi_\theta(\cdot | s)`
    from the optimal one :math:`\pi^*(\cdot | s)`, or how distant is the learned dynamic transition probability
    function :math:`p(\cdot | s, a)` from the true one (or an approximation of it) :math:`p^*(\cdot | s, a)`.
    """

    def __init__(self):
        """
        Initialize the uncertainty metric.
        """
        super(KLMetric, self).__init__()
