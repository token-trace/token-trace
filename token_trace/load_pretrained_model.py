import functools
import pickle
from types import SimpleNamespace

import torch
from huggingface_hub import hf_hub_download
from sae_lens import SparseAutoencoder
from sae_lens.training.utils import BackwardsCompatibleUnpickler
from transformer_lens import HookedTransformer

from token_trace.types import (
    ModuleName,
)

DEFAULT_MODEL_NAME = "gpt2-small"
DEFAULT_REPO_ID = "jbloom/GPT2-Small-SAEs"
DEFAULT_PROMPT = "When John and Mary went to the shops, John gave the bag to"
DEFAULT_ANSWER = " Mary"
DEFAULT_TEXT = DEFAULT_PROMPT + DEFAULT_ANSWER
DEVICE = "cpu"
# if torch.cuda.is_available():
#     DEVICE = "cuda"


@functools.lru_cache(maxsize=1)
def load_model(model_name: str) -> HookedTransformer:
    if model_name != DEFAULT_MODEL_NAME:
        raise ValueError(f"Unknown model: {model_name}")
    return HookedTransformer.from_pretrained(model_name, device=DEVICE)


def load_sae(layer: int) -> SparseAutoencoder:
    filename = (
        f"final_sparse_autoencoder_gpt2-small_blocks.{layer}.hook_resid_pre_24576.pt"
    )
    path = hf_hub_download(repo_id=DEFAULT_REPO_ID, filename=filename)
    # Hacky way to get torch to unpickle an old version of SAELens model
    fake_pickle = SimpleNamespace()
    fake_pickle.Unpickler = BackwardsCompatibleUnpickler
    fake_pickle.__name__ = pickle.__name__
    data = torch.load(path, map_location=DEVICE, pickle_module=fake_pickle)
    cfg = data["cfg"]
    cfg.device = DEVICE
    sparse_autoencoder = SparseAutoencoder(cfg=cfg)
    sparse_autoencoder.load_state_dict(data["state_dict"])
    sparse_autoencoder.train()
    return sparse_autoencoder.to(DEVICE)


@functools.lru_cache(maxsize=1)
def load_sae_dict(model_name: str) -> dict[ModuleName, SparseAutoencoder]:
    if model_name != DEFAULT_MODEL_NAME:
        raise ValueError(f"Unknown model: {model_name}")
    # TODO: un-hardcode n_layers
    n_layers = 12
    return {ModuleName(str(layer)): load_sae(layer) for layer in range(n_layers)}