from torch.utils.data import DataLoader
import streamlit as st
import numpy as np
import argparse
import shutil
import torch
import yaml
import time
import re

from utils.model import get_model, get_vocoder
from utils.tools import to_device, synth_samples
from text import phoneme_to_ids
from norm.src.processing import run

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
    punct2token = {
        "." : "dot",
        ",": "sp"
    }
    text = text.lower()
    words = re.split(r"([\s+])", text)
    
    phonemes = []
    for word in words:
        if word in lexicon:
            phoneme = lexicon[word]
            phonemes += phoneme
        elif len(word.strip()) == 0:
            continue
        elif word in ",.":
            phonemes.append(punct2token[word])
    
    print("Phoneme: ", phonemes)
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

@st.cache_resource
def init_model(configs):
    class args:
        restore_step = 160000

    model = get_model(args(), configs, device="cuda", train=False).cuda()
    vocoder = get_vocoder(model_config, device="cuda").cuda()
    lexicon = read_lexicon("data/data_new/lexicon")

    return model, vocoder, lexicon

from time import time
if __name__ == "__main__":
    st.title("NLP Demo")

    cfg_path = 'configs/config.yaml'
    preprocess_config = "configs/preprocess.yaml"
    model_config = "configs/model.yaml"
    train_config = "configs/train.yaml"

    preprocess_config = yaml.load(open(preprocess_config, "r"), Loader=yaml.FullLoader)
    model_config = yaml.load(open(model_config, "r"), Loader=yaml.FullLoader)
    train_config = yaml.load(open(train_config, "r"), Loader=yaml.FullLoader)
    configs = (preprocess_config, model_config, train_config)

    model, vocoder, lexicon = init_model(configs)

    text = st.text_input("Enter text")
    if st.button("run"):
        print("Raw Text: ", text)
        text = run(text)
        print("Normalized Text: ", text)

        start = time()
        input_batch = text_to_phonemes(text, lexicon)

        with torch.no_grad():
            output = model(*input_batch)

            input_batch.insert(0, ["infer"])
            synth_samples(
                input_batch,
                output,
                vocoder,
                model_config,
                preprocess_config,
                train_config["path"]["result_path"],
            )
        end = time()
        audio_file = open(f'output/result/infer.wav', "rb")
        audio_bytes = audio_file.read()
        st.markdown(f"## Audio : ")
        st.audio(audio_bytes, format="audio/wav", start_time=0)

        print(end-start)
        