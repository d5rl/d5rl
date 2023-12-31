import collections
import copy
import glob
from typing import Optional

import gym
import numpy as np
from gym.utils import seeding


def KitchenDataGenerator(datasets_urls: list,
                                   env: gym.Env,
                                   discount=0.99,
                                   seed: Optional[int] = None):

    observation_space = copy.deepcopy(env.observation_space.spaces)
    pixel_observation_space = observation_space.pop('pixels')
    num_stack = pixel_observation_space.shape[-1]

    np_random, seed = seeding.np_random(seed)

    files = sum([glob.glob(url + '/**/*.pkl', recursive=True) for url in datasets_urls], [])
    print(f'There are {len(files)} total episodes in the offline datasets')
    # files = sum([glob.glob(url + '/**/*.pkl', recursive=True) for url in datasets_urls], [])

    while True:
        np_random.shuffle(files)

        for file in files:
            #print(file)
            episode = np.load(file, allow_pickle=True)
            episode['reward'] = np.sum([episode['reward_' + task] for
                                       task in env.TASK_ELEMENTS], axis = 0)

            reward_to_go = np.zeros_like(episode["reward"])
            prev_return = episode["reward"][-1]/(1- discount)
            # prev_return = 0
            for i in range(episode["reward"].shape[0]):
                reward_to_go[-i-1] = episode["reward"][-i-1] + discount * prev_return
                prev_return = reward_to_go[-i-1]

            episode["mc_returns"] = reward_to_go

            frames = collections.deque(maxlen=num_stack)
            for _ in range(num_stack):
                frames.append(
                    np.concatenate([episode[cam + '_rgb'][0] for cam in env.cameras],
                                   axis=-1))

            for t in range(episode['reward'].shape[0] - 1):
                transition = dict()
                transition['observations'] = dict()
                transition['observations']['pixels'] = np.stack(frames,
                                                                axis=-1)

                transition['observations']['states'] = episode['robot_qp'][t]
                #np.concatenate(
                #        [episode['robot_qp'][t],
                #         episode['ee_qp'][t],
                #         episode['ee_forces'][t]],
                #         axis=-1)

                if env.env.env.pretrained_encoder is not None:
                    # transition['observations']['pretrained_representations'] = env.env.env.pretrained_encoder(frames[0])
                    transition['observations']['pretrained_representations'] = episode["pretrained_representations"][t]
                # else:
                #     transition['observations']['pretrained_representations'] = np.zeros((2,))

                transition['actions'] = np.clip(episode['action'][t + 1], -0.99, 0.99)
                transition['rewards'] = episode['reward'][t + 1]
                transition["mc_returns"] = episode['mc_returns'][t + 1]

                frames.append(
                    np.concatenate([
                        episode[cam + '_rgb'][t + 1]  for cam in env.cameras],
                                   axis=-1))

                transition['next_observations'] = dict()
                transition['next_observations']['pixels'] = np.stack(frames,
                                                                     axis=-1)

                transition['next_observations']['states'] = episode['robot_qp'][t + 1]
                #np.concatenate(
                #       [episode['robot_qp'][t + 1],
                #         episode['ee_qp'][t + 1],
                #         episode['ee_forces'][t + 1]],
                #         axis=-1)
                if env.env.env.pretrained_encoder is not None:
                    # transition['next_observations']['pretrained_representations'] = env.env.env.pretrained_encoder(frames[0])
                    transition['next_observations']['pretrained_representations'] = episode["pretrained_representations"][t + 1]

                transition['masks'] = 0.0
                transition['dones'] = 0.0

                yield transition
