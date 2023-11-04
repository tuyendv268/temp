import soundfile as sf
import numpy as np
import requests
import librosa
import json
import re

from concurrent.futures import ProcessPoolExecutor, as_completed
from flask import Flask, request, jsonify
from underthesea import sent_tokenize
from multiprocessing import Pool
from norm.src.processing import run
from trankit import Pipeline

app = Flask(__name__)
pipline = Pipeline('vietnamese')
def segment_doc(document, max_chunk_size=24, max_num_sent=1):
    chunks = []
    
    # tokenized_doc = sent_tokenize(document)
    tokenized_doc = pipline.tokenize(document)
    tokenized_doc = [sentence["text"] for sentence in tokenized_doc["sentences"]]

    current_sent = tokenized_doc[0]
    current_length, current_num_sent = len(current_sent.split()), 1
    for sent in tokenized_doc[1:]:
        temp = f'{current_sent} {sent}'
        
        if len(temp.split()) > max_chunk_size or current_num_sent >= max_num_sent:
            chunks.append(current_sent)
            
            current_sent = sent
            current_length = len(sent.split())
            current_num_sent = 1
        else:
            current_sent = temp
            current_length += len(temp.split())
        
        current_num_sent += 1
    
    if chunks[-1] != current_sent:
        chunks.append(current_sent)
        
    return chunks

def infer(text):
    text = run(text)
        
    mel = requests.post(
        url='http://127.0.0.1:9090/predictions/encoder',
        json={
            "text": f'{text}'
        }
    )
    
    wav = requests.post(
        url='http://127.0.0.1:9090/predictions/vocoder',
        json={
            "mel": json.dumps(json.loads(mel.content))
        }
    )
    wav = np.array(json.loads(wav.content))[0]
    
    return wav, text

@app.route('/tts', methods=['POST'])
def infer_endpoint():
    text = request.form.get('text')
    text = re.sub("\n", " ", text)
    print("Text: ", text)
    sents = segment_doc(text)
    
    with ProcessPoolExecutor(max_workers=1) as executor:
        futures = (executor.submit(infer, sent) for sent in sents)

        wavs, texts = [], []
        for future in as_completed(futures):
            wav, text = future.result()
            wavs.append(wav)
            texts.append(text)
            
    waveform = np.concatenate(wavs)
    sf.write("output/result/test.wav", waveform, samplerate=22050)
    print("Normlized text: ", " \n ".join(texts))
    return {
        "sample_rate": 22050,
        "wav": waveform.tolist()
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=6868)