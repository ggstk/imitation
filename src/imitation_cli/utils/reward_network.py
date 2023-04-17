import dataclasses
from typing import Optional

import numpy as np
from hydra.core.config_store import ConfigStore
from hydra.utils import call
from omegaconf import MISSING

import imitation_cli.utils.environment as gym_env
from imitation.rewards import reward_nets
from imitation.util import networks


@dataclasses.dataclass
class Config:
    _target_: str = MISSING
    environment: gym_env.Config = "${environment}"


@dataclasses.dataclass
class BasicRewardNet(Config):
    _target_: str = "imitation_cli.utils.reward_network.BasicRewardNet.make"
    use_state: bool = True
    use_action: bool = True
    use_next_state: bool = False
    use_done: bool = False
    normalize_input_layer: bool = True

    @staticmethod
    def make(environment: gym_env.Config, normalize_input_layer: bool, **kwargs):
        env = gym_env.make_venv(environment, rnd=np.random.default_rng())
        reward_net = reward_nets.BasicRewardNet(
            env.observation_space,
            env.action_space,
            **kwargs,
        )
        if normalize_input_layer:
            reward_net = reward_nets.NormalizedRewardNet(
                reward_net,
                networks.RunningNorm,
            )
        return reward_net


@dataclasses.dataclass
class BasicShapedRewardNet(BasicRewardNet):
    _target_: str = "imitation_cli.utils.reward_network.BasicShapedRewardNet.make"
    discount_factor: float = 0.99

    @staticmethod
    def make(environment: gym_env.Config, normalize_input_layer: bool, **kwargs):
        env = gym_env.make_venv(environment, rnd=np.random.default_rng())
        reward_net = reward_nets.BasicShapedRewardNet(
            env.observation_space,
            env.action_space,
            **kwargs,
        )
        if normalize_input_layer:
            reward_net = reward_nets.NormalizedRewardNet(
                reward_net,
                networks.RunningNorm,
            )
        return reward_net


@dataclasses.dataclass
class RewardEnsemble(Config):
    _target_: str = "imitation_cli.utils.reward_network.RewardEnsemble.make"
    ensemble_size: int = MISSING
    ensemble_member_config: BasicRewardNet = MISSING
    add_std_alpha: Optional[float] = None

    @staticmethod
    def make(
        environment: gym_env.Config,
        ensemble_member_config: BasicRewardNet,
        add_std_alpha: Optional[float],
    ):
        env = gym_env.make_venv(environment, rnd=np.random.default_rng())
        members = [call(ensemble_member_config)]
        reward_net = reward_nets.RewardEnsemble(
            env.observation_space, env.action_space, members
        )
        if add_std_alpha is not None:
            reward_net = reward_nets.AddSTDRewardWrapper(
                reward_net,
                default_alpha=add_std_alpha,
            )
        return reward_net


def make_reward_net(config: Config):
    return call(config)


def register_configs(group: str):
    cs = ConfigStore.instance()
    cs.store(group=group, name="basic", node=BasicRewardNet)
    cs.store(group=group, name="shaped", node=BasicShapedRewardNet)
    cs.store(group=group, name="ensemble", node=RewardEnsemble)
