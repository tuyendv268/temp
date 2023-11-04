from text.symbols import symbols

_symbol_to_id = {s: i for i, s in enumerate(symbols)}
_id_to_symbol = {i: s for i, s in enumerate(symbols)}


def phoneme_to_ids(text):
    phoneme = text.strip("{").strip("}")
    # phonemes = " spc ".join(phoneme.split()).split()
    phonemes = phoneme.split()
    phoneme_ids = [_symbol_to_id[s] for s in phonemes]
    
    return phoneme_ids

def ids_to_phoneme(ids):
    phoneme_to_ids = []
    
    for _id in ids:
        phoneme_to_ids.append(_id_to_symbol[_id])
    
    return " ".join(phoneme_to_ids)