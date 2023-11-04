from torch.utils.data import DataLoader
import numpy as np
import argparse
import torch
import yaml
import re
import shutil

from utils.model import get_model, get_vocoder
from utils.tools import to_device, synth_samples
from text import phoneme_to_ids

def read_lexicon(lex_path):
    lexicon = {}
    with open(lex_path) as f:
        for line in f:
            temp = re.split(r"\s+", line.strip("\n"))
            word = temp[0]
            phones = temp[1:]
            if word.lower() not in lexicon:
                lexicon[word.lower()] = phones
    return lexicon

def text_to_phonemes(text, lexicon):
    text = text.lower()
    words = re.split(r"([,;.\-\?\!\s+])", text)
    
    phonemes = []
    for word in words:
        if word in lexicon:
            phoneme = lexicon[word]
            phonemes += phoneme
        elif len(word.strip()) == 0:
            continue
        elif word in ",.?!":
            phonemes.append(word)
    
    phoneme_ids = phoneme_to_ids(" ".join(phonemes))
    phoneme_ids = torch.tensor(phoneme_ids).reshape(1, len(phoneme_ids))
    
    src_lens = torch.tensor([len(phoneme_ids[0])])

    speakers = None
    texts = phoneme_ids.cuda()
    src_lens = src_lens.cuda()
    max_src_len = src_lens.max()
    mels=None
    mel_lens=None
    max_mel_len=None
    p_targets=None
    e_targets=None
    d_targets=None
    p_control=1.0
    e_control=1.0
    d_control=1.0


    batch = [
        speakers, texts, src_lens, \
        max_src_len, mels, mel_lens, max_mel_len, \
        p_targets, e_targets, d_targets, \
        p_control, e_control, d_control]
    
    return batch

preprocess_config = "configs/preprocess.yaml"
model_config = "configs/model.yaml"
train_config = "configs/train.yaml"

preprocess_config = yaml.load(open(preprocess_config, "r"), Loader=yaml.FullLoader)
model_config = yaml.load(open(model_config, "r"), Loader=yaml.FullLoader)
train_config = yaml.load(open(train_config, "r"), Loader=yaml.FullLoader)
configs = (preprocess_config, model_config, train_config)

class args:
    restore_step = 110000

model = get_model(args(), configs, device="cuda", train=False).cuda()
vocoder = get_vocoder(model_config, device="cuda").cuda()
lexicon = read_lexicon("data/lexicon")

text = "bị kẻ trộm đi nhà lấy đồ hả"
input_batch = text_to_phonemes(text, lexicon)

output = model(
    *input_batch
)

input_batch.insert(0, ["infer"])
synth_samples(
    input_batch,
    output,
    vocoder,
    model_config,
    preprocess_config,
    train_config["path"]["result_path"],
)