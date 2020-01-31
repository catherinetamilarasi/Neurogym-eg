#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 15:31:14 2019

@author: molano

Perceptual decision-making with postdecision wagering, based on

  Representation of confidence associated with a decision by
  neurons in the parietal cortex.
  R. Kiani & M. N. Shadlen, Science 2009.

  http://dx.doi.org/10.1126/science.1169405

"""
from __future__ import division

import numpy as np
from gym import spaces

import neurogym as ngym


class PDWager(ngym.EpochEnv):
    metadata = {
        'description': '''Agents do a discrimination task (see PerceptualDecisionMaking). On a
         random half of the trials, the agent is given the option to abort
         the direction discrimination and to choose instead a small but
         certain reward associated with a action.''',
        'paper_link': 'https://science.sciencemag.org/content/324/5928/' +
        '759.long',
        'paper_name': '''Representation of Confidence Associated with a
         Decision by Neurons in the Parietal Cortex''',
        'timing': {
            'fixation': ('constant', 100),  # XXX: not specified
            # 'target':  ('constant', 0), # XXX: not implemented, not specified
            'stimulus': ('truncated_exponential', [180, 100, 900]),
            'delay': ('truncated_exponential', [1350, 1200, 1800]),
            'pre_sure': ('uniform', [500, 750]),
            'decision': ('constant', 100)},  # XXX: not specified
        'tags': ['perceptual', 'delayed response', 'confidence',
                 'supervised setting']
    }

    def __init__(self, dt=100, timing=None):
        super().__init__(dt=dt, timing=timing)
#        # Actions
#        self.actions = tasktools.to_map('FIXATE', 'CHOOSE-LEFT',
#                                        'CHOOSE-RIGHT', 'CHOOSE-SURE')
        # Actions (fixate, left, right, sure)
        self.actions = [0, -1, 1, 2]
        # trial conditions
        self.wagers = [True, False]
        self.choices = [-1, 1]
        self.cohs = [0, 3.2, 6.4, 12.8, 25.6, 51.2]

        # Input noise
        self.sigma = np.sqrt(2*100*0.01)

        # Rewards
        self.R_ABORTED = -0.1
        self.R_CORRECT = +1.
        self.R_FAIL = 0.
        self.abort = False
        self.R_SURE = 0.7*self.R_CORRECT

        # set action and observation space
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(4, ),
                                            dtype=np.float32)

    # Input scaling
    def scale(self, coh):
        return (1 + coh/100)/2

    def new_trial(self, **kwargs):
        # ---------------------------------------------------------------------
        # Wager or no wager?
        # ---------------------------------------------------------------------
        self.trial = {
            'wager': self.rng.choice(self.wagers),
            'ground_truth': self.rng.choice(self.choices),
            'coh': self.rng.choice(self.cohs),
        }
        self.trial.update(kwargs)
        # ---------------------------------------------------------------------
        # Epochs
        # ---------------------------------------------------------------------
        self.add_epoch('fixation', after=0)
        self.add_epoch('stimulus', after='fixation')
        self.add_epoch('delay', after='stimulus')
        self.add_epoch('decision', after='delay', last_epoch=True)

        if self.trial['wager']:
            self.add_epoch('pre_sure', after='stimulus')
            self.add_epoch('sure', duration=10000, after='pre_sure')

    def _step(self, action):
        # ---------------------------------------------------------------------
        # Reward and inputs
        # ---------------------------------------------------------------------
        trial = self.trial
        info = {'new_trial': False}
        # ground truth signal is not well defined in this task
        info['gt'] = np.zeros((4,))
        # rewards
        reward = 0
        # observations
        obs = np.zeros((4,))
        if self.in_epoch('fixation'):
            obs[0] = 1
            if self.actions[action] != 0:
                info['new_trial'] = self.abort
                reward = self.R_ABORTED
        elif self.in_epoch('decision'):
            if self.actions[action] == 2:
                if trial['wager']:
                    reward = self.R_SURE
                else:
                    reward = self.R_ABORTED
            else:
                gt_sign = np.sign(trial['ground_truth'])
                action_sign = np.sign(self.actions[action])
                if gt_sign == action_sign:
                    reward = self.R_CORRECT
                elif gt_sign == -action_sign:
                    reward = self.R_FAIL
            info['new_trial'] = self.actions[action] != 0

        if self.in_epoch('delay'):
            obs[0] = 1
        elif self.in_epoch('stimulus'):
            high = (trial['ground_truth'] > 0) + 1
            low = (trial['ground_truth'] < 0) + 1
            obs[high] = self.scale(+trial['coh']) +\
                self.rng.gauss(mu=0, sigma=self.sigma)/np.sqrt(self.dt)
            obs[low] = self.scale(-trial['coh']) +\
                self.rng.gauss(mu=0, sigma=self.sigma)/np.sqrt(self.dt)
        if trial['wager'] and self.in_epoch('sure'):
            obs[3] = 1

        return obs, reward, False, info
