import dataclasses
import logging
from typing import Optional

import hydra
from hydra.core.config_store import ConfigStore
from hydra.utils import call
from omegaconf import MISSING

from imitation.data import rollout
from imitation_cli.utils import environment as gym_env, optimizer_class, policy, reward_network, rl_algorithm, trajectories
from imitation_cli.utils import policy as policy_conf


@dataclasses.dataclass
class AIRLConfig:
    _target_: str = "imitation.algorithms.adversarial.airl.AIRL"
    venv: gym_env.Config = "${venv}"
    demonstrations: trajectories.Config = "${demonstrations}"
    gen_algo: rl_algorithm.Config = MISSING
    reward_net: reward_network.Config = MISSING
    demo_batch_size: int = 64
    n_disc_updates_per_round: int = 2
    disc_opt_cls: optimizer_class.Config = optimizer_class.Adam
    gen_train_timesteps: Optional[int] = None
    gen_replay_buffer_capacity: Optional[int] = None
    init_tensorboard: bool = False
    init_tensorboard_graph: bool = False
    debug_use_ground_truth: bool = False
    allow_variable_horizon: bool = True  # TODO: true just for debugging


@dataclasses.dataclass
class AIRLRunConfig:
    defaults: list = dataclasses.field(
        default_factory=lambda: [
            {"venv": "gym_env"},
            {"airl/reward_net": "shaped"},
            {"airl/gen_algo": "ppo"},
            "_self_",
        ]
    )
    seed: int = 0
    venv: gym_env.Config = MISSING
    demonstrations: trajectories.Config = MISSING
    airl: AIRLConfig = AIRLConfig()
    total_timesteps: int = int(1e6)
    checkpoint_interval: int = 0


cs = ConfigStore.instance()
cs.store(name="airl", node=AIRLConfig)
cs.store(name="airl_run", node=AIRLRunConfig)
trajectories.register_configs("demonstrations")
gym_env.register_configs("venv")
policy.register_configs("demonstrations/expert_policy", dict(environment="${venv}"))  # Make sure the expert generating the demonstrations uses the same env as the main env
rl_algorithm.register_configs("airl/gen_algo", dict(environment="${venv}", policy=policy_conf.ActorCriticPolicy(environment="${venv}")))  # The generation algo and its policy should use the main env by default
reward_network.register_configs("airl/reward_net", dict(environment="${venv}"))  # The reward network should be tailored to the default environment by default


@hydra.main(
    version_base=None,
    config_path="config",
    config_name="airl_run",
)
def run_airl(cfg: AIRLRunConfig) -> None:

    trainer = call(cfg.airl)

    def callback(round_num: int, /) -> None:
        if cfg.checkpoint_interval > 0 and round_num % cfg.checkpoint_interval == 0:
            logging.log(
                logging.INFO,
                f"Saving checkpoint at round {round_num}. TODO implement this",
            )

    trainer.train(cfg.total_timesteps, callback)
    # TODO: implement evaluation
    # imit_stats = policy_evaluation.eval_policy(trainer.policy, trainer.venv_train)

    # Save final artifacts.
    if cfg.checkpoint_interval >= 0:
        logging.log(logging.INFO, f"Saving final checkpoint. TODO implement this")

    return {
        # "imit_stats": imit_stats,
        "expert_stats": rollout.rollout_stats(cfg.airl.demonstrations),
    }


if __name__ == "__main__":
    run_airl()
