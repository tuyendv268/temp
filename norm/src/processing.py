import os
import re
import sys
sys.path.append("..")
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool
from nltk import sent_tokenize
from norm.utils.abbre import ABBRE
from norm.src.nomalizer import TextNormalizer

def normalize(text):
    normalizer = TextNormalizer()
    
    text = text.replace(': ', ' , ')
    text = text.replace('; ', ' . ')
    text = normalizer.remove_urls(text)
    text = normalizer.remove_emoji(text)
    # text = normalizer.remove_emoticons(text)
    # print(f'1: {text}')
    text = normalizer.remove_special_characters_v1(text)
    # print(f'2: {text}')
    text = normalizer.norm_abbre(text, ABBRE)
    # print(f'3: {text}')
    text = normalizer.normalize_number_plate(text)
    # text = normalizer.norm_punct(text)
    # print(f'4: {text}')
    text = normalizer.norm_tag_measure(text)
    # print(f'5: {text}')
    text = normalizer.normalize_rate(text)
    # print(f'6: {text}')
    text = normalizer.norm_adress(text)
    # print(f'7: {text}')
    text = normalizer.norm_tag_fraction(text)
    # print(f'8: {text}')
    text = normalizer.normalize_phone_number(text)
    # print(f'9: {text}')
    text = normalizer.norm_multiply_number(text)
    # print(f'10: {text}')
    text = normalizer.normalize_sport_score(text)
    # print(f'11: {text}')
    text = normalizer.normalize_date_range(text)
    # print(f'12: {text}')
    text = normalizer.normalize_date(text)
    # print(f'13: {text}')
    text = normalizer.normalize_time(text)
    # print(f'14: {text}')
    text = normalizer.normalize_number_range(text)
    # print(f'15: {text}')
    text = normalizer.norm_id_digit(text)
    # print(f'16: {text}')
    text = normalizer.norm_soccer(text)
    # print(f'17: {text}')
    text = normalizer.norm_tag_roman_num(text)
    # print(f'18: {text}')
    text = normalizer.normalize_AZ09(text)
    # print(f'19: {text}')
    text = normalizer.norm_math_characters(text)
    # print(f'20: {text}')
    text = normalizer.norm_tag_verbatim(text)
    # print(f'21: {text}')
    text = normalizer.normalize_negative_number(text) 
    # print(f'22: {text}')
    text = normalizer.normalize_number(text)
    # print(f'23: {text}')
    # text = normalizer.norm_account_name(text)
    # text = normalizer.normalize_letters(text)
    try:
        text = normalizer.norm_vnmese_accent(text)
    except:
        pass
    text = text.replace('/', ' trên ')
    text = normalizer.remove_special_characters_v2(text)
    text = normalizer.norm_tag_roman_num(text)
    text = normalizer.remove_multi_space(text)
    text = normalizer.normalize_number(text)

    text = normalizer.lowercase(text)
    text = text.replace('.', ' . ')
    text = text.replace('?', ' . ')
    text = text.replace('!', ' . ')
    text = text.replace(',', ' , ')
    text = normalizer.norm_duplicate_word(text)
    return text

def post_processing(text):
    text = re.sub('\s+', ' ', text)
    text = re.sub('\.\.\s', '. ', text)
    text  = text.lower()
    return text
    
def run(text):
    norm_text = []
    for sentence in sent_tokenize(text):
        sentence = normalize(sentence)
        norm_text.append(sentence)
    text = '. '.join(norm_text)
    text = post_processing(text)
    return text