import copy


import gym
from gym import envs
from stable_baselines3.dqn import DQN
from torch import nn
import torch
from torch.optim import Adam
from torchvision import transforms
import numpy as np
import cv2 as cv
from stable_baselines3.common.atari_wrappers import AtariWrapper

# todo: maybe add a minimal version and a fully blown version with all of the nitty-gritty details
# todo: test the replay buffer, visualize images from the buffer
# todo: test Adam vs RMSProp
# todo: checkin trained DQN
# todo: try out gym's Monitor and env.ale.lives will that make sense for every env?
# todo: is gradient clipping in the param domain equivalent to clipping of the MSE loss?
# todo: log episode lengths, value function estimates, min/max/mean/std cumulative rewards, epsilon
# todo: I'm not sure how much training on Atari will take (wallclock time) for 200M frames, try a simpler env initially
# todo: reach OpenAI baseline performance

# todo: Add DQN
# todo: Add vanilla PG
# todo: Add PPO

# todo: make it work for discrete envs: CartPole-v1, Pong, Breakout
# todo: continuous envs: Acrobot, etc.


ATARI_INPUT = (84, 84)


class ReplayBuffer:
    EMPTY = -1

    def __init__(self):
        self.buffer = []

    def append(self, state, action, reward):
        self.buffer.append((state, action, reward))

    def fetch_random(self):
        random_id = np.random.randint(low=0, high=len(self.buffer)-1)
        old_state, action, reward = self.buffer[random_id]
        new_state, _, _ = self.buffer[random_id+1]
        return old_state, action, reward, new_state

    def fetch_last(self):
        state, _, _ = self.buffer[-1] if len(self.buffer) > 0 else (self.EMPTY, self.EMPTY, self.EMPTY)
        return state

    def update_last(self):
        state = 1  # dummy

    def __len__(self):
        return len(self.buffer)


class QNetwork(nn.Module):
    def __init__(self, number_of_actions=3):
        super().__init__()
        num_of_filters = [4, 32, 64, 64]
        kernel_sizes = [8, 4, 3]
        strides = [4, 2, 1]
        self.cnn = nn.Sequential(
            *[(nn.Conv2d(num_of_filters[i], num_of_filters[i+1], kernel_size=kernel_sizes[i], stride=strides[i]), nn.ReLU()) for i in range(len(strides))]
        )

        # Compute shape by doing one forward pass
        with torch.no_grad():
            n_flatten = self.cnn(torch.as_tensor(observation_space.sample()[None]).float()).shape[1]

        self.fc1 = nn.Linear(num_of_filters[3] * 7 * 7, 512)
        self.fc2 = nn.Linear(512, number_of_actions)

        self.relu = nn.ReLU()

    def forward(self, input):
        x = self.relu(self.conv1(input))
        x = self.relu(self.conv2(x))
        x = self.relu(self.conv3(x))
        x = torch.flatten(x, start_dim=1)  # flatten from (N,1,H,W) into (N, HxW)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


def atari_preprocess(img, current_state, tmp_input_buffer):
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    gray_resized = cv.resize(img, (ATARI_INPUT[0], ATARI_INPUT[1]), interpolation=cv.INTER_CUBIC)
    return gray_resized


def atari_fetch_input(input_buffer):
    imgs = input_buffer[-4:]
    return torch.from_numpy(imgs)


if __name__ == '__main__':
    # # # 1. It renders instance for 500 timesteps, perform random actions
    # # env = gym.make('Pong-v4')
    # # env.reset()
    # # for _ in range(500):
    # #     env.render()
    # #     observation, reward, done, info = env.step(env.action_space.sample())
    # #
    # # # 2. To check all env available, uninstalled ones are also shown
    # # for el in envs.registry.all():
    # #     print(el)
    #
    # env = AtariWrapper(gym.make("Pong-v4"))
    #
    # model = DQN("CnnPolicy", env, verbose=1)
    # model.learn(total_timesteps=10000)
    #
    # #
    # # obs = env.reset()
    # # for i in range(1000):
    # #     action, _states = model.predict(obs, deterministic=True)
    # #     obs, reward, done, info = env.step(action)
    # #     env.render()
    # #     if done:
    # #         obs = env.reset()
    # #
    # # env.close()
    #
    # env = gym.make("Pong-v4")
    # obs_space = env.observation_space.sample() # [None]
    # tmp = obs_space[None]
    #
    # number_of_actions = env.action_space.n
    # NUM_EPISODES = 1000
    # current_episode = 0
    # TARGET_DQN_UPDATE_FREQ = 10
    # discount_factor = 0.99
    #
    # dqn_current = DQN(number_of_actions=number_of_actions)
    # dqn_target = DQN(number_of_actions=number_of_actions)
    # optimizer = Adam(dqn_current.parameters())
    #
    # replay_buffer = ReplayBuffer()
    # num_sticky_actions = 4
    #
    # while current_episode < NUM_EPISODES:
    #     observation = env.reset()
    #
    #     end_of_episode = False
    #     while not end_of_episode:
    #         current_state = replay_buffer.fetch_last()
    #         action = dqn_current(current_state) if len(replay_buffer) > 0 else env.action_space.sample()
    #
    #         tmp_input_buffer = []
    #         state_reward = 0
    #         for _ in range(num_sticky_actions):  # sticky actions i.e. repeat the last action num_sticky_actions times
    #             observation, reward, done, info = env.step(action)
    #             env.render()
    #
    #             tmp_input_buffer.append(atari_preprocess(observation, current_state, tmp_input_buffer))
    #             state_reward += reward
    #
    #             if done:
    #                 end_of_episode = True
    #                 current_episode += 1
    #
    #         replay_buffer.update_last((action, state_reward))
    #         replay_buffer.append(tmp_input_buffer)
    #
    #         state, action, reward, next_state = replay_buffer.pop()
    #         q_target = reward + discount_factor * max(dqn_target(next_state))
    #         loss = nn.MSELoss()(dqn_current(state)[action], q_target)
    #
    #         optimizer.zero_grad()
    #         loss.backward()
    #         optimizer.step()
    #
    #     if current_episode % TARGET_DQN_UPDATE_FREQ:
    #         dqn_target = copy.deepcopy(dqn_current)
    #
    # env.close()

    tmp = torch.rand((3, 3))
    print(tmp)
    t = 0.001
    tmp.clamp_(-t, t)
    print(tmp)
